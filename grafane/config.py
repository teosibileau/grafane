"""Grafane configuration system.

This module provides Django-style settings configuration for Grafane.
Users can configure their settings module in three ways (in priority order):

1. Explicit call: `grafane.configure('myproject.settings')`
2. Environment variable: `GRAFANE_SETTINGS_MODULE=myproject.settings`
3. Default: `grafane.settings` (built-in defaults)

Example user settings module (myproject/settings.py):

    INFLUXDB_SETTINGS = {
        'default': {
            'host': 'localhost',
            'port': 8086,
            'database': 'mydb',
            'username': 'admin',
            'password': 'secret',
            'metrics': ['cpu', 'memory', 'disk'],
        },
        'analytics': {
            'host': 'analytics.example.com',
            'port': 8086,
            'database': 'analytics',
            'username': 'analytics_user',
            'password': 'analytics_pass',
            'metrics': ['page_views', 'sessions'],
        },
    }
"""

import importlib
import logging
import os
from typing import Any

from .exceptions import MissingInfluxDBSettings

logger = logging.getLogger("grafane")

# Environment variable name for settings module
ENVIRONMENT_VARIABLE = "GRAFANE_SETTINGS_MODULE"

# Default settings module
DEFAULT_SETTINGS_MODULE = "grafane.settings"

# Required keys for each database configuration
REQUIRED_DB_KEYS = {"host", "port", "database", "username", "password"}

# Required keys for InfluxDB v2 database configuration
REQUIRED_V2_KEYS = {"url", "token", "org", "bucket"}

# Subscribable settings (can be overridden by user settings)
SUBSCRIBABLE_SETTINGS = {"INFLUXDB_SETTINGS"}


