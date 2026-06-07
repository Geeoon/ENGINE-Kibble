# Main python script
import atexit
import datetime
import logging
import signal
import time

from pymongo import MongoClient

from Kibble import Kibble
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
from Kibble.Logging.EventSchema import device_configuration, interface_configuration
from Kibble.Monitoring.Active import ICMPMonitor, SCPIMonitor, SNMPMonitor, DaemonMonitor
from Kibble.Detecting import LatencyDetector
import logging
import argparse
import yaml

# for argument parsing
def positive_int(value):
    n = int(value)  # raises ValueError if not an int
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return n

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# logger for maintainance
maintainance_logger = logging.getLogger("Kibble_Maintainance")
maintainance_logger.setLevel(logging.DEBUG)
maintainance_logger.propagate = True
# screen logging
screen_maintainance_handler = logging.StreamHandler()
screen_maintainance_handler.setLevel(logging.NOTSET)
screen_maintainance_handler.setFormatter(formatter)
# file logging
file_maintainance_handler = logging.FileHandler("./kibble.log")
file_maintainance_handler.setLevel(logging.NOTSET)
file_maintainance_handler.setFormatter(formatter)
# attach loggers
maintainance_logger.addHandler(screen_maintainance_handler)  # just for debugging
maintainance_logger.addHandler(file_maintainance_handler)  # keep a log of the program in case something goes wrong

# set up MongoDB client
mongo_host = 'database.internal'
mongo_port = 27017
mongo_user = 'root'
mongo_passwd = 'password'

try:
    mongo_client = MongoClient(f"mongodb://{mongo_user}:{mongo_passwd}@{mongo_host}:{mongo_port}")
    mongo_client.admin.command('ping')
except Exception as e:
    maintainance_logger.critical(f"Unable to connect to MongoDB: {str(e)}.  Events will only be maintained locally and the fallback list of devices will be used.")

# main logger for status
status_logger = logging.getLogger("Kibble_Status")
status_logger.setLevel(logging.DEBUG)
status_logger.propagate = True
# screen logging
screen_status_handler = logging.StreamHandler()
screen_status_handler.setLevel(logging.NOTSET)
screen_status_handler.setFormatter(formatter)
# file logging
file_status_handler = logging.FileHandler("./kibble_status.log")
file_status_handler.setLevel(logging.NOTSET)
file_status_handler.setFormatter(formatter)
# mongodb logging
mongo_status_handler = MongoHandler(client=mongo_client)
mongo_status_handler.setLevel(logging.NOTSET)
# attach handlers
# status_logger.addHandler(screen_status_handler)  # just for debugging
status_logger.addHandler(file_status_handler)  # keep on disk in case the database goes down
status_logger.addHandler(mongo_status_handler)

# logger for alerts
alert_logger = logging.getLogger("Kibble_Alerts")
status_logger.setLevel(logging.DEBUG)
status_logger.propagate = True
# screen logging
screen_alert_handler = logging.StreamHandler()
screen_alert_handler.setLevel(logging.NOTSET)
screen_alert_handler.setFormatter(formatter)
# file logging
file_alert_handler = logging.FileHandler("./kibble_alerts.log")
file_alert_handler.setLevel(logging.NOTSET)
file_alert_handler.setFormatter(formatter)
# attach handlers
alert_logger.addHandler(screen_alert_handler)
alert_logger.addHandler(file_alert_handler)

# latency configuration
parser = argparse.ArgumentParser()
parser.add_argument("--low-thresh", type=int)
parser.add_argument("--medium-thresh", type=int)
parser.add_argument("--high-thresh", type=int)
parser.add_argument("--monitor-id", type=int, help="Unique integer ID for this monitoring node (lowest ID wins leader election)")
parser.add_argument("--community-string", type=str, help="Community string for SNMP monitor", default='public')
parser.add_argument("--device-timeout", type=positive_int, help="Timeout for the device", default=5)
parser.add_argument("--scan-period", type=positive_int, help="How often to scan the network.  Should be at least double the device timeout", default=60)
parser.add_argument("--threads", type=positive_int, help="The number of threads to launch to do simultaneous device scans.  Should scale with the number of devices.", default=10)
parser.add_argument("--sender-email", type=str, help="The email account to send alerts from", default="kibblealert@gmail.com")
parser.add_argument("--receiver-email", type=str, help="The email accoutn to send alerts to", default="kibblealert@gmail.com")
args = parser.parse_args()

screen_alert = ScreenAlert()
email_alert = EmailAlert(sender_email=args.sender_email, receiver_email=args.receiver_email)

config = {}
election_config = {}
try:
    with open("../kibble.yaml") as f:
        data = yaml.safe_load(f) or {}
        config = data.get("latency_thresholds", {})
        election_config = data.get("election", {})
except FileNotFoundError:
    pass

detector = LatencyDetector(
    low_thresh=args.low_thresh or config.get("low_thresh", 500),
    medium_thresh=args.medium_thresh or config.get("medium_thresh", 1000),
    high_thresh=args.high_thresh or config.get("high_thresh", 2000),
)

# election parameters (CLI overrides YAML)
monitor_id = args.monitor_id if args.monitor_id is not None else election_config.get("monitor_id", 0)
heartbeat_ttl = election_config.get("heartbeat_ttl", 30)
redundancy_factor = election_config.get("redundancy_factor", 2)

icmp_monitor = ICMPMonitor(timeout=args.device_timeout, workers=args.threads)
scpi_monitor = SCPIMonitor(timeout=args.device_timeout, workers=args.threads)
snmp_monitor = SNMPMonitor(timeout=args.device_timeout, community=args.community_string)
daemon_monitor = DaemonMonitor(timeout=args.device_timeout, workers=args.threads)
try:
    kibble = Kibble(
        client=mongo_client,
        monitors=[icmp_monitor, scpi_monitor, daemon_monitor, snmp_monitor],
        monitor_id=monitor_id,
        heartbeat_ttl=heartbeat_ttl,
        redundancy_factor=redundancy_factor,
        alerters=[screen_alert, email_alert],
        detector=detector,
        interval=args.scan_period
    )
except Exception as e:
    maintainance_logger.critical(f"Failed to start Kibble: {str(e)}")
    quit()

maintainance_logger.info(f"Kibble started with monitor_id={monitor_id}, heartbeat_ttl={heartbeat_ttl}s, redundancy_factor={redundancy_factor}")

# --- graceful shutdown ---
def _graceful_shutdown(*_args):
    """Release leases and deregister from election on shutdown."""
    maintainance_logger.info("Graceful shutdown: releasing leases and deregistering...")
    kibble.end("shutting down")

atexit.register(_graceful_shutdown)
signal.signal(signal.SIGTERM, lambda *a: (_graceful_shutdown(), exit(0)))

kibble._get_devices()

tries = 1
last_fail = 0
while tries < 25:
    try:
        kibble.run()
    except KeyboardInterrupt:
        kibble.end("user ended (KeyboardInterrupt)")
        break
    except Exception as e:
        if (time.time() - last_fail) > 300:  # if it's been more than 5 minutes since the last fail
            tries = 1  # reset
        last_fail = time.time()
        maintainance_logger.critical(f"Uncaught exception: {str(e)}.  Attemping to restart the service, try {tries}")
        tries += 1
