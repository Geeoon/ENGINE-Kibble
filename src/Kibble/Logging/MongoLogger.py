"""
MongoLogger derived class from Logger
TODO: discuss to async or not
"""
import time
from pymongo import MongoClient

from Kibble.Logging import Logger, LogLevel

EVENTS_COLLECTION = "timeseries_events"
DEVICES_COLLECTION = "devices"


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

    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        ret = self.events_collection.insert_one(data)
        return ret.inserted_id is not None

    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        assert len(data) == len(levels), "Data length and levels length are not the same"
        for d, l in zip(data, levels):
            self.log(d | {"level": l.value[1]})
        return True
    
    def log_device(self, data: dict) -> bool:
        ret = self.devices_collection.insert_one(data)
        return True if ret.inserted_id else False

    def log_device_many(self, data: list[dict]) -> bool:
        # clear old data and insert the new snapshot each interval.
        self.devices_collection.delete_many({})
        if not data:
            return True
        ret = self.devices_collection.insert_many(data)
        return True if ret.inserted_ids else False

    def close(self):
        self.client.close()

