"""
Lease Manager Tests
"""

import pytest
import mongomock
from datetime import datetime, timedelta, timezone
from Kibble.Election.LeaseManager import LeaseManager

def test_acquire_and_redundancy_limits():
    """
    Ensure that up to max redundancy_factor nodes may grab a lease for a device    """
    client = mongomock.MongoClient()
    db_name = "kibble_test"
    devices = ["device_A", "device_B"]

    lm1 = LeaseManager(client, monitor_id=1, ttl=30, redundancy_factor=2, db_name=db_name)
    lm2 = LeaseManager(client, monitor_id=2, ttl=30, redundancy_factor=2, db_name=db_name)
    lm3 = LeaseManager(client, monitor_id=3, ttl=30, redundancy_factor=2, db_name=db_name)

    # Monitor 1 grabs leases for all devices
    acquired1 = lm1.acquire_leases(devices)
    assert set(acquired1) == set(devices)
    assert len(lm1.get_my_devices()) == 2

    # Monitor 2 grabs leases for all devices 
    acquired2 = lm2.acquire_leases(devices)
    assert set(acquired2) == set(devices)

    # Monitor 3 tries to grab lease but redundancy limit is reached
    acquired3 = lm3.acquire_leases(devices)
    assert len(acquired3) == 0

def test_renew_leases():
    """Ensure renewing a lease extends expiration time"""
    client = mongomock.MongoClient()
    lm = LeaseManager(client, monitor_id=1, ttl=30, db_name="kibble_test")
    
    lm.acquire_leases(["device_C"])
    
    db = client["kibble_test"]
    past_expiry = datetime.now(timezone.utc) + timedelta(seconds=5)
    db["device_leases"].update_many({}, {"$set": {"expires_at": past_expiry}})
    
    # Renew leases
    renewed_count = lm.renew_leases()
    assert renewed_count == 1
    
    # Confirm the new expires_at is ~30 seconds again
    doc = db["device_leases"].find_one({"device_id": "device_C"})
    time_left = (doc["expires_at"].replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
    assert time_left > 25

def test_cleanup_expired_leases():
    """Ensure expired leases are properly dropped and ownership released"""
    client = mongomock.MongoClient()
    lm = LeaseManager(client, monitor_id=1, ttl=30, db_name="kibble_test")
    
    lm.acquire_leases(["device_D"])
    assert len(lm.get_my_devices()) == 1
    
    # Manually expire lease
    db = client["kibble_test"]
    expired_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    db["device_leases"].update_many({}, {"$set": {"expires_at": expired_time}})
    
    cleaned_count = lm.cleanup_expired()
    assert cleaned_count == 1
    
    # Verify monitor no longer owns the device
    assert len(lm.get_my_devices()) == 0
    assert db["device_leases"].count_documents({}) == 0