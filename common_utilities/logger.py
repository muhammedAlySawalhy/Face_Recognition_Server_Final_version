#!/usr/bin/env python3.10

import os
import logging
from enum import Enum
from typing import List, Literal

from .files_handler import create_logfile

class LOG_LEVEL(Enum):
    DEBUG = 0
    INFO = 1
    ERROR = 2
    CRITICAL = 3
    WARNING = 4
# Define color codes
class LogColors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
class Stream__ColoredFormatter(logging.Formatter):

    # Define colors for different log levels
    COLORS = {
        logging.DEBUG: LogColors.CYAN,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.MAGENTA,
    }
    def format(self, record):
        # Get the color based on the log level
        color = self.COLORS.get(record.levelno, LogColors.WHITE)
        # Apply the color to the level name
        record.levelname = f"{color}{record.levelname}{LogColors.WHITE}"
        return super().format(record)
class File__ColoredFormatter(logging.Formatter):
    # Define colors for different log levels
    COLORS = {
        logging.DEBUG: LogColors.CYAN,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.MAGENTA,
    }

    def format(self, record):
        # Get the color based on the log level
        color = self.COLORS.get(record.levelno, LogColors.WHITE)
        # Apply the color to the level name
        record.levelname = f"{color}{record.levelname}{LogColors.WHITE}"
        return super().format(record)

class loggingFilter(logging.Filter):
    __logging_level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "WARNING": logging.WARNING
    }
    def __init__(self, logging_level: list):
        super().__init__()
        if not isinstance(logging_level, list):
            logging_level = [logging_level]
        self.logging_level = map(lambda x: self.__logging_level_mapping.get(x, None), logging_level)
        self.logging_level = list(self.logging_level)
        if None in self.logging_level:
            raise ValueError("Invalid logging level provided. Valid levels are: DEBUG, INFO, ERROR, CRITICAL, WARNING")
    def filter(self, record):
        return record.levelno in self.logging_level
class LOGGER:
    def __init__(self,logger_name):
        if logger_name != None:
            self.__logger=logging.Logger(logger_name)
            self.__logger.setLevel(logging.DEBUG)
        else:
            self.__logger=None

    def _ensure_file_handlers(self):
        if not self.__logger:
            return

        for handler in self.__logger.handlers:
            if not isinstance(handler, logging.FileHandler):
                continue
            base_filename = getattr(handler, "baseFilename", None)
            if not base_filename:
                continue

            needs_reopen = False
            if not os.path.exists(base_filename):
                needs_reopen = True
            else:
                stream = getattr(handler, "stream", None)
                if stream is None or stream.closed:
                    needs_reopen = True

            if not needs_reopen:
                continue

            handler.acquire()
            try:
                handler.close()
                try:
                    handler.stream = handler._open()
                except OSError:
                    handler.stream = None
                    raise
            finally:
                handler.release()

    def create_File_logger(self,logs_name:str,log_levels: List[Literal["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"]]):
        try:
            file_path=create_logfile(logs_name)
            file_logger=logging.FileHandler(file_path, mode="a")
            logger_formate_file=File__ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_logger.setFormatter(logger_formate_file)
            logging_filter = loggingFilter(log_levels)
            file_logger.addFilter(logging_filter)
            self.__logger.addHandler(file_logger)
            # Ensure the handler opens the target file immediately so permission errors surface here.
            self._ensure_file_handlers()
        except ValueError as e:
            raise ValueError(f"Failed to create log file: {e}")
        except OSError as e:
            raise Exception(f"An error occurred while creating the file logger: {e}")
        except Exception as e:
            raise Exception(f"An error occurred while creating the file logger: {e}")

    def create_Stream_logger(self,log_levels: List[Literal["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"]]):
        Stream_logger=logging.StreamHandler()
        logger_formate_consol=Stream__ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        Stream_logger.setFormatter(logger_formate_consol)
        logging_filter = loggingFilter(log_levels)
        Stream_logger.addFilter(logging_filter)
        self.__logger.addHandler(Stream_logger)
    
    def write_logs(self,logs_message,logs_level:LOG_LEVEL):
        if self.__logger:
            try:
                self._ensure_file_handlers()
            except Exception:
                pass
            if logs_level==LOG_LEVEL.DEBUG:
                self.__logger.debug(logs_message)
            elif logs_level==LOG_LEVEL.INFO:
                self.__logger.info(logs_message)
            elif logs_level==LOG_LEVEL.ERROR:
                self.__logger.error(logs_message)
            elif logs_level==LOG_LEVEL.CRITICAL:
                self.__logger.critical(logs_message)
            elif logs_level==LOG_LEVEL.WARNING:
                self.__logger.warning(logs_message)
            else:
                raise ValueError()
