import datetime
from typing import Optional

from bson import ObjectId  # type: ignore[import-untyped]

from Kibble.Logging import LogLevel

# Bump when event shape changes so consumers can branch on version.
EVENT_SCHEMA_VERSION = 1

# Bump when device_configuration document shape changes (device_configurations collection).
DEVICE_CONFIGURATION_SCHEMA_VERSION = 2

# Bump when interface_configuration document shape changes (interface_configurations collection).
INTERFACE_CONFIGURATION_SCHEMA_VERSION = 1

# Event types for endpoint status (fixed set for queries/dashboards; aligns with observability conventions).
EVENT_TYPE_ENDPOINT_UP = "endpoint_up"
EVENT_TYPE_ENDPOINT_DOWN = "endpoint_down"


def ICMP(status_data: dict, severity: LogLevel = LogLevel.CRITICAL, device_id: Optional[ObjectId] = None) -> dict:
    """Builds an ICMP endpoint-status event document for logging.

    Args:
        status_data: Input fields used to build ``status``: optional ``alive`` (default False),
            ``latency`` (default 0, stored as ``latency_ms``), ``last_updated`` (default: event
            ``timestamp`` as ISO string, stored as ``last_updated_ms``).
        severity: Log level (default CRITICAL).
        device_id: Required device ObjectId; must not be None.

    Returns:
        Event dict with ``schema_version``, ``timestamp``, ``event_type`` (``endpoint_up`` or
        ``endpoint_down`` from ``alive``), ``status`` (``alive``, ``latency_ms``, ``last_updated_ms``),
        ``severity_level``, and ``device_id``.

    Raises:
        ValueError: If device_id is None.
    """
    if device_id is None:
        raise ValueError("device_id is required")
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    alive = status_data.get("alive", False)
    event_type = EVENT_TYPE_ENDPOINT_UP if alive else EVENT_TYPE_ENDPOINT_DOWN
    doc: dict = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "timestamp": timestamp,
        "event_type": event_type,
        "status": {
            "alive": alive,
            "latency_ms": status_data.get("latency", 0),
            "last_updated_ms": status_data.get("last_updated", timestamp.isoformat()),
        },
        "severity_level": severity.value[0],
        "device_id": device_id,
    }
    return doc

def device_info(device_type_id: Optional[ObjectId], asset_tag: int) -> dict:
    """Builds the stable ``devices`` collection document (identity only).

    MongoDB adds ``_id``. Do not store IP/hostname/MAC here—use ``interface_configuration`` rows
    referenced from ``device_configuration``.

    Args:
        device_type_id: Device type ObjectId; required.
        asset_tag: Integer asset tag; should be unique per device (sparse unique index recommended).

    Returns:
        Dict with ``asset_tag`` and ``device_type_id``.

    Raises:
        ValueError: If device_type_id is None.
    """
    if device_type_id is None:
        raise ValueError("device_type_id is required")
    doc: dict = {
        "asset_tag": asset_tag,
        "device_type_id": device_type_id,
    }
    return doc



def device_types(name: str, protocols_supported: list[str]) -> dict:
    """Builds a device-type document with name and supported protocols.

    Args:
        name: Display name of the device type.
        protocols_supported: Protocol identifiers (e.g. ``"ICMP"``); shallow-copied into the returned dict.

    Returns:
        Dict with keys ``name`` and ``protocols_supported``.
    """
    return {
        "name": name,
        "protocols_supported": list(protocols_supported),
    }

def device_configuration(
    device_id: Optional[ObjectId],
    interfaces: list[ObjectId],
    applied_date: datetime.datetime,
) -> dict:
    """Builds a device-configuration snapshot: which interface rows apply at ``applied_date``.

    Per-interface IP/MAC/hostname live in ``interface_configurations``; this document only
    references them by ``_id`` (see ``interface_configuration``).

    Args:
        device_id: Device ObjectId; required.
        interfaces: Interface document ObjectIds (non-empty after inserts).
        applied_date: When this snapshot was observed or applied (timezone-aware recommended).

    Returns:
        Dict with ``schema_version``, ``device_id``, ``interfaces``, ``applied_date``.

    Raises:
        ValueError: If ``device_id`` is None or ``interfaces`` is empty.
    """
    if device_id is None:
        raise ValueError("device_id is required")
    if not interfaces:
        raise ValueError("interfaces must be non-empty")
    doc: dict = {
        "schema_version": DEVICE_CONFIGURATION_SCHEMA_VERSION,
        "device_id": device_id,
        "interfaces": list(interfaces),
        "applied_date": applied_date,
    }
    return doc


def interface_configuration(
    device_id: ObjectId,
    interface_name: str,
    ip_address: str,
    subnet_mask: str,
    default_gateway: str,
    hostname: str,
    mac_address: str,
    applied_date: datetime.datetime,
) -> dict:
    """Builds one row in ``interface_configurations`` (mutable network identity per interface).

    Args:
        device_id: Owning device ``_id``.
        interface_name: Interface key (e.g. ``\"default\"`` for the primary row from scans).
        ip_address: Current IPv4/IPv6 address (may be empty when only hostname is known).
        subnet_mask: Subnet mask for the interface.
        default_gateway: Default gateway for this interface.
        hostname: Resolved or configured hostname.
        mac_address: Interface MAC address.
        applied_date: When this snapshot was observed (used for history and IP→device resolution).

    Returns:
        Dict with ``schema_version``, ``device_id``, interface fields, and ``applied_date``.
    """
    doc: dict = {
        "schema_version": INTERFACE_CONFIGURATION_SCHEMA_VERSION,
        "device_id": device_id,
        "interface_name": interface_name,
        "ip_address": ip_address,
        "subnet_mask": subnet_mask,
        "default_gateway": default_gateway,
        "hostname": hostname,
        "mac_address": mac_address,
        "applied_date": applied_date,
    }
    return doc