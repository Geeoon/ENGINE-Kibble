"""
NetworkIoCollector class for measuring network I/O throughput.
"""

import time
from typing import Any
import psutil
from KibbleDaemon.collectors import BaseCollector


class NetworkIoCollector(BaseCollector):
    """
    Tracks network traffic and computes receive/send speed in bytes per second.
    Combines traffic across all network interfaces into a single total (pernic=False).
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "networkio"
        self._prev: tuple[Any, float] | None = None
        self._last_valid: tuple[float, float] | None = None

    def read(self) -> float | None:
        """
        Returns total network throughput (recv + sent) in bytes per second.

        :return: Total bytes per second, or None if not yet available
        """
        recv, sent = self.read_bps()
        if recv is None or sent is None:
            return None
        return recv + sent

    def read_bps(self) -> tuple[float | None, float | None]:
        """
        Returns receive and send throughput in bytes per second since the last call.

        :return: (recv_bps, sent_bps), or (None, None)
        """
        try:
            # pernic = False means all network card's io are combined
            current_counters = psutil.net_io_counters(pernic=False)
        except (OSError, NotImplementedError):
            return None, None

        current_time = time.monotonic()

        if self._prev is None:
            self._prev = (current_counters, current_time)
            return None, None

        prev_counters, prev_time = self._prev

        # Checks for 0 time edge case
        dt = current_time - prev_time
        if dt == 0:
            return self._last_valid if self._last_valid else (None, None)

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
        self._last_valid = (recv_bps, sent_bps)
        return recv_bps, sent_bps
