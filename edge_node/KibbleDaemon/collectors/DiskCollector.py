"""
DiskCollector derived class from BaseCollector
"""

import sys
import psutil
from collectors import BaseCollector


class DiskCollector(BaseCollector):
    """
    DiskCollector class for collecting filesystem usage percentage.
    """

    def __init__(self, path: str | None = None) -> None:
        if path is not None:
            self._path = path
        elif sys.platform == "win32":
            self._path = "C:\\"
        else:
            self._path = "/"

    def read(self) -> float | None:
        """
        Returns disk usage as a percentage.

        :return: Disk usage percentage, or None if the metric cannot be read
        """
        try:
            return psutil.disk_usage(self._path).percent
        except OSError:
            return None
