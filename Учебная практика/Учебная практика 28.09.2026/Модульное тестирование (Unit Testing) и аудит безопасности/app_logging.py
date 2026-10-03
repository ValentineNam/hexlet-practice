import logging
from pathlib import Path


def configure_app_logging(log_path=None):
    destination = Path(log_path) if log_path is not None else Path(__file__).with_name('app.log')
    logger = logging.getLogger('materials_app')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers:
        if getattr(handler, 'baseFilename', None) == str(destination.resolve()):
            return logger

    handler = logging.FileHandler(destination, encoding='utf-8')
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger
