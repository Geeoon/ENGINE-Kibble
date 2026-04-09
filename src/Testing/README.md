# Test Suite

This directory contains individual tests for the Kibble system, ensuring each subsystem functions correctly and handles potential errors as expected.

## Test Cases

### Database Tests
- **`test_db_invalid_host.py`**
  Checks how the system behaves when the database runs into connection issues, specifically handling an invalid or unreachable host.
- **`test_db_log_fault_event.py`**
  Verifies that critical fault events are properly formatted and successfully inserted into the logs collection in the database.
- **`test_db_normal_operation.py`**
  Tests standard database operations to ensure that normal monitoring events are being correctly saved and tracked.

### Detector Tests
- **`test_detector_high_latency.py`**
  Tests the fault detector's capability to correctly identify, log, and handle endpoints that are experiencing abnormally high latency.
- **`test_detector_properly_function.py`**
  Ensures the fault detector does not produce false positives by testing it against normally operating endpoints.
- **`test_detector_severity.py`**
  Verifies that the fault detector evaluates and assigns the proper severity level to varying types of errors and degraded operations.

### Email Alert Tests
- **`test_email_alert_correctly.py`**
  Ensures that the alerting module correctly composes and sends out notification emails whenever critical faults are detected.
- **`test_email_fault_independence.py`**
  Checks that multiple fault events do not interfere with one another, guaranteeing isolated handling and reporting of discrete issues.
- **`test_email_throttle_alerts.py`**
  Tests the rate-limiting algorithms to ensure that the system does not spam the same alert consecutively or send an excessive number of emails.

### End-to-End Tests
- **`test_e2e.py`**
  Performs complete workflow simulation from monitoring initial status to database logging and email generation, ensuring all components interact successfully.

## How to Run Tests

Ensure you have `pytest` installed and a test MongoDB instance accessible before running the tests.

### Run tests collectively
To run the entire suite of tests at once from within the `src/Testing` directory:
```bash
pytest .
```

### Run tests individually
To run a specific test file:
```bash
pytest test_db_normal_operation.py
```

To run a specific test function within a test file:
```bash
pytest test_db_normal_operation.py::name_of_test_function
```