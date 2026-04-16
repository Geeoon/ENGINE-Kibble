"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "hex_str",
    "hexdump",
    "Hexdump",
    "format_sn",
]

from typing import Literal

from SCPISimulator.utils.data import value_sn

_sn_prefixes = {
    24: "Y",
    21: "Z",
    18: "E",
    15: "P",
    12: "T",
    9: "G",
    6: "M",
    3: "k",
    0: " ",
    -3: "m",
    -6: "u",
    -9: "n",
    -12: "p",
    -15: "f",
    -18: "a",
    -21: "z",
    -24: "y",
}

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def hex_str(
        data: bytes,
        hex_fmt: Literal["x", "X"] = "x",
        prefix: bool = True,
        space: bool = True,
) -> str:
    """
    Formats a bytes object as a string of hex bytes.

    :param data: Data to format
    :param hex_fmt: Hex format string 'x' for lowercase hex, 'X' for
        uppercase hex
    :param prefix: If '0x' prefix should be included
    :param space: If space should be added between octets
    :return: Hex string
    """
    prefix_str = "0x " if prefix else ""
    space_str = " " if space else ""
    return prefix_str + space_str.join(f"{x:02{hex_fmt}}" for x in data)


def hexdump(
        data: bytes,
        addr: int = 0x0,
        hex_fmt: Literal["x", "X"] = "x"
) -> str:
    """
    Formats a bytes object as a multiline hexdump.

    :param data: Data to format
    :param addr: Data start address
    :param hex_fmt: Hex format string 'x' for lowercase hex, 'X' for
        uppercase hex
    :return: Hexdump string
    """
    # Magic numbers are needed for counts/spacing for formatting
    # pylint: disable=magic-value-comparison

    ret = ""

    # Count number of lines
    lines = (len(data) + 15) // 16

    for i in range(lines):
        # Single line of bytes
        line = data[i * 16:(i + 1) * 16]

        # Address
        ret += f"{addr:08{hex_fmt}}  "
        addr += 0x10

        # Hex
        for j in range(16):
            ret += f"{line[j]:02{hex_fmt}}" if j < len(line) else "  "
            ret += "-" if j == 7 else " "

        # ASCII
        ret += " |"
        for j in range(16):
            ret += chr(line[j]) \
                if (j < len(line) and 0x20 <= line[j] <= 0x7E) \
                else "."
            ret += "-" if j == 7 else ""
        ret += "|"

        # Newline if this is not the last line
        if i < lines - 1:
            ret += "\n"

    return ret


class Hexdump:
    """
    Class-version of hexdump method. Useful for using hexdumps in logging
    since this will not "process" the hexdump if the log is not emitted.
    """

    def __init__(
            self,
            data: bytes,
            addr: int = 0x0,
            hex_fmt: Literal["x", "X"] = "x"
    ):
        self.data = data
        self.addr = addr
        self.hex_fmt = hex_fmt

    def __str__(self):
        return hexdump(self.data, self.addr, self.hex_fmt)


def format_sn(
        value: float,
        units: str = "",
        digits: int = 1,
        decimals: int = 0,
        minus: bool = False
) -> str:
    """
    Formats a number using sn prefixes and units.

    :param value: Value to format
    :param units: Units for value
    :param digits: Max number of digits to display (used for alignment)
    :param decimals: Number of decimal places to display
    :param minus: If space should be left for a minus sign (used for
        alignment)
    :return: Formatted string
    """
    # If decimal is nonzero, 'total width' in format needs to include
    # the decimal point
    if decimals > 0:
        digits += 1
    aval, mag = value_sn(value)
    # Do some f-string magic to get the final value
    return (
        f"{aval:{' ' if minus else ''}{digits}.{decimals}f} "
        f"{_sn_prefixes[mag]}{units}"
    )
