import datetime
from typing import Optional

from bson import ObjectId  # type: ignore[import-untyped]

from Kibble.Logging import LogLevel


def ICMP(endpoint_ip: str, status_data: dict, severity: LogLevel = LogLevel.CRITICAL, device_id: Optional[ObjectId] = None) -> dict:
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    endpoint: dict = {"ip": endpoint_ip}
    doc: dict = {
        "timestamp": timestamp,
        "event_type": "endpoint_down",
        "endpoint": endpoint,
        "status": {
            "alive": status_data.get("alive", False),
            "latency_ms": status_data.get("latency", 0),
            "last_updated_ms": status_data.get("last_updated", timestamp.isoformat()),
        },
        "severity_level": severity.value[0],
    }
    if device_id is not None:
        doc["device_id"] = device_id
    return doc

def device_info(device_type: str, endpoint_ip: str, status_data: dict ):
    return {
        "device_type": device_type,
        "device_ip": endpoint_ip, # device ip from the database # need ot make capable of supporting multiple?
        "hostname": status_data.get("hostname", ""), 
        "mac_address": status_data.get("mac_address", ""),
    }


#FIX/REVIEW 
def device_types(name: str, protocols_supported: list[str]):
    return {
        "name": name,
        "protocols_supported": list(protocols_supported),
    }

# retrieve hostname if no hostname, ip address as fallback 
# mac address 

