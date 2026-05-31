"""
TC-ML-004: Schema Validation
Verify that MongoHandler handles missing or invalid fields appropriately
"""

import time
import logging
from unittest.mock import MagicMock
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Logging import LogLevel


def _make_handler():
    """Helper: create a MongoHandler backed by a MagicMock client."""
    mock_client = MagicMock()
    handler = MongoHandler(
        db_name='kibble_test',
        client=mock_client
    )
    mock_collection = mock_client['kibble_test']['timeseries_events']
    # Default: insert_many returns a successful result
    mock_collection.insert_many.return_value.inserted_ids = [123]
    return handler, mock_collection


def _make_record(event: dict, level: int = logging.INFO) -> logging.LogRecord:
    """Helper: create a LogRecord with the given event dict on record.status."""
    record = logging.LogRecord(
        name="test_logger", level=level, pathname="", lineno=0,
        msg="Schema Validation Test", args=None, exc_info=None
    )
    record.status = event
    record.levelno = level
    return record


def test_schema_missing_timestamp():
    """
    TC-ML-004a: Test logging event with missing timestamp field
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
    # Create event dictionary missing the 'timestamp' field
    event = {
        'event_type': 'endpoint_down',
        'endpoint': {'ip': '192.168.1.100'},
        'status': {'alive': False, 'latency_ms': 0}
        # NOTE: 'timestamp' field is missing
    }
    
    # Attempt to log the event via the handler
    record = _make_record(event, logging.CRITICAL)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted (MongoDB doesn't enforce schema by default)
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    args, _ = mock_collection.insert_many.call_args
    logged_event = args[0][0]
    
    # Confirm that the timestamp field is indeed missing
    assert 'timestamp' not in logged_event, 'Timestamp field should be missing'
    
    # NOTE: This test reveals that schema validation should be implemented
    # to prevent incomplete events from being logged
    
    # Cleanup
    handler.close()
    
    print('TC-ML-004a: PASS - Missing timestamp accepted (validation needed)')


def test_schema_missing_endpoint():
    """
    TC-ML-004b: Test logging event with missing endpoint field
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
    # Create event missing the 'endpoint' field (critical information)
    event = {
        'timestamp': round(time.time() * 1000),
        'event_type': 'endpoint_down',
        'status': {'alive': False, 'latency_ms': 0}
        # NOTE: 'endpoint' field is missing
    }
    
    # Attempt to log the event
    record = _make_record(event, logging.CRITICAL)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted despite missing critical field
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    # NOTE: Without endpoint information, this event is not useful
    # Schema validation should catch this before insertion
    
    # Cleanup
    handler.close()
    
    print('TC-ML-004b: PASS - Missing endpoint accepted (validation needed)')


def test_schema_wrong_data_types():
    """
    TC-ML-004c: Test logging event with incorrect data types
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
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
    record = _make_record(event, logging.INFO)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    # NOTE: Type validation should be implemented to ensure data consistency
    # Wrong types will cause issues when querying or analyzing data
    
    # Cleanup
    handler.close()
    
    print('TC-ML-004c: PASS - Wrong types accepted (type validation needed)')


def test_schema_empty_dict():
    """
    TC-ML-004d: Test logging an empty dictionary
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
    # Attempt to log a completely empty event
    event = {}  # No fields at all
    
    # MongoDB will accept and insert an empty document
    record = _make_record(event, logging.INFO)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    # NOTE: Empty documents are useless for monitoring
    # Minimum required fields should be validated before insertion
    
    # Cleanup
    handler.close()
    
    print('TC-ML-004d: PASS - Empty dict accepted (validation needed)')


def test_schema_extra_fields():
    """
    TC-ML-004e: Test logging event with extra unexpected fields
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
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
    record = _make_record(event, logging.INFO)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    args, _ = mock_collection.insert_many.call_args
    logged_event = args[0][0]
    
    # Confirm extra fields are preserved in the logged data
    assert 'extra_field' in logged_event, 'Extra fields should be preserved'
    assert logged_event['extra_field'] == 'unexpected_data'
    
    # NOTE: Extra fields might be acceptable for extensibility,
    # but consider logging a warning for unexpected fields
    
    # Cleanup
    handler.close()
    
    print('TC-ML-004e: PASS - Extra fields accepted (might want to warn)')


def test_schema_nested_field_missing():
    """
    TC-ML-004f: Test logging event with nested field missing (endpoint without ip)
    """
    # Initialize handler
    handler, mock_collection = _make_handler()
    
    # Create event where 'endpoint' exists but 'endpoint.ip' is missing
    event = {
        'timestamp': round(time.time() * 1000),
        'event_type': 'endpoint_down',
        'endpoint': {},  # Empty dict - missing 'ip' field
        'status': {'alive': False, 'latency_ms': 0}
    }
    
    # Attempt to log the event
    record = _make_record(event, logging.CRITICAL)
    handler.emit(record)
    handler._send_batch()
    
    # Verify insertion was attempted
    assert mock_collection.insert_many.called, 'insert_many should have been called'
    
    args, _ = mock_collection.insert_many.call_args
    logged_event = args[0][0]
    
    # Verify endpoint exists but has no ip
    assert 'endpoint' in logged_event
    assert 'ip' not in logged_event['endpoint']
    
    # NOTE: Nested field validation is important
    # Should check that endpoint.ip is present and valid
    
    # Cleanup
    handler.close()
    
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