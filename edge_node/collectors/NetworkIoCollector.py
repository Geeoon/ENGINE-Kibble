"""
NetworkIoCollector class for measuring network I/O throughput.
"""

import time
from typing import Any
import psutil


class NetworkIoCollector:
    """
    Tracks network traffic and computes receive/send speed in bytes per second.
    Combines traffic across all network interfaces into a single total (pernic=False).
    """

    def __init__(self) -> None:
        self._prev: tuple[Any, float] | None = None

    def read_bps(self) -> tuple[float | None, float | None]:
        """
        Returns receive and send throughput in bytes per second since the last call.

        :return: (recv_bps, sent_bps), or (None, None) on the first call or if counters cannot be read
        """
        try:
            # pernic = False means all network card's io are combined
            current_counters = psutil.net_io_counters(pernic=False)
        except (OSError, NotImplementedError):
            return None, None

        current_time = time.monotonic()
        
        # Check if this is the first time being called
        if self._prev is None:
            self._prev = (current_counters, current_time)
            return None, None

        prev_counters, prev_time = self._prev

        # Checks for 0 time edge case
        dt = current_time - prev_time
        if dt == 0:
            return None, None

        bytes_received = current_counters.bytes_recv - prev_counters.bytes_recv
        bytes_sent = current_counters.bytes_sent - prev_counters.bytes_sent

        # Catch edge cases / if nums wrap around
        if bytes_received < 0 or bytes_sent < 0:
            self._prev = (current_counters, current_time)
            return None, None

        # Calculate io bytes/sec 
        recv_bps = bytes_received / dt
        sent_bps = bytes_sent / dt

        self._prev = (current_counters, current_time)
        return recv_bps, sent_bps
