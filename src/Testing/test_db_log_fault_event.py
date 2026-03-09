"""
Database Test 2: Log Fault Event
Ensure MongoLogger logs fault events with critical severity
"""

import time
import logging
from unittest.mock import MagicMock
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging import LogLevel, ping_event

def test_log_fault_event():
    """
    Test that MongoLogger successfully logs fault events using Mocks
    """
    mock_client = MagicMock()
    mock_collection = mock_client['kibble_test']['timeseries_events']
    
    # Mock insert_many to return a successful result
    mock_collection.insert_many.return_value.inserted_ids = [123]

    # Initialize with mock to bypass network pings
    logger = MongoHandler(
        db_name='kibble_test',
        client=mock_client
    )
    
    status_data = {
        'alive': False,
        'latency': 0,
        'last_updated': round(time.time() * 1000)
    }
    
    # Create the event and a LogRecord
    event = ping_event('192.168.1.101', status_data, LogLevel.CRITICAL)
    
    record = logging.LogRecord(
        name="test_logger", level=logging.CRITICAL, pathname="", lineno=0,
        msg="Device Down", args=None, exc_info=None
    )
    # The new MongoHandler expects data in the 'status' attribute
    record.status = event 
    record.levelno = logging.CRITICAL

    # Trigger the batching and force a send
    logger.emit(record)
    logger._send_batch() 

    args, _ = mock_collection.insert_many.call_args
    logged_data = args[0][0]
    
    assert logged_data['endpoint']['ip'] == '192.168.1.101'
    assert logged_data['status']['alive'] == False
    assert logged_data['level'] == logging.CRITICAL
    
    logger.close()
    print('DB Test 2: PASS - Fault event logged successfully (Mocked)')


if __name__ == '__main__':
    test_log_fault_event()
