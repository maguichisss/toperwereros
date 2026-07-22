"""Centralized logging configuration for the Store Catalog API.

Call :func:`setup_logging` once at application startup.  The log level is
controlled by the ``LOG_LEVEL`` environment variable (default ``INFO``).

When set to ``DEBUG``, SQLAlchemy query logging and uvicorn access logs are
also enabled at verbose levels.
"""

import logging
import os
import sys


def setup_logging() -> None:
    """Configure root logger, SQLAlchemy logger, and uvicorn loggers.

    Reads the ``LOG_LEVEL`` environment variable (case-insensitive).
    Valid values: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
    Defaults to ``INFO`` if unset or invalid.
    """

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # SQLAlchemy engine — show queries only in DEBUG
    sa_level = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sa_level)

    # Uvicorn — always show startup/error, access logs follow root level
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(level)
