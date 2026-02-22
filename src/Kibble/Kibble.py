"""
Overall system implementation
"""

import logging
import time
import asyncio

from Kibble.Logging import LogLevel, ping_event
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector

class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """
    def __init__(self, monitors: list[StatusMonitor]=[], alerters: list[Alert]=[], detector: Detector=LatencyDetector(), interval: int=10):
        """
        Initializes the Kibble system
        
        :param monitors: the monitors to use for tracking the endpoints
        :type monitors: list[StatusMonitor]
        :param alerters: the alerts to use for alerting faults
        :type alerters: list[Alert]
        :param detector: the detector to use for determining log levels and alerts
        :type detector: Detector
        :param interval: how often to check the status of endpoints in seconds
        :type interval: int
        """
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.logger = logging.getLogger("Kibble_Status")

        self.maintainance_logger.debug("Starting the Kibble service")
        if len(monitors) < 1:
            raise ValueError("You must have at least 1 monitor")

        for monitor in monitors:
            if interval < monitor._timeout:
                raise ValueError("Status interval must be greater than all monitor timeouts")

        self.monitors = monitors
        self.alerters = alerters
        self.detector = detector
        self.interval = interval

    def run(self):
        """
        Starts the Kibble system
        """
        try:
            while True:
                start_time = time.time()
                asyncio.run(self._rescan())
                logs, levels = self._get_logs()
                end_time = time.time()
                behind = end_time - start_time > self.interval
                if behind:
                    self.maintainance_logger.warning(f"Kibble service is lagging behind scanning interval")

                self._send_to_loggers(logs, levels)

                # send alerts if needed
                alerts = self.detector.get_alerts()
                for endpoint in alerts.keys():
                    self.maintainance_logger.info(f"Sending alert(s)")
                    for alerter in self.alerters:
                        alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

                # wait until next interval
                if not behind:
                    sleep_time = self.interval - end_time + start_time
                    self.maintainance_logger.debug(f"Waiting {round(sleep_time, 1)} seconds until scanning again")
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            self._end("user ended (KeyboardInterrupt)")
        except Exception as e:
            self._end(str(e))
            raise e

    async def _rescan(self):
        self.maintainance_logger.debug("Starting a network scan")
        await asyncio.gather(*[monitor.update_status() for monitor in self.monitors])
        self.maintainance_logger.debug("Finished scanning network")

    def _get_logs(self):
        logs: list[dict] = []
        levels: list[LogLevel] = []
        for monitor in self.monitors:
            res = monitor.get_status()
            for key in res.keys():
                log = res[key]
                if not log:
                    # it hasn't been scanned yet
                    continue
                level = self.detector.get_level(key, log)
                logs.append(ping_event(key, log, level))  # format log
                levels.append(level)
        return logs, levels

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel]):
        for log, level in zip(logs, levels):
            self.maintainance_logger.debug("Sending logs")
            self.logger.log(int(level), log, extra={ "status": log })

    def _end(self, msg: str=""):
        self.maintainance_logger.debug(msg)
