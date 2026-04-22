import pytest
import mongomock
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
from Kibble.Kibble import Kibble
from Kibble.Logging.MongoHandler import MongoHandler
from Kibble.Detecting.LatencyDetector import LatencyDetector


def test_e2e_new_device_discovery_and_logging():
    """
    E2E Test: 'First Contact' flow.
    Ensures a brand new IP results in logging.
    """
    # Mock Database
    mock_client = mongomock.MongoClient()
    db_name = "kibble_e2e"
    
    # PATCH: mongomock doesn't support MongoDB's Time Series collections.
    def mock_create_collection(name, **kwargs):
        return mock_client[db_name][name]
    mock_client[db_name].create_collection = mock_create_collection

    handler = MongoHandler(db_name=db_name, client=mock_client)
    
    # add our handler to this logger for the data to reach the mock DB.
    status_logger = logging.getLogger("Kibble_Status")
    status_logger.addHandler(handler)
    status_logger.setLevel(logging.DEBUG)

    mock_monitor = MagicMock()
    mock_monitor._timeout = 1
    mock_monitor.__str__.return_value = "ICMP" 
    
    mock_monitor.update_status = AsyncMock() 
    device_id = "507f1f77bcf86cd799439011" 
    mock_monitor.get_status.return_value = {
        device_id: {
            'status': {
                'alive': True, 
                'latency': 42, 
                'last_updated': 123456789
            }
        }
    }
    
    kibble = Kibble(
        client=mock_client,
        monitors=[mock_monitor],
        detector=LatencyDetector(),
        interval=10
    )

    # mimic what happens inside Kibble.run()
    asyncio.run(kibble._rescan())
    logs, levels = kibble._get_logs()
    kibble._send_to_loggers(logs, levels)
    
    handler._send_batch()

    db = mock_client[db_name]

    # check if event got logged with the correct data
    event_doc = db['timeseries_events'].find_one({"status.latency_ms": 42})
    
    assert event_doc is not None, "Log record should exist in mock MongoDB"
    assert str(event_doc['device_id']) == device_id
    assert event_doc['event_type'] == "endpoint_up"
    
    # Cleanup
    handler.close()
    status_logger.removeHandler(handler)
    print("\nE2E First Contact Test: PASS")

if __name__ == "__main__":
    test_e2e_new_device_discovery_and_logging()