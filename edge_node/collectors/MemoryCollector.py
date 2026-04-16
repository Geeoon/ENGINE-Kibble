"""
MemoryCollector derived class from BaseCollector
"""

import psutil
from .base import BaseCollector


class MemoryCollector(BaseCollector):
    """
    MemoryCollector class for collecting memory usage percentage.
    """
    def read(self) -> float:
        """
        Returns the current memory usage as a percentage.

        :return: memory usage percentage
        """
        return psutil.virtual_memory().percent
