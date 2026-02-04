"""
Alert base class
"""

from abc import ABC, abstractmethod
from Kibble.Logging import LogLevel

class Alert(ABC):
    """
    Abstract class for alerting
    """
    @abstractmethod
    def alert(self, data: dict, level: LogLevel) -> bool:
        """
        Abstract method to alert on an event
        
        :param data: the data to alert on
        :type data: dict
        :param level: the log level
        :type level: LogLevel
        :return: True on success, False on error
        :rtype: bool
        """
        pass