class Settings:
    """Lazy settings container that loads settings on first access."""

    def __init__(self):
        self._settings_module: str | None = None
        self._settings: dict[str, Any] | None = None
        self._configured = False

    def _load_module(self, module_path: str) -> Any:
        """Import and return a settings module by its dotted path."""
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            raise MissingInfluxDBSettings(
                f"Could not import settings module '{module_path}': {e}",
                errors=[str(e)],
            )

    def _validate_database_config(self, name: str, config: dict) -> list[str]:
        """Validate a single database configuration. Returns list of errors."""
        errors = []

        if not isinstance(config, dict):
            errors.append(
                f"Database '{name}' config must be a dict, got {type(config).__name__}"
            )
            return errors

        # Determine version (default to v1)
        version = config.get("version", 1)

        if version == 2:
            # Validate v2 configuration
            missing_keys = REQUIRED_V2_KEYS - set(config.keys())
            if missing_keys:
                errors.append(
                    f"Database '{name}' (v2) missing required keys: {', '.join(sorted(missing_keys))}"
                )
        else:
            # Validate v1 configuration
            missing_keys = REQUIRED_DB_KEYS - set(config.keys())
            if missing_keys:
                errors.append(
                    f"Database '{name}' missing required keys: {', '.join(sorted(missing_keys))}"
                )

            # Validate types for v1
            if "port" in config and not isinstance(config["port"], int):
                errors.append(
                    f"Database '{name}' port must be an int, got {type(config['port']).__name__}"
                )

        if "metrics" in config and not isinstance(config["metrics"], list):
            errors.append(
                f"Database '{name}' metrics must be a list, got {type(config['metrics']).__name__}"
            )

        return errors

    def _validate_settings(self, settings_dict: dict[str, Any]) -> None:
        """Validate the loaded settings. Raises MissingInfluxDBSettings on error."""
        errors = []

        # Check INFLUXDB_SETTINGS exists
        if "INFLUXDB_SETTINGS" not in settings_dict:
            raise MissingInfluxDBSettings(
                "Settings module must define INFLUXDB_SETTINGS",
                errors=["INFLUXDB_SETTINGS not found"],
            )

        influxdb_settings = settings_dict["INFLUXDB_SETTINGS"]

        # Check it's a dict
        if not isinstance(influxdb_settings, dict):
            raise MissingInfluxDBSettings(
                f"INFLUXDB_SETTINGS must be a dict, got {type(influxdb_settings).__name__}",
                errors=["INFLUXDB_SETTINGS must be a dict"],
            )

        # Check it's not empty
        if not influxdb_settings:
            raise MissingInfluxDBSettings(
                "INFLUXDB_SETTINGS cannot be empty",
                errors=["INFLUXDB_SETTINGS is empty"],
            )

        # Validate each database configuration
        for db_name, db_config in influxdb_settings.items():
            db_errors = self._validate_database_config(db_name, db_config)
            errors.extend(db_errors)

        if errors:
            raise MissingInfluxDBSettings(
                f"Invalid INFLUXDB_SETTINGS: {'; '.join(errors)}",
                errors=errors,
            )

    def _load_settings(self, module_path: str) -> dict[str, Any]:
        """Load and merge settings from a module."""
        # Always load default settings first
        default_module = self._load_module(DEFAULT_SETTINGS_MODULE)

        # Extract non-subscribable settings from default (UUID, TESTING)
        settings_dict = {}

        # Get UUID from default settings (not subscribable)
        if hasattr(default_module, "UUID"):
            settings_dict["UUID"] = default_module.UUID

        # TESTING is controlled by env var only (not subscribable)
        settings_dict["TESTING"] = bool(os.environ.get("TESTING", 0))

        # If using a custom module, load subscribable settings from it
        if module_path != DEFAULT_SETTINGS_MODULE:
            user_module = self._load_module(module_path)

            # User module MUST define INFLUXDB_SETTINGS (no fallback for this)
            if not hasattr(user_module, "INFLUXDB_SETTINGS"):
                raise MissingInfluxDBSettings(
                    f"Settings module '{module_path}' must define INFLUXDB_SETTINGS",
                    errors=["INFLUXDB_SETTINGS not found"],
                )

            # Load subscribable settings from user module
            for setting_name in SUBSCRIBABLE_SETTINGS:
                if hasattr(user_module, setting_name):
                    settings_dict[setting_name] = getattr(user_module, setting_name)
        else:
            # Using default module, get all subscribable settings from it
            for setting_name in SUBSCRIBABLE_SETTINGS:
                if hasattr(default_module, setting_name):
                    settings_dict[setting_name] = getattr(default_module, setting_name)

        return settings_dict

    def configure(self, settings_module: str | None = None) -> None:
        """Configure Grafane with a settings module.

        Args:
            settings_module: Dotted path to settings module (e.g., 'myproject.settings').
                           If None, uses GRAFANE_SETTINGS_MODULE env var or default.

        Raises:
            MissingInfluxDBSettings: If settings are invalid or module cannot be imported.
        """
        if self._configured:
            logger.warning(
                "Grafane settings already configured. "
                "Reconfiguring with new settings module."
            )
            # Reset state for reconfiguration
            self._settings = None

        # Determine which module to use (priority order)
        if settings_module is not None:
            module_path = settings_module
        elif ENVIRONMENT_VARIABLE in os.environ:
            module_path = os.environ[ENVIRONMENT_VARIABLE]
        else:
            module_path = DEFAULT_SETTINGS_MODULE

        # Load and validate settings
        self._settings = self._load_settings(module_path)
        self._validate_settings(self._settings)

        self._settings_module = module_path
        self._configured = True

        logger.debug(f"Grafane configured with settings module: {module_path}")

    def _ensure_configured(self) -> None:
        """Ensure settings are configured, using defaults if not."""
        if not self._configured:
            self.configure()

    @property
    def configured(self) -> bool:
        """Return True if settings have been configured."""
        return self._configured

    @property
    def settings_module(self) -> str | None:
        """Return the configured settings module path."""
        return self._settings_module

    def __getattr__(self, name: str) -> Any:
        """Get a setting value by name."""
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        self._ensure_configured()

        if self._settings is None:
            raise MissingInfluxDBSettings(
                "Settings not loaded",
                errors=["Settings not loaded"],
            )

        if name not in self._settings:
            raise AttributeError(f"Setting '{name}' not found")

        return self._settings[name]

    def reset(self) -> None:
        """Reset settings to unconfigured state. Primarily for testing."""
        self._settings_module = None
        self._settings = None
        self._configured = False


# Global settings instance
settings = Settings()


def configure(settings_module: str | None = None) -> None:
    """Configure Grafane with a settings module.

    This is the main entry point for configuring Grafane settings.

    Args:
        settings_module: Dotted path to settings module (e.g., 'myproject.settings').
                       If None, uses GRAFANE_SETTINGS_MODULE env var or default.

    Example:
        >>> import grafane
        >>> grafane.configure('myproject.settings')

        Or use environment variable:
        >>> # export GRAFANE_SETTINGS_MODULE=myproject.settings
        >>> import grafane
        >>> grafane.configure()  # Will use env var
    """
    settings.configure(settings_module)
