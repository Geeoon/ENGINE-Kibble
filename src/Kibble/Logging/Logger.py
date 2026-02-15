"""
Logger base class and log levels
"""

from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime

class LogLevel(Enum):
    DEBUG=('debug', 4)
    INFO=('info', 3)
    WARNING=('warning', 2)
    ERROR=('error', 1)
    CRITICAL=('critical', 0)

    def __str__(self):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {self.value[0].upper()}]"

    def __lt__(self, other):
        if not isinstance(other, LogLevel):
            raise NotImplemented
        # intentionally backwards to make comparisons easier to understand
        return int(self) > int(other)

    def __eq__(self, other):
        if not isinstance(other, LogLevel):
            raise NotImplemented
        return int(self) == int(other)
    
    def __int__(self):
        return self.value[1]

class Logger(ABC):
    """
    Abstract class for logging a single event/data
    """
    @abstractmethod
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        """
        Abstract method to log an event
        
        :param data: the data to log
        :type data: dict
        :param level: the log level
        :type level: LogLevel
        :return: True on success, False on error
        :rtype: bool
        """
        pass

    @abstractmethod
    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        """
        Abstract method to log multiple events
        
        :param data: the data to log
        :type data: list[dict]
        :param level: the log level
        :type level: list[LogLevel]
        :return: True on success, False on error
        :pre the data list is the same length as the level list
        :rtype: bool
        """
        pass

    def close(self):
        """
        Abstract method to close a logger
        """
        pass
