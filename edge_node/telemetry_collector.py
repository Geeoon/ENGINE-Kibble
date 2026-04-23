"""
Collects CPU usage, memory usage, and temperature on an edge node.
"""

import datetime
import time
from collectors import CpuCollector, MemoryCollector, TemperatureCollector, PowerCollector

INTERVAL = 30  # seconds between collections

cpu_collector = CpuCollector()
memory_collector = MemoryCollector()
temperature_collector = TemperatureCollector()
power_collector = PowerCollector()

records = [] # This will be changed once we have the protocol defined

while True:
    now = datetime.datetime.now(datetime.timezone.utc)
    records.append({
        "timestamp": now.isoformat(),
        "cpu_percent": cpu_collector.read(),
        "memory_percent": memory_collector.read(),
        "temperature_celsius": temperature_collector.read(),
        "power_usage_w": power_collector.read(),
    })
    time.sleep(INTERVAL)
