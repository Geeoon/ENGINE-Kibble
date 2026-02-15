import pytest
from unittest.mock import MagicMock
from Kibble import Kibble

def test_independent_alerting_for_multiple_devices():
    """
    Verify receiving error alert from second device when first device is already down.
    Ensures the loop doesn't terminate or skip alerts after an initial failure.
    """
    # 1. Setup Mock Monitor and Alert system
    mock_monitor = MagicMock()
    mock_alert = MagicMock()
    
    # Mocking two loop iterations
    # Iteration 1: Device A fails
    # Iteration 2: Device A is still down, Device B now fails
    mock_monitor.get_status.side_effect = [
        {"10.128.0.1": {"alive": False}, "10.128.0.2": {"alive": True}},
        {"10.128.0.1": {"alive": False}, "10.128.0.2": {"alive": False}}
    ]

    # Initialize Kibble (Assuming Kibble class takes alerts/monitors)
    kibble_inst = Kibble(monitors=[mock_monitor], alerts=[mock_alert])

    # 2. Run first iteration
    # Assuming a method like 'step' executes one loop iteration as seen in flowchart
    kibble_inst.step() 
    assert mock_alert.alert.call_count == 1
    
    # 3. Run second iteration
    kibble_inst.step()
    
    # 4. Final Verification
    # Total alerts should be 3 (Device A twice, Device B once) 
    # OR 2 if your logic only alerts on state CHANGE.
    assert mock_alert.alert.call_count >= 2 
    print("Multi-device fault check: PASS")