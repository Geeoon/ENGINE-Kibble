"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "BaseClientHandler",
    "BaseServer",
]

import logging
import socket
import threading
import time
from abc import ABC, abstractmethod

from SCPISimulator.utils.printing import Hexdump


class BaseClientHandler(threading.Thread, ABC):
    """
    Base class for client connection handler. Manages communication with
    a single client.
    """

    def __init__(
            self,
            connection: socket.socket,
            address: tuple[str, int]
    ):
        """
        :param connection: Socket connection to client
        :param address: Client address (IP address and port tuple)
        """
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

        self._connection = connection
        self._address = address

    @abstractmethod
    def _handle_packet(self, data: bytes) -> bytes | None:
        """
        Handler function for incoming client data. Data returned by this
        function will be sent back to the client.

        :param data: Data received from client
        :return: Data to send back to client or None
        """

    def run(self):
        self._logger.info("Connected by %s", self._address)

        with self._connection:
            # Run forever (until client disconnects)
            while True:
                # Receive data from client
                data = self._connection.recv(1024)
                # If we get a 0 length packet, client disconnected
                if len(data) == 0:
                    break
                self._logger.debug(
                    "Received data:\n%s",
                    Hexdump(data)
                )
                # Call packet handler
                response = self._handle_packet(data)
                # If handler returned a response, send to client
                if response is not None:
                    self._logger.debug(
                        "Sending data:\n%s",
                        Hexdump(response)
                    )
                    self._connection.sendall(response)

                # Release GIL
                time.sleep(0)

        self._logger.info("Client disconnected")


class BaseServer(threading.Thread, ABC):
    """
    Base class for TCP servers.

    CLIENT_HANDLER_CLASS must be initialized on subclasses.
    """

    CLIENT_HANDLER_CLASS: type[BaseClientHandler]

    def __init__(
            self,
            server_address: str,
            server_port: int,
    ):
        """
        :param server_address: Address to host server on
        :param server_port: Port for server to listen on
        """
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

        self._server_address = server_address
        self._server_port = server_port

        self._client_handlers: list[BaseClientHandler] = []

    def run(self):
        # Create TCP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Bind socket to localhost
            s.bind((self._server_address, self._server_port))

            # Listen for incoming connection
            s.listen()
            self._logger.info("Server listening...")

            # Run forever
            while True:
                try:
                    # Accept a new connection
                    conn, addr = s.accept()

                    # Create and start client handler
                    handler = self.CLIENT_HANDLER_CLASS(conn, addr)
                    # Register handler so it can be closed properly later
                    self._client_handlers.append(handler)
                    handler.start()

                    # Release GIL
                    time.sleep(0)

                except KeyboardInterrupt:
                    self._logger.info(
                        "Keyboard interrupt received, stopping server"
                    )
                except Exception:
                    self._logger.exception("Unknown error occurred")
