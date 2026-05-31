"""
ScreenAlert derived class from Alert
"""

import logging

from Kibble.Alerting import Alert
from Kibble.Logging import LogLevel

class ScreenAlert(Alert):
    """
    ScreenAlert for displaying alerts.  For testing.
    """

    def __init__(self):
        self.logger = logging.getLogger("Kibble_Alerts")

    def alert(self, data: dict, level: LogLevel) -> bool:
        self.logger.log(int(level), str(data))
        return True
