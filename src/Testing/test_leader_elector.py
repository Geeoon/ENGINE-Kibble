"""
Leader Elector Tests
"""

import pytest
import mongomock
from datetime import datetime, timedelta, timezone
from Kibble.Election.LeaderElector import LeaderElector

def test_single_node_election():
    """singular node elects itself leader immediately"""
    client = mongomock.MongoClient()
    elector = LeaderElector(client=client, monitor_id=1, heartbeat_ttl=30, db_name="kibble_test")
    
    elector.register()
    leader_id = elector.elect_leader()
    
    assert leader_id == 1
    assert elector.is_leader is True

def test_multi_node_election_and_failover():
    """
    lowest monitor_id wins and if heartbeat expires, next lowest takes over
    """
    client = mongomock.MongoClient()
    db_name = "kibble_test"
    
    elector1 = LeaderElector(client=client, monitor_id=1, heartbeat_ttl=30, db_name=db_name)
    elector2 = LeaderElector(client=client, monitor_id=2, heartbeat_ttl=30, db_name=db_name)
    
    elector1.register()
    elector2.register()
    
    # Node 1 should win (lowest id)
    assert elector1.elect_leader() == 1
    assert elector2.elect_leader() == 1
    assert elector1.is_leader is True
    assert elector2.is_leader is False

    # Simulate Node 1 dying
    db = client[db_name]
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=40)
    db["monitors"].update_one({"monitor_id": 1}, {"$set": {"last_heartbeat": stale_time}})

    # Re-elect: Node 2 should promote itself
    assert elector2.elect_leader() == 2
    assert elector2.is_leader is True

def test_on_leader_change_callback():
    """Ensure callback occurs when leadership changes"""
    client = mongomock.MongoClient()
    elector = LeaderElector(client=client, monitor_id=5, db_name="kibble_test")
    
    callback_triggered = []
    def mock_callback(is_leader):
        callback_triggered.append(is_leader)
        
    elector.set_on_leader_change(mock_callback)
    elector.elect_leader()
    
    assert len(callback_triggered) == 1
    assert callback_triggered[0] is True