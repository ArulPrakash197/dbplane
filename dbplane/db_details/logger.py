import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name, filename):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger  # Prevent duplicate handlers

    log_path = os.path.join(LOG_DIR, filename)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=10
    )

    def namer(default_name):
        # default_name → postgresql.log.1
        base, ext = os.path.splitext(default_name)
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{base}.{date_str}{ext}"

    file_handler.namer = namer

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    console_handler.setFormatter(formatter)
    
    logger.propagate = False

    return logger