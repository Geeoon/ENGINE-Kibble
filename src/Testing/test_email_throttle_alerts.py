"""
Email Alerting Test 3: Prevent Alert Spam (Throttling)
Only trigger alert when severity increases, creating only one email per error
"""

import pytest
from Kibble.Detecting.LatencyDetector import LatencyDetector
from Kibble.Logging import LogLevel

def test_detector_throttling_logic():
    """
    device goes down and stays down, system should only create 1 failure
    """
    detector = LatencyDetector(depth=2)
    ip = "10.128.0.5"

    detector.get_level(ip, {'alive': False, 'latency': 0})
    alerts_1 = detector.get_alerts()
    
    assert ip in alerts_1, "Initial failure should trigger an alert"
    assert alerts_1[ip]['level'] == LogLevel.CRITICAL

    # device is still down
    detector.get_level(ip, {'alive': False, 'latency': 0})
    alerts_2 = detector.get_alerts()
    
    assert ip not in alerts_2, "Persistent fault should not trigger a duplicate alert"

def test_alert_escalation_logic():
    """
    device is in warning then goes down to critical, creating new system alert
    """
    detector = LatencyDetector(depth=2, low_thresh=500)
    ip = "10.128.0.6"

    detector.get_level(ip, {'alive': True, 'latency': 600})
    assert ip in detector.get_alerts(), "Should alert for initial latency warning"

    detector.get_level(ip, {'alive': False, 'latency': 0})
    
    alerts = detector.get_alerts()
    assert ip in alerts, "Should alert, status escalates from Warning to Critical"
    assert alerts[ip]['level'] == LogLevel.CRITICAL

if __name__ == '__main__':
    test_detector_throttling_logic()
    test_alert_escalation_logic()
    print("Alert Throttling and Escalation Tests: PASS")
