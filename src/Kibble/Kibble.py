"""
Overall system implementation
"""

import time
import asyncio

from Kibble.Logging import Logger, LogLevel, abnormal_ping_event
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert

class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """
    def __init__(self, monitors: list[StatusMonitor]=[], loggers: list[Logger]=[], alerters: list[Alert]=[], interval: int=10):
        """
        Initializes the Kibble system
        
        :param monitors: the monitors to use for tracking the endpoints
        :type monitors: list[StatusMonitor]
        :param loggers: the loggers to use for logging status
        :type loggers: list[Logger]
        :param alerters: the alerts to use for alerting faults
        :type alerters: list[Alert]
        :param interval: how often to check the status of endpoints in seconds
        :type interval: int
        """
        assert len(monitors) > 0, "You must have at least 1 monitor"
        assert len(loggers) > 0, "You must have at least 1 logger"
        for monitor in monitors:
            assert interval > monitor._timeout, "Status interval must be greater than all monitor timeouts"
        self.monitors = monitors
        self.loggers = loggers
        self.alerters = alerters
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
                
                # TODO: determine if an alert is needed
                # wait until next interval
                if not behind:
                    print(f"Sleeping for {self.interval - end_time + start_time}")
                    time.sleep(self.interval - end_time + start_time)
        except KeyboardInterrupt:
            self._end("user ended (KeyboardInterrupt)")
        except Exception as e:
            self._end(str(e))

    async def _rescan(self):
        await asyncio.gather(*[monitor.update_status() for monitor in self.monitors])

    def _get_logs(self):
        logs: list[dict] = []
        levels: list[LogLevel] = []
        for monitor in self.monitors:
            res = monitor.get_status()
            print(res)
            for key in res.keys():
                if not res[key]:
                    # it hasn't been scanned yet
                    continue
                level = LogLevel.INFO
                if not res[key]["alive"]:
                    level = LogLevel.CRITICAL
                logs.append(abnormal_ping_event(key, res[key], level))
                levels.append(level)
        return logs, levels

    def _send_to_loggers(self, logs: list[dict], levels: list[LogLevel], behind: bool):
        for logger in self.loggers:
            logger.log_many(logs, levels)
            if behind:
                logger.log({"msg": "Kibble did not meet the status interval requirement!"}, LogLevel.DEBUG)
                        

    def _end(self, msg: str=""):
        for logger in self.loggers:
            logger.log({"msg": f"Kibble shutting down: {msg}"})
            logger.close()
