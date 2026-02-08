"""
Database Test 1: Log Normal Operation
Ensure MongoLogger logs normal monitoring data to collection
"""

import time
from Kibble.Logging.MongoLogger import MongoLogger
from Kibble.Logging import LogLevel
from Kibble.Events import ping_event



def test_log_normal_operation():
    """
    Test that MongoLogger successfully logs normal monitoring data
    """
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    status_data = {
        'alive': True,
        'latency': 25,
        'last_updated': round(time.time() * 1000)
    }
    
    event = ping_event('192.168.1.100', status_data, LogLevel.INFO)
    result = logger.log(event, LogLevel.INFO)
    
    assert result == True, 'log() should return True on successful insert'
    logged_event = logger.events_collection.find_one(
        {'endpoint.ip': '192.168.1.100'}
    )
    
    assert logged_event is not None, 'Event should exist in database'
    assert logged_event['event_type'] == 'endpoint_down', 'Event type should match'
    assert logged_event['endpoint']['ip'] == '192.168.1.100', 'IP should match'
    assert logged_event['status']['alive'] == True, 'Alive status should be True'
    assert logged_event['status']['latency_ms'] == 25, 'Latency should be 25ms'
    assert 'timestamp' in logged_event, 'Timestamp field should be present'
    
    # cleanup/close connection
    logger.events_collection.delete_many({})
    logger.close()

    print('Database Test 1: PASS - Normal operation logged successfully')


if __name__ == '__main__':
    test_log_normal_operation()
