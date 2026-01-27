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
    
    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        assert(len(data) == len(levels))
        out = True
        for d, l in zip(data, levels):
            out &= self._fd.write(f"{l}: {d}\n")  # Python buffers I/O, so no issues here
        return out
    
    def close_file(self):
        if not self._fd.closed:
            self._fd.close()
