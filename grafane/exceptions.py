"""Grafane exception classes."""


class GrafaneError(Exception):
    """Base exception for all Grafane errors."""

    pass


class MissingInfluxDBSettings(GrafaneError):
    """Raised when required InfluxDB settings are missing or invalid."""

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class MetricNotFoundError(GrafaneError):
    """Raised when a metric is not found in any database's metrics list."""

    pass


class MultipleConfigError(GrafaneError):
    """Raised when a metric is found in multiple databases."""

    def __init__(self, message, databases=None):
        super().__init__(message)
        self.databases = databases


class DatabaseNotFoundError(GrafaneError):
    """Raised when an explicit database name is not found in settings."""

    pass


class InfluxDBV1NotInstalled(GrafaneError):
    """Raised when InfluxDB v1 client is required but not installed."""

    def __init__(self, message=None):
        if message is None:
            message = (
                "InfluxDB v1 client requires 'influxdb' package. "
                "Install with: pip install grafane[v1]"
            )
        super().__init__(message)


class InfluxDBV2NotInstalled(GrafaneError):
    """Raised when InfluxDB v2 client is required but not installed.

    Deprecated: v2 is now installed by default.
    """

    def __init__(self, message=None):
        if message is None:
            message = (
                "InfluxDB v2 client requires 'influxdb-client' package. "
                "Install with: pip install grafane"
            )
        super().__init__(message)


class UnsupportedOperationError(GrafaneError):
    """Raised when an operation is not supported for a specific InfluxDB version."""

    def __init__(self, message, version=None):
        super().__init__(message)
        self.version = version
