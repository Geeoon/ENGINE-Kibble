"""
FileLogger derived class from Logger
"""

from .Logger import Logger, LogLevel

class FileLogger(Logger):
    """
    Class for logging events/data to the a file
    """
    def __init__(self, path: str):
        """
        Initialize FileLogger
        
        :param path: path to the log file
        :type path: str
        """
        self._fd = open(path, 'a')

    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        if self._fd.closed:
            return False
        self._fd.write(f"{level}: {data}\n")
        return True
    
    def close_file(self):
        if not self._fd.closed:
            self._fd.close()
