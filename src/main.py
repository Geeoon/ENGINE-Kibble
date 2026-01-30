# Main python script

from time import sleep
import asyncio

from Logging.ScreenLogger import ScreenLogger
from Logging.MongoLogger import MongoLogger
from Logging.Logger import LogLevel
from StatusMonitor.Active.ICMPMonitor import ICMPMonitor

screen_logger = ScreenLogger()
mongo_logger = MongoLogger('kibble', 'events')
# logger.log({"latency": .5}, LogLevel.DEBUG)
# logger.log({"latency": .6}, LogLevel.INFO)
# logger.log({"latency": 1.0}, LogLevel.CRITICAL)
# logger.log_many([{"latency": 1.5}] * 10, [LogLevel.WARNING] * 10)

#                                 localhost    non existant    test computers...
monitor = ICMPMonitor(endpoints=["127.0.0.1", "192.67.67.67", "10.128.0.1", "10.128.0.2", "10.128.0.3", "10.128.0.4", "10.128.0.5"], timeout=5)
try:
    while True:
        asyncio.run(monitor.update_status())
        res = monitor.get_status()
        for key in res.keys():
            if res[key]:
                if not res[key]["alive"]:
                    screen_logger.log(f"{key} endpoint is down!", LogLevel.CRITICAL)
                    mongo_logger.log(res[key] | {"ip": key}, LogLevel.CRITICAL)
        sleep(1)
            
except KeyboardInterrupt:
    pass

screen_logger.log("Shutting down.")
