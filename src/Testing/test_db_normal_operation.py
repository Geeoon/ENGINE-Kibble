import time
import logging
from unittest.mock import MagicMock
from bson import ObjectId
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging import LogLevel
from Kibble.Logging.EventSchema import ICMP  # Changed from ping_event

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
    
    # The new ICMP function requires status_data, severity, and device_id.
    # Note: The IP is no longer a direct argument; it's usually tied to the device_id in the DB.
    event = ICMP(status_data=status_data, severity=LogLevel.LOW, device_id=ObjectId())
    
    record = logging.LogRecord(
        name="test_logger", level=logging.INFO, pathname="", lineno=0,
        msg="Normal Ping", args=None, exc_info=None
    )
    # The new MongoHandler expects the actual event dict in record.status
    record.status = event 
    record.levelno = logging.INFO

    # Trigger the logging and manually force the batch to send
    logger.emit(record)
    logger._send_batch() 

    # Verify the Mock received the correct data structure
    args, _ = mock_collection.insert_many.call_args
    logged_data = args[0][0]
    
    # Updated assertions to match the new ICMP schema structure
    assert isinstance(logged_data['device_id'], ObjectId)
    assert logged_data['status']['alive'] is True
    assert logged_data['status']['latency_ms'] == 25
    assert logged_data['event_type'] == "endpoint_up"
    
    logger.close()
    print('Database Test 1: PASS - Normal operation logged successfully (Mocked)')

if __name__ == '__main__':
    test_log_normal_operation()