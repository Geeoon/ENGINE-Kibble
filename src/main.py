# Main python script

from Kibble import Kibble
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
from Kibble.Monitoring.Active import ICMPMonitor
import logging
import os


mode = os.getenv("KIBBLE_MODE", "docker").strip().lower()
if mode not in {"docker", "hardware", "hybrid"}:
    mode = "docker"

# Read .env to get secondary devices, uses default of 5
docker_secondary_count = max(1, int(os.getenv("DOCKER_SECONDARY_COUNT", "5")))
hardware_ips = []

for ip in os.getenv("HARDWARE_IPS", "").split(","):
    cleaned = ip.strip()
    if cleaned:
        hardware_ips.append(cleaned)

# set up loggers
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

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

# mongodb logging -- Potentially change to env vars
if mode == "hardware":
    mongo_status_handler = MongoHandler('kibble',
        host="localhost",
        port=27017)
else:
    mongo_status_handler = MongoHandler('kibble')
mongo_status_handler.setLevel(logging.NOTSET)

# attach handlers
# status_logger.addHandler(screen_status_handler)  # just for debugging
status_logger.addHandler(file_status_handler)  # keep on disk in case the database goes down
status_logger.addHandler(mongo_status_handler)

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

screen_alert = ScreenAlert()  # TODO: replace with logger possibly
email_alert = EmailAlert()

monitor = ICMPMonitor(endpoints=[], timeout=5)
kibble = Kibble(client=mongo_status_handler.client, monitors=[monitor], alerters=[screen_alert], default_device_type=("device 1", ["ICMP"]))

# add to db for testing
if mode in {"docker", "hybrid"}:
    for i in range(1, docker_secondary_count + 1):
        mongo_status_handler.db['devices'].update_one({"hostname": f"simulator-secondary-{i}"}, { "$setOnInsert": {
            "hostname": f"simulator-secondary-{i}",
            "device_type_id": kibble.default_device_type_id
            } }, upsert=True)

if mode in {"hardware", "hybrid"}:
    for ip in hardware_ips:
        mongo_status_handler.db['devices'].update_one({"device_ip": ip}, { "$setOnInsert": {
            "device_ip": ip,
            "device_type_id": kibble.default_device_type_id
            } }, upsert=True)

kibble._get_devices()

kibble.run()
