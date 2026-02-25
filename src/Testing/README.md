# MongoLogger Test Suite

This directory contains comprehensive test cases for the Kibble MongoLogger class.

## Test Structure

```
Tests/
├── __init__.py                      # Package initialization
├── README.md                        # This file
├── schema_validator.py              # Helper module with validation functions
├── test_log_normal_operation.py     # TC-ML-001: Normal operation
├── test_log_fault_event.py          # TC-ML-002: Fault events
├── test_db_connection_issues.py     # TC-ML-003: Connection issues
└── test_schema_validation.py        # TC-ML-004: Schema validation
```

## Test Cases

### TC-ML-001: Log Normal Operation
**File:** `test_log_normal_operation.py`

Tests that MongoLogger successfully logs normal monitoring data with all fields present and correct.

- Verifies successful insertion
- Validates all fields are stored correctly
- Checks timestamp, event_type, endpoint, and status fields

### TC-ML-002: Log Fault Event
**File:** `test_log_fault_event.py`

Tests logging of critical fault events when devices go down.

- Verifies CRITICAL severity logging
- Validates alive=False status
- Checks latency_ms=0 for down devices

### TC-ML-003: Database Connection Issues
**File:** `test_db_connection_issues.py`

Tests various database connection failure scenarios:

- **TC-ML-003a:** Invalid host
- **TC-ML-003b:** Invalid port
- **TC-ML-003c:** Invalid credentials
- **TC-ML-003d:** Connection loss during operation

### TC-ML-004: Schema Validation
**File:** `test_schema_validation.py`

Tests handling of missing or invalid fields:

- **TC-ML-004a:** Missing timestamp
- **TC-ML-004b:** Missing endpoint
- **TC-ML-004c:** Wrong data types
- **TC-ML-004d:** Empty dictionary
- **TC-ML-004e:** Extra unexpected fields
- **TC-ML-004f:** Missing nested fields

## Prerequisites

### Required Python Packages
```bash
pip install pytest pymongo
```

### MongoDB Setup
Ensure MongoDB is running and accessible:
- Host: `database.internal`
- Port: `27017`
- User: `root`
- Password: `password`
- Test Database: `kibble_test`

## Running the Tests

### Run All Tests
```bash
# From the project root
pytest Tests/

# With verbose output
pytest Tests/ -v

# With detailed output
pytest Tests/ -vv
```

### Run Specific Test File
```bash
# Run only normal operation tests
pytest Tests/test_log_normal_operation.py

# Run only connection tests
pytest Tests/test_db_connection_issues.py

# Run only schema validation tests
pytest Tests/test_schema_validation.py -v
```

### Run Individual Test Function
```bash
# Run specific test within a file
pytest Tests/test_schema_validation.py::test_schema_missing_timestamp

# Run with print statements visible
pytest Tests/test_log_normal_operation.py -s
```

### Run Tests Without pytest
Each test file can also be run directly:
```bash
python Tests/test_log_normal_operation.py
python Tests/test_log_fault_event.py
python Tests/test_db_connection_issues.py
python Tests/test_schema_validation.py
```

## Test Output

### Successful Test Run
```
Tests/test_log_normal_operation.py .                                    [25%]
Tests/test_log_fault_event.py .                                         [50%]
Tests/test_db_connection_issues.py ....                                 [75%]
Tests/test_schema_validation.py ......                                  [100%]

============================== 12 passed in 2.34s ==============================
```

### Failed Test Example
```
FAILED Tests/test_log_normal_operation.py::test_log_normal_operation
_________________________ test_log_normal_operation __________________________

    def test_log_normal_operation():
        ...
>       assert result == True, 'log() should return True on successful insert'
E       AssertionError: log() should return True on successful insert
```

## Integration with MongoLogger

The `schema_validator.py` module contains validation functions that can be integrated into your MongoLogger class:

```python
from Tests.schema_validator import validate_event_schema

class MongoLogger(Logger):
    def log(self, data: dict, level: LogLevel=LogLevel.INFO) -> bool:
        # Validate schema before inserting
        is_valid, error_msg = validate_event_schema(data)
        if not is_valid:
            print(f'Schema validation failed: {error_msg}')
            return False
        
        # Proceed with insertion
        try:
            ret = self.events_collection.insert_one(data)
            return True if ret.inserted_id else False
        except Exception as e:
            print(f'Failed to insert event: {e}')
            return False
```

## Recommendations

Based on the test results, consider implementing:

1. **Schema Validation** - Add validation before database insertion
2. **Error Handling** - Improve handling of connection failures
3. **Retry Logic** - Implement automatic retry for transient failures
4. **Type Checking** - Validate data types match expected schema
5. **Logging** - Add internal logging for debugging

## Continuous Integration

To run tests in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run MongoLogger Tests
  run: |
    pip install pytest pymongo
    pytest Tests/ -v --junitxml=test-results.xml
```

## Troubleshooting

### Connection Errors
If tests fail with connection errors:
1. Verify MongoDB is running: `systemctl status mongod`
2. Check network connectivity: `ping database.internal`
3. Verify credentials are correct
4. Check firewall settings on port 27017

### Import Errors
If tests fail with import errors:
1. Ensure you're in the correct directory
2. Check that Kibble package is in PYTHONPATH
3. Verify all required modules are installed

### Cleanup Issues
If tests leave data in the database:
```python
# Manual cleanup
from pymongo import MongoClient
client = MongoClient('mongodb://root:password@database.internal:27017')
db = client['kibble_test']
db.events.delete_many({})
db.devices.delete_many({})
```

## Contributing

When adding new test cases:
1. Follow the naming convention: `test_<description>.py`
2. Add inline comments explaining each step
3. Include cleanup in test functions
4. Update this README with new test descriptions
5. Update `__init__.py` if needed

## Contact

For questions or issues with the test suite, contact the Kibble team.