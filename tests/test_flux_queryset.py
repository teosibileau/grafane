"""Tests for FluxQuerySet."""

import pytest
from datetime import datetime

from grafane.querysets import FluxQuerySet, WrongArgumentType


class TestFluxQuerySetInitialization:
    """Tests for FluxQuerySet initialization."""

    def test_init_with_metric_and_bucket(self):
        """Test initialization with metric and bucket."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        assert qs.metric == "cpu"
        assert qs.bucket == "metrics"

    def test_init_defaults(self):
        """Test initialization with default values."""
        qs = FluxQuerySet("cpu")
        assert qs.metric == "cpu"
        assert qs.bucket is None

    def test_reset_clears_state(self):
        """Test that reset clears all query state."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select(["value"], ["mean"])
        qs.filter_by("host", "=", "server1")
        qs.reset()

        assert qs.fields == []
        assert qs.aggregation == []
        assert qs.filter == []


class TestFluxQuerySetSelect:
    """Tests for select() method."""

    def test_select_default_field(self):
        """Test select with default field."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select()
        assert qs.fields == ["_value"]

    def test_select_single_field(self):
        """Test select with single field as string."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select("usage")
        assert qs.fields == ["usage"]

    def test_select_multiple_fields(self):
        """Test select with multiple fields as list."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select(["usage", "idle"])
        assert qs.fields == ["usage", "idle"]

    def test_select_with_aggregation_string(self):
        """Test select with aggregation as string."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select("value", "mean")
        assert qs.fields == ["value"]
        assert qs.aggregation == ["mean"]
        assert qs._has_aggregation is True

    def test_select_with_aggregation_list(self):
        """Test select with aggregation as list."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select(["value1", "value2"], ["mean", "max"])
        assert qs.aggregation == ["mean", "max"]

    def test_select_invalid_fields_raises(self):
        """Test that invalid fields type raises WrongArgumentType."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        with pytest.raises(WrongArgumentType):
            qs.select(123)

    def test_select_invalid_aggregation_raises(self):
        """Test that invalid aggregation type raises WrongArgumentType."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        with pytest.raises(WrongArgumentType):
            qs.select("value", 123)


class TestFluxQuerySetFilterBy:
    """Tests for filter_by() method."""

    def test_filter_by_measurement(self):
        """Test filter by _measurement."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_by("_measurement", "=", "cpu")
        assert any("r._measurement" in f for f in qs.filter)

    def test_filter_by_field(self):
        """Test filter by _field."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_by("_field", "=", "value")
        assert any("r._field" in f for f in qs.filter)

    def test_filter_by_tag(self):
        """Test filter by regular tag."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_by("host", "=", "server1")
        assert any('r["host"]' in f for f in qs.filter)

    def test_filter_by_different_operators(self):
        """Test different comparison operators."""
        qs = FluxQuerySet("cpu", bucket="metrics")

        qs.select().filter_by("host", "!=", "server1")
        assert any("!=" in f for f in qs.filter)

        qs.reset()
        qs.select().filter_by("value", ">", "50")
        assert any(">" in f for f in qs.filter)


class TestFluxQuerySetTimeRange:
    """Tests for filter_time_range() method."""

    def test_filter_time_range_with_start_and_end(self):
        """Test time range with both start and end."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 2, 0, 0, 0)
        qs.select().filter_time_range([start, end])

        assert any("range" in tr for tr in qs.time_range)
        assert qs.query is not None

    def test_filter_time_range_start_only(self):
        """Test time range with start only."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        start = datetime(2024, 1, 1, 0, 0, 0)
        qs.select().filter_time_range([start])

        assert any("range" in tr for tr in qs.time_range)

    def test_filter_time_range_invalid_type_raises(self):
        """Test that invalid type raises WrongArgumentType."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        with pytest.raises(WrongArgumentType):
            qs.select().filter_time_range("invalid")


class TestFluxQuerySetTimeBlock:
    """Tests for time_block() method."""

    def test_time_block(self):
        """Test time_block adds window function."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_time_range([datetime(2024, 1, 1)]).time_block("1h")

        assert qs._has_aggregation is True
        assert any("window" in tr for tr in qs.time_range)


