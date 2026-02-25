# Main python script

from Kibble.Logging import ScreenLogger
from Kibble.Logging import MongoLogger
from Kibble.Monitoring.Active import ICMPMonitor
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble import Kibble

screen_logger = ScreenLogger()
mongo_logger = MongoLogger('kibble')

# Adding device type for ICMP logging (normalized: devices reference this by device_type_id)
device_type_id = mongo_logger._ensure_device_type("device 1", ["ICMP"])
screen_alert = ScreenAlert()
email_alert = EmailAlert()

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)

kibble = Kibble(
    monitors=[monitor],
    loggers=[screen_logger, mongo_logger],
    alerters=[screen_alert],
    default_device_type_id=device_type_id,
    devices_collection=mongo_logger.devices_collection,
    device_types_collection=mongo_logger.device_types_collection,
    events_collection=mongo_logger.events_collection,
)
kibble.run()
