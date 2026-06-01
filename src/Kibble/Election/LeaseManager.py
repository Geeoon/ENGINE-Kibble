"""
Lease-based device assignment for distributed monitoring.

Each monitoring node acquires time-limited leases on the devices it is
responsible for.  Leases are stored in a ``device_leases`` MongoDB
collection with a TTL.  If a monitor goes down and its leases expire,
other monitors can pick up those devices so that every device always has
up to ``redundancy_factor`` monitors watching it.
"""

import datetime
import logging
from typing import Optional

from bson import ObjectId  # type: ignore[import-untyped]
from pymongo import MongoClient

DEVICE_LEASES_COLLECTION = "device_leases"


class LeaseManager:
    """Manages per-device lease assignments in MongoDB.

    :param client: shared ``MongoClient`` instance
    :param monitor_id: unique integer identifier for *this* monitoring node
    :param ttl: lease duration in seconds before expiry
    :param redundancy_factor: max number of monitors that should hold a
        lease for any single device
    :param db_name: MongoDB database name
    """

    def __init__(
        self,
        client: MongoClient,
        monitor_id: int,
        ttl: int = 30,
        redundancy_factor: int = 2,
        db_name: str = "kibble",
    ):
        self._logger = logging.getLogger("Kibble_Maintainance")
        self._client = client
        self._db = self._client[db_name]
        self.monitor_id = monitor_id
        self.ttl = ttl
        self.redundancy_factor = redundancy_factor

        self._collection = None
        try:
            self._ensure_collection()
        except Exception as e:
            self._logger.critical(
                f"LeaseManager: unable to initialise device_leases collection: {e}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire_leases(self, device_ids: list) -> list:
        """Attempt to acquire leases for devices that need more monitors.

        For each device in *device_ids*, if the device currently has fewer
        than ``redundancy_factor`` active leases **and** this monitor does
        not already hold a lease for it, atomically insert a new lease.

        :param device_ids: list of device identifiers (``ObjectId`` or ``str``)
        :return: list of device IDs for which a new lease was acquired
        """
        acquired = []
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(seconds=self.ttl)

        try:
            if self._collection is None:
                self._ensure_collection()

            for device_id in device_ids:
                did = self._to_key(device_id)

                # How many active leases does this device currently have?
                active_count = self._collection.count_documents(
                    {"device_id": did, "expires_at": {"$gt": now}}
                )
                if active_count >= self.redundancy_factor:
                    continue

                # Do we already hold one (even if expired)?
                existing = self._collection.find_one(
                    {"device_id": did, "monitor_id": self.monitor_id}
                )
                if existing and existing.get("expires_at", now) > now:
                    # We already have an active lease - skip.
                    continue

                # Atomic upsert: insert only if we don't already have one
                self._collection.update_one(
                    {"device_id": did, "monitor_id": self.monitor_id},
                    {
                        "$set": {
                            "acquired_at": now,
                            "expires_at": expires,
                        },
                        "$setOnInsert": {
                            "device_id": did,
                            "monitor_id": self.monitor_id,
                        },
                    },
                    upsert=True,
                )
                acquired.append(device_id)

            if acquired:
                self._logger.info(
                    f"LeaseManager: acquired leases for {len(acquired)} device(s)"
                )
        except Exception as e:
            self._logger.critical(f"LeaseManager: acquire_leases failed: {e}")

        return acquired

    def renew_leases(self) -> int:
        """Extend ``expires_at`` for all leases held by this monitor.

        :return: number of leases renewed
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(seconds=self.ttl)

        try:
            if self._collection is None:
                self._ensure_collection()

            result = self._collection.update_many(
                {"monitor_id": self.monitor_id, "expires_at": {"$gt": now}},
                {"$set": {"expires_at": expires}},
            )
            count = result.modified_count
            self._logger.debug(f"LeaseManager: renewed {count} lease(s)")
            return count
        except Exception as e:
            self._logger.critical(f"LeaseManager: renew_leases failed: {e}")
            return 0

    def release_leases(self) -> int:
        """Delete all leases held by this monitor (graceful shutdown).

        :return: number of leases released
        """
        try:
            if self._collection is None:
                self._ensure_collection()

            result = self._collection.delete_many(
                {"monitor_id": self.monitor_id}
            )
            count = result.deleted_count
            self._logger.info(f"LeaseManager: released {count} lease(s)")
            return count
        except Exception as e:
            self._logger.critical(f"LeaseManager: release_leases failed: {e}")
            return 0

    def get_my_devices(self) -> list:
        """Return device IDs for which this monitor holds an active lease."""
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            if self._collection is None:
                self._ensure_collection()
            cursor = self._collection.find(
                {"monitor_id": self.monitor_id, "expires_at": {"$gt": now}},
                {"device_id": 1, "_id": 0},
            )
            return [doc["device_id"] for doc in cursor]
        except Exception as e:
            self._logger.critical(f"LeaseManager: get_my_devices failed: {e}")
            return []

    def cleanup_expired(self) -> int:
        """Remove all expired leases from the collection.

        :return: number of expired leases removed
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            if self._collection is None:
                self._ensure_collection()
            result = self._collection.delete_many(
                {"expires_at": {"$lte": now}}
            )
            count = result.deleted_count
            if count:
                self._logger.info(
                    f"LeaseManager: cleaned up {count} expired lease(s)"
                )
            return count
        except Exception as e:
            self._logger.critical(
                f"LeaseManager: cleanup_expired failed: {e}"
            )
            return 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        if DEVICE_LEASES_COLLECTION not in self._db.list_collection_names():
            self._db.create_collection(DEVICE_LEASES_COLLECTION)
        self._collection = self._db[DEVICE_LEASES_COLLECTION]
        # Unique compound index: one lease per (device, monitor) pair.
        self._collection.create_index(
            [("device_id", 1), ("monitor_id", 1)], unique=True
        )
        # Index for efficient expiry queries.
        self._collection.create_index("expires_at")

    @staticmethod
    def _to_key(device_id):
        """Normalise device_id to a string for consistent storage."""
        if isinstance(device_id, ObjectId):
            return str(device_id)
        return device_id
