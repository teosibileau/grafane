"""Integration tests for InfluxDB v2 support.

These tests require:
- docker-compose up metrics-v2
- pip install influxdb-client
- Tests are marked with @pytest.mark.integration and @pytest.mark.v2

Run with:
    docker-compose up -d metrics-v2
    poetry run pytest tests/test_integration_v2.py -v -m "integration and v2"
"""

import pytest

# Skip all tests if influxdb-client is not installed
influxdb_client = pytest.importorskip("influxdb_client")


@pytest.mark.integration
@pytest.mark.v2
class TestGrafaneV2Integration:
    """End-to-end tests against real InfluxDB v2 (metrics-v2 compose service)."""

    def test_write_and_query(self, v2_settings):
        """Test writing and reading from InfluxDB v2."""
        from datetime import datetime
        from grafane import Grafane

        metric_name = f"test_metric_{datetime.now().strftime('%s')}"
        c = Grafane(metric_name)

        c.report(fields={"value": 42}, tags={"host": "test"})
        c.report(fields={"value": 43}, tags={"host": "test"})
        c.report(fields={"value": 44}, tags={"host": "test"})

        results = c.select(["value"]).filter_by("host", "=", "test").execute_query()

        assert len(results) >= 1

        c.drop_measurement()

    def test_filter_by_host(self, v2_settings):
        """Test filtering by host tag."""
        from datetime import datetime
        from grafane import Grafane

        metric_name = f"test_filter_{datetime.now().strftime('%s')}"
        c = Grafane(metric_name)

        c.report(fields={"value": 10}, tags={"host": "server1"})
        c.report(fields={"value": 20}, tags={"host": "server2"})
        c.report(fields={"value": 30}, tags={"host": "server1"})

        results = c.select(["value"]).filter_by("host", "=", "server1").execute_query()

        assert len(results) >= 1

        c.drop_measurement()

    def test_time_block_aggregation(self, v2_settings):
        """Test time_block with aggregation."""
        from datetime import datetime, timedelta, timezone
        from grafane import Grafane

        metric_name = f"test_agg_{datetime.now().strftime('%s')}"
        c = Grafane(metric_name)

        start = datetime.now(timezone.utc) - timedelta(hours=1)
        c.report(fields={"value": 10}, tags={"host": "test"})
        c.report(fields={"value": 20}, tags={"host": "test"})
        c.report(fields={"value": 30}, tags={"host": "test"})
        end = datetime.now(timezone.utc) + timedelta(seconds=1)

        results = (
            c.select(["value"], ["mean"])
            .filter_time_range([start, end])
            .execute_query()
        )

        assert results is not None
        assert len(results) >= 1

        c.drop_measurement()

    def test_filter_value_in(self, v2_settings):
        """Test filter_value_in for multiple values."""
        from datetime import datetime
        from grafane import Grafane

        metric_name = f"test_in_{datetime.now().strftime('%s')}"
        c = Grafane(metric_name)

        c.report(fields={"value": 1}, tags={"host": "server1"})
        c.report(fields={"value": 2}, tags={"host": "server2"})
        c.report(fields={"value": 3}, tags={"host": "server3"})

        results = (
            c.select(["value"])
            .filter_value_in("host", ["server1", "server2"])
            .execute_query()
        )

        assert len(results) >= 1

        c.drop_measurement()


@pytest.mark.integration
@pytest.mark.v2
class TestGrafaneMixedVersions:
    """Test mixed v1/v2 database configuration."""

    def test_mixed_database_resolution(self, mixed_v1_v2_settings):
        """Test that metrics are resolved to correct database versions."""
        from grafane import Grafane

        c = Grafane("cpu", db="legacy")
        assert c._version == 1

        c = Grafane("events", db="modern")
        assert c._version == 2

    def test_fallback_to_v1(self, mixed_v1_v2_settings):
        """Test that unknown metric falls back to v1 default."""
        from grafane import Grafane

        c = Grafane("completely_unknown_metric")
        assert c._version == 1
