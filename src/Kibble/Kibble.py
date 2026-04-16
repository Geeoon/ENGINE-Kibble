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

from Kibble.Logging import LogLevel, LatencyStructure
from Kibble.Logging.EventSchema import device_configuration, interface_configuration
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector
from Kibble.Retrieval import DeviceRetriever

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

        self.device_retriever = DeviceRetriever(client=client, db_name="kibble")
        self.default_device_type_id = self.device_retriever.ensure_device_type(
            default_device_type, ["ICMP"]
        )
        # Collections
        self.devices_collection = self.device_retriever.devices_collection

        # devices from the database
        self.devices = {}
        self._get_devices()

    # TODO: Add correlation_id to events so we can tie all events from one run
    # or alert cycle together in the DB.
    def run(self):
        """
        Starts the Kibble system
        """
        asyncio.run(self._rescan())
        self._last_device_log_time = time.time()

        while True:
            start_time = time.time()
            asyncio.run(self._rescan())
            logs, levels = self._get_logs()
            end_time = time.time()
            behind = (end_time - start_time) > self.interval

            if behind:
                self.maintainance_logger.warning(
                    "Kibble service is lagging behind scanning interval"
                )

            self._send_to_loggers(logs, levels)

            # send alerts if needed
            alerts = self.detector.get_alerts()
            for endpoint in alerts.keys():
                self.maintainance_logger.info(f"Sending alert(s)")
                for alerter in self.alerters:
                    alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]["level"])

            # check devices again
            self._get_devices()
            # wait until next interval
            if not behind:
                sleep_time = self.interval - end_time + start_time
                self.maintainance_logger.debug(
                    f"Waiting {round(sleep_time, 1)} seconds before scanning again"
                )
                time.sleep(sleep_time)

    async def _rescan(self):
        self.maintainance_logger.debug("Starting a network scan")
        await asyncio.gather(*[monitor.update_status() for monitor in self.monitors])
        self.maintainance_logger.debug("Finished scanning network")

    @staticmethod
    def _device_id_for_log(key: object) -> ObjectId:
        if isinstance(key, ObjectId):
            return key
        if isinstance(key, str) and ObjectId.is_valid(key):
            return ObjectId(key)
        raise ValueError(f"monitor status key must be a valid ObjectId string, got {key!r}")

    def _get_logs(self) -> tuple[list[dict], list[LogLevel]]:
        logs: list[dict] = []
        levels: list[LogLevel] = []

        for monitor in self.monitors:
            res = monitor.get_status()
            for key, log in res.items():
                this_status = log["status"]
                if not this_status:
                    continue
                level = self.detector.get_level(key, this_status)
                logs.append(
                    LatencyStructure(
                        this_status, level, device_id=self._device_id_for_log(key)
                    )
                )
                levels.append(level)

        return logs, levels

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel]):
        try:
            for log, level in zip(logs, levels):
                self.maintainance_logger.debug("Sending logs")
                self.logger.log(int(level), log, extra={"status": log})
        except ValueError:
            # e.g. data/levels length mismatch; skip this logger and continue
            pass

    def _primary_interface_fields_from_device_configuration(
        self, device_cfg: dict
    ) -> Optional[tuple[str, str, str, str, str]]:
        """Return primary interface fields tuple from one device_configuration snapshot."""
        ids = device_cfg.get("interfaces") or []
        if not ids:
            return None
        rows = self.device_retriever.get_interface_documents_ordered(ids)
        if not rows:
            return None

        primary = next(
            (
                row
                for row in rows
                if row.get("interface_name") == DEFAULT_MONITOR_INTERFACE_NAME
            ),
            rows[0],
        )

        return (
            str(primary.get("ip_address") or ""),
            str(primary.get("hostname") or ""),
            str(primary.get("mac_address") or ""),
            str(primary.get("subnet_mask") or ""),
            str(primary.get("default_gateway") or ""),
        )

    def _record_device_configuration_if_changed(self, id_str: str, new_device: dict) -> None:
        """Insert interface + device_configuration rows when the primary interface identity changed.

        Subnet mask and gateways are not sourced yet; stored as empty strings until a probe exists.
        """
        subnet_mask = ""
        default_gateway = ""
        ip_address = str(new_device.get("ip") or "")
        hostname = str(new_device.get("hostname") or "")
        mac_address = str(new_device.get("mac") or "")
        proposed_primary = (
            ip_address,
            hostname,
            mac_address,
            subnet_mask,
            default_gateway,
        )

        oid = ObjectId(id_str)
        latest = self.device_retriever.get_latest_device_configuration(oid)
        if latest is not None:
            latest_primary = self._primary_interface_fields_from_device_configuration(
                latest
            )
            if latest_primary is not None and latest_primary == proposed_primary:
                return

        applied_date = datetime.datetime.now(datetime.timezone.utc)
        interface_doc = interface_configuration(
            oid,
            DEFAULT_MONITOR_INTERFACE_NAME,
            ip_address,
            subnet_mask,
            default_gateway,
            hostname,
            mac_address,
            applied_date,
        )
        interface_id = self.device_retriever.insert_interface_configuration(interface_doc)
        doc = device_configuration(oid, [interface_id], applied_date)
        self.device_retriever.insert_device_configuration(doc)

    def _get_devices(self):
        self.maintainance_logger.debug("Getting devices from database")

        previous = dict(self.devices)
        self.devices = self.device_retriever.get_devices(
            default_interface_name=DEFAULT_MONITOR_INTERFACE_NAME
        )

        for device_id, device in self.devices.items():
            if previous.get(device_id) != device:
                if previous and device_id not in previous:
                    self.maintainance_logger.info(f"Found new device: {device_id}")
                elif device_id in previous:
                    self.maintainance_logger.info(
                        f"Updating device information for {device_id}"
                    )
                self._record_device_configuration_if_changed(device_id, device)

            if (
                previous.get(device_id) != device
                and not device.get("ip")
                and not device.get("hostname")
            ):
                self.maintainance_logger.warning(
                    f"Device {device_id} has no device_configuration snapshot (need ip and/or hostname to monitor)"
                )

        for id, device in self.devices.items():
            protocols = device.get("protocols") or []
            for protocol in protocols:
                found = False
                for monitor in self.monitors:
                    if protocol == str(monitor):
                        monitor.add_endpoint(additional=[device | {"id": id}])
                        found = True
                if not found:
                    self.maintainance_logger.error(
                        f"{id} attempting to use unsupported protocol {protocol}"
                    )

    def end(self, msg: str = ""):
        self.maintainance_logger.debug(msg)

    def _end(self, msg: str = ""):
        """Backward-compatible alias for ``end``."""
        self.end(msg)
