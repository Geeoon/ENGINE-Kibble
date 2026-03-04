"""
Overall system implementation
"""

import logging
import time
import asyncio
from typing import Optional

from pymongo import MongoClient

from Kibble.Logging import LogLevel, ICMP
from Kibble.Logging.EventSchema import device_info
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector
from Kibble.Retrieval import DeviceRetriever


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
            self._last_device_log_time = time.time()

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
                logs.append(ICMP(this_status, level, device_id=key))
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
            if id not in self.devices.keys():
                self.maintainance_logger.info(f"Found new device: {id}")
                self.devices[id] = {}
            if not device['device_type']:
                self.maintainance_logger.error(f"No corresponding device type found for {id}")
                continue

            new_device = {
                'ip': device.get('device_ip', None),
                'hostname': device.get('hostname', None),
                'mac': device.get('mac_address', None),
                'protocols': list({proto for protocol in device.get('device_type', []) for proto in protocol.get('protocols_supported', [])}),
            }

            if self.devices[id] != new_device:
                self.maintainance_logger.info(f"Updating device information for {id}")
                self.devices[id] = new_device
        
        for id, device in self.devices.items():
            for protocol in device['protocols']:
                found = False
                for monitor in self.monitors:
                    if protocol == str(monitor):
                        monitor.add_endpoint(additional=[device | {'id': id}])
                        found = True
                if not found:  # no monitor found for this protocol
                    self.maintainance_logger.error(f"{id} attempting to use unsupported protocol {protocol}")

    # deprecated
    def _log_devices(self):
        devices: list[dict] = []
        for monitor in self.monitors:
            for endpoint_ip, status_data in monitor.get_status().items():
                if status_data is None:
                    continue
                
                # getting the device type for each endpoint
                meta = self.device_unique_ids["index"].get(endpoint_ip)
                dtype_id = (
                    meta.get("device_type_id") if meta and meta.get("device_type_id") else self.default_device_type_id
                )

                devices.append(device_info(dtype_id, endpoint_ip, status_data))

        if not devices:
            return

        for doc in devices:
            device_ip = doc.get("device_ip")
            if device_ip is None:
                continue
            # no longer using logger.log_device_many, using direct DB writes
            self.devices_collection.update_one(
                {"device_ip": device_ip},
                {"$set": doc},
                upsert=True,
            )

        # Refresh caches after upserting devices so the next run can use the updated device info (if any chnages0
        self._get_devices() 

    def _end(self, msg: str=""):
        self.maintainance_logger.debug(msg)
