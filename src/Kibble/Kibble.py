"""
Overall system implementation
"""

import logging
import time
import asyncio

from Kibble.Logging import Logger, LogLevel, ping_event
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
        assert len(monitors) > 0, "You must have at least 1 monitor"
        for monitor in monitors:
            assert interval > monitor._timeout, "Status interval must be greater than all monitor timeouts"
        self.monitors = monitors
        self.logger = logging.getLogger("Kibble_Status")

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
                
                self._send_to_loggers(logs, levels, behind)
                
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

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel], behind: bool):
        for log, level in zip(logs, levels):
            self.logger.log(int(level), log, extra={ "status": log })

        # TODO: make maintainence logger
        # if behind:
        #     logger.log({"msg": "Kibble did not meet the status interval requirement!"}, LogLevel.DEBUG)
                        
    def _end(self, msg: str=""):
        # TODO: make maintainence logger
        # self.logger.log({"msg": f"Kibble shutting down: {msg}"})
        pass
