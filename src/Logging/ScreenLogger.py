"""
ScreenLogger derived class from Logger
"""

from .Logger import Logger, LogLevel

class ScreenLogger(Logger):
    """
    Class for logging events/data to the screen
    """
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        print(f"{level}: {data}")
        return True
