"""
Detector Test 3: High Latency Detection
Verifies that delays trigger the correct warning severity 
and appear in the alert map
"""

import pytest
from Kibble.Detecting.LatencyDetector import LatencyDetector
from Kibble.Logging import LogLevel

def test_high_latency_warning_trigger():
    """
    Device is alive but responding slowly at 600ms which is above WARNING threshold
    Level should be WARNING and an alert should be generated
    """
    detector = LatencyDetector(depth=2, low_thresh=200, medium_thresh=500, high_thresh=2000)
    ip = "192.168.1.75"
    
    # Set up alive device with 600ms latency
    slow_status = {'alive': True, 'latency': 600}
    
    level = detector.get_level(ip, slow_status)
    assert level == LogLevel.MEDIUM, f"Expected WARNING for 600ms, got {level.name}"

    # check alerting map for warning
    alerts = detector.get_alerts()
    assert ip in alerts, "High latency should have triggered an alert entry"
    assert alerts[ip]['level'] == LogLevel.MEDIUM

def test_latency_escalation_to_error():
    detector = LatencyDetector(depth=5, low_thresh=200, medium_thresh=500, high_thresh=2000)
    ip = "192.168.1.80"

    detector.get_level(ip, {'alive': True, 'latency': 600})
    detector.get_alerts() 

    detector.get_level(ip, {'alive': True, 'latency': 2500})
    
    alerts = detector.get_alerts()
    assert ip in alerts, "Escalation should trigger an alert immediately"
    assert alerts[ip]['level'] == LogLevel.HIGH

    detector.get_level(ip, {'alive': True, 'latency': 2500})
    assert ip not in detector.get_alerts(), "Persistent same-level faults should be throttled"
