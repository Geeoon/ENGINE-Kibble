# Main python script

from Kibble.Logging import ScreenLogger
from Kibble.Logging import MongoLogger
from Kibble.Monitoring.Active import ICMPMonitor
from Kibble.Alerting import EmailAlert
from Kibble import Kibble

screen_logger = ScreenLogger()
mongo_logger = MongoLogger('kibble', 'events')
email_alert = EmailAlert()

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)

kibble = Kibble([monitor], [screen_logger, mongo_logger])
kibble.run()
