# Main python script
import asyncio

from Logging.ScreenLogger import ScreenLogger
from Logging.Logger import LogLevel
from StatusMonitor.Active.ICMPMonitor import ICMPMonitor

logger = ScreenLogger()
# logger.log({"latency": .5}, LogLevel.DEBUG)
# logger.log({"latency": .6}, LogLevel.INFO)
# logger.log({"latency": 1.0}, LogLevel.CRITICAL)
# logger.log_many([{"latency": 1.5}] * 10, [LogLevel.WARNING] * 10)

monitor = ICMPMonitor(endpoints=["192.67.67.67", "127.0.0.1"])
asyncio.run(monitor.update_status())
logger.log(monitor.get_status(), LogLevel.DEBUG)
