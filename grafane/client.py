import copy
import functools
from datetime import datetime

import pytz
from influxdb import InfluxDBClient

from .exceptions import MissingInfluxDBSettings
from .querysets import InfluxQLQuerySet
from .settings import INFLUXDB_SETTINGS, TESTING


def cache_invalidation(func):
    """Decorator that resets query cache before executing query-building methods."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._executed:
            self.reset_query()
        return func(self, *args, **kwargs)

    return wrapper


class Grafane:
    def __init__(self, metric="generic"):
        self.ignore_query = False

        uuid = INFLUXDB_SETTINGS.get("uuid", False)
        if not uuid:
            raise MissingInfluxDBSettings(
                "missing uuid in INFLUXDB_SETTINGS", ["missing uuid"]
            )

        self.uuid = uuid
        self._client = InfluxDBClient(
            host=INFLUXDB_SETTINGS["db_host"],
            port=INFLUXDB_SETTINGS["db_port"],
            username=INFLUXDB_SETTINGS["db_user"],
            password=INFLUXDB_SETTINGS["db_pass"],
            database=INFLUXDB_SETTINGS["db_name"],
            ssl=False,
        )

        self.metric = metric
        if TESTING:
            self.metric = f"{metric}-testing"

        self._queryset = InfluxQLQuerySet(self.metric)
        self._results = None
        self._executed = False

    # === Query State ===
    def reset_query(self):
        self._queryset.reset()
        self._results = None
        self._executed = False

    # === Delegation to QuerySet ===
    @cache_invalidation
    def select(self, fields=["value"], aggregation=[]):
        self._queryset.select(fields, aggregation)
        return self

    @cache_invalidation
    def filter_by(self, tag, operator, value):
        self._queryset.filter_by(tag, operator, value)
        return self

    @cache_invalidation
    def filter_by_from_dict(self, filter_by):
        self._queryset.filter_by_from_dict(filter_by)
        return self

    @cache_invalidation
    def filter_time_range(self, r):
        self._queryset.filter_time_range(r)
        return self

    @cache_invalidation
    def time_block(self, block):
        self._queryset.time_block(block)
        return self

    @cache_invalidation
    def group_by(self, group):
        self._queryset.group_by(group)
        return self

    @cache_invalidation
    def fill_with(self, fill=False):
        self._queryset.fill_with(fill)
        return self

    def filter_value_in(self, tag, values):
        if self._executed:
            self.reset_query()
        self._queryset.filter_value_in(tag, values)
        return self

    # === Execution ===
    def execute_query(self, uuid=None):
        if self._executed:
            return self._results
        if uuid:
            self._queryset.filter_by("origin", "=", uuid)

        raw_results = self._client.query(self._queryset.query)
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
        tags["origin"] = self.uuid
        d = {
            "fields": fields,
            "tags": tags,
            "measurement": self.metric,
        }
        if timestamp:
            d["time"] = timestamp
        return self.report_points([d])

    def report_points(self, points=[]):
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
            r = self._client.write_points(points)
            return r
        return False

    def drop_measurement(self, metric=False):
        if not metric:
            metric = self.metric
        self._client.drop_measurement(metric)

    # === Iteration ===
    def __iter__(self):
        return iter(self.execute_query())

    def __len__(self):
        return len(self.execute_query())

    def __bool__(self):
        return bool(self.execute_query())
