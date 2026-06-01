"""
Overall system implementation
"""

import asyncio
import logging
import time
from typing import Optional

from pymongo import MongoClient

from Kibble.Logging.EventSchema import TelemetryStructure
from Kibble.Logging import LogLevel, LatencyStructure
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector
from Kibble.Retrieval import DeviceRetriever
from Kibble.Election import LeaderElector, LeaseManager

DEFAULT_MONITOR_INTERFACE_NAME = "default" # set for now, but should be configurable


class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """

    def __init__(
        self,
        client: MongoClient,
        monitors: list[StatusMonitor],
        monitor_id: int = 0,
        heartbeat_ttl: int = 30,
        redundancy_factor: int = 2,
        alerters: list[Alert] | None = None,
        detector: Detector = LatencyDetector(),
        interval: int = 10,
    ):
        """
        Initializes the Kibble system.

        :param client: MongoClient to use for retrieval
        :param monitors: the monitors to use for detecting device status
        :param monitor_id: unique integer ID for this monitoring node (lowest ID wins leader election)
        :param heartbeat_ttl: seconds before a monitor's heartbeat is considered stale
        :param redundancy_factor: target number of monitors per device for lease assignment
        :param alerters: the alerts to use for alerting faults
        :param detector: the detector to use for determining log levels and alerts
        :param interval: how often to check the status of endpoints in seconds
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

        self.monitor_id = monitor_id
        self.monitors = monitors
        self.alerters = alerters or []
        self.detector = detector
        self.interval = interval

        # --- distributed coordination ---
        self.elector = LeaderElector(
            client, monitor_id, heartbeat_ttl=heartbeat_ttl
        )
        self.lease_manager = LeaseManager(
            client, monitor_id, ttl=heartbeat_ttl,
            redundancy_factor=redundancy_factor,
        )
        self.elector.register()

        self.device_retriever = DeviceRetriever(client=client)
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
            # --- distributed coordination ---
            self.elector.heartbeat()
            self.elector.elect_leader()
            self.lease_manager.renew_leases()
            self.lease_manager.cleanup_expired()
            self.lease_manager.acquire_leases(list(self.devices.keys()))

            start_time = time.time()
            asyncio.run(self._rescan())
            logs, levels = self._get_logs()
            end_time = time.time()
            behind = (end_time - start_time) > self.interval

            if behind:
                self.maintainance_logger.warning("Kibble service is lagging behind scanning interval")

            self._send_to_loggers(logs, levels)

            # send alerts if needed — leader only
            alerts = self.detector.get_alerts()
            if self.elector.is_leader:
                for endpoint in alerts.keys():
                    self.maintainance_logger.info(f"Sending alert(s)")
                    for alerter in self.alerters:
                        alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

            # check devices again
            self._get_devices()
            # wait until next interval
            if not behind:
                sleep_time = self.interval - end_time + start_time
                self.maintainance_logger.debug(f"Waiting {round(sleep_time, 1)} seconds before scanning again")
                time.sleep(sleep_time)

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
                if this_status.get("telemetry", None):
                    logs.append(TelemetryStructure(status_data=this_status, severity=level, device_id=key, monitor_id=self.monitor_id))
                else:
                    logs.append(LatencyStructure(status_data=this_status, severity=level, device_id=key, monitor_id=self.monitor_id))
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

    def _get_devices(self):
        try:
            previous = dict(self.devices) # used to track changes in the devices configurations
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
                    self.device_retriever.record_device_configuration_if_changed(
                        device_id,
                        device,
                        default_interface_name=DEFAULT_MONITOR_INTERFACE_NAME,
                    )

                if (
                    previous.get(device_id) != device
                    and not device.get("ip")
                    and not device.get("hostname")
                ):
                    self.maintainance_logger.warning(
                        f"Device {device_id} has no device_configuration snapshot (need ip and/or hostname to monitor)"
                    )
        except Exception as e:
            self.maintainance_logger.critical(f"Failed to get the newest devices: {str(e)}")

        for id, device in self.devices.items():
            for protocol in device['protocols']:
                found = False
                for monitor in self.monitors:
                    if protocol == str(monitor):
                        monitor.add_endpoint(additional=[device | {'id': id}])
                        found = True
                if not found:
                    self.maintainance_logger.error(f"{id} attempting to use unsupported protocol {protocol}")

    def end(self, msg: str=""):
        self.maintainance_logger.debug(msg)
        # graceful shutdown: release leases and deregister from election
        self.lease_manager.release_leases()
        self.elector.deregister()
