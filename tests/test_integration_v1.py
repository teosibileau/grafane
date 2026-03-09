"""Integration tests for InfluxDB v1 support.

These tests require a running InfluxDB v1 instance.

Run with:
    docker-compose up -d metrics
    poetry run pytest tests/test_integration_v1.py -v -m "integration and v1"
"""

from datetime import datetime

import pytest

from grafane import Grafane, WrongArgumentType


@pytest.fixture
def client(v1_settings):
    """Real Grafane client for v1 integration tests."""
    metric_name = f"test_{datetime.now().strftime('%s')}"
    c = Grafane(metric_name)
    yield c
    c.drop_measurement()


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneSelect:
    """Tests for Grafane select functionality."""

    def test_select_builds_query(self, client):
        """select() should build proper query."""
        client.select()
        assert "SELECT" in client._queryset.query
        assert "value" in client._queryset.query

    def test_select_multiple_fields(self, client):
        """select() with multiple fields builds proper query."""
        client.select(fields=["value", "value2"])
        query = client._queryset.query
        assert "value" in query
        assert "value2" in query

    def test_select_with_aggregation(self, client):
        """select() with aggregation builds proper query."""
        client.select("value", "sum")
        assert "SUM" in client._queryset.query.upper()


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneFilter:
    """Tests for Grafane filter functionality."""

    def test_filter_by_builds_query(self, client):
        """filter_by() should add WHERE clause."""
        client.select().filter_by("tag1", "=", "value1")
        query = client._queryset.query
        assert "WHERE" in query.upper()
        assert "tag1" in query

    def test_filter_by_from_dict_single(self, client):
        """filter_by_from_dict() with single filter."""
        client.select()
        client.filter_by_from_dict({"tag": "tag1", "operator": "=", "value": "value1"})
        query = client._queryset.query
        assert "tag1" in query

    def test_filter_by_from_dict_multiple(self, client):
        """filter_by_from_dict() with multiple filters."""
        client.select()
        client.filter_by_from_dict(
            [
                {"tag": "tag1", "operator": "=", "value": "value1"},
                {"tag": "tag2", "operator": "=", "value": "value2"},
            ]
        )
        query = client._queryset.query
        assert "tag1" in query
        assert "tag2" in query

    def test_filter_by_from_dict_invalid_type(self, client):
        """filter_by_from_dict() with invalid type raises WrongArgumentType."""
        with pytest.raises(WrongArgumentType):
            client.filter_by_from_dict("invalid")

    def test_filter_by_from_dict_invalid_tuple(self, client):
        """filter_by_from_dict() with tuple raises WrongArgumentType."""
        with pytest.raises(WrongArgumentType):
            client.filter_by_from_dict(("tag", "=", "value"))

    def test_filter_by_from_dict_missing_key(self, client):
        """filter_by_from_dict() with missing key raises WrongArgumentType."""
        with pytest.raises(WrongArgumentType):
            client.filter_by_from_dict([{"tag": "tag1", "operator": "="}])

    def test_filter_by_from_dict_deprecation_warning(self, client):
        """filter_by_from_dict() emits deprecation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.filter_by_from_dict(
                [{"tag": "tag1", "operator": "=", "value": "value1"}]
            )
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message)


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneTimeOperations:
    """Tests for Grafane time-related operations."""

    def test_filter_time_range(self, client):
        """filter_time_range() adds time condition."""
        from datetime import timedelta

        now = datetime.now()
        client.select().filter_time_range([now - timedelta(hours=1)])
        query = client._queryset.query
        assert "time" in query.lower()

    def test_time_block(self, client):
        """time_block() adds GROUP BY time."""
        client.select("value", "sum").time_block("1h")
        query = client._queryset.query
        assert "GROUP BY" in query.upper()
        assert "time" in query.lower()


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneGroupBy:
    """Tests for Grafane GROUP BY functionality."""

    def test_group_by_single(self, client):
        """group_by() with single tag."""
        client.select("value", "sum").group_by("tag1")
        query = client._queryset.query
        assert "GROUP BY" in query.upper()
        assert "tag1" in query


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneChaining:
    """Tests for method chaining."""

    def test_chaining_select_and_filter(self, client):
        """Methods can be chained together."""
        result = client.select(fields=["value"], aggregation=["count"]).filter_by(
            tag="tag1", operator="=", value="value1"
        )
        assert result is client

    def test_chaining_full(self, client):
        """Full chain of methods works."""
        result = (
            client.select(fields=["value"], aggregation=["sum"])
            .filter_by(tag="tag1", operator="=", value="value1")
            .group_by("tag2")
        )
        assert result is client
        query = client._queryset.query
        assert "SELECT" in query.upper()
        assert "WHERE" in query.upper()
        assert "GROUP BY" in query.upper()


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneClientProperties:
    """Tests for Grafane client properties."""

    def test_database_name_property(self, client):
        """database_name property returns the configured database."""
        assert client.database_name == "default"

    def test_uuid_from_settings(self, client, v1_settings):
        """UUID is loaded from settings."""
        assert client.uuid == v1_settings.UUID


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneQueryState:
    """Tests for Grafane query state management."""

    def test_execute_query_sets_executed_flag(self, client):
        """execute_query() sets _executed flag."""
        client.report(fields={"value": 1.0}, tags={"tag1": "v1"})

        client.select()
        assert client._executed is False
        client.execute_query()
        assert client._executed is True

    def test_reset_query_clears_executed_flag(self, client):
        """reset_query() clears _executed flag."""
        client._executed = True
        client._results = [{"value": 1}]

        client.reset_query()

        assert client._executed is False
        assert client._results is None

    def test_execute_query_caches_results(self, client):
        """execute_query() caches and returns same results."""
        client.report(fields={"value": 1.0}, tags={"tag1": "v1"})

        client.select()
        result1 = client.execute_query()
        result2 = client.execute_query()

        assert result1 == result2


@pytest.mark.integration
@pytest.mark.v1
class TestGrafaneIteration:
    """Tests for Grafane iteration support."""

    def test_iter_triggers_query_execution(self, client):
        """Iterating over client triggers query execution."""
        client.report(fields={"value": 1.0}, tags={"tag1": "v1"})
        client.report(fields={"value": 2.0}, tags={"tag1": "v2"})

        client.select()
        results = list(client)

        assert len(results) >= 2
        assert client._executed is True

    def test_len_triggers_query_execution(self, client):
        """len(client) triggers query execution."""
        client.report(fields={"value": 1.0}, tags={"tag1": "v1"})
        client.report(fields={"value": 2.0}, tags={"tag1": "v2"})

        client.select()
        length = len(client)

        assert length >= 2
        assert client._executed is True

    def test_bool_triggers_query_execution(self, client):
        """bool(client) triggers query execution."""
        client.report(fields={"value": 1.0}, tags={"tag1": "v1"})

        client.select()
        result = bool(client)

        assert result is True
        assert client._executed is True

    def test_bool_false_for_empty_results(self, client):
        """bool(client) is False when no results."""
        # Use a unique metric with no data — client fixture already has a unique name
        client.select()
        result = bool(client)

        assert result is False
