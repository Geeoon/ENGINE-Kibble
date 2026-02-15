"""
Database Test 2: Log Fault Event
Ensure MongoLogger logs fault events with critical severity
"""

import time
from Kibble.Logging.MongoLogger import MongoLogger
from Kibble.Logging import LogLevel, ping_event

def test_log_fault_event():
    """
    Test that MongoLogger successfully logs fault events
    """
    logger = MongoLogger(
        db_name='kibble_test',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    status_data = {
        'alive': False,          # device is offline
        'latency': 0,            # no latency with device down
        'last_updated': round(time.time() * 1000)
    }
    
    event = ping_event('192.168.1.101', status_data, LogLevel.CRITICAL)
    result = logger.log(event, LogLevel.CRITICAL)
    assert result == True, 'log() should return True for fault events'
    
    logged_event = logger.events_collection.find_one(
        {'endpoint.ip': '192.168.1.101'}
    )
    
    assert logged_event is not None, 'Fault event should exist in database'
    assert logged_event['event_type'] == 'endpoint_down', 'Event type should be endpoint_down'
    assert logged_event['status']['alive'] == False, 'Device should be marked as not alive'
    assert logged_event['status']['latency_ms'] == 0, 'Latency should be 0 for down device'
    assert 'timestamp' in logged_event, 'Timestamp should be present'
    
    logger.events_collection.delete_many({})
    logger.close()

    print('DB Test 2: PASS - Fault event logged successfully')


if __name__ == '__main__':
    test_log_fault_event()