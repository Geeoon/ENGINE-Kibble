import datetime
from typing import Optional

from bson import ObjectId  # type: ignore[import-untyped]

from Kibble.Logging import LogLevel

# Bump when event shape changes so consumers can branch on version.
EVENT_SCHEMA_VERSION = 1

# Event types for endpoint status (fixed set for queries/dashboards; aligns with observability conventions).
EVENT_TYPE_ENDPOINT_UP = "endpoint_up"
EVENT_TYPE_ENDPOINT_DOWN = "endpoint_down"


def ICMP(status_data: dict, severity: LogLevel = LogLevel.CRITICAL, device_id: Optional[ObjectId] = None) -> dict:
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    alive = status_data.get("alive", False)
    event_type = EVENT_TYPE_ENDPOINT_UP if alive else EVENT_TYPE_ENDPOINT_DOWN
    doc: dict = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "timestamp": timestamp,
        "event_type": event_type,
        "status": {
            "alive": alive,
            "latency_ms": status_data.get("latency", 0),
            "last_updated_ms": status_data.get("last_updated", timestamp.isoformat()),
        },
        "severity_level": severity.value[0],
    }
    if device_id is not None:
        doc["device_id"] = device_id
    return doc

def device_info(device_type_id: Optional[ObjectId], endpoint_ip: str, status_data: dict) -> dict:
    doc: dict = {
        "device_ip": endpoint_ip,
        "hostname": status_data.get("hostname", ""),
        "mac_address": status_data.get("mac_address", ""),
    }
    if device_type_id is not None:
        doc["device_type_id"] = device_type_id
    return doc


#FIX/REVIEW 
def device_types(name: str, protocols_supported: list[str]):
    return {
        "name": name,
        "protocols_supported": list(protocols_supported),
    }

# retrieve hostname if no hostname, ip address as fallback 
# mac address 

