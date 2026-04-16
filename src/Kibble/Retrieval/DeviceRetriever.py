"""
Defines a device retriever
"""

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

    def get_device_id(self, endpoint_ip: str) -> Optional[ObjectId]:
        """Resolve device ``_id`` from the newest interface row whose ``ip_address`` matches."""
        doc = self.interface_configurations_collection.find_one(
            {"ip_address": endpoint_ip},
            sort=[("applied_date", -1)],
            projection={"device_id": 1},
        )
        return doc["device_id"] if doc else None

    def get_device_id_by_asset_tag(self, asset_tag: int) -> Optional[ObjectId]:
        doc = self.devices_collection.find_one({"asset_tag": asset_tag}, {"_id": 1})
        return doc["_id"] if doc else None

    def get_device_ids(self, endpoint_ips: list[str]) -> dict[str, ObjectId]:
        """Map ``endpoint_ip`` -> device ``_id`` using latest configuration rows."""
        if not endpoint_ips:
            return {}
        out: dict[str, ObjectId] = {}
        for ip in endpoint_ips:
            oid = self.get_device_id(ip)
            if oid is not None:
                out[ip] = oid
        return out

    def ensure_device_type(
        self,
        name_or_spec: Optional[Union[str, tuple[str, list[str]]]],
        protocols_supported: Optional[list[str]] = None,
    ) -> ObjectId:
        """Ensure a device_types row exists. Accepts ``(name, protocols)`` (Kibble default_device_type) or separate name and protocols."""
        if name_or_spec is None:
            name = "default"
            protos = list(protocols_supported) if protocols_supported else ["ICMP"]
        elif isinstance(name_or_spec, tuple):
            name, protos = name_or_spec[0], list(name_or_spec[1])
        else:
            name = name_or_spec
            if protocols_supported is None:
                raise ValueError("protocols_supported is required when name is a str")
            protos = list(protocols_supported)

        existing = self.device_types_collection.find_one({"name": name})
        if existing:
            return existing["_id"]
        doc = device_types(name, protos)
        ret = self.device_types_collection.insert_one(doc)
        return ret.inserted_id

    def insert_device_configuration(self, doc: dict) -> ObjectId:
        """Insert a document from ``EventSchema.device_configuration`` (enforces ``schema_version``)."""
        if doc.get("schema_version") != DEVICE_CONFIGURATION_SCHEMA_VERSION:
            raise ValueError(
                f"device_configuration schema_version must be {DEVICE_CONFIGURATION_SCHEMA_VERSION}, "
                f"got {doc.get('schema_version')!r}; build docs with EventSchema.device_configuration"
            )
        ret = self.device_configurations_collection.insert_one(doc)
        return ret.inserted_id

    def insert_interface_configuration(self, doc: dict) -> ObjectId:
        """Insert a document from ``EventSchema.interface_configuration`` (enforces ``schema_version``)."""
        if doc.get("schema_version") != INTERFACE_CONFIGURATION_SCHEMA_VERSION:
            raise ValueError(
                f"interface_configuration schema_version must be {INTERFACE_CONFIGURATION_SCHEMA_VERSION}, "
                f"got {doc.get('schema_version')!r}; build docs with EventSchema.interface_configuration"
            )
        ret = self.interface_configurations_collection.insert_one(doc)
        return ret.inserted_id

    def get_interface_documents_ordered(self, interface_ids: list[ObjectId]) -> list[dict]:
        """Return interface rows for ``interface_ids``, in the same order as the id list."""
        if not interface_ids:
            return []
        cursor = self.interface_configurations_collection.find({"_id": {"$in": interface_ids}})
        by_id = {d["_id"]: d for d in cursor}
        return [by_id[i] for i in interface_ids if i in by_id]

    def get_latest_device_configuration(self, device_id: ObjectId) -> Optional[dict]:
        """Newest configuration row for this device (by ``applied_date``), or None."""
        return self.device_configurations_collection.find_one(
            {"device_id": device_id},
            sort=[("applied_date", -1)],
        )

    def get_devices(self, default_interface_name: str = "default") -> dict[str, dict]:
        """Return monitor-ready devices keyed by device ``_id`` string.

        Network identity is resolved from the latest ``device_configuration`` and referenced
        ``interface_configurations`` rows; stable device metadata comes from ``devices``.
        """
        results = self.devices_collection.aggregate(
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
                        "device_ip": "$_iface.ip_address",
                        "hostname": "$_iface.hostname",
                        "mac_address": "$_iface.mac_address",
                        "device_type.protocols_supported": 1,
                    }
                },
            ]
        )

        devices: dict[str, dict] = {}
        for device in results:
            if not device.get("device_type"):
                continue
            protocols = list(
                {
                    proto
                    for protocol in device.get("device_type", [])
                    for proto in protocol.get("protocols_supported", [])
                }
            )
            device_id = str(device["_id"])
            devices[device_id] = {
                "ip": device.get("device_ip"),
                "hostname": device.get("hostname"),
                "mac": device.get("mac_address"),
                "protocols": protocols,
            }

        return devices

    def get_device_configuration_history(
        self, device_id: ObjectId, *, limit: int = 100
    ) -> list[dict]:
        """Configuration snapshots for a device, newest ``applied_date`` first."""
        if limit < 1:
            return []
        cursor = self.device_configurations_collection.find(
            {"device_id": device_id},
            sort=[("applied_date", -1)],
            limit=limit,
        )
        return list(cursor)

    def get_interface_configuration_history(
        self, device_id: ObjectId, *, limit: int = 200
    ) -> list[dict]:
        """Interface configuration snapshots for a device, newest ``applied_date`` first."""
        if limit < 1:
            return []
        cursor = self.interface_configurations_collection.find(
            {"device_id": device_id},
            sort=[("applied_date", -1)],
            limit=limit,
        )
        return list(cursor)

    def close(self):
        self.client.close()
