"""
Implements the ICMPMonitor
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from scapy.layers.inet import IP, ICMP
from scapy.sendrecv import sr1

from Kibble.Monitoring import StatusMonitor

class ICMPMonitor(StatusMonitor):
    """
    Monitors the status of endpoints using ICMP echo request/reply 
    """

    def __init__(self, endpoints: list[str], timeout: int=10, workers: int=5):
        """
        Initializes the ICMPMonitor
        
        :param endpoints: see StatusMonitor.__init__
        :type endpoints: list[str]
        :param timeout: see StatusMonitor.__init__
        :type timeout: int
        :param workers: the max number of threads for the thread pool
        :type workers: int
        """
        super().__init__(endpoints, timeout)
        self._executor = ThreadPoolExecutor(workers)
    
    def __str__(self):
        return 'ICMP'
        
    async def update_status(self):
        with self._status_lock:
            ips = list(self._status.keys())
            coroutines = [self._send_request_await_reply(ip) for ip in ips]
            results = await asyncio.gather(*coroutines)

            for ip, result in zip(ips, results):
                self._status[ip] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2]
                }

    async def _send_request_await_reply(self, ip: str) -> tuple[bool, int, int]:
        """
        Sends an ICMP echo request and waits for a reply
        
        :param ip: the target to send the echo request
        :type ip: str
        :return: whether or not it's alive, the latency in milliseconds, and
                the timestamp of when the reply was received in milliseconds
                (or when it timed out)
        :rtype: tuple[bool, int, int]
        """
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
        
