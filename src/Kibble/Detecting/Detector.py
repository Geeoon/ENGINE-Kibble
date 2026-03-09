"""
Detector base class
"""
from Kibble.Logging import LogLevel
from abc import ABC, abstractmethod

class Detector(ABC):
    """
    Base class for detecting anomalies
    """
    @abstractmethod
    def get_level(self, log: dict) -> LogLevel:
        """
        Determines the severity of a log.  Shall be called every time a new log
        is generated.
        
        :param log: the log to check
        :return: the severity of the log
        """
        pass

    @abstractmethod
    def get_alerts(self) -> list[dict]:
        """
        Gets a list of new alerts that should be published
        
        :return: the list of alerts
        """
        pass
