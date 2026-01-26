"""
MongoLogger derived class from Logger
TODO: discuss to async or not
"""

from pymongo import MongoClient

from .Logger import Logger, LogLevel

class MongoLogger(Logger):
    """
    Class for logging events/data to the MongoDB
    """
    def __init__(self, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password'):
        self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")

    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        return True
    
    def close_connection(self):
        self.client.close()
