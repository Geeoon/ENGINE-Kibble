import logging
import time
import datetime

from pymongo import MongoClient

from Kibble import Kibble
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
from Kibble.Logging.EventSchema import device_configuration, interface_configuration
from Kibble.Monitoring.Active import ICMPMonitor

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

# logger for maintenance
maintainance_logger = logging.getLogger("Kibble_Maintainance")
maintainance_logger.setLevel(logging.DEBUG)
maintainance_logger.propagate = True
screen_maintainance_handler = logging.StreamHandler()
screen_maintainance_handler.setLevel(logging.NOTSET)
screen_maintainance_handler.setFormatter(formatter)
file_maintainance_handler = logging.FileHandler("./kibble.log")
file_maintainance_handler.setLevel(logging.NOTSET)
file_maintainance_handler.setFormatter(formatter)
maintainance_logger.addHandler(screen_maintainance_handler)  # just for debugging
maintainance_logger.addHandler(file_maintainance_handler)  # keep a log of the program in case something goes wrong

mongo_host = "database.internal"
mongo_port = 27017
mongo_user = "root"
mongo_passwd = "password"
mongo_client = None
try:
    mongo_client = MongoClient(
        f"mongodb://{mongo_user}:{mongo_passwd}@{mongo_host}:{mongo_port}"
    )
    mongo_client.admin.command("ping")
except Exception as e:
    maintainance_logger.critical(
        f"Unable to connect to MongoDB: {str(e)}. Events will not be persisted."
    )
    raise SystemExit(1)

status_logger = logging.getLogger("Kibble_Status")
status_logger.setLevel(logging.DEBUG)
status_logger.propagate = True
screen_status_handler = logging.StreamHandler()
screen_status_handler.setLevel(logging.NOTSET)
screen_status_handler.setFormatter(formatter)
file_status_handler = logging.FileHandler("./kibble_status.log")
file_status_handler.setLevel(logging.NOTSET)
file_status_handler.setFormatter(formatter)
mongo_status_handler = MongoHandler(client=mongo_client)
mongo_status_handler.setLevel(logging.NOTSET)
status_logger.addHandler(file_status_handler)
status_logger.addHandler(mongo_status_handler)

screen_alert = ScreenAlert()
email_alert = EmailAlert()

icmp_monitor = ICMPMonitor(timeout=5)
try:
    kibble = Kibble(
        client=mongo_client,
        monitors=[icmp_monitor],
        alerters=[screen_alert],
        default_device_type=("device 1", ["ICMP"]),
    )
except Exception as e:
    maintainance_logger.critical(f"Failed to start Kibble: {str(e)}")
    raise SystemExit(1)

db = mongo_status_handler.db
# testing only: add devices to db, if they don't exist, for testing.
# testing only: add scpi device type to db
scpi_id = kibble.device_retriever.ensure_device_type("device 2", ["SCPI"])
mongo_status_handler.db["devices"].update_one(
    {"device_ip": "127.0.0.1"},
    {"$setOnInsert": {"device_ip": "127.0.0.1", "device_type_id": kibble.default_device_type_id}},
    upsert=True,
)
mongo_status_handler.db["devices"].update_one(
    {"hostname": "doesnotexist.internal"},
    {"$setOnInsert": {"hostname": "doesnotexist.internal", "device_type_id": kibble.default_device_type_id}},
    upsert=True,
)
mongo_status_handler.db["devices"].update_one(
    {"device_ip": "192.67.67.67"},
    {"$setOnInsert": {"device_ip": "192.67.67.67", "device_type_id": kibble.default_device_type_id}},
    upsert=True,
)
for id in range(1, 6):
    mongo_status_handler.db["devices"].update_one(
        {"hostname": f"simulator-secondary-{id}"},
        {
            "$setOnInsert": {
                "hostname": f"simulator-secondary-{id}",
                "device_type_id": kibble.default_device_type_id,
            }
        },
        upsert=True,
    )
    mongo_status_handler.db["devices"].update_one(
        {"hostname": f"simulator-scpi-{id}"},
        {"$setOnInsert": {"hostname": f"simulator-scpi-{id}", "device_type_id": scpi_id}},
        upsert=True,
    )

# Ensure seeded device rows also have initial interface/device configuration snapshots.
for dev in db["devices"].find({}, {"_id": 1, "device_ip": 1, "hostname": 1, "mac_address": 1}):
    oid = dev["_id"]
    if db["device_configurations"].find_one({"device_id": oid}, projection={"_id": 1}) is not None:
        continue
    applied_date = datetime.datetime.now(datetime.timezone.utc)
    iface_doc = interface_configuration(
        oid,
        "default",
        str(dev.get("device_ip") or ""),
        "",
        "",
        str(dev.get("hostname") or ""),
        str(dev.get("mac_address") or ""),
        applied_date,
    )
    iface_id = kibble.device_retriever.insert_interface_configuration(iface_doc)
    doc = device_configuration(oid, [iface_id], applied_date)
    kibble.device_retriever.insert_device_configuration(doc)

kibble._get_devices()
tries = 1
last_fail = 0.0
while tries < 25:
    try:
        kibble.run()
    except KeyboardInterrupt:
        kibble._end("user ended (KeyboardInterrupt)")
        break
    except Exception as e:
        now = time.time()
        if (now - last_fail) > 300:
            tries = 1
        last_fail = now
        maintainance_logger.critical(
            f"Uncaught exception: {str(e)}. Attempting to restart the service, try {tries}"
        )
        tries += 1
