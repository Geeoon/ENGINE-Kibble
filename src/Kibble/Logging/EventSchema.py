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
    """Builds an ICMP endpoint-status event document for logging.

    Args:
        status_data: Dict with "alive", "latency", and "last_updated" status.
        severity: Log level (default CRITICAL).
        device_id: Required device ObjectId; must not be None.

    Returns:
        Event dict with schema_version, timestamp, event_type, status, severity_level, and device_id.

    Raises:
        ValueError: If device_id is None.
    """
    if device_id is None:
        raise ValueError("device_id is required")
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
        "device_id": device_id,
    }
    return doc

def device_info(device_type_id: Optional[ObjectId], endpoint_ip: str, status_data: dict) -> dict:
    """Builds a device-info document from endpoint IP and status data.

    Args:
        device_type_id: Optional device type ObjectId; included in doc if not None.
        endpoint_ip: The endpoint IP address (stored as device_ip).
        status_data: Dict with "hostname" and "mac_address" (default to "" if missing).

    Returns:
        Dict with device_ip, hostname, mac_address, and optionally device_type_id.
    """
    if device_type_id is None:
        raise ValueError("device_id is required")
    doc: dict = {
        "device_ip": endpoint_ip,
        "hostname": status_data.get("hostname", ""),
        "mac_address": status_data.get("mac_address", ""),
        "device_type_id": device_type_id,
    }
    return doc



def device_types(name: str, protocols_supported: list[str]):
    """Builds a device-type document with name and supported protocols.

    Args:
        name: Display name of the device type.
        protocols_supported: List of protocol identifiers (e.g. "ICMP"); copied into the doc.

    Returns:
        Dict with "name" and "protocols_supported".
    """
    return {
        "name": name,
        "protocols_supported": list(protocols_supported),
    }

