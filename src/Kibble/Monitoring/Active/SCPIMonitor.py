"""
Implements the SCPIMonitor
"""

import asyncio
import time
import socket
import logging
from concurrent.futures import ThreadPoolExecutor
from Kibble.Monitoring import StatusMonitor

class SCPIMonitor(StatusMonitor):
    """
    Monitors the status of endpoints using SCPI *IDN? commands 
    """

    def __init__(self, endpoints: list[str], timeout: int=10, workers: int=5, port: int=5025):
        """
        Initializes the SCPIMonitor
        
        :param endpoints: see StatusMonitor.__init__
        :param timeout: see StatusMonitor.__init__
        :param workers: the max number of threads for the thread pool
        :param port: the TCP port to use for SCPI
        """
        super().__init__(endpoints, timeout)
        self._executor = ThreadPoolExecutor(workers)
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.port = port
    
    def __str__(self):
        return 'SCPI'
        
    async def update_status(self):
        with self._status_lock:
            targets = []
            for id, target in self._status.items():
                if target['details']['hostname']:  # prioritze using hostname
                    targets.append((id, target['details']['hostname']))
                else:
                    targets.append((id, target['details']['ip']))

            coroutines = [self._send_idn_await_reply(target[1]) for target in targets]
            results = await asyncio.gather(*coroutines)

            for target, result in zip(targets, results):
                self._status[target[0]]['status'] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2]
                }
    
    def _get_scpi_idn(self, target: str) -> str | None:
        """
        :param target: the target IP address
        :return: the result from the IDN, or None if no response
        """
        scpi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        scpi_socket.settimeout(self.timeout)
        try:
            scpi_socket.connect((target, self.port))
            scpi_socket.send("*IDN?")
            return str(scpi_socket.recv(1024))
        except:
            return None

    async def _send_idn_await_reply(self, target: str) -> tuple[bool, int, int]:
        """
        Sends a SCPI *IDN? and waits for a reply
        
        :param target: the target to send the *IDN? request
        :return: whether or not it's alive, the latency in milliseconds, and
                the timestamp of when the reply was received in milliseconds
                (or when it timed out)
        """
        # resolve hostname
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            self.maintainance_logger.critical(f"Could not resolve the hostname for {target}")
            return (False, self._timeout * 1000, round(time.time() * 1000))
        
        loop = asyncio.get_event_loop()
        
        request_time = time.time()
        # NOTE: could be some overhead from the thread starting and ending
        response = await loop.run_in_executor(self._executor, lambda: self._get_scpi_idn(ip))
        response_time = time.time() 

        # timed out
        if not response:
            return (False, self._timeout * 1000, round(response_time * 1000))
        
        return (True, round((response_time - request_time) * 1000), round(response_time * 1000))
        
