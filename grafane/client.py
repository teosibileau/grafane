"""Grafane client module.

This module provides the main Grafane client class for interacting with InfluxDB.
"""

import copy
import functools
from datetime import datetime
from typing import TYPE_CHECKING

from influxdb_client.client.write_api import SYNCHRONOUS
import pytz

from .config import settings
from .querysets import FluxQuerySet, InfluxQLQuerySet
from .router import router

if TYPE_CHECKING:
    pass


def cache_invalidation(func):
    """Decorator that resets query cache before executing query-building methods."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._executed:
            self.reset_query()
        return func(self, *args, **kwargs)

    return wrapper


class Grafane:
    """Main client for interacting with InfluxDB.

    The Grafane client provides a Django-ORM-like interface for querying
    and writing data to InfluxDB.

    Args:
        metric: The metric/measurement name to work with
        db: Explicit database configuration name (optional). If not provided,
            the router will determine the database based on the metric.

    Raises:
        MetricNotFoundError: If metric is not in any database's metrics list
            and no fallback database is configured.
        MultipleConfigError: If metric is found in multiple databases' metrics
            lists and no explicit db is provided.
        DatabaseNotFoundError: If explicit db parameter is not found in settings.

    Example:
        >>> client = Grafane('cpu_usage')
        >>> results = client.select(['value']).filter_by('host', '=', 'server1').execute_query()

        >>> # With explicit database
        >>> client = Grafane('page_views', db='analytics')
    """

    def __init__(self, metric: str = "generic", db: str | None = None):
        self.ignore_query = False

        # Get UUID from config (machine identifier for origin tag)
        self.uuid = settings.UUID

        # Get the appropriate InfluxDB client via router
        self._client, self._db_name = router.get_client_for_metric(metric, db)

        # Get version from database config
        db_config = router.influxdb_settings[self._db_name]
        self._version = db_config.get("version", 1)

        # Store the original metric name
        self._original_metric = metric

        # Apply testing suffix if in testing mode
        self.metric = metric
        if settings.TESTING:
            self.metric = f"{metric}-testing"

        # Select appropriate queryset based on version
        if self._version == 1:
            self._queryset = InfluxQLQuerySet(self.metric)
        else:
            bucket = db_config.get("bucket", "metrics")
            self._queryset = FluxQuerySet(self.metric, bucket=bucket)

        self._results: list | None = None
        self._executed = False

    @property
    def database_name(self) -> str:
        """Return the database configuration name being used."""
        return self._db_name

    # === Query State ===
    def reset_query(self):
        """Reset the query state to allow building a new query."""
        self._queryset.reset()
        self._results = None
        self._executed = False

    # === Delegation to QuerySet ===
    @cache_invalidation
    def select(self, fields=None, aggregation=None):
        """Select fields to return from the query.

        Args:
            fields: List of field names to select (default: ['value'])
            aggregation: List of aggregation functions to apply (default: [])

        Returns:
            self for method chaining
        """
        if fields is None:
            fields = ["value"]
        if aggregation is None:
            aggregation = []
        self._queryset.select(fields, aggregation)
        return self

    @cache_invalidation
    def filter_by(self, tag, operator, value):
        """Add a filter condition to the query.

        Args:
            tag: The tag name to filter on
            operator: The comparison operator (e.g., '=', '!=', '<', '>')
            value: The value to compare against

        Returns:
            self for method chaining
        """
        self._queryset.filter_by(tag, operator, value)
        return self

    @cache_invalidation
    def filter_by_from_dict(self, filter_by):
        """Add filter conditions from a dictionary.

        Deprecated: Use chained filter_by() calls instead.

        Args:
            filter_by: Dict with 'tag', 'operator', 'value' keys

        Returns:
            self for method chaining
        """
        self._queryset.filter_by_from_dict(filter_by)
        return self

    @cache_invalidation
    def filter_time_range(self, r):
        """Filter by time range.

        Args:
            r: Time range as string (e.g., '1h') or tuple of (start, end)

        Returns:
            self for method chaining
        """
        self._queryset.filter_time_range(r)
        return self

    @cache_invalidation
    def time_block(self, block):
        """Group results by time intervals.

        Args:
            block: Time interval string (e.g., '1h', '5m')

        Returns:
            self for method chaining
        """
        self._queryset.time_block(block)
        return self

    @cache_invalidation
    def group_by(self, group):
        """Group results by tag(s).

        Args:
            group: Tag name or list of tag names to group by

        Returns:
            self for method chaining
        """
        self._queryset.group_by(group)
        return self

    @cache_invalidation
    def fill_with(self, fill=False):
        """Fill missing values in grouped results.

        Args:
            fill: Fill strategy ('none', 'null', '0', 'previous', 'linear') or False to disable

        Returns:
            self for method chaining
        """
        self._queryset.fill_with(fill)
        return self

    def filter_value_in(self, tag, values):
        """Filter where tag value is in a list of values.

        Args:
            tag: The tag name to filter on
            values: List of values to match

        Returns:
            self for method chaining
        """
        if self._executed:
            self.reset_query()
        self._queryset.filter_value_in(tag, values)
        return self

    # === Execution ===
    def execute_query(self, uuid=None):
        """Execute the built query and return results.

        Args:
            uuid: Optional UUID to filter by origin tag

        Returns:
            List of result dictionaries
        """
        if self._executed:
            return self._results
        if uuid:
            self._queryset.filter_by("origin", "=", uuid)

        if self._version == 1:
            raw_results = self._client.query(self._queryset.query)
        else:
            db_config = router.influxdb_settings[self._db_name]
            query_api = self._client.query_api()
            org = db_config.get("org", "my-org")
            raw_results = query_api.query(org=org, query=self._queryset.query)

        self._results = self._queryset.parse_results(raw_results)
        self._executed = True
        return self._results

    def query(
        self,
        query,
        params=None,
        epoch=None,
        expected_response_code=200,
        database=None,
        raise_errors=True,
        chunked=False,
        chunk_size=0,
        method="GET",
    ):
        """Execute a raw InfluxQL query.

        Args:
            query: The InfluxQL query string
            params: Query parameters
            epoch: Time precision for returned timestamps
            expected_response_code: Expected HTTP response code
            database: Database to query (overrides configured database)
            raise_errors: Whether to raise exceptions on errors
            chunked: Whether to use chunked responses
            chunk_size: Size of chunks for chunked responses
            method: HTTP method to use

        Returns:
            Query results from InfluxDB
        """
        results = self._client.query(
            query,
            params,
            epoch,
            expected_response_code,
            database,
            raise_errors,
            chunked,
            chunk_size,
            method,
        )
        self.reset_query()
        return results

    # === Data Operations ===
    def report(self, fields, tags, timestamp=False):
        """Write a single data point to InfluxDB.

        Args:
            fields: Dict of field names and values
            tags: Dict of tag names and values
            timestamp: Optional timestamp (default: current time)

        Returns:
            True if successful, False otherwise
        """
        tags["origin"] = self.uuid
        d = {
            "fields": fields,
            "tags": tags,
            "measurement": self.metric,
        }
        if timestamp:
            d["time"] = timestamp
        return self.report_points([d])

    def report_points(self, points=None):
        """Write multiple data points to InfluxDB.

        Args:
            points: List of point dictionaries with 'fields', 'tags', and optionally
                   'measurement' and 'time' keys

        Returns:
            True if successful, False if no points to write
        """
        if points is None:
            points = []
        points = copy.deepcopy(points)
        for i in range(len(points)):
            p = points[i]
            if "time" not in p:
                u = datetime.now(pytz.utc)
                p["time"] = u
            p["time"] = str(p["time"])
            if "origin" not in p["tags"]:
                p["tags"]["origin"] = self.uuid
            if "measurement" not in p:
                p["measurement"] = self.metric
            points[i] = p
        if len(points):
            if self._version == 1:
                r = self._client.write_points(points)
            else:
                db_config = router.influxdb_settings[self._db_name]
                bucket = db_config.get("bucket", "metrics")
                org = db_config.get("org", "my-org")

                write_api = self._client.write_api(write_options=SYNCHRONOUS)

                write_api.write(bucket=bucket, org=org, record=points)
                r = True
            return r
        return False

    def drop_measurement(self, metric=False):
        """Drop a measurement from the database.

        Args:
            metric: Measurement name to drop (default: current metric)
        """
        if not metric:
            metric = self.metric

        if self._version == 1:
            self._client.drop_measurement(metric)
        else:
            db_config = router.influxdb_settings[self._db_name]
            bucket = db_config.get("bucket", "metrics")
            org = db_config.get("org", "my-org")
            delete_api = self._client.delete_api()
            from datetime import datetime, timezone

            start = datetime(1970, 1, 1, tzinfo=timezone.utc)
            stop = datetime.now(timezone.utc)
            predicate = f'_measurement="{metric}"'
            delete_api.delete(start, stop, predicate, bucket=bucket, org=org)

    # === Iteration ===
    def __iter__(self):
        """Iterate over query results."""
        results = self.execute_query()
        if results is None:
            return iter([])
        return iter(results)

    def __len__(self):
        """Return the number of results."""
        results = self.execute_query()
        if results is None:
            return 0
        return len(results)

    def __bool__(self):
        """Return True if there are results."""
        results = self.execute_query()
        return bool(results)
