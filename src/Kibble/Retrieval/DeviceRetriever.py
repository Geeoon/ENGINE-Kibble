"""
Defines a device retriever
"""

import logging
import json
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId  
from Kibble.Logging.EventSchema import device_types, EVENT_SCHEMA_VERSION

DEVICES_COLLECTION = "devices"
DEVICE_TYPES_COLLECTION = "device_types"

class DeviceRetriever:
    def __init__(self, db_name: str='kibble', client: MongoClient=None):
        """
        Initializes a device retriever getting devices and device types from MongoDB
        
        :param db_name: the MongoDB database to use
        :param client: the MongoDB client to use
        """
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.client = client
        self.db = self.client[db_name]
        self._devices = {}

        # pull endpoints from file
        # self.maintainance_logger.info("Adding devices from static files")
        # device_types = []
        # try:
        #     with open('./device_types.json') as f:
        #         device_types = json.load(f)
        # except FileNotFoundError as e:
        #     self.maintainance_logger.critical(f"Unable to open device_types.json: {str(e)}")
        # if device_types:
        #     try:
        #         with open('./devices.json') as f:
        #             devices = json.load(f)
        #     except FileNotFoundError as e:
        #         self.maintainance_logger.critical(f"Unable to open devices.json: {str(e)}")
        #     print(devices)
        #     print(device_types)
        
        try:
            if DEVICES_COLLECTION not in self.db.list_collection_names():
                self.db.create_collection(DEVICES_COLLECTION)
            self.devices_collection = self.db[DEVICES_COLLECTION]

            if DEVICE_TYPES_COLLECTION not in self.db.list_collection_names():
                self.db.create_collection(DEVICE_TYPES_COLLECTION)
            self.device_types_collection = self.db[DEVICE_TYPES_COLLECTION]
        except:
            pass
    
    def ensure_device_type(self, name: str, protocols_supported: list[str]) -> ObjectId:
        existing = self.device_types_collection.find_one({"name": name})
        if existing:
            return existing["_id"]
        doc = device_types(name, protocols_supported)
        ret = self.device_types_collection.insert_one(doc)
        return ret.inserted_id
    
    def get_devices(self):
        self.maintainance_logger.debug("Getting devices from database")

        if self.devices_collection is None:
            raise ValueError("devices_collection must be provided")

        results = self.devices_collection.aggregate([
            # join devices and device type over _id
            {
                "$lookup": {
                    "from": "device_types",
                    "localField": "device_type_id",
                    "foreignField": "_id",
                    "as": "device_type"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "device_ip": 1,
                    "hostname": 1,
                    "mac_address": 1,
                    # "device_type.name": 1,  # is this useful to us?
                    "device_type.protocols_supported": 1
                }
            }
        ])

        # convert results to the dictionary
        for device in results:
            id = str(device['_id'])
            if id not in self._devices.keys():
                self.maintainance_logger.info(f"Found new device: {id}")
                self._devices[id] = {}
            if not device['device_type']:
                self.maintainance_logger.error(f"No corresponding device type found for {id}")
                continue

            new_device = {
                'ip': device.get('device_ip', None),
                'hostname': device.get('hostname', None),
                'mac': device.get('mac_address', None),
                'protocols': list({proto for protocol in device.get('device_type', []) for proto in protocol.get('protocols_supported', [])}),
            }

            if self._devices[id] != new_device:
                self.maintainance_logger.info(f"Updating device information for {id}")
                self._devices[id] = new_device
        return self._devices

    def close(self):
        self.client.close()
