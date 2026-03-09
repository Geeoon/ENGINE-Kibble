"""
Email Alerting Test 1: Email alert occurs on failure
Ensuring email alerting system properly transmits an alert when device goes down.
"""

import os
import pytest
from unittest.mock import MagicMock
from Kibble.Kibble import Kibble
from Kibble.Alerting.EmailAlert import EmailAlert
from Kibble.Logging import LogLevel
from Kibble.Logging.EventSchema import ICMP

def test_email_alert_content_and_trigger():
    # Verify environment variable for password is set or there will be a failure
    if not os.getenv('EMAIL_PASSWD'):
        pytest.fail("EMAIL_PASSWD env var not set. Run: $env:EMAIL_PASSWD='your_pass'")
    
    mock_monitor = MagicMock()
    mock_monitor._timeout = 1
        
    real_email_alerter = EmailAlert()
    
    mock_detector = MagicMock()
    faulty_ip = "10.128.0.5"
    critical_lvl = LogLevel.CRITICAL
    
    mock_detector.get_alerts.return_value = {
        faulty_ip: {'level': critical_lvl}
    }

    mock_client = MagicMock()

    kibble_inst = Kibble(
        monitors=[mock_monitor], 
        alerters=[real_email_alerter], 
        detector=mock_detector, 
        interval=10,
        client=mock_client
    )

    alerts = kibble_inst.detector.get_alerts()
    results = []
    for endpoint in alerts.keys():
        for alerter in kibble_inst.alerters:
            status = alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])
            results.append(status)

    assert all(results) is True, "The real email transmission failed."
    
    print(f"Email successfully sent to kibblealert@gmail.com")

if __name__ == "__main__":
    test_email_alert_content_and_trigger()