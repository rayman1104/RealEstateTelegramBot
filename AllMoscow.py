import LoggerInit
import config
import time
import logging

from GlobalManager.GlobalParser import GlobalParser
from GlobalManager.SuspiciousChecker import SuspiciousChecker
from Queues import QueueWrapper

LoggerInit.init_logging(config.log_all_moscow_file)
logger = logging.getLogger("AllMoscowParser")


@LoggerInit.catch_exceptions
def main():
    QueueWrapper.init()
    GlobalParser.register()
    SuspiciousChecker.register()
    QueueWrapper.start(detach=True)
    try:
        while True:
            time.sleep(60 * 60 * 60)
    except KeyboardInterrupt:
        GlobalParser.close_thread()
        SuspiciousChecker.close_thread()
        QueueWrapper.close()


if __name__ == "__main__":
    main()
