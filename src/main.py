# Main python script

from Kibble import Kibble
from Kibble.Monitoring.Active import ICMPMonitor
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble.Logging import MongoHandler
import logging

# set up loggers
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# main logger for status
status_logger = logging.getLogger("Kibble_Status")
status_logger.setLevel(logging.DEBUG)
status_logger.propagate = True
# screen logging
screen_status_handler = logging.StreamHandler()
screen_status_handler.setLevel(logging.NOTSET)
screen_status_handler.setFormatter(formatter)
# file logging
file_status_handler = logging.FileHandler("./kibble_status.log")
file_status_handler.setLevel(logging.NOTSET)
file_status_handler.setFormatter(formatter)
# mongodb logging
mongo_status_handler = MongoHandler('kibble')
mongo_status_handler.setLevel(logging.INFO)
# attach handlers
# status_logger.addHandler(screen_status_handler)  # just for debugging
status_logger.addHandler(file_status_handler)  # keep on disk in case the database goes down
status_logger.addHandler(mongo_status_handler)

# logger for maintainance
maintainance_logger = logging.getLogger("Kibble_Maintainance")
maintainance_logger.setLevel(logging.DEBUG)
maintainance_logger.propagate = True
# screen logging
screen_maintainance_handler = logging.StreamHandler()
screen_maintainance_handler.setLevel(logging.NOTSET)
screen_maintainance_handler.setFormatter(formatter)
# file logging
file_maintainance_handler = logging.FileHandler("./kibble.log")
file_maintainance_handler.setLevel(logging.NOTSET)
file_maintainance_handler.setFormatter(formatter)
# attach loggers
maintainance_logger.addHandler(screen_maintainance_handler)  # just for debugging
maintainance_logger.addHandler(file_maintainance_handler)  # keep a log of the program in case something goes wrong

screen_alert = ScreenAlert()  # TODO: replace with logger possibly
email_alert = EmailAlert()

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)

kibble = Kibble(monitors=[monitor], alerters=[screen_alert])
kibble.run()