class TestFluxQuerySetGroupBy:
    """Tests for group_by() method."""

    def test_group_by_single_tag(self):
        """Test group_by with single tag."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select(["value"], ["mean"]).group_by("host")

        assert any('"host"' in g for g in qs.group)

    def test_group_by_multiple_tags(self):
        """Test group_by with multiple tags."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select(["value"], ["mean"]).group_by(["host", "region"])

        assert len(qs.group) == 2

    def test_group_by_without_aggregation_raises(self):
        """Test that group_by without aggregation raises."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        with pytest.raises(WrongArgumentType):
            qs.select().group_by("host")


class TestFluxQuerySetFillWith:
    """Tests for fill_with() method."""

    def test_fill_with_previous(self):
        """Test fill_with with previous."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("previous")
        assert qs.fill == "previous"

    def test_fill_with_null(self):
        """Test fill_with with null."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("null")
        assert qs.fill == "null"

    def test_fill_with_0(self):
        """Test fill_with with 0."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("0")
        assert qs.fill == "0"

    def test_fill_with_linear(self):
        """Test fill_with with linear."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("linear")
        assert qs.fill == "linear"

    def test_fill_with_false_disables(self):
        """Test fill_with with False disables fill."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("previous")
        qs.fill_with(False)
        assert qs.fill is False

    def test_fill_with_invalid_value(self):
        """Test fill_with with invalid value disables fill."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().fill_with("invalid")
        assert qs.fill is False


class TestFluxQuerySetFilterValueIn:
    """Tests for filter_value_in() method."""

    def test_filter_value_in_single(self):
        """Test filter_value_in with single value."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_value_in("host", ["server1"])

        assert any("in [" in f for f in qs.filter)

    def test_filter_value_in_multiple(self):
        """Test filter_value_in with multiple values."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_value_in("host", ["server1", "server2", "server3"])

        assert any("in [" in f for f in qs.filter)


class TestFluxQuerySetQuery:
    """Tests for query property."""

    def test_query_returns_string(self):
        """Test that query returns a string."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select()
        assert isinstance(qs.query, str)

    def test_query_contains_bucket(self):
        """Test that query contains bucket."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select()
        assert 'bucket: "metrics"' in qs.query

    def test_query_contains_filter(self):
        """Test that query contains filter."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        qs.select().filter_by("host", "=", "server1")
        assert "filter" in qs.query.lower()


class TestFluxQuerySetChaining:
    """Tests for method chaining."""

    def test_full_chain(self):
        """Test full method chain."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        result = (
            qs.select(["value"], ["mean"])
            .filter_by("host", "=", "server1")
            .filter_time_range([datetime(2024, 1, 1), datetime(2024, 1, 2)])
            .time_block("1h")
            .group_by("region")
            .fill_with("previous")
        )

        assert result is qs
        assert qs.fields == ["value"]
        assert qs.aggregation == ["mean"]
        assert qs._has_aggregation is True


class TestFluxQuerySetParseResults:
    """Tests for parse_results() method."""

    def test_parse_results_empty(self):
        """Test parse_results with empty results."""
        qs = FluxQuerySet("cpu", bucket="metrics")
        results = qs.parse_results([])
        assert results == []

    def test_parse_results_structure(self):
        """Test parse_results with mocked results."""
        qs = FluxQuerySet("cpu", bucket="metrics")

        class MockRecord:
            def __init__(self):
                self.values = {"host": "server1", "_field": "value"}

            def get_time(self):
                return datetime(2024, 1, 1, 0, 0, 0)

            def get_value(self):
                return 42.5

        class MockTable:
            def __init__(self):
                self.records = [MockRecord()]

        results = qs.parse_results([MockTable()])

        assert len(results) == 1
        assert results[0]["host"] == "server1"
        assert results[0]["_value"] == 42.5
