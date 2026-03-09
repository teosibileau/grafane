"""Tests for grafane.exceptions module."""

import pytest

from grafane.exceptions import (
    DatabaseNotFoundError,
    GrafaneError,
    InfluxDBV1NotInstalled,
    InfluxDBV2NotInstalled,
    MetricNotFoundError,
    MissingInfluxDBSettings,
    MultipleConfigError,
    UnsupportedOperationError,
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


class TestInfluxDBV1NotInstalled:
    """Tests for InfluxDBV1NotInstalled exception."""

    def test_inherits_from_grafane_error(self):
        """InfluxDBV1NotInstalled should inherit from GrafaneError."""
        assert issubclass(InfluxDBV1NotInstalled, GrafaneError)

    def test_default_message(self):
        """Default message should mention pip install grafane[v1]."""
        with pytest.raises(InfluxDBV1NotInstalled) as exc_info:
            raise InfluxDBV1NotInstalled()
        assert "pip install grafane[v1]" in str(exc_info.value)

    def test_custom_message(self):
        """Can provide custom message."""
        with pytest.raises(InfluxDBV1NotInstalled) as exc_info:
            raise InfluxDBV1NotInstalled("custom error message")
        assert str(exc_info.value) == "custom error message"

    def test_catchable_as_grafane_error(self):
        """InfluxDBV1NotInstalled can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise InfluxDBV1NotInstalled()


class TestInfluxDBV2NotInstalled:
    """Tests for InfluxDBV2NotInstalled exception."""

    def test_inherits_from_grafane_error(self):
        """InfluxDBV2NotInstalled should inherit from GrafaneError."""
        assert issubclass(InfluxDBV2NotInstalled, GrafaneError)

    def test_default_message(self):
        """Default message should mention pip install grafane."""
        with pytest.raises(InfluxDBV2NotInstalled) as exc_info:
            raise InfluxDBV2NotInstalled()
        assert "pip install grafane" in str(exc_info.value)

    def test_custom_message(self):
        """Can provide custom message."""
        with pytest.raises(InfluxDBV2NotInstalled) as exc_info:
            raise InfluxDBV2NotInstalled("custom error message")
        assert str(exc_info.value) == "custom error message"

    def test_catchable_as_grafane_error(self):
        """InfluxDBV2NotInstalled can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise InfluxDBV2NotInstalled()


class TestUnsupportedOperationError:
    """Tests for UnsupportedOperationError exception."""

    def test_inherits_from_grafane_error(self):
        """UnsupportedOperationError should inherit from GrafaneError."""
        assert issubclass(UnsupportedOperationError, GrafaneError)

    def test_message_and_version(self):
        """Stores version attribute when provided."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            raise UnsupportedOperationError("operation not supported", version=2)
        assert str(exc_info.value) == "operation not supported"
        assert exc_info.value.version == 2

    def test_message_only(self):
        """Works without version."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            raise UnsupportedOperationError("operation not supported")
        assert str(exc_info.value) == "operation not supported"
        assert exc_info.value.version is None

    def test_catchable_as_grafane_error(self):
        """UnsupportedOperationError can be caught as GrafaneError."""
        with pytest.raises(GrafaneError):
            raise UnsupportedOperationError("test")


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_all_exceptions_inherit_from_grafane_error(self):
        """All custom exceptions should inherit from GrafaneError."""
        exceptions = [
            MissingInfluxDBSettings,
            MetricNotFoundError,
            MultipleConfigError,
            DatabaseNotFoundError,
            InfluxDBV1NotInstalled,
            InfluxDBV2NotInstalled,
            UnsupportedOperationError,
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
            InfluxDBV1NotInstalled("test"),
            InfluxDBV2NotInstalled("test"),
            UnsupportedOperationError("test"),
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
