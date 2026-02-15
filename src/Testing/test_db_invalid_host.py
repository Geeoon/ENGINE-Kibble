"""
Database Test 3: Connection Issues
Ensure MongoLogger handles database connection failures properly
"""

import pytest
import time
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from Kibble.Logging.MongoLogger import MongoLogger
from Kibble.Events import ping_event


def test_db_connection_invalid_host():
    """
    DB Test 3A: Test connection failure with invalid host
    """
    # connect to non-existent host
    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError)):
        logger = MongoLogger(
            db_name='kibble_test',
            collection='events',
            host='invalid.host.doesnotexist',  # invalid hostname
            port=27017,
            user='root',
            passwd='password'
        )
    
    print('DB Test 3A: PASS - Invalid host raises error')


def test_db_connection_invalid_port():
    """
    DB Test 3B: Test connection failure with invalid port
    """
    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError)):
        logger = MongoLogger(
            db_name='kibble_test',
            collection='events',
            host='database.internal',
            port=99999,  # invalid port number
            user='root',
            passwd='password'
        )

    print('DB Test 3B: PASS - Invalid port raises error')


def test_db_connection_loss_during_operation():
    """
    DB Test 3C: Test connection lost during operation
    """
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # manually close MongoDB client
    logger.client.close()
    
    status_data = {
        'alive': True,
        'latency': 25,
        'last_updated': round(time.time() * 1000)
    }
    event = ping_event('192.168.1.100', status_data)
    
    # log with closed connection
    with pytest.raises(Exception):
        logger.log(event)

    print('DB Test 3C: PASS - Connection loss during operation raises exception')


if __name__ == '__main__':
    try:
        test_db_connection_invalid_host()
    except Exception as e:
        print(f"DB Test 3A FAILED: {e}")

    try:
        test_db_connection_invalid_port()
    except Exception as e:
        print(f"DB Test 3B FAILED: {e}")

    try:
        test_db_connection_loss_during_operation()
    except Exception as e:
        print(f"DB Test 3C FAILED: {e}")