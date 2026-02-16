"""
Overall system implementation
"""

import time
import asyncio

from Kibble.Logging import Logger, LogLevel, abnormal_ping_event
from Kibble.Monitoring import StatusMonitor
from Kibble.Alerting import Alert
from Kibble.Detecting import Detector, LatencyDetector

class Kibble:
    """
    Monitors a series of endpoints and logs their status
    """
    def __init__(
        self, 
        monitors: list[StatusMonitor]=[], 
        loggers: list[Logger]=[], 
        alerters: list[Alert]=[], 
        detector: Detector=LatencyDetector(), 
        interval: int=10,
        devices_collection = None,
        protocol_events_collection = None
        ):
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
        self.devices_collection = devices_collection
        self.protocol_events_collection = protocol_events_collection

        self.device_index = {}  
        self.device_id_index = {}
        self.protocol_cache = {}
        self._get_devices()

    def run(self):
        """
        Starts the Kibble system
        """
        try:
            while True:
                start_time = time.time()
                asyncio.run(self._rescan())
                logs, levels = self._get_logs()

                self._get_protocols()

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
                logs.append(abnormal_ping_event(key, log, level))  # format log
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

    def _get_devices(self):
        cursor = self.devices_collection.find({}, {
            "_id" : 1, "hostname" : 1, "ip_address" : 1, "device_type" : 1})
        device_index = {}
        device_id_index = {}

        for device in cursor:
            hostname = (device.get("hostname") or "").strip()
            ip = (device.get("ip_address") or "").strip()

            if not hostname and not ip: continue

            data = {
                "device_id": device["_id"],
                "device_type": device.get("device_type"),
                "hostname": hostname or None,
                "ip_address": ip or None,
            }
            

            if hostname: device_index[hostname] = data
            if ip: device_index[ip] = data

            device_id_index[device["_id"]] = data

        self.device_index = device_index
        self.device_id_index = device_id_index

    def _get_protocols(self):
        for device_id, data in self.device_id_index.items():
            device = self.devices_collection.find_one({"_id": device_id}, {"supported_protocols": 1})
            protocols = (device or {}).get("supported_protocols", []) or []
            event_types_by_protocol: dict[str, set] = {}

            if protocols: 
                cursor = self.protocol_events_collection.find(
                    {"device_id": device_id, "protocol": {"$in": protocols}},
                    {"_id": 0, "protocol": 1, "event_type": 1}
                )

                for event in cursor:
                    p = event.get("protocol")
                    e_type = event.get("event_type")
                    if not p or not e_type:
                        continue
                    event_types_by_protocol.setdefault(p, set()).add(e_type)        

            self.protocol_cache[device_id] = {
                "protocols": protocols,
                "event_types_by_protocol": {p: sorted(list(s)) for p, s in event_types_by_protocol.items()}
            }