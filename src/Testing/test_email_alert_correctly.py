"""
Email Alerting Test 1: Email alert occurs on failure
Ensuring email alerting system properly transmits an alert when device goes down.
"""

import pytest
from unittest.mock import MagicMock, patch
from Kibble.Kibble import Kibble
from Kibble.Alerting import EmailAlert
from Kibble.Logging import LogLevel

@patch('smtplib.SMTP_SSL')
def test_email_alert_content_and_trigger(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    mock_monitor = MagicMock()
    mock_monitor._timeout = 1
    
    mock_logger = MagicMock() 
    
    real_email_alerter = EmailAlert()
    
    mock_detector = MagicMock()
    faulty_ip = "10.128.0.5"
    critical_lvl = LogLevel.CRITICAL
    
    mock_detector.get_alerts.return_value = {
        faulty_ip: {'level': critical_lvl}
    }

    kibble_inst = Kibble(
        monitors=[mock_monitor], 
        loggers=[mock_logger],
        alerters=[real_email_alerter], 
        detector=mock_detector, 
        interval=10
    )

    alerts = kibble_inst.detector.get_alerts()
    for endpoint in alerts.keys():
        for alerter in kibble_inst.alerters:
            alerter.alert(f"ALERT FOR {endpoint}", alerts[endpoint]['level'])

    mock_server.login.assert_called_once()
    args, _ = mock_server.sendmail.call_args
    sender = args[0]
    receiver = args[1]
    full_email_text = args[2]

    assert sender == "kibblealert@gmail.com"
    assert receiver == "kibblealert@gmail.com"
    assert f"ALERT FOR {faulty_ip}" in full_email_text
    assert "CRITICAL" in full_email_text