"""
Detector Test 1: Severity Correctness
Ensures difference between normal latency, high latency (Warning),
system errors (Error), and unreachable devices (Critical).
"""

import pytest
from Kibble.Detecting.LatencyDetector import LatencyDetector
from Kibble.Logging import LogLevel, ping_event

def test_severity_levels_for_different_latencies():
    detector = LatencyDetector(depth=2, low_thresh=200, medium_thresh=500, high_thresh=2000)
    ip = "10.128.0.10"

    # DEBUG: latency (<= low_thresh)
    status_debug = {'alive': True, 'latency': 200}
    assert detector.get_level(ip, status_debug) == LogLevel.DEBUG

    # LOW: latency (> low_thresh but <= medium_thresh)
    status_low = {'alive': True, 'latency': 201}
    assert detector.get_level(ip, status_low) == LogLevel.LOW

    # MEDIUM: latency (> medium_thresh)
    status_medium = {'alive': True, 'latency': 501}
    assert detector.get_level(ip, status_medium) == LogLevel.MEDIUM

    # HIGH: latency (> high_thresh)
    status_high = {'alive': True, 'latency': 2001}
    assert detector.get_level(ip, status_high) == LogLevel.HIGH

    # CRITICAL: unreachable
    status_down = {'alive': False, 'latency': 0}
    assert detector.get_level(ip, status_down) == LogLevel.CRITICAL

def test_ping_event_schema_integration():
    ip = "10.128.0.11"
    status = {'alive': True, 'latency': 600}
    
    # Pass thresholds so 600 triggers MEDIUM
    detector = LatencyDetector(low_thresh=200, medium_thresh=500)
    assigned_level = detector.get_level(ip, status)
    
    event = ping_event(ip, status, assigned_level)
    
    assert event['endpoint']['ip'] == ip
    assert event['status']['latency_ms'] == 600
    assert assigned_level == LogLevel.MEDIUM

if __name__ == '__main__':
    test_severity_levels_for_different_latencies()
    test_ping_event_schema_integration()
    print("Detector Severity Tests: PASS")
