"""
Detector Test 1: Severity Correctness
Ensures difference between normal latency, high latency (Warning),
system errors (Error), and unreachable devices (Critical).
"""

import pytest
from Kibble.Detecting.LatencyDetector import LatencyDetector
from Kibble.Logging import LogLevel, ping_event

def test_severity_levels_for_different_latencies():
    """
    Test that the detector assigns the correct LogLevel based on latency data.
    Based on LatencyDetector defaults: warn=500, error=2000.
    """
    detector = LatencyDetector(depth=2, warn_thresh=500, error_thresh=2000)
    ip = "10.128.0.10"

    # normal latency (<= threshold)
    status_normal = {'alive': True, 'latency': 500}
    level_normal = detector.get_level(ip, status_normal)
    assert level_normal == LogLevel.INFO, "500ms should still be LogLevel.INFO"

    # high latency (> warning threshold)
    status_slow = {'alive': True, 'latency': 501}
    level_slow = detector.get_level(ip, status_slow)
    assert level_slow == LogLevel.WARNING, "501ms should trigger LogLevel.WARNING"

    # error (> error threshold)
    status_error = {'alive': True, 'latency': 2001}
    level_error = detector.get_level(ip, status_error)
    assert level_error == LogLevel.ERROR, "2001ms should trigger LogLevel.ERROR"

    # unreachable (down device)
    status_down = {'alive': False, 'latency': 0}
    level_down = detector.get_level(ip, status_down)
    assert level_down == LogLevel.CRITICAL, "Unreachable device must be LogLevel.CRITICAL"



def test_ping_event_schema_integration():
    """
    Ensures the ping_event formatter preserves the status data correctly
    """
    ip = "10.128.0.11"
    status = {'alive': True, 'latency': 600}
    
    detector = LatencyDetector()
    assigned_level = detector.get_level(ip, status)
    
    event = ping_event(ip, status, assigned_level)
    
    assert event['endpoint']['ip'] == ip
    assert event['status']['latency_ms'] == 600
    assert event['status']['alive'] is True
    assert assigned_level == LogLevel.WARNING

if __name__ == '__main__':
    test_severity_levels_for_different_latencies()
    test_ping_event_schema_integration()
    print("Detector Severity Tests: PASS")