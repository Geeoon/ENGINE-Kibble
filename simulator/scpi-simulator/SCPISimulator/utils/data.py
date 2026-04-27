"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    # Enums
    "DataType",
    "ByteOrder",
    "Endianness",
    # Conversion dicts
    "struct_fmt_dtype",
    "dtype_struct_fmt",
    "dtype_len",
    "struct_fmt_endianness",
    "dtype_signed",
    # Functions
    "value_sn",
    "clamp",
]

import math
from enum import StrEnum


class DataType(StrEnum):
    """Python struct datatypes"""
    INT8 = "b"
    INT16 = "h"
    INT32 = "i"
    INT64 = "q"
    UINT8 = "B"
    UINT16 = "H"
    UINT32 = "I"
    UINT64 = "Q"
    FLOAT = "f"
    DOUBLE = "d"
    BYTES = "s"


class ByteOrder(StrEnum):
    """Byte ordering"""
    BIG = "big"
    LITTLE = "little"
    NETWORK = "big"


Endianness = ByteOrder

# Datatype conversion dictionaries

# DataTypes -> "dtype" string aliases
struct_fmt_dtype: dict[str, list[str]] = {
    DataType.INT8: ["int8", "i8", "INT8_TYPE"],
    DataType.INT16: ["int16", "i16", "INT16_TYPE"],
    DataType.INT32: ["int32", "i32", "INT32_TYPE"],
    DataType.INT64: ["int64", "i64", "INT64_TYPE"],
    DataType.UINT8: ["uint8", "u8", "UINT8_TYPE", "BOOL_TYPE"],
    DataType.UINT16: ["uint16", "u16", "UINT16_TYPE"],
    DataType.UINT32: ["uint32", "u32", "UINT32_TYPE"],
    DataType.UINT64: ["uint64", "u64", "UINT64_TYPE"],
    DataType.FLOAT: ["float", "float32", "f32"],
    DataType.DOUBLE: ["double", "d64"],
    DataType.BYTES: ["bytes"],
}

# "dtype" string aliases -> DataTypes
dtype_struct_fmt = {
    v: k
    for k, values in struct_fmt_dtype.items()
    for v in values
}

# DataType byte length
dtype_len = {
    DataType.INT8: 1,
    DataType.INT16: 2,
    DataType.INT32: 4,
    DataType.INT64: 8,
    DataType.UINT8: 1,
    DataType.UINT16: 2,
    DataType.UINT32: 4,
    DataType.UINT64: 8,
    DataType.FLOAT: 4,
    DataType.DOUBLE: 8,
}

# ByteOrder -> Python struct fmt characters
struct_fmt_endianness = {
    ByteOrder.BIG: ">",
    ByteOrder.LITTLE: "<",
    ByteOrder.NETWORK: "!",
}

# If DataType is signed
dtype_signed = {
    DataType.INT8: True,
    DataType.INT16: True,
    DataType.INT32: True,
    DataType.INT64: True,
    DataType.UINT8: False,
    DataType.UINT16: False,
    DataType.UINT32: False,
    DataType.UINT64: False,
    DataType.FLOAT: True,
    DataType.DOUBLE: True,
}


def value_sn(value: float) -> tuple[float, int]:
    """
    Converts a numeric value to scientific notation as a value, exponent
    tuple

    :param value: Value to convert
    :return: 2-tuple of base value, 10^x exponent
    """
    try:
        mag = int((math.floor(math.log10(value)) // 3) * 3)
    except ValueError:
        mag = 0
    aval = value / (10 ** mag)

    return aval, mag


def clamp(val: float, min_val: float, max_val: float) -> float:
    """
    Limits returned value between min_val and max_val.

    :param val: Value to limit. Will return this value if
        min_val <= val <= max_val.
    :param min_val: Minimum value to return
    :param max_val: Maximum value to return
    :return: Limited value
    """
    return max(min(max_val, val), min_val)
