"""
MongoLogger derived class from Logger
NOTE: this has been depricated
"""
import datetime
from typing import Optional

from pymongo import MongoClient  

from bson import ObjectId  

from Kibble.Logging import Logger, LogLevel
from Kibble.Logging.EventSchema import device_types, EVENT_SCHEMA_VERSION
from Kibble.Retrieval.DeviceRetriever import INTERFACE_CONFIGURATIONS_COLLECTION

EVENTS_COLLECTION = "timeseries_events"
DEVICES_COLLECTION = "devices"
DEVICE_TYPES_COLLECTION = "device_types"


class MongoLogger(Logger):
    """
    Class for logging events/data to the MongoDB.
    Events go to a time series collection; devices use a normal collection.
    """
    #TODO: Use retryWrite in MongoClient options in case initial connection fails.
    def __init__(self, db_name: str, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password'):
        self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")
        self.client.admin.command('ping')  # can raise ConnectionFailure
        self.db = self.client[db_name]

        # Time series collection
        time_series_options = {
            "timeField": "timestamp",
            "metaField": "device_id",
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

    def _get_device_id(self, endpoint_ip: str) -> Optional[ObjectId]:
        doc = self.db[INTERFACE_CONFIGURATIONS_COLLECTION].find_one(
            {"ip_address": endpoint_ip},
            sort=[("applied_date", -1)],
            projection={"device_id": 1},
        )
        return doc["device_id"] if doc else None

    def _get_device_ids(self, endpoint_ips: list[str]) -> dict[str, ObjectId]:
        """Map endpoint IP -> device _id using latest interface_configuration rows."""
        if not endpoint_ips:
            return {}
        coll = self.db[INTERFACE_CONFIGURATIONS_COLLECTION]
        out: dict[str, ObjectId] = {}
        for ip in endpoint_ips:
            doc = coll.find_one(
                {"ip_address": ip},
                sort=[("applied_date", -1)],
                projection={"device_id": 1},
            )
            if doc:
                out[ip] = doc["device_id"]
        return out

    def _ensure_device_type(self, name: str, protocols_supported: list[str]) -> ObjectId:
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
        if "schema_version" not in data:
            data = {"schema_version": EVENT_SCHEMA_VERSION, **data}
        ret = self.events_collection.insert_one(data)
        return ret.inserted_id is not None

    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        if len(data) != len(levels):
            raise ValueError("Data length and levels length are not the same")
        # Ensure every event has schema_version for evolution
        for doc in data:
            if "schema_version" not in doc:
                doc["schema_version"] = EVENT_SCHEMA_VERSION
        ret = self.events_collection.insert_many(data)
        return bool(ret.inserted_ids)
    
    
    def log_device(self, data: dict) -> bool:
        ret = self.devices_collection.insert_one(data)
        return True if ret.inserted_id else False

    def log_device_many(self, data: list[dict]) -> bool:
        for doc in data:
            asset_tag = doc.get("asset_tag")
            if asset_tag is None:
                continue
            self.devices_collection.update_one(
                {"asset_tag": asset_tag},
                {"$set": doc},
                upsert=True,
            )
        return True

    def close(self):
        self.client.close()

