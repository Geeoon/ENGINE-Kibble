"""
MongoLogger derived class from Logger
"""
import logging
from pymongo import MongoClient
import threading

EVENTS_COLLECTION = "timeseries_events"
DEVICES_COLLECTION = "devices"

class MongoHandler(logging.Handler):
    """
    Class for logging events/data to the MongoDB.
    Events go to a time series collection; devices use a normal collection.
    """
    def __init__(self, db_name: str, host: str='database.internal', port: int=27017, user: str='root', passwd: str='password', client: MongoClient=None, update_frequency: float=1.0):
        """
        Initializes a handler for logging to MongoDB
        
        :param db_name: the MongoDB database to use
        :param host: the host of the MongoDB server
        :param port: the port of the MongoDB server
        :param user: the username of the MongoDB server
        :param passwd: the password of the MongoDB server
        :param client: the client to use instead of creating a new one
        :param update_frequency: how often to send batches of logs to MongoDB in seconds
        """
        super().__init__()
        if client is None:
            self.client = MongoClient(f"mongodb://{user}:{passwd}@{host}:{port}")
            self.client.admin.command('ping')  # can raise ConnectionFailure
        else:
            self.client = client

        self.db = self.client[db_name]

        # Time series collection
        time_series_options = {
            "timeField": "timestamp",
            "metaField": "endpoint",
            "granularity": "seconds",
        }
        if EVENTS_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(EVENTS_COLLECTION, timeseries=time_series_options)
        self.events_collection = self.db[EVENTS_COLLECTION]

        # instead of logging individually, log in batches
        self._batch: list[tuple[dict, int]] = []
        self._batch_lock = threading.Lock()
        self.update_frequency = update_frequency
        self._batch_thread = threading.Timer(self.update_frequency, self._send_batch)
        self._batch_thread.daemon = True
        self._batch_thread.start()

    def emit(self, record):
        if not hasattr(record, "status"):
            raise AttributeError("Record must have the status attribute")
        data = record.status
        if not type(data) == dict:
            raise TypeError("MongoHandler only takes dict for status")
        # TODO: ensure data has timestamp key properly formatted
        level = record.levelno
        self._add_to_batch(data, level)

    def _add_to_batch(self, data: dict, level: int):
        with self._batch_lock:
            self._batch.append((data, level))

    def _send_batch(self):
        with self._batch_lock:
            if len(self._batch) != 0:
                ret = self.events_collection.insert_many([d | {"level": l} for d, l in self._batch])
                if not ret.inserted_ids:
                    raise Exception("Failed to insert into database")  # TODO: replace with better exception
                self._batch.clear()
        self._batch_thread = threading.Timer(self.update_frequency, self._send_batch)
        self._batch_thread.daemon = True
        self._batch_thread.start()
        
    def close(self):
        self.flush()
        if self._batch_thread:
            self._batch_thread.cancel()
            # send any remaining records to the database
            self._send_batch()
        self.client.close()
