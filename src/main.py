# Main python script

import datetime

from Kibble import Kibble
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
from Kibble.Logging.EventSchema import device_configuration
from Kibble.Monitoring.Active import ICMPMonitor
import logging

screen_alert = ScreenAlert()
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
# mongodb logging
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

_db = mongo_status_handler.db
_dtype = kibble.default_device_type_id
_retriever = kibble.device_retriever


def _seed_device(asset_tag: int, ip_address: str, hostname: str, mac_address: str = "") -> None:
    """Upsert stable device row (asset_tag + device_type_id) and ensure one initial configuration snapshot."""
    _db["devices"].update_one(
        {"asset_tag": asset_tag},
        {"$setOnInsert": {"device_type_id": _dtype, "asset_tag": asset_tag}},
        upsert=True,
    )
    dev = _db["devices"].find_one({"asset_tag": asset_tag})
    if dev is None:
        raise RuntimeError(f"devices upsert failed for asset_tag={asset_tag}")
    oid = dev["_id"]
    if _db["device_configurations"].find_one({"device_id": oid}, projection={"_id": 1}) is None:
        applied = datetime.datetime.now(datetime.timezone.utc)
        doc = device_configuration(
            oid,
            ip_address,
            "",
            "",
            "",
            hostname,
            mac_address,
            applied,
        )
        _retriever.insert_device_configuration(doc)


# testing only: devices = identity only; network identity lives in device_configurations.
_seed_device(101, "127.0.0.1", "")
_seed_device(102, "", "doesnotexist.internal")
_seed_device(103, "192.67.67.67", "")
for sim_id in range(1, 6):
    _seed_device(200 + sim_id, "", f"simulator-secondary-{sim_id}")

# __init__ ran before seeds; refresh monitors from DB + configs now.
kibble._get_devices()

kibble.run()
