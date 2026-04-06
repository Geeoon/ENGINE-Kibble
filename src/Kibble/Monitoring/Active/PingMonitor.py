"""
Implements the PingMonitor
"""

import re
import subprocess
import time

from Kibble.Monitoring import StatusMonitor


class PingMonitor(StatusMonitor):
    """
    Monitors the status of endpoints with the system ping
    """

    def __str__(self):
        return "ICMP"

    def _get_target_address(self, target: dict) -> str:
        """
        Returns the address to ping

        :param target: a target status dict
        :return: the hostname if available, otherwise the IP address
        """
        return target["details"]["hostname"] or target["details"]["ip"]

    def _ping_target(self, address: str) -> subprocess.CompletedProcess:
        """
        Pings the given address once using the system ping command

        :param address: the hostname or IP address to ping
        :return: the completed process result
        """
        return subprocess.run(
            ["ping", "-c", "1", "-W", str(self._timeout), address],
            capture_output=True,
            text=True,
            check=False,
        )

    def _get_latency(self, output: str, alive: bool) -> int:
        """
        Parses the latency from ping output

        :param output: ping command output
        :param alive: whether the ping was successful
        :return: the latency in milliseconds, or timeout * 1000 if unreachable
                 or the latency could not be parsed
        """
        if alive:
            match = re.search(r"time[=<]([0-9.]+)\s*ms", output)
            if match:
                return round(float(match.group(1)))
        return self._timeout * 1000

    async def update_status(self):
        """
        Pings all monitored endpoints and updates their status
        """
        for target_id, target in self._status.items():
            address = self._get_target_address(target)
            result = self._ping_target(address)
            alive = result.returncode == 0

            target["status"] = {
                "alive": alive,
                "latency": self._get_latency(result.stdout, alive),
                "last_updated": round(time.time() * 1000),
            }