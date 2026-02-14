"""
MongoLogger derived class from Logger
TODO: discuss to async or not
"""
import datetime
import time
from typing import Optional

from pymongo import MongoClient

from bson import ObjectId  # type: ignore[import-untyped]

from Kibble.Logging import Logger, LogLevel
from Kibble.Logging.EventSchema import device_types

EVENTS_COLLECTION = "timeseries_events"
DEVICES_COLLECTION = "devices"
DEVICE_TYPES_COLLECTION = "device_types"


class MongoLogger(Logger):
    """
    Class for logging events/data to the MongoDB.
    Events go to a time series collection; devices use a normal collection.
    """
    def __init__(self, db_name: str, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password'):
        self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")
        self.client.admin.command('ping')  # can raise ConnectionFailure
        self.db = self.client[db_name]

        # Time series collection
        time_series_options = {
            "timeField": "timestamp",
            "metaField": "endpoint",
            "granularity": "seconds",
        }
        if EVENTS_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(EVENTS_COLLECTION, timeseries=time_series_options)
        self.events_collection = self.db[EVENTS_COLLECTION]

        if DEVICES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICES_COLLECTION)
        self.devices_collection = self.db[DEVICES_COLLECTION]

        if DEVICE_TYPES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICE_TYPES_COLLECTION)
        self.device_types_collection = self.db[DEVICE_TYPES_COLLECTION]

    # returns the unique id of the device
    def get_device_id(self, endpoint_ip: str) -> Optional[ObjectId]:
        doc = self.devices_collection.find_one({"device_ip": endpoint_ip}, {"_id": 1})
        return doc["_id"] if doc else None

    # returns the _id of the device type
    def ensure_device_type(self, name: str, protocols_supported: list[str]) -> ObjectId:
        existing = self.device_types_collection.find_one({"name": name})
        if existing:
            return existing["_id"]
        doc = device_types(name, protocols_supported)
        ret = self.device_types_collection.insert_one(doc)
        return ret.inserted_id

    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        # Time series collection requires a BSON UTC datetime in "timestamp"
        if "timestamp" not in data:
            data = {"timestamp": datetime.datetime.now(datetime.timezone.utc), **data}
        ret = self.events_collection.insert_one(data)
        return ret.inserted_id is not None

    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        assert len(data) == len(levels), "Data length and levels length are not the same"
        # Event docs already have "severity" (string) from the schema; do not add numeric "level"
        ret = self.events_collection.insert_many(data)
        return bool(ret.inserted_ids)
    
    
    def log_device(self, data: dict) -> bool:
        ret = self.devices_collection.insert_one(data)
        return True if ret.inserted_id else False

    def log_device_many(self, data: list[dict]) -> bool:
        for doc in data:
            device_ip = doc.get("device_ip")
            if device_ip is None:
                continue
            self.devices_collection.update_one(
                {"device_ip": device_ip},
                {"$set": doc},
                upsert=True,
            )
        return True

    def close(self):
        self.client.close()

