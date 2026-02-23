"""
Overall system implementation
"""

import time
import asyncio
from typing import Optional

from bson import ObjectId  

from Kibble.Logging import Logger, LogLevel, ICMP
from Kibble.Logging.EventSchema import device_info
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector

class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """
    def __init__(self, monitors: list[StatusMonitor]=[], loggers: list[Logger]=[], alerters: list[Alert]=[], detector: Detector=LatencyDetector(), interval: int=10, device_log_interval: int=600, default_device_type_id: Optional[ObjectId]=None):
        """
        Initializes the Kibble system

        :param monitors: the monitors to use for tracking the endpoints
        :type monitors: list[StatusMonitor]
        :param loggers: the loggers to use for logging status
        :type loggers: list[Logger]
        :param alerters: the alerts to use for alerting faults
        :type alerters: list[Alert]
        :param detector: the detector to use for determining log levels and alerts
        :type detector: Detector
        :param interval: how often to check the status of endpoints in seconds
        :type interval: int
        :param device_log_interval: how often to log device snapshot in seconds (e.g. 600 = 10 min)
        :type device_log_interval: int
        :param default_device_type_id: MongoDB ObjectId of the device type (from device_types collection); used when a device is not yet in the DB or has no device_type_id
        :type default_device_type_id: Optional[ObjectId]
        """
        assert len(monitors) > 0, "You must have at least 1 monitor"
        assert len(loggers) > 0, "You must have at least 1 logger"
        for monitor in monitors:
            assert interval > monitor._timeout, "Status interval must be greater than all monitor timeouts"
        self.monitors = monitors
        self.loggers = loggers
        self.alerters = alerters
        self.detector = detector
        self.interval = interval
        self.device_log_interval = device_log_interval
        self.default_device_type_id = default_device_type_id
        self._last_device_log_time: float = 0.0

    #TODO: Add correlation_id to the events so that we can tie all events from one "run" or one alert cycle together and see in db 
    def run(self):
        """
        Starts the Kibble system
        """
        try:
            # Ensure devices exist before first event batch so device_id is always set (time series metaField).
            asyncio.run(self._rescan())
            self._log_devices()
            self._last_device_log_time = time.time()
            #TODO: Edge case where device is added after first scan but before first event batch.

            while True:
                start_time = time.time()
                asyncio.run(self._rescan())
                logs, levels = self._get_logs()
                end_time = time.time()
                behind = end_time - start_time > self.interval
                
                self._send_to_loggers(logs, levels, behind)

                # log device snapshot at a less frequent interval
                if (end_time - self._last_device_log_time) >= self.device_log_interval:
                    self._log_devices()
                    self._last_device_log_time = end_time

                # send alerts if needed
                alerts = self.detector.get_alerts()
                for endpoint in alerts.keys():
                    for alerter in self.alerters:
                        alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

                # wait until next interval
                if not behind:
                    time.sleep(self.interval - end_time + start_time)
        except KeyboardInterrupt:
            self._end("user ended (KeyboardInterrupt)")
        except Exception as e:
            self._end(str(e))
            raise e

    async def _rescan(self):
        await asyncio.gather(*[monitor.update_status() for monitor in self.monitors])

    def _get_logs(self):
        logs: list[dict] = []
        levels: list[LogLevel] = []
        device_id_logger = next(
            (lg for lg in self.loggers if hasattr(lg, "_get_device_ids")), None
        )
        # Collect (endpoint_ip, status_data) for all endpoints that have been scanned
        entries: list[tuple[str, dict]] = []
        for monitor in self.monitors:
            res = monitor.get_status()
            for key, log in res.items():
                if not log:
                    continue
                entries.append((key, log))
        # One batch lookup for all device IDs (using $in) instead of per-endpoint queries
        endpoint_ips = [key for key, _ in entries]
        device_ids = (
            device_id_logger._get_device_ids(endpoint_ips) if device_id_logger else {}
        )
        for key, log in entries:
            level = self.detector.get_level(key, log)
            device_id = device_ids.get(key)
            logs.append(ICMP(log, level, device_id=device_id))
            levels.append(level)
        return logs, levels

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel], behind: bool):
        for logger in self.loggers:
            try:
                logger.log_many(logs, levels)
                if behind:
                    logger.log({"msg": "Kibble did not meet the status interval requirement!"}, LogLevel.DEBUG)
            except ValueError:
                # e.g. data/levels length mismatch; skip this logger and continue
                pass

    def _log_devices(self):
        devices: list[dict] = []
        for monitor in self.monitors:
            for endpoint_ip, status_data in monitor.get_status().items():
                if status_data is None:
                    continue
                devices.append(device_info(self.default_device_type_id, endpoint_ip, status_data))
        if not devices:
            return
        for logger in self.loggers:
            if hasattr(logger, "log_device_many"):
                logger.log_device_many(devices)

    def _end(self, msg: str=""):
        for logger in self.loggers:
            logger.log({"msg": f"Kibble shutting down: {msg}"})
            logger.close()
