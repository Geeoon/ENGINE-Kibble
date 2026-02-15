"""
ScreenAlert derived class from Alert
"""

from Kibble.Alerting import Alert
from Kibble.Logging import LogLevel

class ScreenAlert(Alert):
    """
    ScreenAlert for displaying alerts.  For testing.
    """
    def alert(self, data: dict, level: LogLevel) -> bool:
        print(f"{level}: {data}")
        return True
