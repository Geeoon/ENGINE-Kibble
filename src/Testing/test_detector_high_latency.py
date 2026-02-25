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
    detector = LatencyDetector(depth=2, warn_thresh=500)
    ip = "192.168.1.75"
    
    # Set up alive device with 600ms latency
    slow_status = {'alive': True, 'latency': 600}
    
    level = detector.get_level(ip, slow_status)
    assert level == LogLevel.WARNING, f"Expected WARNING for 600ms, got {level.name}"

    # check alerting map for warning
    alerts = detector.get_alerts()
    assert ip in alerts, "High latency should have triggered an alert entry"
    assert alerts[ip]['level'] == LogLevel.WARNING

def test_latency_escalation_to_error():
    """
    Increasing latency from 600ms (Warning) to 2500ms (Error)
    Level should be ERROR and alert should be triggered
    """
    detector = LatencyDetector(depth=2, warn_thresh=500, error_thresh=2000)
    ip = "192.168.1.80"

    detector.get_level(ip, {'alive': True, 'latency': 600})
    detector.get_alerts() # Clear initial alert from map

    # increase latency to Error level
    detector.get_level(ip, {'alive': True, 'latency': 2500})
    
    level = detector.get_level(ip, {'alive': True, 'latency': 2500})
    assert level == LogLevel.ERROR
    
    alerts = detector.get_alerts()
    assert ip in alerts, "Escalation from Warning to Error should trigger an alert"
    assert alerts[ip]['level'] == LogLevel.ERROR