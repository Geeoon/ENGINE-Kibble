"""
Logger base class and log levels
"""

from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime

class LogLevel(Enum):
    DEBUG='debug'
    INFO='info'
    WARNING='warning'
    ERROR='error'
    CRITICAL='critical'
    def __str__(self):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {self.value.upper()}]"

class Logger(ABC):
    """
    Abstract class for logging events/data
    """
    @abstractmethod
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        """
        Abstract method to log data
        
        :param data: the data to log
        :type data: dict
        :param level: the log level
        :type level: LogLevel
        :return: True on success, False on error
        :rtype: bool
        """
        pass
