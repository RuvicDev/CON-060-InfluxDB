"""Conector Ruvic para InfluxDB (solo lectura)."""

from .client import InfluxDBClientWrapper
from .config import ENV_PREFIX, InfluxDBConfig
from .exceptions import (
    InfluxDBAuthError,
    InfluxDBConfigError,
    InfluxDBConnectorError,
    InfluxDBDataError,
    InfluxDBNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "InfluxDBAuthError",
    "InfluxDBClientWrapper",
    "InfluxDBConfig",
    "InfluxDBConfigError",
    "InfluxDBConnectorError",
    "InfluxDBDataError",
    "InfluxDBNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
