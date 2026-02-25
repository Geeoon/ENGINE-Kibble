"""
TC-ML-004: Schema Validation
Verify that MongoLogger handles missing or invalid fields appropriately
"""

import time
from Kibble.Logging.MongoLogger import MongoLogger
from Kibble.Logging import LogLevel


def test_schema_missing_timestamp():
    """
    TC-ML-004a: Test logging event with missing timestamp field
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Create event dictionary missing the 'timestamp' field
    event = {
        'event_type': 'endpoint_down',
        'endpoint': {'ip': '192.168.1.100'},
        'status': {'alive': False, 'latency_ms': 0}
        # NOTE: 'timestamp' field is missing
    }
    
    # Attempt to log the event
    # MongoDB will accept this by default (no schema enforcement)
    result = logger.log(event, LogLevel.CRITICAL)
    
    # Verify insertion succeeded (MongoDB doesn't enforce schema by default)
    assert result == True, 'MongoDB should accept document even with missing timestamp'
    
    # Query the database to verify the event was inserted
    logged_event = logger.events_collection.find_one({'endpoint.ip': '192.168.1.100'})
    assert logged_event is not None, 'Event should be in database'
    
    # Confirm that the timestamp field is indeed missing
    assert 'timestamp' not in logged_event, 'Timestamp field should be missing'
    
    # NOTE: This test reveals that schema validation should be implemented
    # to prevent incomplete events from being logged
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004a: PASS - Missing timestamp accepted (validation needed)')


def test_schema_missing_endpoint():
    """
    TC-ML-004b: Test logging event with missing endpoint field
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Create event missing the 'endpoint' field (critical information)
    event = {
        'timestamp': round(time.time() * 1000),
        'event_type': 'endpoint_down',
        'status': {'alive': False, 'latency_ms': 0}
        # NOTE: 'endpoint' field is missing
    }
    
    # Attempt to log the event
    result = logger.log(event, LogLevel.CRITICAL)
    
    # Verify insertion succeeded despite missing critical field
    assert result == True, 'MongoDB accepts event without endpoint'
    
    # NOTE: Without endpoint information, this event is not useful
    # Schema validation should catch this before insertion
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004b: PASS - Missing endpoint accepted (validation needed)')


def test_schema_wrong_data_types():
    """
    TC-ML-004c: Test logging event with incorrect data types
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Create event with intentionally wrong data types
    event = {
        'timestamp': 'not_a_number',      # Should be int, not string
        'event_type': 123,                 # Should be string, not int
        'endpoint': {'ip': 192168},        # Should be string, not int
        'status': {
            'alive': 'yes',                # Should be bool, not string
            'latency_ms': 'fast'           # Should be numeric, not string
        }
    }
    
    # Attempt to log the event
    # MongoDB accepts any types (schema-less by default)
    result = logger.log(event, LogLevel.INFO)
    
    # Verify insertion succeeded
    assert result == True, 'MongoDB accepts any data types'
    
    # NOTE: Type validation should be implemented to ensure data consistency
    # Wrong types will cause issues when querying or analyzing data
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004c: PASS - Wrong types accepted (type validation needed)')


def test_schema_empty_dict():
    """
    TC-ML-004d: Test logging an empty dictionary
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Attempt to log a completely empty event
    event = {}  # No fields at all
    
    # MongoDB will accept and insert an empty document
    result = logger.log(event, LogLevel.INFO)
    
    # Verify insertion succeeded
    assert result == True, 'MongoDB accepts empty documents'
    
    # NOTE: Empty documents are useless for monitoring
    # Minimum required fields should be validated before insertion
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004d: PASS - Empty dict accepted (validation needed)')


def test_schema_extra_fields():
    """
    TC-ML-004e: Test logging event with extra unexpected fields
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Create event with all required fields plus additional unexpected fields
    event = {
        'timestamp': round(time.time() * 1000),
        'event_type': 'endpoint_down',
        'endpoint': {'ip': '192.168.1.100'},
        'status': {'alive': False, 'latency_ms': 0},
        # Extra fields that aren't part of the schema
        'extra_field': 'unexpected_data',
        'another_field': 123,
        'random_data': {'nested': 'object'}
    }
    
    # Attempt to log the event with extra fields
    result = logger.log(event, LogLevel.INFO)
    
    # Verify insertion succeeded
    assert result == True, 'MongoDB accepts extra fields'
    
    # Query the database to verify extra fields are preserved
    logged_event = logger.events_collection.find_one({'endpoint.ip': '192.168.1.100'})
    
    # Confirm extra fields are stored in the database
    assert 'extra_field' in logged_event, 'Extra fields should be preserved'
    assert logged_event['extra_field'] == 'unexpected_data'
    
    # NOTE: Extra fields might be acceptable for extensibility,
    # but consider logging a warning for unexpected fields
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004e: PASS - Extra fields accepted (might want to warn)')


def test_schema_nested_field_missing():
    """
    TC-ML-004f: Test logging event with nested field missing (endpoint without ip)
    """
    # Initialize logger
    logger = MongoLogger(
        db_name='kibble_test',
        collection='events',
        host='database.internal',
        port=27017,
        user='root',
        passwd='password'
    )
    
    # Create event where 'endpoint' exists but 'endpoint.ip' is missing
    event = {
        'timestamp': round(time.time() * 1000),
        'event_type': 'endpoint_down',
        'endpoint': {},  # Empty dict - missing 'ip' field
        'status': {'alive': False, 'latency_ms': 0}
    }
    
    # Attempt to log the event
    result = logger.log(event, LogLevel.CRITICAL)
    
    # Verify insertion succeeded
    assert result == True, 'MongoDB accepts endpoint without ip'
    
    # Query the database
    logged_event = logger.events_collection.find_one({'event_type': 'endpoint_down'})
    
    # Verify endpoint exists but has no ip
    assert 'endpoint' in logged_event
    assert 'ip' not in logged_event['endpoint']
    
    # NOTE: Nested field validation is important
    # Should check that endpoint.ip is present and valid
    
    # Cleanup
    logger.events_collection.delete_many({})
    logger.close()
    
    print('TC-ML-004f: PASS - Nested field missing accepted (validation needed)')


if __name__ == '__main__':
    # Run all schema validation tests
    try:
        test_schema_missing_timestamp()
    except Exception as e:
        print(f"TC-ML-004a FAILED: {e}")
    
    try:
        test_schema_missing_endpoint()
    except Exception as e:
        print(f"TC-ML-004b FAILED: {e}")
    
    try:
        test_schema_wrong_data_types()
    except Exception as e:
        print(f"TC-ML-004c FAILED: {e}")
    
    try:
        test_schema_empty_dict()
    except Exception as e:
        print(f"TC-ML-004d FAILED: {e}")
    
    try:
        test_schema_extra_fields()
    except Exception as e:
        print(f"TC-ML-004e FAILED: {e}")
    
    try:
        test_schema_nested_field_missing()
    except Exception as e:
        print(f"TC-ML-004f FAILED: {e}")