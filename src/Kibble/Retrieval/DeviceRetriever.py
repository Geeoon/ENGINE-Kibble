"""
Defines a device retriever
"""

import json
import logging
from typing import Optional, Union

from bson import ObjectId
from pymongo import MongoClient

from Kibble.Logging.EventSchema import (
    DEVICE_CONFIGURATION_SCHEMA_VERSION,
    INTERFACE_CONFIGURATION_SCHEMA_VERSION,
    device_types,
)

DEVICES_COLLECTION = "devices"
DEVICE_TYPES_COLLECTION = "device_types"
DEVICE_CONFIGURATIONS_COLLECTION = "device_configurations"
INTERFACE_CONFIGURATIONS_COLLECTION = "interface_configurations"


class DeviceRetriever:
    def __init__(self, client: MongoClient, db_name: str = 'kibble'):
        """
        Initializes a device retriever getting devices and device types from MongoDB

        :param db_name: the MongoDB database to use
        :param client: the MongoDB client to use
        """
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.client = client
        self.db = self.client[db_name]
        self._devices = {}

        self.devices_collection = None
        self.device_types_collection = None
        self._fallback_device_id = None
        self.device_configurations_collection = None
        self.interface_configurations_collection = None
       

        try:
            self._create_collections()
        except Exception as e:
            self.maintainance_logger.critical(f"Unable to create the devices and device_types collection: {str(e)}")
            # pull endpoints from file
            self.maintainance_logger.info("Adding devices from files")
            device_types = []
            device_types = []
            try:
                with open('./device_types.json') as f:
                    device_types = json.load(f)
            except FileNotFoundError as e:
                self.maintainance_logger.critical(f"Unable to open device_types.json: {str(e)}")
            if device_types:
                self._fallback_device_id = device_types[0]['_id']
                device_types_dict = dict((d_type['_id'], d_type['protocols_supported']) for d_type in device_types)
                try:
                    with open("./devices.json") as f:
                        devices = json.load(f)
                except FileNotFoundError:
                    self.maintainance_logger.critical("Unable to open devices.json")
                for device in devices:
                    self.maintainance_logger.info(f"Adding device from file: {device['_id']}")
                    self._devices[device['_id']] = {
                        'ip': device.get('device_ip', None),
                        'hostname': device.get('hostname', None),
                        'mac': device.get('mac_address', None),
                        'protocols': device_types_dict[device['device_type_id']],
                    }

    def _create_collections(self):
        if DEVICES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICES_COLLECTION)
        self.devices_collection = self.db[DEVICES_COLLECTION]
        self.devices_collection.create_index([("asset_tag", 1)], unique=True, sparse=True)

        if DEVICE_TYPES_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICE_TYPES_COLLECTION)
        self.device_types_collection = self.db[DEVICE_TYPES_COLLECTION]

        if DEVICE_CONFIGURATIONS_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(DEVICE_CONFIGURATIONS_COLLECTION)
        self.device_configurations_collection = self.db[DEVICE_CONFIGURATIONS_COLLECTION]
        self.device_configurations_collection.create_index(
            [("device_id", 1), ("applied_date", -1)]
        )

        if INTERFACE_CONFIGURATIONS_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(INTERFACE_CONFIGURATIONS_COLLECTION)
        self.interface_configurations_collection = self.db[INTERFACE_CONFIGURATIONS_COLLECTION]
        self.interface_configurations_collection.create_index(
            [("device_id", 1), ("applied_date", -1)]
        )
        self.interface_configurations_collection.create_index(
            [("ip_address", 1), ("applied_date", -1)]
        )

    def ensure_device_type(self, name: str, protocols_supported: list[str]) -> ObjectId:
        try:
            if self.devices_collection is None or self.device_types_collection is None:
                self._create_collections()
            existing = self.device_types_collection.find_one({"name": name})
            if existing:
                return existing["_id"]
            doc = device_types(name, protocols_supported)
            ret = self.device_types_collection.insert_one(doc)
            return ret.inserted_id
        except Exception as e:
            self.maintainance_logger.critical(f"Unable to ensure device type for {name}: {str(e)}")
        return self._fallback_device_id

    def get_devices(self, default_interface_name: str = "default") -> dict[str, dict]:
        self.maintainance_logger.debug("Getting devices from database")

        try:
            if self.devices_collection is None or self.device_types_collection is None:
                self._create_collections()

            results = self.devices_collection.aggregate(
                # join devices and device type over _id
                [
                    {
                        "$lookup": {
                            "from": DEVICE_TYPES_COLLECTION,
                            "localField": "device_type_id",
                            "foreignField": "_id",
                            "as": "device_type",
                        }
                    },
                    {
                        "$lookup": {
                            "from": DEVICE_CONFIGURATIONS_COLLECTION,
                            "let": {"dev_id": "$_id"},
                            "pipeline": [
                                {"$match": {"$expr": {"$eq": ["$device_id", "$$dev_id"]}}},
                                {"$sort": {"applied_date": -1}},
                                {"$limit": 1},
                            ],
                            "as": "latest_config",
                        }
                    },
                    {"$addFields": {"_cfg": {"$arrayElemAt": ["$latest_config", 0]}}},
                    {
                        "$lookup": {
                            "from": INTERFACE_CONFIGURATIONS_COLLECTION,
                            "let": {"iface_ids": {"$ifNull": ["$_cfg.interfaces", []]}},
                            "pipeline": [
                                {"$match": {"$expr": {"$in": ["$_id", "$$iface_ids"]}}},
                            ],
                            "as": "iface_docs",
                        }
                    },
                    {
                        "$addFields": {
                            "_iface": {
                                "$ifNull": [
                                    {
                                        "$arrayElemAt": [
                                            {
                                                "$filter": {
                                                    "input": {"$ifNull": ["$iface_docs", []]},
                                                    "as": "i",
                                                    "cond": {
                                                        "$eq": [
                                                            "$$i.interface_name",
                                                            default_interface_name,
                                                        ]
                                                    },
                                                }
                                            },
                                            0,
                                        ]
                                    },
                                    {"$arrayElemAt": [{"$ifNull": ["$iface_docs", []]}, 0]},
                                ]
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "device_ip": {
                                "$ifNull": [
                                    "$_iface.ip_address",
                                    {"$ifNull": ["$device_ip", "$ip"]},
                                ]
                            },
                            "hostname": {
                                "$ifNull": ["$_iface.hostname", "$hostname"],
                            },
                            "mac_address": {
                                "$ifNull": ["$_iface.mac_address", "$mac_address"],
                            },
                            "device_type.protocols_supported": 1,
                        }
                    },
                ]
            )

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
        except Exception as e:
            self.maintainance_logger.critical(f"Failed to get latest devices from MongoDB: {str(e)}")
        return self._devices

    def insert_device_configuration(self, doc: dict) -> ObjectId:
        """Insert a device configuration"""
        if self.device_configurations_collection is None:
            self._create_collections()
        if doc.get("schema_version") != DEVICE_CONFIGURATION_SCHEMA_VERSION:
            raise ValueError(
                f"device_configuration schema_version must be {DEVICE_CONFIGURATION_SCHEMA_VERSION}, "
                f"got {doc.get('schema_version')!r}; build docs with EventSchema.device_configuration"
            )
        ret = self.device_configurations_collection.insert_one(doc)
        return ret.inserted_id

    def insert_interface_configuration(self, doc: dict) -> ObjectId:
        """Inserts an interface configuration."""
        if self.interface_configurations_collection is None:
            self._create_collections()
        if doc.get("schema_version") != INTERFACE_CONFIGURATION_SCHEMA_VERSION:
            raise ValueError(
                f"interface_configuration schema_version must be {INTERFACE_CONFIGURATION_SCHEMA_VERSION}, "
                f"got {doc.get('schema_version')!r}; build docs with EventSchema.interface_configuration"
            )
        ret = self.interface_configurations_collection.insert_one(doc)
        return ret.inserted_id

    def get_interface_documents_ordered(self, interface_ids: list[ObjectId]) -> list[dict]:
        """Return interface rows for ``interface_ids``, in the same order as the id list."""
        if self.interface_configurations_collection is None:
            self._create_collections()
        if not interface_ids:
            return []
        cursor = self.interface_configurations_collection.find({"_id": {"$in": interface_ids}})
        by_id = {d["_id"]: d for d in cursor}
        return [by_id[i] for i in interface_ids if i in by_id]

    def get_latest_device_configuration(self, device_id: ObjectId) -> Optional[dict]:
        """Newest configuration row for this device (by ``applied_date``), or None."""
        if self.device_configurations_collection is None:
            self._create_collections()
        return self.device_configurations_collection.find_one(
            {"device_id": device_id},
            sort=[("applied_date", -1)],
        )
    def close(self) -> None:
        self.client.close()
