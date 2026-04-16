"""
Implements the ICMPMonitor
"""

import asyncio
import time
import socket
import logging
from concurrent.futures import ThreadPoolExecutor
from scapy.layers.inet import IP, ICMP
from scapy.sendrecv import sr1
from Kibble.Monitoring import StatusMonitor

class ICMPMonitor(StatusMonitor):
    """
    Monitors the status of endpoints using ICMP echo request/reply 
    """

    def __init__(self, endpoints: list[str]=[], timeout: int=10, workers: int=5):
        """
        Initializes the ICMPMonitor
        
        :param endpoints: see StatusMonitor.__init__
        :param timeout: see StatusMonitor.__init__
        :param workers: the max number of threads for the thread pool
        """
        super().__init__(endpoints, timeout)
        self._executor = ThreadPoolExecutor(workers)
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
    
    def __str__(self):
        return 'ICMP'
        
    async def update_status(self):
        with self._status_lock:
            targets = []
            for id, target in self._status.items():
                if target['details']['hostname']:  # prioritze using hostname
                    targets.append((id, target['details']['hostname']))
                else:
                    targets.append((id, target['details']['ip']))

            coroutines = [self._send_request_await_reply(target[1]) for target in targets]
            results = await asyncio.gather(*coroutines)

            for target, result in zip(targets, results):
                self._status[target[0]]['status'] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2]
                }

    async def _send_request_await_reply(self, target: str) -> tuple[bool, int, int]:
        """
        Sends an ICMP echo request and waits for a reply
        
        :param target: the target to send the echo request
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
        request = IP(dst=ip) / ICMP()
        
        request_time = time.time()
        # NOTE: could be some overhead from the thread starting and ending
        response = await loop.run_in_executor(self._executor, lambda: sr1(request, timeout=self._timeout, verbose=False))
        response_time = time.time() 

        # timed out
        if not response:
            return (False, self._timeout * 1000, round(response_time * 1000))
        
        return (True, round((response_time - request_time) * 1000), round(response_time * 1000))
        
