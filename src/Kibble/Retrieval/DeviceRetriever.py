"""
Defines a device retriever
"""

from typing import Optional
from pymongo import MongoClient
from bson import ObjectId  
from Kibble.Logging.EventSchema import device_types, EVENT_SCHEMA_VERSION

DEVICES_COLLECTION = "devices"
DEVICE_TYPES_COLLECTION = "device_types"

class DeviceRetriever:
    def __init__(self, db_name: str, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password', client: MongoClient=None):
        """
        Initializes a device retriever getting devices and device types from MongoDB
        
        :param db_name: the MongoDB database to use
        :param host: the host of the MongoDB server
        :param port: the port of the MongoDB server
        :param user: the username of the MongoDB server
        :param passwd: the password of the MongoDB server
        :param client: the client to use instead of creating a new one
        """
        if client is None:
            self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")
            self.client.admin.command('ping')  # can raise ConnectionFailure
        else:
            self.client = client
        
        self.db = self.client[db_name]

        if DEVICES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICES_COLLECTION)
        self.devices_collection = self.db[DEVICES_COLLECTION]

        if DEVICE_TYPES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICE_TYPES_COLLECTION)
        self.device_types_collection = self.db[DEVICE_TYPES_COLLECTION]

    def get_device_id(self, endpoint_ip: str) -> Optional[ObjectId]:
        doc = self.devices_collection.find_one({"device_ip": endpoint_ip}, {"_id": 1})
        return doc["_id"] if doc else None

    def get_device_ids(self, endpoint_ips: list[str]) -> dict[str, ObjectId]:
        """Return mapping of device_ip -> _id for all IPs present in the devices collection (one query)."""
        if not endpoint_ips:
            return {}
        cursor = self.devices_collection.find(
            {"device_ip": {"$in": endpoint_ips}},
            {"_id": 1, "device_ip": 1},
        )
        return {doc["device_ip"]: doc["_id"] for doc in cursor}
    
    def ensure_device_type(self, name: str, protocols_supported: list[str]) -> ObjectId:
        existing = self.device_types_collection.find_one({"name": name})
        if existing:
            return existing["_id"]
        doc = device_types(name, protocols_supported)
        ret = self.device_types_collection.insert_one(doc)
        return ret.inserted_id

    def close(self):
        self.client.close()
