# Main python script

from Kibble import Kibble
from Kibble.Logging import ScreenLogger
from Kibble.Monitoring.Active import ICMPMonitor
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
# from Kibble.Logging import MongoLogger
import logging

# set up loggers
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# main logger for maintenance
status_logger = logging.getLogger("Kibble_Status")
status_logger.setLevel(logging.DEBUG)
status_logger.propagate = True

# screen logging
screen_handler = logging.StreamHandler()
screen_handler.setLevel(logging.NOTSET)
screen_handler.setFormatter(formatter)

# file logging
file_handler = logging.FileHandler("./kibble.log")
file_handler.setLevel(logging.NOTSET)
file_handler.setFormatter(formatter)

# mongodb logging
mongo_handler = MongoHandler('kibble')
mongo_handler.setLevel(logging.INFO)

# attach handlers
# status_logger.addHandler(screen_handler)
# status_logger.addHandler(file_handler)
status_logger.addHandler(mongo_handler)

# status_logger.debug("", extra={"status": { "msg": "debug" }})
# status_logger.info("", extra={"status": { "msg": "info" }})
# status_logger.warning("", extra={"status": { "msg": "warning" }})
# status_logger.error("", extra={"status": { "msg": "error" }})
# status_logger.critical("", extra={"status": { "msg": "critical" }})

# screen_logger = ScreenLogger()
# mongo_logger = MongoLogger('kibble')
screen_alert = ScreenAlert()
email_alert = EmailAlert()

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)

kibble = Kibble(monitors=[monitor], alerters=[screen_alert])
kibble.run()
