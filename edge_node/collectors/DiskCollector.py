"""
DiskCollector derived class from BaseCollector
"""

import sys
import psutil
from .base import BaseCollector


class DiskCollector(BaseCollector):
    """
    DiskCollector class for collecting root filesystem usage percentage.
    """

    def read(self) -> float | None:
        """
        Returns disk usage as a percentage.

        :return: Disk usage percentage, or None if the metric cannot be read
        """
        if sys.platform == "win32":
            path = "C:\\"
        else:
            path = "/"
        try:
            return psutil.disk_usage(path).percent
        except OSError:
            return None
