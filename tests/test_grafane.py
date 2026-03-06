"""Unit tests for the Grafane client.

These tests verify pure logic with mocked InfluxDB connections.
No services required.
"""

from unittest.mock import MagicMock, patch


from grafane import Grafane
from grafane.client import cache_invalidation


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


class TestGrafaneWithExplicitDb:
    """Tests for Grafane with explicit database parameter."""

    def test_explicit_db_parameter(self, configured_settings):
        """Client can be created with explicit db parameter."""
        with patch("grafane.router.InfluxDBClientV1"):
            client = Grafane("any_metric", db="default")
            assert client.database_name == "default"


class TestGrafaneClientProperties:
    """Tests for Grafane client properties that require mocking."""

    def test_metric_stored(self, configured_settings):
        """Metric name is stored on client."""
        with patch("grafane.router.InfluxDBClientV1"):
            client = Grafane("my_metric")
            assert client._original_metric == "my_metric"
            assert client.metric == "my_metric"
