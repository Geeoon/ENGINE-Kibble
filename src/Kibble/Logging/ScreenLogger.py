"""
ScreenLogger derived class from Logger
"""

from Kibble.Logging import Logger, LogLevel

class ScreenLogger(Logger):
    """
    Class for logging events/data to the screen
    """
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        print(f"{level}: {data}")
        return True
    
    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        assert len(data) == len(levels), "Data length and levels length are not the same"
        for d, l in zip(data, levels):
            self.log(d, l)
        return True
