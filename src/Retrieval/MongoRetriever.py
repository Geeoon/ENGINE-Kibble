from __future__ import annotations

import time
from typing import Any, Optional

from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database


class MongoRetriever:
    """
    Retrieval helper for devices.

    {
        "timestamp_ms": timestamp_ms,
        "device_name": status_data.get("name", "Unknown"),
        "device_ip": endpoint_ip,
        "device_status": status_data.get("alive", False),
        "device_latency_ms": status_data.get("latency", 0),
        "device_last_updated_ms": status_data.get("last_updated", timestamp_ms)
    }

    """

    def __init__(
        self,
        db_name: str = "kibble",
        collection_name: str = "devices",
        host: str = "database.internal",
        port: int = 27017,
        user: str = "root",
        passwd: str = "password",
        connect_timeout_ms: int = 3000,
    ) -> None:
        uri = f"mongodb://{user}:{passwd}@{host}:{port}/?authSource={auth_source}"
        self.client = MongoClient(uri, serverSelectionTimeoutMS=connect_timeout_ms)
        # Fail fast if connection/auth is wrong
        self.client.admin.command("ping")

        self.db: Database = self.client[db_name]
        self.col: Collection = self.db[collection_name]

    def get_all_devices(self) -> list[str]:
        return self.col.distinct("device_ip", filter={"device_ip": {"$type": "string"}})

    def ensure_indexes(self) -> None:
        self.col.create_index([("device_ip", ASCENDING), ("timestamp_ms", DESCENDING)], name="idx_device_ip_ts_desc")

    def close(self) -> None:
        self.client.close()
