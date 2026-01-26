# Main python script
from Logging.ScreenLogger import ScreenLogger
from Logging.FileLogger import FileLogger
from Logging.Logger import LogLevel

logger = FileLogger('./test.log')
logger.log({"hello": 1}, LogLevel.INFO)
logger.log({"hello": 1}, LogLevel.CRITICAL)
logger.close_file()
