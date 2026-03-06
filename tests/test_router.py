"""Tests for grafane.router module."""

from unittest.mock import MagicMock, patch

import pytest

from grafane.exceptions import (
    DatabaseNotFoundError,
    MetricNotFoundError,
    MultipleConfigError,
)
from grafane.router import Router, router


class TestRouterResolveMetric:
    """Tests for Router.resolve_metric method."""

    def test_resolve_explicit_db(self, configured_settings):
        """Explicit db parameter returns that database."""
        r = Router()
        db_name = r.resolve_metric("any_metric", db="default")
        assert db_name == "default"

    def test_resolve_explicit_db_not_found(self, configured_settings):
        """Explicit db parameter that doesn't exist raises DatabaseNotFoundError."""
        r = Router()
        with pytest.raises(DatabaseNotFoundError) as exc_info:
            r.resolve_metric("any_metric", db="nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_resolve_metric_in_metrics_list(self, multi_db_settings):
        """Metric found in exactly one database's metrics list."""
        r = Router()
        db_name = r.resolve_metric("cpu")
        assert db_name == "monitoring"

    def test_resolve_metric_in_analytics(self, multi_db_settings):
        """Analytics metrics resolve to analytics database."""
        r = Router()
        assert r.resolve_metric("page_views") == "analytics"
        assert r.resolve_metric("sessions") == "analytics"
        assert r.resolve_metric("events") == "analytics"

    def test_resolve_unknown_metric_uses_fallback(self, multi_db_settings):
        """Unknown metric uses fallback database (empty metrics list)."""
        r = Router()
        db_name = r.resolve_metric("unknown_metric")
        assert db_name == "default"  # default has empty metrics list

    def test_resolve_metric_multiple_matches_raises(self, conflicting_metrics_settings):
        """Metric in multiple databases raises MultipleConfigError."""
        r = Router()
        with pytest.raises(MultipleConfigError) as exc_info:
            r.resolve_metric("shared_metric")
        assert exc_info.value.databases is not None
        assert set(exc_info.value.databases) == {"db1", "db2"}
        assert "multiple databases" in str(exc_info.value)

    def test_resolve_metric_multiple_matches_with_explicit_db(
        self, conflicting_metrics_settings
    ):
        """Metric in multiple databases works with explicit db parameter."""
        r = Router()
        assert r.resolve_metric("shared_metric", db="db1") == "db1"
        assert r.resolve_metric("shared_metric", db="db2") == "db2"

    def test_resolve_unknown_metric_no_fallback_raises(self, no_fallback_settings):
        """Unknown metric without fallback database raises MetricNotFoundError."""
        r = Router()
        with pytest.raises(MetricNotFoundError) as exc_info:
            r.resolve_metric("unknown_metric")
        assert "not found" in str(exc_info.value)
        assert "unknown_metric" in str(exc_info.value)


class TestRouterFindDatabasesForMetric:
    """Tests for Router.find_databases_for_metric method."""

    def test_find_single_database(self, multi_db_settings):
        """Metric in one database returns single-item list."""
        r = Router()
        dbs = r.find_databases_for_metric("cpu")
        assert dbs == ["monitoring"]

    def test_find_multiple_databases(self, conflicting_metrics_settings):
        """Metric in multiple databases returns all matching."""
        r = Router()
        dbs = r.find_databases_for_metric("shared_metric")
        assert set(dbs) == {"db1", "db2"}

    def test_find_no_databases(self, multi_db_settings):
        """Metric not in any database returns empty list."""
        r = Router()
        dbs = r.find_databases_for_metric("nonexistent_metric")
        assert dbs == []


class TestRouterFindFallbackDatabase:
    """Tests for Router.find_fallback_database method."""

    def test_find_fallback_exists(self, multi_db_settings):
        """Returns database with empty metrics list."""
        r = Router()
        fallback = r.find_fallback_database()
        assert fallback == "default"

    def test_find_fallback_none(self, no_fallback_settings):
        """Returns None when no fallback database exists."""
        r = Router()
        fallback = r.find_fallback_database()
        assert fallback is None


class TestRouterGetClient:
    """Tests for Router.get_client method."""

    def test_get_client_creates_client(self, configured_settings):
        """get_client creates an InfluxDBClient."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = r.get_client("default")

            assert client == mock_instance
            mock_client.assert_called_once()

    def test_get_client_caches_client(self, configured_settings):
        """get_client caches and reuses clients."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client1 = r.get_client("default")
            client2 = r.get_client("default")

            assert client1 is client2
            assert mock_client.call_count == 1  # Only created once

    def test_get_client_not_found(self, configured_settings):
        """get_client raises DatabaseNotFoundError for unknown database."""
        r = Router()
        with pytest.raises(DatabaseNotFoundError):
            r.get_client("nonexistent")


class TestRouterGetClientForMetric:
    """Tests for Router.get_client_for_metric method."""

    def test_get_client_for_metric_returns_tuple(self, configured_settings):
        """get_client_for_metric returns (client, db_name) tuple."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client, db_name = r.get_client_for_metric("any_metric")

            assert client == mock_instance
            assert db_name == "default"

    def test_get_client_for_metric_with_explicit_db(self, multi_db_settings):
        """get_client_for_metric with explicit db uses that database."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client, db_name = r.get_client_for_metric("any_metric", db="analytics")

            assert db_name == "analytics"


class TestRouterCacheManagement:
    """Tests for Router cache management."""

    def test_clear_cache(self, configured_settings):
        """clear_cache removes all cached clients."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_client.return_value = MagicMock()

            r.get_client("default")
            assert len(r.cached_databases) == 1

            r.clear_cache()
            assert len(r.cached_databases) == 0

    def test_cached_databases_property(self, configured_settings):
        """cached_databases returns list of cached database names."""
        r = Router()
        with patch("grafane.router.InfluxDBClient") as mock_client:
            mock_client.return_value = MagicMock()

            assert r.cached_databases == []

            r.get_client("default")
            assert r.cached_databases == ["default"]


class TestGlobalRouter:
    """Tests for the global router instance."""

    def test_global_router_exists(self):
        """Global router instance is available."""
        assert router is not None
        assert isinstance(router, Router)
