"""
DiskCollector derived class from BaseCollector
"""

import psutil
from .base import BaseCollector


class DiskCollector(BaseCollector):
    """
    DiskCollector class for collecting root filesystem usage percentage.
    """

    def read(self) -> float | None:
        """
        Returns space usage for / as a percentage.

        :return: Disk usage percentage, or None if the metric cannot be read
        """
        try:
            return psutil.disk_usage("/").percent
        except OSError:
            return None
