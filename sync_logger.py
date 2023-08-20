""" Logger class used for folder sync """
import os
import logging


class SyncLogger:
    """ Creates a logger to console & file """
    # pylint: disable= [too-few-public-methods]
    __slots__ = ("logger_file", "logger_path", "verbose", "main_logger")

    def __init__(self, logger_path: str = "", verbose: bool = False):
        self.logger_file = 'sync_logger.log'
        self.logger_path = logger_path
        self.verbose = verbose

        self.main_logger = logging.getLogger()
        self.set_logger()

    def set_logger(self) -> None:
        """ Sets the logger basic config"""
        wanted_logging_level = logging.DEBUG
        if not self.verbose:
            wanted_logging_level = logging.WARNING
        self.main_logger.setLevel(wanted_logging_level)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s: ::%(funcName)s:: %(message)s',
                                      datefmt='%m/%d/%Y %I:%M:%S%p')
        file_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)

        console_logger = logging.FileHandler(
            filename=os.path.join(self.logger_path, self.logger_file),
            mode='w+'
        )
        console_logger.setFormatter(formatter)
        self.main_logger.addHandler(console_logger)
        self.main_logger.addHandler(file_handler)
