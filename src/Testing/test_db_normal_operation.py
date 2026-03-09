import time
import logging
from unittest.mock import MagicMock
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging import LogLevel, ping_event

def test_log_normal_operation():
    """
    Test that MongoHandler successfully batches and logs normal monitoring data (Mocked)
    """
    mock_client = MagicMock()
    mock_collection = mock_client['kibble_test']['timeseries_events']
    
    # Initialize with Mock to bypass pings and network errors
    logger = MongoHandler(
        db_name='kibble_test',
        client=mock_client
    )
    
    status_data = {
        'alive': True,
        'latency': 25,
        'last_updated': round(time.time() * 1000)
    }
    
    # Create the event and a standard Python LogRecord
    event = ping_event('192.168.1.100', status_data, LogLevel.LOW)
    
    record = logging.LogRecord(
        name="test_logger", level=logging.INFO, pathname="", lineno=0,
        msg="Normal Ping", args=None, exc_info=None
    )
    # The new MongoHandler expects the actual event dict in record.status
    record.status = event 
    record.levelno = logging.INFO

    #Trigger the logging and manually force the batch to send
    logger.emit(record)
    logger._send_batch() 

    # Verify the Mock received the correct data structure
    # args[0][0] retrieves the first document from the insert_many call list
    args, _ = mock_collection.insert_many.call_args
    logged_data = args[0][0]
    
    assert logged_data['endpoint']['ip'] == '192.168.1.100'
    assert logged_data['status']['alive'] is True
    assert logged_data['status']['latency_ms'] == 25
    
    logger.close()
    print('Database Test 1: PASS - Normal operation logged successfully (Mocked)')

if __name__ == '__main__':
    test_log_normal_operation()