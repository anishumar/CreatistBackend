from __future__ import annotations

import logging
import logging.handlers
import os
from collections import deque, namedtuple
from datetime import datetime
from typing import Iterable

from pytz import timezone

# Get environment
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Configure logging level based on environment
if ENVIRONMENT == "production":
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
else:
    log_level = logging.DEBUG

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

filehandler = logging.handlers.RotatingFileHandler(
    "logs/log.log",
    maxBytes=1024 * 1024 * 5,  # 5MB
    backupCount=5,  # Keep 5 backup files
    mode="a",
)
filehandler.setLevel(log_level)

# Production-friendly formatter
if ENVIRONMENT == "production":
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
else:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
    )

filehandler.setFormatter(formatter)


class Record(namedtuple("Record", ["time", "name", "levelname", "msg"])):
    """
    A simple named tuple to represent a log record.
    """

    def __str__(self):
        return f"{self.time} - {self.name} - {self.levelname} - {self.msg}"

    def __repr__(self):
        return self.__str__()


class CustomLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.addHandler(filehandler)

        self._recent_logs = deque(maxlen=1024)

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)
        self._recent_logs.append((datetime.now(timezone("UTC")), "debug", args, kwargs))

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)
        self._recent_logs.append((datetime.now(timezone("UTC")), "info", args, kwargs))

    def warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)
        self._recent_logs.append(
            (datetime.now(timezone("UTC")), "warning", args, kwargs)
        )

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)
        self._recent_logs.append((datetime.now(timezone("UTC")), "error", args, kwargs))

    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)
        self._recent_logs.append(
            (datetime.now(timezone("UTC")), "critical", args, kwargs)
        )

    @property
    def recent_logs(self) -> Iterable[Record]:
        """
        Returns the most recent logs.
        """
        for time, level, args, kwargs in self._recent_logs:
            formatted_message = self.logger.makeRecord(
                self.logger.name,
                getattr(logging, level.upper()),
                fn="",
                lno=0,
                msg=args[0] if args else "",
                args=args[1:],
                exc_info=kwargs.get("exc_info", None),
            )
            yield Record(
                time=time,
                name=formatted_message.name,
                levelname=formatted_message.levelname,
                msg=formatted_message.getMessage(),
            )


def get_logger(name: str) -> CustomLogger:
    """
    Returns a CustomLogger instance for the given name.
    """
    return CustomLogger(name)


log = get_logger("app")
