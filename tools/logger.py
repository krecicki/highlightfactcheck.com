import logging
import os


def get_log_level():
    log_level_str = os.environ.get('LOG_LEVEL', 'DEBUG').upper()
    return getattr(logging, log_level_str, logging.DEBUG)


def setup_logger(log_level=None):
    if log_level is None:
        log_level = get_log_level()

    logger = logging.getLogger('app_logger')
    logger.setLevel(log_level)

    if not logger.handlers:
        console_handler = logging.StreamHandler()

        # Create formatters and add it to handlers
        log_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
