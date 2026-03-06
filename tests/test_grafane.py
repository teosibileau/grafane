"""Integration tests for the Grafane client.

These tests verify the Grafane client's query building and data operations.
They use a real InfluxDB connection when available, or mock it otherwise.
"""

import warnings
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from grafane import Grafane, WrongArgumentType
from grafane.client import cache_invalidation


@pytest.fixture
def points():
    """Sample data points for testing."""
    return [
        {
            "fields": {
                "value": 1.2,
                "value2": 1.3,
            },
            "tags": {"tag1": "value1", "tag2": "value2"},
        },
        {
            "fields": {
                "value": 1.86,
                "value2": 2.3,
            },
            "tags": {"tag1": "value2", "tag2": "value1"},
        },
        {
            "fields": {
                "value": 1.4,
                "value2": 1.1,
            },
            "tags": {"tag1": "value3", "tag2": "value2"},
        },
        {
            "fields": {
                "value": 1.8,
                "value2": 1.95,
            },
            "tags": {"tag1": "value1", "tag2": "value2"},
        },
    ]


@pytest.fixture
def client(configured_settings):
    """Create a Grafane client for testing.

    Uses the configured_settings fixture from conftest.py to ensure
    settings are properly configured before creating the client.
    """
    with patch("grafane.router.InfluxDBClient") as mock_influx:
        mock_client = MagicMock()
        mock_influx.return_value = mock_client

        client = Grafane()
        yield client

        # Cleanup
        try:
            client.drop_measurement()
        except Exception:
            pass  # Ignore cleanup errors in tests


@pytest.fixture
def integration_client(configured_settings):
    """Create a real Grafane client for integration testing.

    This fixture creates a real InfluxDB connection for integration tests.
    Skip tests using this fixture if InfluxDB is not available.
    """
    try:
        client = Grafane()
        yield client
        client.drop_measurement()
    except Exception as e:
        pytest.skip(f"InfluxDB not available: {e}")


# === Unit Tests (mocked InfluxDB) ===


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
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.filter_by_from_dict(
                [{"tag": "tag1", "operator": "=", "value": "value1"}]
            )
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message)


class TestGrafaneTimeOperations:
    """Tests for Grafane time-related operations."""

    def test_filter_time_range(self, client):
        """filter_time_range() adds time condition."""

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


class TestGrafaneGroupBy:
    """Tests for Grafane GROUP BY functionality."""

    def test_group_by_single(self, client):
        """group_by() with single tag."""
        client.select("value", "sum").group_by("tag1")
        query = client._queryset.query
        assert "GROUP BY" in query.upper()
        assert "tag1" in query


class TestGrafaneQueryState:
    """Tests for Grafane query state management."""

    def test_execute_query_sets_executed_flag(self, client):
        """execute_query() sets _executed flag."""
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = []

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
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = [{"value": 1}]

        client.select()
        result1 = client.execute_query()
        result2 = client.execute_query()

        assert result1 == result2
        # Should only query once due to caching
        assert client._client.query.call_count == 1


class TestGrafaneIteration:
    """Tests for Grafane iteration support."""

    def test_iter_triggers_query_execution(self, client):
        """Iterating over client triggers query execution."""
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = [
            {"value": 1},
            {"value": 2},
        ]

        client.select()
        results = list(client)

        assert len(results) == 2
        assert client._executed is True

    def test_len_triggers_query_execution(self, client):
        """len(client) triggers query execution."""
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = [
            {"value": 1},
            {"value": 2},
        ]

        client.select()
        length = len(client)

        assert length == 2
        assert client._executed is True

    def test_bool_triggers_query_execution(self, client):
        """bool(client) triggers query execution."""
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = [{"value": 1}]

        client.select()
        result = bool(client)

        assert result is True
        assert client._executed is True

    def test_bool_false_for_empty_results(self, client):
        """bool(client) is False when no results."""
        client._client.query.return_value = MagicMock()
        client._client.query.return_value.get_points.return_value = []

        client.select()
        result = bool(client)

        assert result is False


class TestCacheInvalidationDecorator:
    """Tests for the cache_invalidation decorator."""

    def test_decorator_calls_function(self):
        """Decorator should call the wrapped function."""
        mock_func = MagicMock(return_value="result")
        decorated = cache_invalidation(mock_func)

        mock_self = MagicMock()
        result = decorated(mock_self)

        mock_func.assert_called_once_with(mock_self)
        assert result == "result"

    def test_decorator_resets_when_executed(self):
        """Decorator should call reset_query when _executed is True."""
        mock_func = MagicMock(return_value="result")
        decorated = cache_invalidation(mock_func)

        mock_self = MagicMock()
        mock_self._executed = True

        result = decorated(mock_self)

        mock_self.reset_query.assert_called_once()
        assert result == "result"

    def test_decorator_does_not_reset_when_not_executed(self):
        """Decorator should NOT call reset_query when _executed is False."""
        mock_func = MagicMock(return_value="result")
        decorated = cache_invalidation(mock_func)

        mock_self = MagicMock()
        mock_self._executed = False

        result = decorated(mock_self)

        mock_self.reset_query.assert_not_called()
        assert result == "result"

    def test_decorator_passes_args(self):
        """Decorator should pass arguments to wrapped function."""
        mock_func = MagicMock(return_value="result")
        decorated = cache_invalidation(mock_func)

        mock_self = MagicMock()

        result = decorated(mock_self, "arg1", "arg2", key="value")

        mock_func.assert_called_once_with(mock_self, "arg1", "arg2", key="value")
        assert result == "result"


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


class TestGrafaneClientProperties:
    """Tests for Grafane client properties."""

    def test_database_name_property(self, client):
        """database_name property returns the configured database."""
        assert client.database_name == "default"

    def test_uuid_from_settings(self, client, configured_settings):
        """UUID is loaded from settings."""
        assert client.uuid == configured_settings.UUID

    def test_metric_stored(self, configured_settings):
        """Metric name is stored on client."""
        with patch("grafane.router.InfluxDBClient"):
            client = Grafane("my_metric")
            assert client._original_metric == "my_metric"
            assert client.metric == "my_metric"


class TestGrafaneWithExplicitDb:
    """Tests for Grafane with explicit database parameter."""

    def test_explicit_db_parameter(self, configured_settings):
        """Client can be created with explicit db parameter."""
        with patch("grafane.router.InfluxDBClient"):
            client = Grafane("any_metric", db="default")
            assert client.database_name == "default"
