"""Flux query set implementation for InfluxDB v2.

This module provides a query builder that generates Flux queries
while maintaining the same fluent interface as InfluxQL.
"""

from datetime import datetime
from typing import Any, Self

from .base import BaseQuerySet
from .exceptions import WrongArgumentType


class FluxQuerySet(BaseQuerySet):
    """Builds Flux query strings for InfluxDB v2.

    This class generates Flux queries while maintaining the same
    fluent interface as InfluxQLQuerySet for API parity.
    """

    def __init__(self, metric: str, bucket: str | None = None):
        """Initialize the Flux query builder.

        Args:
            metric: The measurement/table name to query
            bucket: The InfluxDB v2 bucket name (required for v2)
        """
        self.metric = metric
        self.bucket = bucket
        self.reset()

    def reset(self) -> None:
        """Reset all query state to defaults."""
        self.fields: list[str] = []
        self.aggregation: list[str] = []
        self.group: list[str] = []
        self.filter: list[str] = []
        self.time_range: list[str] = []
        self.fill: str | bool = False
        self.flux: str = ""
        self._has_aggregation: bool = False
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the Flux query string from current state."""
        parts = []

        from_part = f'from(bucket: "{self.bucket}")'
        parts.append(from_part)

        if self.time_range:
            parts.append(" |> " + " |> ".join(self.time_range))
        else:
            parts.append(" |> range(start: -1h)")

        # Always filter by measurement
        parts.append(f' |> filter(fn: (r) => r._measurement == "{self.metric}")')

        filter_parts = [f for f in self.filter if f]
        if filter_parts:
            combined_filter = " and ".join(filter_parts)
            parts.append(f" |> filter(fn: (r) => {combined_filter})")

        if self._has_aggregation:
            if self.time_range:
                time_block = None
                for tr in self.time_range:
                    if "window" in tr:
                        time_block = tr
                        break

                if time_block:
                    window_config = self._extract_window_config(time_block)
                    if window_config:
                        every, fn = window_config
                        parts.append(
                            f" |> aggregateWindow(every: {every}, fn: {fn}, createEmpty: false)"
                        )
            else:
                parts.append(
                    " |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)"
                )

        if self.group:
            group_cols = ", ".join(self.group)
            parts.append(f" |> group(columns: [{group_cols}])")

        if self.fill:
            fill_config = self._get_fill_config()
            if fill_config:
                parts.append(f" |> fill({fill_config})")

        self.flux = "".join(parts)

    def _extract_window_config(self, time_block: str) -> tuple[str, str] | None:
        """Extract window interval and function from time_block."""
        import re

        match = re.search(r"window\(every:\s*(\w+)\)", time_block)
        if match:
            every = match.group(1)
            if self.aggregation:
                fn = self.aggregation[0] if self.aggregation else "mean"
            else:
                fn = "mean"
            return (every, fn)
        return None

    def _get_fill_config(self) -> str | None:
        """Convert fill strategy to Flux fill config."""
        fill_map = {
            "none": 'mode: "none"',
            "null": 'mode: "null"',
            "0": "value: 0.0",
            "previous": "usePrevious: true",
            "linear": 'method: "linear"',
        }
        return fill_map.get(self.fill)

    @property
    def query(self) -> str:
        """Return the built Flux query string."""
        return self.flux

    def select(self, fields: Any = None, aggregation: Any = None) -> Self:
        """Set fields and optional aggregations.

        Args:
            fields: Field name(s) to select
            aggregation: Aggregation function(s) to apply

        Returns:
            Self for method chaining
        """
        self.fields, self.aggregation = [], []
        if fields is None:
            fields = ["_value"]
        if isinstance(fields, list):
            self.fields = fields
        elif isinstance(fields, str):
            self.fields = [fields]
        else:
            raise WrongArgumentType(
                "Fields must be either a list or a string", [type(fields)]
            )

        if aggregation:
            if isinstance(aggregation, list):
                self.aggregation = aggregation
            elif isinstance(aggregation, str):
                self.aggregation = [aggregation for _ in self.fields]
            else:
                raise WrongArgumentType(
                    "Aggregation should either be a list or a string",
                    [type(aggregation)],
                )
            self._has_aggregation = True
        else:
            self._has_aggregation = False

        self.rebuild()
        return self

    def filter_by(self, tag: str, operator: str, value: str) -> Self:
        """Add a filter condition.

        Args:
            tag: Tag name to filter on
            operator: Comparison operator (=, !=, <, >, etc.)
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        op_map = {
            "=": "==",
            "!=": "!=",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
            "==": "==",
        }
        flux_op = op_map.get(operator, operator)

        if tag in ("_measurement", "measurement"):
            f = f'r._measurement {flux_op} "{value}"'
        elif tag in ("_field", "field"):
            f = f'r._field {flux_op} "{value}"'
        else:
            f = f'r["{tag}"] {flux_op} "{value}"'

        if f not in self.filter:
            self.filter.append(f)
            self.rebuild()
        return self

    def filter_by_from_dict(self, filter_by: Any) -> Self:
        """Add filters from dict (DEPRECATED).

        Deprecated: Use chained filter_by() calls instead.

        Args:
            filter_by: Dict or list of dicts with 'tag', 'operator', 'value' keys

        Returns:
            Self for method chaining
        """
        import warnings

        warnings.warn(
            "filter_by_from_dict is deprecated. Use chained filter_by() calls instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not isinstance(filter_by, (list, dict)):
            raise WrongArgumentType(
                "Filter should be provided as a list or a dictionary"
            )
        if isinstance(filter_by, dict):
            filter_by = [filter_by]
        validate = ["tag", "operator", "value"]
        for f in filter_by:
            for v in validate:
                if v not in f:
                    raise WrongArgumentType("Missing filter_by[%s] key" % v)
            self.filter_by(**f)
        return self

    def filter_time_range(self, r: Any) -> Self:
        """Filter results by time range.

        Args:
            r: Tuple/list of (start, end) datetime objects

        Returns:
            Self for method chaining
        """
        if not isinstance(r, (list, tuple)):
            raise WrongArgumentType(
                "Time range should be provided as a list or a tuple"
            )

        r = list(r)
        if len(r) == 2:
            if r[0] > r[1]:
                start, stop = r[1], r[0]
            else:
                start, stop = r[0], r[1]
        else:
            start = r[0]
            stop = None

        start_str = self._format_datetime(start)
        if stop:
            stop_str = self._format_datetime(stop)
            range_part = f"range(start: {start_str}, stop: {stop_str})"
        else:
            range_part = f"range(start: {start_str})"

        self.time_range = [range_part]
        self.rebuild()
        return self

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for Flux query."""
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)

    def time_block(self, block: str) -> Self:
        """Group results by time interval.

        Args:
            block: Time interval (e.g., '1h', '5m', '1d')

        Returns:
            Self for method chaining
        """
        window_part = f"window(every: {block})"
        for tr in self.time_range:
            if "range" in tr:
                self.time_range.append(window_part)
                break
        self._has_aggregation = True
        self.rebuild()
        return self

    def group_by(self, group: Any) -> Self:
        """Group results by tag(s).

        Args:
            group: Tag name(s) to group by

        Returns:
            Self for method chaining
        """
        if not self._has_aggregation and not self.aggregation:
            raise WrongArgumentType("In order to group results, aggregate first")

        if isinstance(group, str):
            group = [group]

        for g in group:
            self.group.append(f'"{g}"')

        self.group = list(set(self.group))
        self.rebuild()
        return self

    def fill_with(self, fill: str | bool = False) -> Self:
        """Fill missing values in the result set.

        Args:
            fill: Fill strategy ('none', 'null', '0', 'previous', 'linear')
                  or False to disable

        Returns:
            Self for method chaining
        """
        f = ["none", "null", "0", "previous", "linear"]
        if fill and fill in f:
            self.fill = fill
        else:
            self.fill = False
        self.rebuild()
        return self

    def filter_value_in(self, tag: str, values: list) -> Self:
        """Filter where tag value is in a list of values.

        Args:
            tag: Tag name to filter on
            values: List of acceptable values

        Returns:
            Self for method chaining
        """
        if values:
            value_parts = [f'"{v}"' for v in values]
            values_str = ", ".join(value_parts)
            filters = f'contains(value: r["{tag}"], set: [{values_str}])'
            self.filter.append(filters)
        self.rebuild()
        return self

    def parse_results(self, raw_results: Any) -> list:
        """Parse Flux query results into list of dicts.

        Args:
            raw_results: Flux query result (tables)

        Returns:
            List of result dictionaries with consistent format
        """
        results = []
        for table in raw_results:
            for record in table.records:
                result = {
                    "time": record.get_time(),
                    "_value": record.get_value(),
                }
                result.update(record.values)
                results.append(result)
        return results
