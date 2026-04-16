"""
Overall system implementation
"""

import asyncio
import datetime
import logging
import time
from typing import Optional

from bson import ObjectId
from pymongo import MongoClient

from Kibble.Logging import LogLevel, ICMP
from Kibble.Logging.EventSchema import device_configuration, interface_configuration
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector
from Kibble.Retrieval import (
    DEVICE_CONFIGURATIONS_COLLECTION,
    INTERFACE_CONFIGURATIONS_COLLECTION,
    DeviceRetriever,
)

DEFAULT_MONITOR_INTERFACE_NAME = "default"


class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """

    def __init__(
        self,
        client: MongoClient,
        monitors: list[StatusMonitor],
        alerters: list[Alert] | None = None,
        detector: Detector = LatencyDetector(),
        interval: int = 10,
        default_device_type: Optional[tuple[str, list[str]]] = None,
    ):
        """
        Initializes the Kibble system.

        :param client: MongoClient to use for retrieval
        :param monitors: the monitors to use for detecting device status
        :param alerters: the alerts to use for alerting faults
        :param detector: the detector to use for determining log levels and alerts
        :param interval: how often to check the status of endpoints in seconds
        :param default_device_type: (name, [protocols]) for a default device_type row
        """

        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.logger = logging.getLogger("Kibble_Status")

        self.maintainance_logger.debug("Starting the Kibble service")

        if not monitors:
            raise ValueError("At least one monitor must be used")

        for monitor in monitors:
            if interval <= monitor._timeout:
                raise ValueError(
                    "Status interval must be greater than each monitor's timeout"
                )
            
        self.monitors = monitors
        self.alerters = alerters or []
        self.detector = detector
        self.interval = interval

        self.device_retriever = DeviceRetriever(db_name="kibble", client=client)
        self.default_device_type_id = self.device_retriever.ensure_device_type(default_device_type, ['ICMP']) 

        # Collections
        self.devices_collection = self.device_retriever.devices_collection
        self.device_types_collection = self.device_retriever.device_types_collection
        self.events_collection = self.device_retriever.db["timeseries_events"] # Fix later for constistency with dataretriever 

        # devices from the database
        self.devices = {}
        self._get_devices()

    # TODO: Add correlation_id to events so we can tie all events from one run
    # or alert cycle together in the DB.
    def run(self):
        """
        Starts the Kibble system
        """
        try:
            asyncio.run(self._rescan())

            while True:
                start_time = time.time()
                asyncio.run(self._rescan())
                logs, levels = self._get_logs()
                end_time = time.time()
                behind = (end_time - start_time) > self.interval

                if behind:
                    self.maintainance_logger.warning("Kibble service is lagging behind scanning interval")

                self._send_to_loggers(logs, levels)

                # send alerts if needed
                alerts = self.detector.get_alerts()
                for endpoint in alerts.keys():
                    self.maintainance_logger.info(f"Sending alert(s)")
                    for alerter in self.alerters:
                        alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

                # check devices again
                self._get_devices()
                # wait until next interval
                if not behind:
                    sleep_time = self.interval - end_time + start_time
                    self.maintainance_logger.debug(f"Waiting {round(sleep_time, 1)} seconds until scanning again")
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            self._end("user ended (KeyboardInterrupt)")
        except Exception as e:
            self._end(str(e))
            raise

    async def _rescan(self):
        self.maintainance_logger.debug("Starting a network scan")
        await asyncio.gather(*[monitor.update_status() for monitor in self.monitors])
        self.maintainance_logger.debug("Finished scanning network")

    def _get_logs(self) -> tuple[list[dict], list[LogLevel]]:
        logs: list[dict] = []
        levels: list[LogLevel] = []

        for monitor in self.monitors:
            res = monitor.get_status()
            for key, log in res.items():
                this_status = log['status']
                if not this_status:
                    continue
                level = self.detector.get_level(key, this_status)
                logs.append(ICMP(this_status, level, device_id=ObjectId(key)))
                levels.append(level)

        return logs, levels

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel]):
        try:
            for log, level in zip(logs, levels):
                self.maintainance_logger.debug("Sending logs")
                self.logger.log(int(level), log, extra={ "status": log })
        except ValueError:
            # e.g. data/levels length mismatch; skip this logger and continue
            pass

    @staticmethod
    def _interface_row_fingerprint(iface: dict) -> tuple[str, ...]:
        """Stable tuple for one interface row (excludes schema_version, applied_date, _id, device_id)."""
        return (
            str(iface.get("interface_name") or ""),
            str(iface.get("ip_address") or ""),
            str(iface.get("hostname") or ""),
            str(iface.get("mac_address") or ""),
            str(iface.get("subnet_mask") or ""),
            str(iface.get("default_gateway") or ""),
        )

    def _primary_interface_from_device_configuration(self, device_cfg: dict) -> Optional[dict]:
        ids = device_cfg.get("interfaces") or []
        if not ids:
            return None
        rows = self.device_retriever.get_interface_documents_ordered(ids)
        for row in rows:
            if row.get("interface_name") == DEFAULT_MONITOR_INTERFACE_NAME:
                return row
        return rows[0] if rows else None

    def _record_device_configuration_if_changed(self, id_str: str, new_device: dict) -> None:
        """Insert interface + device_configuration rows when the primary interface identity changed.

        Subnet mask and gateways are not sourced yet; stored as empty strings until a probe exists.
        """
        # TODO: populate from SNMP/agent when available
        subnet_mask = ""
        default_gateway = ""

        ip_address = str(new_device.get("ip") or "")
        hostname = str(new_device.get("hostname") or "")
        mac_address = str(new_device.get("mac") or "")

        oid = ObjectId(id_str)
        proposed_iface = {
            "interface_name": DEFAULT_MONITOR_INTERFACE_NAME,
            "ip_address": ip_address,
            "hostname": hostname,
            "mac_address": mac_address,
            "subnet_mask": subnet_mask,
            "default_gateway": default_gateway,
        }
        proposed = self._interface_row_fingerprint(proposed_iface)

        latest = self.device_retriever.get_latest_device_configuration(oid)
        if latest is not None:
            primary = self._primary_interface_from_device_configuration(latest)
            if primary is not None and self._interface_row_fingerprint(primary) == proposed:
                return

        applied_date = datetime.datetime.now(datetime.timezone.utc)
        iface_doc = interface_configuration(
            oid,
            DEFAULT_MONITOR_INTERFACE_NAME,
            ip_address,
            subnet_mask,
            default_gateway,
            hostname,
            mac_address,
            applied_date,
        )
        iface_id = self.device_retriever.insert_interface_configuration(iface_doc)
        doc = device_configuration(oid, [iface_id], applied_date)
        self.device_retriever.insert_device_configuration(doc)

    def _get_devices(self):
        self.maintainance_logger.debug("Getting devices from database")

        if self.devices_collection is None:
            raise ValueError("devices_collection must be provided")

        # Network fields come only from latest device_configuration; devices hold device_type_id + asset_tag.
        results = self.devices_collection.aggregate(
            [
                {
                    "$lookup": {
                        "from": "device_types",
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
                            {
                                "$match": {
                                    "$expr": {"$eq": ["$device_id", "$$dev_id"]},
                                }
                            },
                            {"$sort": {"applied_date": -1}},
                            {"$limit": 1},
                        ],
                        "as": "latest_config",
                    }
                },
                {
                    "$addFields": {
                        "_cfg": {"$arrayElemAt": ["$latest_config", 0]},
                    }
                },
                {
                    "$lookup": {
                        "from": INTERFACE_CONFIGURATIONS_COLLECTION,
                        "let": {
                            "iface_ids": {"$ifNull": ["$_cfg.interfaces", []]},
                        },
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {"$in": ["$_id", "$$iface_ids"]},
                                }
                            },
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
                                                        DEFAULT_MONITOR_INTERFACE_NAME,
                                                    ]
                                                },
                                            }
                                        },
                                        0,
                                    ]
                                },
                                {"$arrayElemAt": [{"$ifNull": ["$iface_docs", []]}, 0]},
                            ]
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "asset_tag": 1,
                        "device_ip": "$_iface.ip_address",
                        "hostname": "$_iface.hostname",
                        "mac_address": "$_iface.mac_address",
                        "device_type.protocols_supported": 1,
                    }
                },
            ]
        )

        # convert results to the dictionary
        for device in results:
            id = str(device['_id'])
            if not device["device_type"]:
                self.maintainance_logger.error(f"No corresponding device type found for {id}")
                continue

            protocols = list(
                {
                    proto
                    for protocol in device.get("device_type", [])
                    for proto in protocol.get("protocols_supported", [])
                }
            )

            if not device.get("device_ip") and not device.get("hostname"):
                self.maintainance_logger.warning(
                    f"Device {id} has no device_configuration snapshot (need ip and/or hostname to monitor)"
                )
                if id not in self.devices.keys():
                    self.maintainance_logger.info(f"Found new device: {id}")
                self.devices[id] = {
                    "ip": None,
                    "hostname": None,
                    "mac": None,
                    "protocols": protocols,
                }
                continue

            if id not in self.devices.keys():
                self.maintainance_logger.info(f"Found new device: {id}")
                self.devices[id] = {}

            new_device = {
                "ip": device.get("device_ip", None),
                "hostname": device.get("hostname", None),
                "mac": device.get("mac_address", None),
                "protocols": protocols,
            }

            if self.devices[id] != new_device:
                self.maintainance_logger.info(f"Updating device information for {id}")
                self._record_device_configuration_if_changed(id, new_device)
                self.devices[id] = new_device

        for id, device in self.devices.items():
            if not device.get("ip") and not device.get("hostname"):
                continue
            protocols = device.get("protocols")
            if not protocols:
                continue
            for protocol in protocols:
                found = False
                for monitor in self.monitors:
                    if protocol == str(monitor):
                        monitor.add_endpoint(additional=[device | {'id': id}])
                        found = True
                if not found:  # no monitor found for this protocol
                    self.maintainance_logger.error(f"{id} attempting to use unsupported protocol {protocol}")

    def _end(self, msg: str=""):
        self.maintainance_logger.debug(msg)
