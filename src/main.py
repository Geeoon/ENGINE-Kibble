# Main python script
from Logging.MongoLogger import MongoLogger
from Logging.FileLogger import FileLogger
from Logging.ScreenLogger import ScreenLogger
from Logging.Logger import LogLevel

logger = MongoLogger('kibble', 'events')
logger.log({"latency": .5}, LogLevel.DEBUG)
logger.log({"latency": .6}, LogLevel.INFO)
logger.log({"latency": 1.0}, LogLevel.CRITICAL)
logger.log_many([{"latency": 1.5}] * 10, [LogLevel.WARNING] * 10)
logger.close_connection()
