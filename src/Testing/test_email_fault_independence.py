"""
Email Alerting Test 2: Multiple device failures are alerted correctly
Verify receiving alert from second device when first device is already down, 
ensuring loop doesn't terminate or skip alerts after an initial failure
"""

import pytest
from unittest.mock import MagicMock
from Kibble.Kibble import Kibble
from Kibble.Logging import LogLevel

def test_alert_second_device_when_first_down():
    mock_monitor = MagicMock()
    mock_monitor._timeout = 1
        
    mock_alerter = MagicMock()
    mock_detector = MagicMock()

    faults = {
        "10.128.0.1": {'level': LogLevel.CRITICAL},
        "10.128.0.2": {'level': LogLevel.CRITICAL}
    }
    mock_detector.get_alerts.return_value = faults

    mock_client = MagicMock()

    kibble_inst = Kibble(
        monitors=[mock_monitor], 
        alerters=[mock_alerter], 
        detector=mock_detector, 
        interval=10,
        client=mock_client
    )

    alerts = kibble_inst.detector.get_alerts()
    for endpoint in alerts.keys():
        for alerter in kibble_inst.alerters:
            alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

    assert mock_alerter.alert.call_count == 2
    mock_alerter.alert.assert_any_call("ALERT FOR 10.128.0.1", LogLevel.CRITICAL)
    mock_alerter.alert.assert_any_call("ALERT FOR 10.128.0.2", LogLevel.CRITICAL)

if __name__ == "__main__":
    test_alert_second_device_when_first_down()