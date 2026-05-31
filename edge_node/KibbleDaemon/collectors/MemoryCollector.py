"""
MemoryCollector derived class from BaseCollector
"""

import psutil
from KibbleDaemon.collectors import BaseCollector


class MemoryCollector(BaseCollector):
    """
    MemoryCollector class for collecting memory usage percentage.
    """
    def __init__(self):
        super().__init__()
        self.name = 'memory'

    def read(self) -> float:
        """
        Returns the current memory usage as a percentage.

        :return: memory usage percentage
        """
        return psutil.virtual_memory().percent
