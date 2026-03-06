import pytest
import warnings
from datetime import datetime
from grafane.querysets import InfluxQLQuerySet, WrongArgumentType


class TestInfluxQLQuerySetSelect:
    def test_default_select(self):
        qs = InfluxQLQuerySet("my_metric")
        assert qs.query == 'SELECT value FROM "my_metric"'

    def test_select_single_field(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["temperature"])
        assert qs.query == 'SELECT temperature FROM "my_metric"'

    def test_select_single_field_as_string(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select("temperature")
        assert qs.query == 'SELECT temperature FROM "my_metric"'

    def test_select_multiple_fields(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value", "value2"])
        assert qs.query == 'SELECT value, value2 FROM "my_metric"'

    def test_select_with_single_aggregation(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["sum"])
        assert qs.query == 'SELECT sum("value") FROM "my_metric"'

    def test_select_with_aggregation_as_string(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], "sum")
        assert qs.query == 'SELECT sum("value") FROM "my_metric"'

    def test_select_multiple_fields_with_single_aggregation(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value", "value2"], ["sum"])
        assert 'sum("value")' in qs.query
        assert 'sum("value2")' in qs.query

    def test_select_multiple_fields_with_multiple_aggregations(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value", "value2"], ["sum", "count"])
        assert 'sum("value")' in qs.query
        assert 'count("value2")' in qs.query

    def test_select_invalid_fields_type(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(WrongArgumentType):
            qs.select(123)

    def test_select_invalid_aggregation_type(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(TypeError):
            qs.select(["value"], 123)

    def test_select_mismatched_aggregation_length(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(WrongArgumentType):
            qs.select(["value", "value2"], ["sum", "count", "mean"])


class TestInfluxQLQuerySetFilter:
    def test_filter_by(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_by("host", "=", "server1")
        assert "WHERE (\"host\" = 'server1')" in qs.query

    def test_filter_by_multiple(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_by("host", "=", "server1").filter_by(
            "region", "=", "us-east"
        )
        assert "(\"host\" = 'server1')" in qs.query
        assert "(\"region\" = 'us-east')" in qs.query
        assert " AND " in qs.query

    def test_filter_by_no_duplicate(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_by("host", "=", "server1").filter_by("host", "=", "server1")
        assert qs.query.count("host") == 1

    def test_filter_value_in(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_value_in("host", ["server1", "server2"])
        assert "(\"host\" = 'server1')" in qs.query
        assert "(\"host\" = 'server2')" in qs.query
        assert " OR " in qs.query

    def test_filter_value_in_empty(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_value_in("host", [])
        assert "WHERE" not in qs.query

    def test_filter_by_from_dict_single(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_by_from_dict(
            {"tag": "host", "operator": "=", "value": "server1"}
        )
        assert "(\"host\" = 'server1')" in qs.query

    def test_filter_by_from_dict_multiple(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select().filter_by_from_dict(
            [
                {"tag": "host", "operator": "=", "value": "server1"},
                {"tag": "region", "operator": "=", "value": "us-east"},
            ]
        )
        assert "(\"host\" = 'server1')" in qs.query
        assert "(\"region\" = 'us-east')" in qs.query

    def test_filter_by_from_dict_deprecation_warning(self):
        qs = InfluxQLQuerySet("my_metric")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            qs.select().filter_by_from_dict(
                {"tag": "host", "operator": "=", "value": "server1"}
            )
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_filter_by_from_dict_invalid_type(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(WrongArgumentType):
            qs.filter_by_from_dict("invalid")

    def test_filter_by_from_dict_missing_key(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(WrongArgumentType):
            qs.filter_by_from_dict({"tag": "host", "operator": "="})


class TestInfluxQLQuerySetTimeRange:
    def test_filter_time_range_single(self):
        qs = InfluxQLQuerySet("my_metric")
        dt = datetime(2024, 1, 1, 12, 0, 0)
        qs.select().filter_time_range([dt])
        assert "(time >=" in qs.query
        assert "ms)" in qs.query

    def test_filter_time_range_tuple(self):
        qs = InfluxQLQuerySet("my_metric")
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 2, 12, 0, 0)
        qs.select().filter_time_range((start, end))
        assert "(time >=" in qs.query
        assert "(time <=" in qs.query

    def test_filter_time_range_swaps_if_reversed(self):
        qs = InfluxQLQuerySet("my_metric")
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 2, 12, 0, 0)
        qs.select().filter_time_range([end, start])
        assert "(time >=" in qs.query
        assert "(time <=" in qs.query

    def test_filter_time_range_invalid_type(self):
        qs = InfluxQLQuerySet("my_metric")
        with pytest.raises(WrongArgumentType):
            qs.filter_time_range("invalid")


class TestInfluxQLQuerySetGroupBy:
    def test_time_block(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h")
        assert "GROUP BY time(1h)" in qs.query

    def test_time_block_replaces_previous(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").time_block("30m")
        assert "time(30m)" in qs.query
        assert "time(1h)" not in qs.query

    def test_group_by_single(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["count"]).group_by("region")
        assert '"region"' in qs.query

    def test_group_by_multiple(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["count"]).group_by(["region", "host"])
        assert '"region"' in qs.query
        assert '"host"' in qs.query

    def test_group_by_requires_aggregation(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"])
        with pytest.raises(WrongArgumentType):
            qs.group_by("region")


class TestInfluxQLQuerySetFill:
    def test_fill_with_none(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("none")
        assert "fill(none)" in qs.query

    def test_fill_with_null(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("null")
        assert "fill(null)" in qs.query

    def test_fill_with_zero(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("0")
        assert "fill(0)" in qs.query

    def test_fill_with_previous(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("previous")
        assert "fill(previous)" in qs.query

    def test_fill_with_linear(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("linear")
        assert "fill(linear)" in qs.query

    def test_fill_with_invalid_ignored(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("invalid")
        assert "fill(" not in qs.query

    def test_fill_with_false_clears(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["mean"]).time_block("1h").fill_with("none").fill_with(
            False
        )
        assert "fill(" not in qs.query


class TestInfluxQLQuerySetChaining:
    def test_chaining_returns_self(self):
        qs = InfluxQLQuerySet("my_metric")
        result = qs.select(["value"], ["sum"])
        assert result is qs

    def test_full_chain(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["value"], ["sum"]).filter_by("host", "=", "server1").group_by(
            "region"
        )
        assert "SELECT" in qs.query
        assert "WHERE" in qs.query
        assert "GROUP BY" in qs.query


class TestInfluxQLQuerySetReset:
    def test_reset_clears_state(self):
        qs = InfluxQLQuerySet("my_metric")
        qs.select(["temperature"], ["max"]).filter_by("host", "=", "server1").group_by(
            "region"
        )
        qs.reset()
        assert qs.query == 'SELECT value FROM "my_metric"'
        assert qs.fields == ["value"]
        assert qs.aggregation == []
        assert qs.group == []
        assert qs.filter == []
        assert qs.fill is False
