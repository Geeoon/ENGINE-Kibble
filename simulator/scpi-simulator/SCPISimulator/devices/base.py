"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
from __future__ import annotations

__all__ = [
    "BOOL_PATTERN",
    "FLOAT_PATTERN",
    "handler",
    "HandlerResponse",
    "SCPIDevice",
]

import re
from abc import ABC
from collections.abc import Callable
from typing import Any


BOOL_PATTERN = r"0|1|off|on"
FLOAT_PATTERN = r"[+-]?\d+(\.\d+)?(e\d+)?"

# Response data type for command handler methods.
#   - String indicates data to send back in response
#   - None indicates send no response (but command was handled)
HandlerResponse = str | None


class _Handler:
    """
    Command Handler class. Instances of this will be created by a wrapper
    function to allow Device command handler methods to be decorated.

    This allows all command handler methods to be found at runtime using
    getattr/isinstance. It also removes the pattern-matching logic from
    individual handler methods.
    """

    def __init__(
            self,
            pattern: str,
            func: Callable[[SCPIDevice, tuple[str, ...]], HandlerResponse]
    ):
        """
        :param pattern: Command pattern to match
        :param func: Function to execute if command pattern is matched
        """
        self._pattern = pattern
        # Compile regex pattern
        self._re_pattern = re.compile(pattern)
        self._func = func

    def __repr__(self) -> str:
        return f'<Handler "{self._pattern}">'

    def match(self, string: str) -> re.Match[str] | None:
        return self._re_pattern.fullmatch(string)

    def handle(
            self,
            instance: SCPIDevice,
            groups: tuple[str, ...]
    ) -> HandlerResponse:
        return self._func(instance, groups)


def handler(pattern: str):
    """
    Decorator for marking a method as a command handler method. Will
    wrap the method in a Handler instance with the provided pattern.

    :param pattern: Pattern to match Handler against
    :return: Wrapped method
    """

    def wrapper(
            func: Callable[[SCPIDevice, tuple[str, ...]], HandlerResponse]
    ):
        """
        Function to return a Handler-wrapped function.

        :param func: Function to wrap
        :return: Wrapped function
        """
        return _Handler(pattern, func)

    return wrapper


class SCPIDevice(ABC):
    """
    Base class for SCPI Devices.

    This implements some based handles for standard SCPI commands as well
    as the logic for finding command handlers at runtime
    """

    def __init__(self):
        # Get all handlers for this instance and index by path
        self._handlers: list[_Handler] = [
            getattr(self, key)
            for key in dir(self)
            if isinstance(getattr(self, key), _Handler)
        ]

    @handler(r"\*cls")
    def _cls(self, data: str) -> HandlerResponse:
        return "Hello World"

    def handle_command(self, data: str) -> HandlerResponse:
        """
        Handle a single SCPI command.

        :param data: Command to handle
        :return: Response to send back to client or None
        """
        # Check all handlers
        for handler_ in self._handlers:
            # See if handler pattern matches
            m = handler_.match(data)
            if m is not None:
                # If it does, actually handle the data (matched groups)
                return handler_.handle(self, m.groups())

        return None

