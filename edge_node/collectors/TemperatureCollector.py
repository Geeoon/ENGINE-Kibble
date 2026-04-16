"""
TemperatureCollector reads CPU temperature in Celsius
"""

import psutil
from .base import BaseCollector


class TemperatureCollector(BaseCollector):
    """
    TemperatureCollector class for collecting CPU temperature.
    """
    def read(self) -> float | None:
        """
        Reads CPU temperature with psutil

        :return: temperature in Celsius, or None if unavailable
        """
        try:
            temps = psutil.sensors_temperatures()
        except (OSError, NotImplementedError):
            return None

        if not temps:
            return None

        # psutil returns groups of sensors
        for entries in temps.values():
            if entries:
                return entries[0].current
        return None
