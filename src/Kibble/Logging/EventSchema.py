import time
from Kibble.Logging import LogLevel

# can add more for different types of events (e.g. high latency, etc.)
def abnormal_ping_event(endpoint_ip: str, status_data: dict, severity: LogLevel = LogLevel.CRITICAL) -> dict:
    timestamp_ms = round(time.time() * 1000)
    return {
        "timestamp": timestamp_ms,
        "severity": severity.value[0],  # String like "critical"
        "event_type": "endpoint_down",
        "endpoint": {
            "ip": endpoint_ip
        },
        "status": {
            "alive": status_data.get("alive", False),
            "latency_ms": status_data.get("latency", 0),
            "last_updated_ms": status_data.get("last_updated", timestamp_ms)
        }
    }