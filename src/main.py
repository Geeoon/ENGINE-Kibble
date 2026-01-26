# Main python script
from Logging.MongoLogger import MongoLogger
from Logging.FileLogger import FileLogger
from Logging.ScreenLogger import ScreenLogger
from Logging.Logger import LogLevel

logger = MongoLogger('./test.log', 'kibble', 'events')
logger.log({"hello": 1}, LogLevel.INFO)
logger.log({"hello": 1}, LogLevel.CRITICAL)
logger.close_connection()
