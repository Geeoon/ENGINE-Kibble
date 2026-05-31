"""
Collects CPU usage, memory usage, temperature, disk usage, and network io
on an edge node.
"""

import datetime
import time
from KibbleDaemon.collectors import CpuCollector, DiskCollector, MemoryCollector, TemperatureCollector, NetworkIoCollector, PowerCollector

INTERVAL = 30  # seconds between collections

cpu_collector = CpuCollector()
memory_collector = MemoryCollector()
# temp will only work on linux for (psutil temp only works on linux)
temperature_collector = TemperatureCollector()
power_collector = PowerCollector()
disk_collector = DiskCollector()
network_io_collector = NetworkIoCollector()

records = []  # This will be changed once we have the protocol defined


def run(stop_event=None):
    """
    Collects telemetry in a loop until stop_event is set or the process exits.
    """
    # This structure is needed for windows service to work
    while not (stop_event and stop_event.is_set()):
        recv_bps, sent_bps = network_io_collector.read_bps()
        records.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cpu_percent": cpu_collector.read(),
            "memory_percent": memory_collector.read(),
            "temperature_celsius": temperature_collector.read(),
            "disk_usage_percent": disk_collector.read(),
            "network_recv_bps": recv_bps,
            "network_sent_bps": sent_bps,
        })
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run()
