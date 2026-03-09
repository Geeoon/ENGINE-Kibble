"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
import argparse
import time
import tomllib

from SCPISimulator.anomalies import AnomalyManager
from SCPISimulator.devices import (
    SCPIPowerSupply,
)
from SCPISimulator.devices.base import SCPIDevice
from SCPISimulator.server.scpi import SCPIClientHandler, SCPIServer
from SCPISimulator.utils.loggers import setup_minimal_logger


# pylint: disable-next=missing-function-docstring
def main():
    # Dictionary of devices that can be selected from (keys are argparse
    # choice name)
    devices: dict[str, type[SCPIDevice]] = {
        "power_supply": SCPIPowerSupply
    }

    # Configure default minimal logger
    logger = setup_minimal_logger(20, colored=False)

    parser = argparse.ArgumentParser(
        prog="SCPI Simulator",
        description=(
            "Standard Commands for Programmable Instruments (SCPI) device "
            "simulator."
        )
    )

    parser.add_argument(
        "-a",
        "--address",
        default="127.0.0.1"
    )

    parser.add_argument(
        "-p",
        "--port",
        default=5025,
        type=int,
    )

    parser.add_argument(
        "-d",
        "--device",
        required=True,
        choices=list(devices.keys())
    )

    parser.add_argument(
        "-c",
        "--config",
    )

    args = parser.parse_args()

    # Load configuration from file if supplied
    with open(args.config, "rb") as f:
        config = tomllib.load(f)

    # Create anomaly manager
    anomaly_manager = AnomalyManager(config)

    # Create a device instance based on selected device
    device_instance = devices[args.device]()

    # Set device instance for SCPI client handler
    SCPIClientHandler.device = device_instance
    SCPIClientHandler.anomaly_manager = anomaly_manager

    logger.info("Starting server on %s:%s", args.address, args.port)

    # Create server instance and run (on its own thread
    server = SCPIServer(
        server_address=args.address,
        server_port=args.port,
    )
    server.start()

    while True:
        anomaly_manager.update()

        if anomaly_manager.settings.drop_clients:
            # Close all client connections
            for handler in server._client_handlers:
                handler._connection.close()

        # Release the GIL
        time.sleep(0.1)


if __name__ == "__main__":
    main()
