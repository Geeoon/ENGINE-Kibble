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
        protocol_events_collection = None,
        device_types_collection = None
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
        self.device_types_collection = device_types_collection

        self.device_unique_ids = {"index": {}, "id_index": {}, "protocol_cache": {}}
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
        """
        Pull devices info docs and build quick lookup indexes:
        - hostname/ip -> metadata (device_id, device_type_id)
        - device_id   -> metadata        
        """
        if self.devices_collection is None:
            raise ValueError("devices_collection must be provided")
        if self.protocol_events_collection is None:
            raise ValueError("protocol_events_collection must be provided")
        if self.device_types_collection is None:
            raise ValueError("device_types_collection must be provided")

        cursor = self.devices_collection.find({}, {
            "_id" : 1, "device_ip" : 1, "hostname" : 1, "device_type_id" : 1})
        index = {}
        id_index = {}

        for device in cursor:
            hostname = (device.get("hostname") or "").strip()
            ip = (device.get("device_ip") or "").strip()

            if not hostname and not ip: continue

            data = {
                "device_id": device["_id"],
                "device_type_id": device.get("device_type_id"),
                "hostname": hostname or None,
                "device_ip": ip or None,
            }
            

            if hostname: index[hostname] = data
            if ip: index[ip] = data

            id_index[device["_id"]] = data

        self.device_unique_ids["index"] = index
        self.device_unique_ids["id_index"] = id_index

    def _get_protocols(self):
        """
        For each device, fetch supported protocols and collect event types per protocol
        Stores results in self.device_unique_ids["protocol_cache"]
        """
        if self.devices_collection is None:
            raise ValueError("devices_collection must be provided")
        if self.protocol_events_collection is None:
            raise ValueError("protocol_events_collection must be provided")
        if self.device_types_collection is None:
            raise ValueError("device_types_collection must be provided")

        protocol_cache = {}

        for device_id, data in self.device_unique_ids["id_index"].items():
            device_type_id = data.get("device_type_id")

            if not device_type_id:
                protocol_cache[device_id] = {"protocols": [], "event_types_by_protocol":{}}
                continue

            dtype = self.device_types_collection.find_one(
                {"_id": device_type_id},
                {"protocols_supported": 1, "name": 1})

            protocols = (dtype or {}).get("protocols_supported", []) or []
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

            protocol_cache[device_id] = {
                "protocols": protocols,
                "event_types_by_protocol": {p: sorted(list(s)) for p, s in event_types_by_protocol.items()}
            }
            
            self.device_unique_ids["protocol_cache"] = protocol_cache