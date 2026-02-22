import time
import datetime
from Kibble.Logging import LogLevel

# can add more for different types of events (e.g. high latency, etc.)
def ping_event(endpoint_ip: str, status_data: dict, severity: LogLevel = LogLevel.CRITICAL) -> dict:
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    return {
        "timestamp": timestamp,
        "event_type": "endpoint_down",  # this is wrong
        "endpoint": {
            "ip": endpoint_ip
        },
        "status": {
            "alive": status_data.get("alive", False),
            "latency_ms": status_data.get("latency", 0),
            "last_updated_ms": status_data.get("last_updated", timestamp.isoformat())
        }
    }

def device_info(endpoint_ip: str, status_data: dict ):
    timestamp_ms = round(time.time() * 1000)
    return {
        "device_ip": endpoint_ip,
        "hostname": status_data.get("hostname", ""),
    }
