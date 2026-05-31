"""
Leader election via MongoDB heartbeats.

Every monitoring node writes a heartbeat document to the
monitors collection.  The node with the lowest monitor_id is elected
leader.  Leadership is evaluated every heartbeat cycle, and the next-lowest ID 
takes over automatically.
"""

import datetime
import logging
import socket
from typing import Callable, Optional

from pymongo import MongoClient

MONITORS_COLLECTION = "monitors"


class LeaderElector:
    """Heartbeat-based leader election using MongoDB.

    :client: shared MongoClient instance
    :monitor_id: unique integer identifier for monitoring node
    :heartbeat_ttl: seconds before a heartbeat is considered stale
    :db_name: MongoDB database name
    """

    def __init__(
        self,
        client: MongoClient,
        monitor_id: int,
        heartbeat_ttl: int = 30,
        db_name: str = "kibble",
    ):
        self._logger = logging.getLogger("Kibble_Maintainance")
        self._client = client
        self._db = self._client[db_name]
        self.monitor_id = monitor_id
        self.heartbeat_ttl = heartbeat_ttl

        self._is_leader: bool = False
        self._leader_id: Optional[int] = None
        self._on_leader_change: Optional[Callable[[bool], None]] = None

        self._collection = None
        try:
            self._ensure_collection()
        except Exception as e:
            self._logger.critical(
                f"LeaderElector: unable to initialise monitors collection: {e}"
            )

    # Public API

    @property
    def is_leader(self) -> bool:
        """Whether this monitor is currently the elected leader"""
        return self._is_leader

    @property
    def leader_id(self) -> Optional[int]:
        """The monitor_id of the current leader"""
        return self._leader_id

    def set_on_leader_change(self, callback: Callable[[bool], None]) -> None:
        """Register a callback fired when this node's leadership status changes"""
        self._on_leader_change = callback

    def register(self) -> None:
        """Register (or re-register) this monitor in MongoDB"""
        now = datetime.datetime.now(datetime.timezone.utc)
        doc = {
            "monitor_id": self.monitor_id,
            "hostname": socket.gethostname(),
            "last_heartbeat": now,
            "started_at": now,
        }
        try:
            if self._collection is None:
                self._ensure_collection()
            self._collection.update_one(
                {"monitor_id": self.monitor_id},
                {"$set": doc},
                upsert=True,
            )
            self._logger.info(
                f"LeaderElector: registered monitor {self.monitor_id}"
            )
        except Exception as e:
            self._logger.critical(f"LeaderElector: failed to register: {e}")

    def heartbeat(self) -> None:
        """Update this monitor's heartbeat timestamp"""
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            if self._collection is None:
                self._ensure_collection()
            self._collection.update_one(
                {"monitor_id": self.monitor_id},
                {"$set": {"last_heartbeat": now}},
            )
        except Exception as e:
            self._logger.critical(f"LeaderElector: heartbeat failed: {e}")

    def get_active_monitors(self) -> list[int]:
        """Return sorted list of monitor_id values with new heartbeat"""
        cutoff = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(seconds=self.heartbeat_ttl)
        try:
            if self._collection is None:
                self._ensure_collection()
            cursor = self._collection.find(
                {"last_heartbeat": {"$gte": cutoff}},
                {"monitor_id": 1, "_id": 0},
            ).sort("monitor_id", 1)
            return [doc["monitor_id"] for doc in cursor]
        except Exception as e:
            self._logger.critical(
                f"LeaderElector: failed to query active monitors: {e}"
            )
            return [self.monitor_id]

    def elect_leader(self) -> int:
        """Re-evaluate who the leader is and return the leader's monitor_id"""
        active = self.get_active_monitors()
        if not active:
            active = [self.monitor_id]

        new_leader = active[0]
        was_leader = self._is_leader
        self._leader_id = new_leader
        self._is_leader = new_leader == self.monitor_id

        if was_leader != self._is_leader:
            role = "LEADER" if self._is_leader else "FOLLOWER"
            self._logger.info(
                f"LeaderElector: role changed → {role} "
                f"(leader_id={self._leader_id}, active={active})"
            )
            if self._on_leader_change:
                try:
                    self._on_leader_change(self._is_leader)
                except Exception as e:
                    self._logger.error(
                        f"LeaderElector: on_leader_change callback error: {e}"
                    )

        return self._leader_id

    def deregister(self) -> None:
        """Graceful shutdown"""
        try:
            if self._collection is None:
                self._ensure_collection()
            self._collection.delete_one({"monitor_id": self.monitor_id})
            self._logger.info(
                f"LeaderElector: deregistered monitor {self.monitor_id}"
            )
        except Exception as e:
            self._logger.error(f"LeaderElector: failed to deregister: {e}")

    def _ensure_collection(self) -> None:
        if MONITORS_COLLECTION not in self._db.list_collection_names():
            self._db.create_collection(MONITORS_COLLECTION)
        self._collection = self._db[MONITORS_COLLECTION]
        self._collection.create_index("monitor_id", unique=True)
