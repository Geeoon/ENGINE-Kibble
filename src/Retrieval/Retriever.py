from pymongo import MongoClient, DESCENDING, ASCENDING
import time


from MongoRetriever import MongoRetriever

client = MongoClient("mongodb://root:password@localhost:27017")
col = client["kibble"]["devices"]

def get_all_devices(self) -> list[str]:
    """
    Returns all known devices in the system.
    """
    return self.mongo.get_all_devices()


class Retreiver:
    def __init__(self, mongo: MongoRetriver):
        self.mongo = mongo

    def list_devices_ips(self) -> list[str]:
        return self.mongo.get_all_devices()
