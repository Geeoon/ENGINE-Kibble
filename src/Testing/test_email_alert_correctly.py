"""
Email Alerting Test 1: Email alert occurs on failure
Ensuring email alerting system properly transmits an alert when device goes down.
"""

import pytest
from unittest.mock import patch, MagicMock
from Kibble.Alerting import EmailAlert
from Kibble.Logging import LogLevel

@patch('smtplib.SMTP_SSL')
def test_email_alert_functionality(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    alert_system = EmailAlert()
    test_data = {"device_id": "RPi_01", "status": "down"}
    test_level = LogLevel.ERROR

    success = alert_system.alert(test_data, test_level)

    assert success is True
    mock_server.login.assert_called_once()
    
    # verify email content
    _, _, msg = mock_server.sendmail.call_args[0]
    assert "RPi_01" in msg
    assert "ERROR" in msg