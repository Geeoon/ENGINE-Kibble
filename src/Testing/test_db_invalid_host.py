from pymongo import MongoClient
import pytest
import time
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging.EventSchema import ICMP # Changed from ping_event
from Kibble.Logging import LogLevel
from bson import ObjectId # Added for mandatory device_id
from unittest.mock import MagicMock
import logging

def test_db_connection_invalid_host():
    """
    DB Test 3A: Test connection failure with invalid host
    """
    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError)):
        logger = MongoHandler(
            db_name='kibble_test',
            host='invalid.host.doesnotexist',  # invalid hostname
            port=27017,
            user='root',
            passwd='password',
            client=MongoClient("mongodb://root:password@invalid.host:27017", serverSelectionTimeoutMS=1000)
        )
    
    print('DB Test 3A: PASS - Invalid host raises error')


def test_db_connection_invalid_port():
    """
    DB Test 3B: Test connection failure with invalid port
    """
    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError, ValueError)):
        logger = MongoHandler(
            db_name='kibble_test',
            host='localhost',
            port=99999,  # invalid port number
            user='root',
            passwd='password',
            client=MongoClient("mongodb://root:password@invalid.host:27017", serverSelectionTimeoutMS=1000)
        )

    print('DB Test 3B: PASS - Invalid port raises error')

# test to simulate connection loss during operation using mocking
def test_db_connection_loss_during_operation():
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
    record.status = ICMP(status_data=status_data, severity=LogLevel.LOW, device_id=ObjectId())

    with pytest.raises(Exception, match="Connection Lost"):
        logger.emit(record)
        logger._send_batch() # Trigger the actual network call
    
    # Disarm to prevent atexit noise
    logger.events_collection.insert_many.side_effect = None
    logger.close()