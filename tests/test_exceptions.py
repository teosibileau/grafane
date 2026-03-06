"""Tests for grafane.exceptions module."""

import pytest

from grafane.exceptions import (
    DatabaseNotFoundError,
    GrafaneError,
    MetricNotFoundError,
    MissingInfluxDBSettings,
    MultipleConfigError,
)


class TestGrafaneError:
    """Tests for the base GrafaneError exception."""

    def test_is_exception(self):
        """GrafaneError should be an Exception subclass."""
        assert issubclass(GrafaneError, Exception)

    def test_can_raise_with_message(self):
        """GrafaneError can be raised with a message."""
        with pytest.raises(GrafaneError) as exc_info:
            raise GrafaneError("test error")
        assert str(exc_info.value) == "test error"


class TestMissingInfluxDBSettings:
    """Tests for MissingInfluxDBSettings exception."""

    def test_inherits_from_grafane_error(self):
        """MissingInfluxDBSettings should inherit from GrafaneError."""
        assert issubclass(MissingInfluxDBSettings, GrafaneError)

    def test_message_only(self):
        """Can be raised with just a message."""
        with pytest.raises(MissingInfluxDBSettings) as exc_info:
            raise MissingInfluxDBSettings("missing settings")
        assert str(exc_info.value) == "missing settings"
        assert exc_info.value.errors is None

    def test_message_and_errors(self):
        """Can be raised with message and errors list."""
        errors = ["missing host", "missing port"]
        with pytest.raises(MissingInfluxDBSettings) as exc_info:
            raise MissingInfluxDBSettings("invalid settings", errors=errors)
        assert str(exc_info.value) == "invalid settings"
        assert exc_info.value.errors == ["missing host", "missing port"]

    def test_catchable_as_grafane_error(self):
        """MissingInfluxDBSettings can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise MissingInfluxDBSettings("test")


class TestMetricNotFoundError:
    """Tests for MetricNotFoundError exception."""

    def test_inherits_from_grafane_error(self):
        """MetricNotFoundError should inherit from GrafaneError."""
        assert issubclass(MetricNotFoundError, GrafaneError)

    def test_can_raise_with_message(self):
        """Can be raised with a message."""
        with pytest.raises(MetricNotFoundError) as exc_info:
            raise MetricNotFoundError("metric 'cpu' not found in any database")
        assert str(exc_info.value) == "metric 'cpu' not found in any database"

    def test_catchable_as_grafane_error(self):
        """MetricNotFoundError can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise MetricNotFoundError("test")


class TestMultipleConfigError:
    """Tests for MultipleConfigError exception."""

    def test_inherits_from_grafane_error(self):
        """MultipleConfigError should inherit from GrafaneError."""
        assert issubclass(MultipleConfigError, GrafaneError)

    def test_message_only(self):
        """Can be raised with just a message."""
        with pytest.raises(MultipleConfigError) as exc_info:
            raise MultipleConfigError("metric found in multiple databases")
        assert str(exc_info.value) == "metric found in multiple databases"
        assert exc_info.value.databases is None

    def test_message_and_databases(self):
        """Can be raised with message and databases list."""
        databases = ["production", "staging"]
        with pytest.raises(MultipleConfigError) as exc_info:
            raise MultipleConfigError(
                "metric 'cpu' found in multiple databases",
                databases=databases,
            )
        assert str(exc_info.value) == "metric 'cpu' found in multiple databases"
        assert exc_info.value.databases == ["production", "staging"]

    def test_catchable_as_grafane_error(self):
        """MultipleConfigError can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise MultipleConfigError("test")


class TestDatabaseNotFoundError:
    """Tests for DatabaseNotFoundError exception."""

    def test_inherits_from_grafane_error(self):
        """DatabaseNotFoundError should inherit from GrafaneError."""
        assert issubclass(DatabaseNotFoundError, GrafaneError)

    def test_can_raise_with_message(self):
        """Can be raised with a message."""
        with pytest.raises(DatabaseNotFoundError) as exc_info:
            raise DatabaseNotFoundError("database 'unknown' not found in settings")
        assert str(exc_info.value) == "database 'unknown' not found in settings"

    def test_catchable_as_grafane_error(self):
        """DatabaseNotFoundError can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise DatabaseNotFoundError("test")


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_all_exceptions_inherit_from_grafane_error(self):
        """All custom exceptions should inherit from GrafaneError."""
        exceptions = [
            MissingInfluxDBSettings,
            MetricNotFoundError,
            MultipleConfigError,
            DatabaseNotFoundError,
        ]
        for exc_class in exceptions:
            assert issubclass(
                exc_class, GrafaneError
            ), f"{exc_class.__name__} should inherit from GrafaneError"

    def test_catch_all_grafane_exceptions(self):
        """Can catch all grafane exceptions with GrafaneError."""
        exceptions_to_test = [
            MissingInfluxDBSettings("test"),
            MetricNotFoundError("test"),
            MultipleConfigError("test"),
            DatabaseNotFoundError("test"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except GrafaneError:
                pass  # Expected
            except Exception:
                pytest.fail(
                    f"{type(exc).__name__} was not caught by GrafaneError handler"
                )
