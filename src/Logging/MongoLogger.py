"""
MongoLogger derived class from Logger
TODO: discuss to async or not
"""
import time 
from pymongo import MongoClient

from .Logger import Logger, LogLevel

class MongoLogger(Logger):
    """
    Class for logging events/data to the MongoDB
    """
    def __init__(self, db_name: str, collection: str, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password'):
        self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")
        self.client.admin.command('ping')  # can raise ConnectionFailure
        self.db = self.client[db_name]
        self.collection = self.db[collection]

    # logging abnormal ping results to MongoDB
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        ret = self.collection.insert_one(data | { "level": level.value[1], "time": round(time.time() * 1000) })
        return True if ret.inserted_id else False

    def log_many(self, data: list[dict], levels: list[LogLevel]=[]) -> bool:
        assert(len(data) == len(levels))
        ret = self.collection.insert_many([d | { "level": l.value[1], "time": round(time.time() * 1000) } for d, l in zip(data, levels)])
        return True if ret.inserted_ids else False
    
    def close_connection(self):
        self.client.close()

