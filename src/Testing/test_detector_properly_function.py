"""
Detector Test 2: Reachable Host Detection
Verifies that a healthy, normal, reachable device is properly detected 
and does not trigger alerts
"""

import pytest
from Kibble.Detecting.LatencyDetector import LatencyDetector
from Kibble.Logging import LogLevel

def test_reachable_host_detection_and_silence():
    """
    Scenario: A device is online with healthy latency (20ms).
    System should log it as INFO and send no alerts
    """
    detector = LatencyDetector(depth=2, low_thresh=500)
    healthy_ip = "192.168.1.50"
    
    healthy_status = {'alive': True, 'latency': 20}
    
    detected_level = detector.get_level(healthy_ip, healthy_status)
    
    assert detected_level == LogLevel.DEBUG, f"Expected DEBUG for 20ms, got {detected_level.name}"

    # The detector should only alert if the level is > DEBUG
    alerts = detector.get_alerts()
    
    assert healthy_ip not in alerts, "Alert was triggered for a healthy reachable host!"
    assert len(alerts) == 0, "Alert dictionary should be empty for normal operation"

def test_recovery_from_fault_to_reachable():
    """
    Scenario: A device was DOWN (Critical), but is now UP (Info).
    Ensure it doesn't trigger a 'fault' alert.
    """
    detector = LatencyDetector(depth=2)
    ip = "192.168.1.60"

    # Device is initially down
    detector.get_level(ip, {'alive': False, 'latency': 0})
    initial_alerts = detector.get_alerts()
    assert ip in initial_alerts, "Should have alerted for initial failure"

    # Device recovers and is now reachable
    detector.get_level(ip, {'alive': True, 'latency': 15})
    
    recovery_alerts = detector.get_alerts()
    assert recovery_alerts.get(ip, {}).get('level') == LogLevel.DEBUG, "Recovery should emit DEBUG level, not a fault alert"

if __name__ == '__main__':
    test_reachable_host_detection_and_silence()
    test_recovery_from_fault_to_reachable()
    print("Reachable Host Tests: PASS")
