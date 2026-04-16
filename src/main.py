# Main python script
import logging
import time
import datetime

from pymongo import MongoClient

from Kibble import Kibble
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
from Kibble.Logging.EventSchema import device_configuration, interface_configuration
from Kibble.Monitoring.Active import ICMPMonitor, SCPIMonitor

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

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
        f"Unable to connect to MongoDB: {str(e)}.  Events will only be maintained locally and the fallback list of devices will be used."
    )

if mongo_client is None:
    maintainance_logger.critical("MongoDB client is not available; exiting.")
    quit()

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

screen_alert = ScreenAlert()  # TODO: replace with logger possibly
email_alert = EmailAlert()

icmp_monitor = ICMPMonitor(endpoints=[], timeout=5)
scpi_monitor = SCPIMonitor(endpoints=[], timeout=5)
try:
    kibble = Kibble(
        client=mongo_client,
        monitors=[icmp_monitor, scpi_monitor],
        alerters=[screen_alert],
        default_device_type=("device 1", ["ICMP"]),
    )
except Exception as e:
    maintainance_logger.critical(f"Failed to start Kibble: {str(e)}")
    quit()

# testing only: add devices to db, if they don't exist, for testing.
# testing only: add scpi device type to db
scpi_id = kibble.device_retriever.ensure_device_type("device 2", ["SCPI"])
mongo_status_handler.db["devices"].update_one(
    {"ip": "127.0.0.1"},
    {
        "$setOnInsert": {
            "device_ip": "127.0.0.1",
            "device_type_id": kibble.default_device_type_id,
        }
    },
    upsert=True,
)
mongo_status_handler.db["devices"].update_one(
    {"hostname": "doesnotexist.internal"},
    {
        "$setOnInsert": {
            "hostname": "doesnotexist.internal",
            "device_type_id": kibble.default_device_type_id,
        }
    },
    upsert=True,
)
mongo_status_handler.db["devices"].update_one(
    {"device_ip": "192.67.67.67"},
    {
        "$setOnInsert": {
            "device_ip": "192.67.67.67",
            "device_type_id": kibble.default_device_type_id,
        }
    },
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
        {
            "$setOnInsert": {
                "hostname": f"simulator-scpi-{id}",
                "device_type_id": scpi_id,
            }
        },
        upsert=True,
    )

# Interface-based device resolution needs initial snapshots for seeded devices.
db = mongo_status_handler.db
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
        maintainance_logger.critical(
            f"Uncaught exception: {str(e)}.  Attemping to restart the service, try {tries}"
        )
        tries += 1
