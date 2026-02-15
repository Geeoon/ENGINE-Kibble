"""
Logger base class and log levels
"""

import logging
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime

class LogLevel(Enum):
    DEBUG=('debug', logging.DEBUG)
    INFO=('info', logging.INFO)
    WARNING=('warning', logging.WARNING)
    ERROR=('error', logging.ERROR)
    CRITICAL=('critical', logging.CRITICAL)

    def __str__(self):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {self.value[0].upper()}]"

    def __lt__(self, other):
        if not isinstance(other, LogLevel):
            raise NotImplemented
        return int(self) < int(other)

    def __eq__(self, other):
        if not isinstance(other, LogLevel):
            raise NotImplemented
        return int(self) == int(other)
    
    def __int__(self):
        return self.value[1]
