"""
MongoHandler derived class from logging.Handler
"""
import logging
from pymongo import MongoClient
import threading

EVENTS_COLLECTION = "timeseries_events"

class MongoHandler(logging.Handler):
    """
    Class for logging events/data to the MongoDB.
    Events go to a time series collection; devices use a normal collection.
    """
    def __init__(self, db_name: str='kibble', client: MongoClient=None, update_frequency: float=1.0):
        """
        Initializes a handler for logging to MongoDB
        
        :param db_name: the MongoDB database to use
        :param client: the MongoDB client to use
        :param update_frequency: how often to send batches of logs to MongoDB in seconds
        """
        super().__init__()
        self.client = client
        self.db = self.client[db_name]

        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")

        self.events_collection = None
        try:
            self._create_events_collection()
        except Exception as e:
            self.maintainance_logger.critical(f"Unable to connect to MongoDB: {str(e)}")

        # instead of logging individually, log in batches
        self._batch: list[tuple[dict, int]] = []
        self._batch_lock = threading.Lock()
        self.update_frequency = update_frequency
        self._batch_thread = threading.Timer(self.update_frequency, self._batch_worker)
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

    def _batch_worker(self):
        self._send_batch()
        self._batch_thread = threading.Timer(self.update_frequency, self._batch_worker)
        self._batch_thread.daemon = True
        self._batch_thread.start()

    def _create_events_collection(self):
        # Time series collection
        time_series_options = {
            "timeField": "timestamp",
            "metaField": "endpoint",
            "granularity": "seconds",
        }
        if EVENTS_COLLECTION not in self.db.list_collection_names():
            self.db.create_collection(EVENTS_COLLECTION, timeseries=time_series_options)
        self.events_collection = self.db[EVENTS_COLLECTION]

    def _send_batch(self):
        try:
            if self.events_collection is not None:
                self._create_events_collection()
            with self._batch_lock:
                if len(self._batch) != 0:
                    ret = self.events_collection.insert_many([d | {"level": l} for d, l in self._batch])
                    if not ret.inserted_ids:
                        raise Exception("Insertion operation failed")
                self._batch.clear()  # don't clear unless we succeed
        except Exception as e:
            self.maintainance_logger.critical(f"Failed to log to MongoDB: {str(e)}")
                
    def close(self):
        self.flush()
        if self._batch_thread:
            self._batch_thread.cancel()
        # send any remaining records to the database
        self._send_batch()
        self.client.close()
