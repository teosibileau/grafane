"""Grafane database router.

This module provides routing logic for multi-database InfluxDB setups.
It resolves metrics to their configured databases and caches InfluxDB clients.

Router behavior:
- Grafane('metric-1')           → db that has 'metric-1' in metrics list
- Grafane('metric-in-both')     → raises MultipleConfigError
- Grafane('metric-in-both', db='db1') → explicit db
- Grafane('unknown-metric')     → raises MetricNotFoundError
- Grafane('any', db='unknown')  → raises DatabaseNotFoundError
"""

import logging
from typing import TYPE_CHECKING

from influxdb import InfluxDBClient as InfluxDBClientV1

from .config import settings
from .exceptions import (
    DatabaseNotFoundError,
    InfluxDBV2NotInstalled,
    MetricNotFoundError,
    MultipleConfigError,
)

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger("grafane")

# Lazy import for v2 client
InfluxDBClientV2 = None


def _get_v2_client():
    """Lazy import and return InfluxDB v2 client class."""
    global InfluxDBClientV2
    if InfluxDBClientV2 is None:
        try:
            from influxdb_client import InfluxDBClient

            InfluxDBClientV2 = InfluxDBClient
        except ImportError:
            raise InfluxDBV2NotInstalled()
    return InfluxDBClientV2


class Router:
    """Routes metrics to their configured InfluxDB databases.

    The router maintains a cache of InfluxDBClient instances per database,
    and provides methods to resolve which database a metric belongs to.
    """

    def __init__(self):
        self._client_cache: dict[str, "Any"] = {}

    @property
    def influxdb_settings(self) -> dict[str, "Any"]:
        """Get the INFLUXDB_SETTINGS from config."""
        return settings.INFLUXDB_SETTINGS

    def _get_version(self, db_config: dict) -> int:
        """Get the InfluxDB version from config (default: 1)."""
        return db_config.get("version", 1)

    def _create_client(self, db_name: str, db_config: dict) -> "Any":
        """Create an InfluxDBClient for a database configuration."""
        version = self._get_version(db_config)

        if version == 1:
            return InfluxDBClientV1(
                host=db_config["host"],
                port=db_config["port"],
                username=db_config["username"],
                password=db_config["password"],
                database=db_config["database"],
                ssl=db_config.get("ssl", False),
            )
        elif version == 2:
            v2_client = _get_v2_client()
            return v2_client(
                url=db_config["url"],
                token=db_config["token"],
                org=db_config["org"],
            )
        else:
            raise ValueError(f"Unsupported InfluxDB version: {version}")

    def get_client(self, db_name: str) -> "Any":
        """Get an InfluxDBClient for a database by name.

        Args:
            db_name: The database configuration name (e.g., 'default', 'analytics')

        Returns:
            An InfluxDBClient instance (cached)

        Raises:
            DatabaseNotFoundError: If the database name is not in settings
        """
        if db_name not in self.influxdb_settings:
            raise DatabaseNotFoundError(
                f"Database '{db_name}' not found in INFLUXDB_SETTINGS. "
                f"Available databases: {', '.join(sorted(self.influxdb_settings.keys()))}"
            )

        if db_name not in self._client_cache:
            db_config = self.influxdb_settings[db_name]
            self._client_cache[db_name] = self._create_client(db_name, db_config)
            logger.debug(f"Created InfluxDB client for database '{db_name}'")

        return self._client_cache[db_name]

    def find_databases_for_metric(self, metric: str) -> list[str]:
        """Find all databases that have the metric in their metrics list.

        Args:
            metric: The metric name to search for

        Returns:
            List of database names that include this metric
        """
        matching_dbs = []
        for db_name, db_config in self.influxdb_settings.items():
            metrics_list = db_config.get("metrics", [])
            if metric in metrics_list:
                matching_dbs.append(db_name)
        return matching_dbs

    def find_fallback_database(self) -> str | None:
        """Find a database with an empty metrics list (fallback/catch-all).

        Returns:
            The database name with empty metrics list, or None if not found
        """
        for db_name, db_config in self.influxdb_settings.items():
            metrics_list = db_config.get("metrics", [])
            if not metrics_list:  # Empty list = fallback
                return db_name
        return None

    def resolve_metric(self, metric: str, db: str | None = None) -> str:
        """Resolve which database a metric should use.

        Args:
            metric: The metric name
            db: Explicit database name (optional). If provided, validates it exists.

        Returns:
            The database name to use

        Raises:
            DatabaseNotFoundError: If explicit db is not found
            MetricNotFoundError: If metric is not in any database's metrics list
            MultipleConfigError: If metric is in multiple databases' metrics lists
        """
        # If explicit db is provided, validate it exists
        if db is not None:
            if db not in self.influxdb_settings:
                raise DatabaseNotFoundError(
                    f"Database '{db}' not found in INFLUXDB_SETTINGS. "
                    f"Available databases: {', '.join(sorted(self.influxdb_settings.keys()))}"
                )
            return db

        # Find databases that have this metric in their list
        matching_dbs = self.find_databases_for_metric(metric)

        if len(matching_dbs) == 1:
            return matching_dbs[0]

        if len(matching_dbs) > 1:
            raise MultipleConfigError(
                f"Metric '{metric}' found in multiple databases: {', '.join(sorted(matching_dbs))}. "
                f"Use explicit db= parameter to specify which database to use.",
                databases=matching_dbs,
            )

        # No explicit match, try fallback database
        fallback_db = self.find_fallback_database()
        if fallback_db is not None:
            logger.debug(
                f"Metric '{metric}' not found in any metrics list, "
                f"using fallback database '{fallback_db}'"
            )
            return fallback_db

        # No matches and no fallback
        raise MetricNotFoundError(
            f"Metric '{metric}' not found in any database's metrics list, "
            f"and no fallback database (empty metrics list) is configured."
        )

    def get_client_for_metric(
        self, metric: str, db: str | None = None
    ) -> tuple["Any", str]:
        """Get an InfluxDBClient for a metric.

        This is the main entry point for getting a client for a metric.

        Args:
            metric: The metric name
            db: Explicit database name (optional)

        Returns:
            Tuple of (InfluxDBClient, database_name)

        Raises:
            DatabaseNotFoundError: If explicit db is not found
            MetricNotFoundError: If metric is not in any database's metrics list
            MultipleConfigError: If metric is in multiple databases' metrics lists
        """
        db_name = self.resolve_metric(metric, db)
        client = self.get_client(db_name)
        return client, db_name

    def clear_cache(self) -> None:
        """Clear the client cache. Primarily for testing."""
        self._client_cache.clear()

    @property
    def cached_databases(self) -> list[str]:
        """Return list of database names with cached clients."""
        return list(self._client_cache.keys())


# Global router instance
router = Router()
