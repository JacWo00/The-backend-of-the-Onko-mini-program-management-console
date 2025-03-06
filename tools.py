import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time

import time

from config import config_sys

class HourlyLogHandler:
    def __init__(self, log_directory, log_name, backupcount):
        """
        初始化日志处理器，按每小时整点分割日志文件。
        :param log_directory: 日志文件存储的目录，例如 'logs'。
        :param log_name: 日志文件的基本名称，例如 'x'。
        """
        self.log_directory = log_directory
        self.log_name = log_name
        self.backupcount = backupcount
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handler()

    def _setup_handler(self):
        """设置 TimedRotatingFileHandler 来每小时旋转日志文件。"""
        # 检查日志目录是否存在，如果不存在，则创建它
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        log_path = os.path.join(self.log_directory, f"{self.log_name}.log")

        # 设置 TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(log_path, when="H", interval=1, backupCount=self.backupcount, utc=True, encoding='utf-8')

        # 计算到下一个整点的时间，设置为首次旋转时间
        current_time = time.time()
        rotate_at_time = current_time + (3600 - current_time % 3600)
        handler.rolloverAt = rotate_at_time

        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        # print(message)
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
