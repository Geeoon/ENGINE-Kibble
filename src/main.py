# Main python script

from Kibble.Logging import ScreenLogger
from Kibble.Logging import MongoLogger
from Kibble.Monitoring.Active import ICMPMonitor
from Kibble.Alerting import EmailAlert, ScreenAlert
from Kibble import Kibble

screen_logger = ScreenLogger()
mongo_logger = MongoLogger('kibble', 'events')
screen_alert = ScreenAlert()
email_alert = EmailAlert()

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)

kibble = Kibble(monitors=[monitor], loggers=[screen_logger, mongo_logger], alerters=[screen_alert])
kibble.run()
