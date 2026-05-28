"""
CpuCollector derived class from BaseCollector
"""

import psutil
from KibbleDaemon.collectors import BaseCollector


class CpuCollector(BaseCollector):
    """
    CpuCollector class for collecting CPU usage percentage.
    """
    def __init__(self):
        super().__init__()
        self.name = "cpu"

    def read(self) -> float:
        """
        Returns the current CPU usage as a percentage.

        :return: CPU usage percentage
        """
        return psutil.cpu_percent(interval=1)
