# Main python script
import datetime
import logging
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

screen_alert = ScreenAlert()
email_alert = EmailAlert()

# latency configuration
parser = argparse.ArgumentParser()
parser.add_argument("--low-thresh", type=int)
parser.add_argument("--medium-thresh", type=int)
parser.add_argument("--high-thresh", type=int)
args = parser.parse_args()

config = {}
try:
    with open("../kibble.yaml") as f:
        data = yaml.safe_load(f) or {}
        config = data.get("latency_thresholds", {})
except FileNotFoundError:
    pass

detector = LatencyDetector(
    low_thresh=args.low_thresh or config.get("low_thresh", 500),
    medium_thresh=args.medium_thresh or config.get("medium_thresh", 1000),
    high_thresh=args.high_thresh or config.get("high_thresh", 2000),
)

icmp_monitor = ICMPMonitor(timeout=5)
scpi_monitor = SCPIMonitor(timeout=5)
snmp_monitor = SNMPMonitor(timeout=5, community='public')
daemon_monitor = DaemonMonitor(timeout=5)
try:
    kibble = Kibble(client=mongo_client, monitors=[icmp_monitor, scpi_monitor, daemon_monitor, snmp_monitor], alerters=[screen_alert], detector=detector, default_device_type=("device 1", ["ICMP"]))
except Exception as e:
    maintainance_logger.critical(f"Failed to start Kibble: {str(e)}")
    quit()

# testing only: add devices to db, if they don't exist, for testing.
# Keep devices identity-only (asset_tag + device_type_id). Network identity is stored in configuration collections.
if False:
    scpi_id = kibble.device_retriever.ensure_device_type('device 2', ['SCPI'])
    test_devices = [
        {'asset_tag': 1001, 'device_type_id': kibble.default_device_type_id, 'ip': '127.0.0.1', 'hostname': '', 'mac': ''},
        {'asset_tag': 1002, 'device_type_id': kibble.default_device_type_id, 'ip': '', 'hostname': 'doesnotexist.internal', 'mac': ''},
        {'asset_tag': 1003, 'device_type_id': kibble.default_device_type_id, 'ip': '192.67.67.67', 'hostname': '', 'mac': ''},
    ]
    for id in range(1, 6):
        test_devices.append(
            {
                'asset_tag': 2000 + id,
                'device_type_id': kibble.default_device_type_id,
                'ip': '',
                'hostname': f'simulator-secondary-{id}',
                'mac': '',
            }
        )
        test_devices.append(
            {
                'asset_tag': 3000 + id,
                'device_type_id': scpi_id,
                'ip': '',
                'hostname': f'simulator-scpi-{id}',
                'mac': '',
            }
        )

    db = mongo_status_handler.db
    for test_device in test_devices:
        db['devices'].update_one(
            {'asset_tag': test_device['asset_tag']},
            {
                '$setOnInsert': {
                    'asset_tag': test_device['asset_tag'],
                    'device_type_id': test_device['device_type_id'],
                }
            },
            upsert=True,
        )

    # Initialize one configuration snapshot per seeded device if none exists.
    for test_device in test_devices:
        dev = db['devices'].find_one({'asset_tag': test_device['asset_tag']}, {'_id': 1})
        if dev is None:
            continue
        oid = dev['_id']
        if db['device_configurations'].find_one({'device_id': oid}, projection={'_id': 1}) is not None:
            continue

        applied_date = datetime.datetime.now(datetime.timezone.utc)
        iface_doc = interface_configuration(
            oid,
            'default',
            str(test_device.get('ip') or ''),
            '',
            '',
            str(test_device.get('hostname') or ''),
            str(test_device.get('mac') or ''),
            applied_date,
        )
        iface_id = kibble.device_retriever.insert_interface_configuration(iface_doc)
        doc = device_configuration(oid, [iface_id], applied_date)
        kibble.device_retriever.insert_device_configuration(doc)

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