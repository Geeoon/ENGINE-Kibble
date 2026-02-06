from __future__ import annotations

import time
from typing import Any, Optional

from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database


class MongoRetriever:
    """
    Retrieval helper for MongoDB events.
    Reads from db='kibble', collection='events' by default.
    """

    def __init__(
        self,
        db_name: str = "kibble",
        collection_name: str = "events",
        host: str = "localhost",
        port: int = 27017,
        user: str = "root",
        passwd: str = "password",
        connect_timeout_ms: int = 3000,
    ) -> None:
        uri = f"mongodb://{user}:{passwd}@{host}:{port}"
        self.client = MongoClient(uri, serverSelectionTimeoutMS=connect_timeout_ms)
        # Fail fast if connection/auth is wrong
        self.client.admin.command("ping")

        self.db: Database = self.client[db_name]
        self.col: Collection = self.db[collection_name]

    # -------------------------
    # Basic retrieval queries
    # -------------------------

    def get_latest_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self.col.find({}).sort("time", DESCENDING).limit(limit))

    def get_failures_since(
        self,
        minutes: int = 30,
        event_type: str = "endpoint_down",
        severity: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        since_ms = int(time.time() * 1000) - minutes * 60 * 1000
        query: dict[str, Any] = {
            "event_type": event_type,
            "time": {"$gte": since_ms},
        }
        if severity is not None:
            query["severity"] = severity

        cursor = self.col.find(query).sort("time", DESCENDING)
        if limit is not None:
            cursor = cursor.limit(limit)
        return list(cursor)

    def get_endpoint_timeline(
        self,
        endpoint_ip: str,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
        limit: int = 500,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"endpoint.ip": endpoint_ip}

        time_clause: dict[str, Any] = {}
        if start_ms is not None:
            time_clause["$gte"] = start_ms
        if end_ms is not None:
            time_clause["$lte"] = end_ms
        if time_clause:
            query["time"] = time_clause

        direction = ASCENDING if ascending else DESCENDING
        return list(self.col.find(query).sort("time", direction).limit(limit))

    def get_latest_per_endpoint(self) -> list[dict[str, Any]]:
        """
        Returns one latest document per endpoint.ip (current-status view).
        """
        pipeline = [
            {"$sort": {"time": -1}},
            {"$group": {"_id": "$endpoint.ip", "latest": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$latest"}},
            {"$sort": {"time": -1}},
        ]
        return list(self.col.aggregate(pipeline))

    def get_last_seen(self, endpoint_ip: str) -> Optional[int]:
        doc = self.col.find_one({"endpoint.ip": endpoint_ip}, sort=[("time", DESCENDING)])
        return None if doc is None else int(doc.get("time"))

    # -------------------------
    # Indexing helpers
    # -------------------------

    def ensure_indexes(self) -> None:
        """
        Create indexes used by retrieval queries.
        Safe to run multiple times.
        """
        self.col.create_index([("time", DESCENDING)], name="idx_time_desc")
        self.col.create_index([("endpoint.ip", ASCENDING), ("time", DESCENDING)], name="idx_endpoint_ip_time_desc")
        self.col.create_index([("event_type", ASCENDING), ("time", DESCENDING)], name="idx_event_type_time_desc")
        self.col.create_index([("severity", ASCENDING), ("time", DESCENDING)], name="idx_severity_time_desc")

    def close(self) -> None:
        self.client.close()
