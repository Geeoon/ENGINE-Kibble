from pymongo import MongoClient
import pytest
import time
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging import LatencyStructure
from Kibble.Logging import LogLevel
from bson import ObjectId
from unittest.mock import MagicMock
import logging

def test_db_connection_invalid_host(caplog):
    """
    DB Test 3A: Test connection failure with invalid host
    """
    with caplog.at_level(logging.CRITICAL):
        logger = MongoHandler(
            db_name='kibble_test',
            client=MongoClient("mongodb://root:password@invalid.host:27017", serverSelectionTimeoutMS=1000)
        )
    
    assert "Unable to connect to MongoDB" in caplog.text
    logger.close()
    print('DB Test 3A: PASS - Invalid host caught and logged')


def test_db_connection_invalid_port():
    """
    DB Test 3B: Test connection failure with invalid port
    """
    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError, ValueError)):
        logger = MongoHandler(
            db_name='kibble_test',
            client=MongoClient("mongodb://root:password@invalid.host:99999", serverSelectionTimeoutMS=1000)
        )

    print('DB Test 3B: PASS - Invalid port raises error')

# test to simulate connection loss during operation using mocking
def test_db_connection_loss_during_operation(caplog):
    mock_client = MagicMock()
    
    logger = MongoHandler(
        db_name='kibble_test',
        client=mock_client # Inject the mock here
    )
    
    logger.events_collection.insert_many.side_effect = Exception("Connection Lost")
    
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test", args=None, exc_info=None
    )
    
    # Updated to use ICMP to match the required schema
    status_data = {'alive': True, 'latency': 25}
    record.status = LatencyStructure(status_data, LogLevel.LOW, device_id=ObjectId())

    with caplog.at_level(logging.CRITICAL):
        logger.emit(record)
        logger._send_batch() # Trigger the actual network call

    assert "Connection Lost" in caplog.text
    
    # Disarm to prevent atexit noise
    logger.events_collection.insert_many.side_effect = None
    logger.close()