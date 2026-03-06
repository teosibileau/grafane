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
