"""
TemperatureCollector reads CPU temperature in Celsius
"""

import psutil
from KibbleDaemon.collectors import BaseCollector


class TemperatureCollector(BaseCollector):
    """
    TemperatureCollector class for collecting CPU temperature.
    """
    def __init__(self):
        super().__init__()
        self.name = 'temp'

    def read(self) -> float | None:
        """
        Reads CPU temperature with psutil

        :return: temperature in Celsius, or None if unavailable
        """
        try:
            temps = psutil.sensors_temperatures()
        except (OSError, NotImplementedError, AttributeError):
            return None

        if not temps:
            return None

        all_readings = []
        for entries in temps.values():
            for entry in entries:
                all_readings.append(entry.current)

        return max(all_readings) if all_readings else None
