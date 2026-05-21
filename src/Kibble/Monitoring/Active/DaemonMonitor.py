"""
Implements the DaemonMonitor
"""

import asyncio
import time
import socket
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor

from google.protobuf.json_format import MessageToDict

from Kibble.Monitoring import StatusMonitor

from . import protocol_pb2

class DaemonMonitor(StatusMonitor):
    """
    Monitors the status of endpoints using the custom daemon protocl
    """

    def __init__(self, endpoints: list[str]=[], timeout: int=10, workers: int=5, port: int=5000):
        """
        Initializes the DaemonMonitor
        
        :param endpoints: see StatusMonitor.__init__
        :param timeout: see StatusMonitor.__init__
        :param workers: the max number of threads for the thread pool
        :param port: the TCP port to use for communication with the daemons
        """
        super().__init__(endpoints, timeout)
        self._executor = ThreadPoolExecutor(workers)
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.port = port
    
    def __str__(self):
        return 'daemon'
        
    async def update_status(self):
        with self._status_lock:
            targets = []
            for id, target in self._status.items():
                if target['details']['hostname']:  # prioritze using hostname
                    targets.append((id, target['details']['hostname']))
                else:
                    targets.append((id, target['details']['ip']))

            coroutines = [self._get_telemetry_await_reply(target[1]) for target in targets]
            results = await asyncio.gather(*coroutines)

            for target, result in zip(targets, results):
                self._status[target[0]]['status'] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2],
                    "telemetry": result[3]
                }

    def _get_daemon_telemetry(self, target: str) -> list[dict] | None:
        """
        :param target: the target IP address
        :return: the result from the telemetry request (as a list of telemetry
                entries), or None if no response
        """
        try:
            with urllib.request.urlopen(f"http://{target}:{self.port}/status", timeout=self._timeout) as res:
                response = res.read()
                if res.code != 200:
                    return None
            status = protocol_pb2.StatusResponse()
            status.ParseFromString(response)
            return MessageToDict(
                status,
                preserving_proto_field_name=True,
                use_integers_for_enums=True)["telemetry"]
        except:
            self.maintainance_logger.error(f"Could not connect to the daemon for {target}")
            return None

    async def _get_telemetry_await_reply(self, target: str) -> tuple[bool, int, int, list[dict]]:
        """
        Sends an status request and waits for a reply
        
        :param target: the target to send the status request
        :return: whether or not it's alive, the latency in milliseconds, the
                timestamp of when the reply was received in milliseconds (or
                when it timed out), the associated telemetry data
        """
        # resolve hostname
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            self.maintainance_logger.critical(f"Could not resolve the hostname for {target}")
            return (False, self._timeout * 1000, round(time.time() * 1000), None)
        
        loop = asyncio.get_event_loop()
        
        request_time = time.time()
        # NOTE: could be some overhead from the thread starting and ending
        response = await loop.run_in_executor(self._executor, lambda: self._get_daemon_telemetry(ip))
        response_time = time.time() 

        # timed out
        if not response:
            return (False, self._timeout * 1000, round(response_time * 1000), None)
        
        return (True, round((response_time - request_time) * 1000), round(response_time * 1000), response)
        
