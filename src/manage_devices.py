"""Script we can use to add or remove devices in MongoDB from the terminal."""

import argparse
import logging
import sys

from pymongo import MongoClient

from Kibble.Retrieval import DeviceRetriever

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("Kibble_ManageDevices")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

DEFAULT_MONGO_HOST = 'localhost'
DEFAULT_MONGO_PORT = 27017
mongo_user = 'root'
mongo_passwd = 'password'

PRESET_DEVICE_TYPES = {
    'icmp': ('device 1', ['ICMP']),    # Latency / connectivity
    'scpi': ('device 2', ['SCPI']),    # Latency / connectivity
    'snmp': ('device 3', ['SNMP']),    # Latency / overall network health
    'daemon': ('device 4', ['Daemon']),  # Latency / edge device health
}


def connect(mongo_host: str, mongo_port: int) -> DeviceRetriever | None:
    uri = f"mongodb://{mongo_user}:{mongo_passwd}@{mongo_host}:{mongo_port}"
    try:
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
    except Exception as e:
        logger.critical(
            f"Unable to connect to MongoDB at {mongo_host}:{mongo_port}: {e}. "
            "Is the database container running? (see simulator/compose.yaml)"
        )
        return None
    return DeviceRetriever(client=mongo_client)


def resolve_device_type(device_retriever: DeviceRetriever, preset: str | None, type_name: str | None, protocols: list[str] | None):
    if preset is not None:
        if type_name is not None or protocols is not None:
            raise ValueError('Use either --type or --type-name/--protocols, not both')
        return device_retriever.ensure_device_type(*PRESET_DEVICE_TYPES[preset])

    if type_name is None:
        raise ValueError('Provide --device_type (icmp, scpi, snmp, or daemon) or --type-name with --protocols')
    if not protocols:
        raise ValueError('--protocols is required when using --type-name')
    return device_retriever.ensure_device_type(type_name, protocols)


def add_device(
    device_retriever: DeviceRetriever,
    asset_tag: int,
    device_type_id,
    ip: str,
    hostname: str,
    mac: str,
) -> bool:
    db = device_retriever.db
    db['devices'].update_one(
        {'asset_tag': asset_tag},
        {
            '$set': {'device_type_id': device_type_id},
            '$setOnInsert': {'asset_tag': asset_tag},
        },
        upsert=True,
    )

    dev = db['devices'].find_one({'asset_tag': asset_tag}, {'_id': 1})
    if dev is None:
        logger.error(f"Failed to upsert device {asset_tag}")
        return False

    if not ip and not hostname:
        logger.warning('Device has no ip or hostname; monitoring may not work until one is set')

    device_retriever.record_device_configuration_if_changed(
        dev['_id'],
        {'ip': ip, 'hostname': hostname, 'mac': mac},
    )
    logger.info(f"Added/updated device {asset_tag}")
    return True


def remove_device(device_retriever: DeviceRetriever, asset_tag: int) -> bool:
    db = device_retriever.db
    dev = db['devices'].find_one({'asset_tag': asset_tag}, {'_id': 1})
    if dev is None:
        logger.error(f"No device found with asset_tag {asset_tag}")
        return False

    oid = dev['_id']
    iface_result = db['interface_configurations'].delete_many({'device_id': oid})
    cfg_result = db['device_configurations'].delete_many({'device_id': oid})
    db['devices'].delete_one({'_id': oid})
    logger.info(
        f"Removed device {asset_tag} "
        f"({iface_result.deleted_count} interface row(s), {cfg_result.deleted_count} configuration row(s))"
    )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Add or remove devices in MongoDB.')
    parser.add_argument(
        '--mongo-host',
        default=DEFAULT_MONGO_HOST,
        help='MongoDB host (default: localhost; use database.internal inside Docker)',
    )
    parser.add_argument(
        '--mongo-port',
        type=int,
        default=DEFAULT_MONGO_PORT,
        help='MongoDB port (default: 27017)',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    add_parser = subparsers.add_parser('add', help='Add or update a device')
    add_parser.add_argument('--asset-tag', type=int, required=True, help='Unique asset tag')
    add_parser.add_argument(
        '--type',
        choices=sorted(PRESET_DEVICE_TYPES),
        help=(
            'Preset device type: icmp/scpi (latency/connectivity), '
            'snmp (network health), daemon (edge device health)'
        ),
    )
    add_parser.add_argument('--type-name', help='Custom device type name (requires --protocols)')
    add_parser.add_argument('--protocols', nargs='+', help='Protocols for a custom device type (e.g. ICMP SNMP Daemon)')
    add_parser.add_argument('--ip', default='', help='Device IP address')
    add_parser.add_argument('--hostname', default='', help='Device hostname')
    add_parser.add_argument('--mac', default='', help='Device MAC address')

    remove_parser = subparsers.add_parser('remove', help='Remove a device by asset tag')
    remove_parser.add_argument('--asset-tag', type=int, required=True, help='Asset tag of the device to remove')

    return parser


def main() -> int:
    args = build_parser().parse_args()
    device_retriever = connect(args.mongo_host, args.mongo_port)
    if device_retriever is None:
        return 1

    if args.command == 'add':
        try:
            device_type_id = resolve_device_type(
                device_retriever,
                args.type,
                args.type_name,
                args.protocols,
            )
        except ValueError as e:
            logger.error(str(e))
            return 1
        return 0 if add_device(
            device_retriever,
            args.asset_tag,
            device_type_id,
            args.ip,
            args.hostname,
            args.mac,
        ) else 1

    if args.command == 'remove':
        return 0 if remove_device(device_retriever, args.asset_tag) else 1

    return 1


if __name__ == '__main__':
    sys.exit(main())
