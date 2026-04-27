"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "SCPIClientHandler",
    "SCPIServer",
]

import socket
import time

from SCPISimulator.anomalies import AnomalyManager
from SCPISimulator.devices.base import SCPIDevice
from SCPISimulator.server.base import BaseClientHandler, BaseServer


class SCPIClientHandler(BaseClientHandler):
    """Handler to connect a client to a simulated SCPI device."""

    device: SCPIDevice
    anomaly_manager: AnomalyManager | None = None

    def __init__(self, connection: socket.socket, address: tuple[str, int]):
        super().__init__(connection, address)
        self._buffer = b""

    def _handle_scpi_packet(self, data: bytes) -> bytes | None:
        # Decode bytes to string
        string = data.decode("utf-8")

        # Force to lowercase and strip any leading/trailing whitespace for
        # easier SCPI parsing
        string = string.lower().strip()

        self._logger.info("Got packet: '%s'", string)

        # Call device handler and get response
        response = self.device.handle_command(string)

        # If there's a response, append \r\n, encode it back to bytes,
        # and send
        if response is not None:
            return (response + "\r\n").encode("utf-8")

        return None

    def _handle_packet(self, data: bytes) -> bytes | None:
        # Delay if configured
        if self.anomaly_manager is not None:
            time.sleep(self.anomaly_manager.settings.latency)

        # SCPI is newline-delimited, buffer then parse if a partial
        # packet is received.
        # Append data to buffer
        self._buffer += data

        # Check if we have one or more complete packets
        packets = self._buffer.split(b"\n")

        # 1 packet means the delimiter was never found
        if len(packets) < 2:
            return None

        full_response = b""
        # Skip last packet (it's the carryover)
        for packet in packets[:-1]:
            # Don't respond if in "no_response" anomaly state
            if (self.anomaly_manager is not None
                    and self.anomaly_manager.settings.no_response):
                continue
            # Handle individual packets
            response = self._handle_scpi_packet(packet)
            # Append response to full response if it's not None
            if response is not None:
                full_response += response

        # Last packet is always carryover, save for next time
        self._buffer = packets[-1]

        # Return response
        return full_response


class SCPIServer(BaseServer):
    """
    Server to handle incoming client connections using SCPIClientHandler.
    """
    CLIENT_HANDLER_CLASS = SCPIClientHandler
