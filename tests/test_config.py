"""Tests for grafane.config module."""

import os
import sys
from unittest.mock import patch

import pytest

from grafane.config import (
    DEFAULT_SETTINGS_MODULE,
    ENVIRONMENT_VARIABLE,
    Settings,
    configure,
    settings,
)
from grafane.exceptions import MissingInfluxDBSettings


@pytest.fixture
def fresh_settings():
    """Provide a fresh Settings instance for each test."""
    s = Settings()
    yield s
    s.reset()


@pytest.fixture
def reset_global_settings():
    """Reset the global settings before and after each test."""
    settings.reset()
    yield settings
    settings.reset()


class TestSettingsClass:
    """Tests for the Settings class."""

    def test_initial_state(self, fresh_settings):
        """Settings should start unconfigured."""
        assert fresh_settings.configured is False
        assert fresh_settings.settings_module is None

    def test_configure_with_default(self, fresh_settings):
        """configure() without args uses default settings module."""
        fresh_settings.configure()
        assert fresh_settings.configured is True
        assert fresh_settings.settings_module == DEFAULT_SETTINGS_MODULE

    def test_configure_with_explicit_module(self, fresh_settings):
        """configure() with explicit module path uses that module."""
        # We'll use the default module as our "custom" module for testing
        fresh_settings.configure("grafane.settings")
        assert fresh_settings.configured is True
        assert fresh_settings.settings_module == "grafane.settings"

    def test_configure_with_env_var(self, fresh_settings):
        """configure() uses GRAFANE_SETTINGS_MODULE env var if set."""
        with patch.dict(os.environ, {ENVIRONMENT_VARIABLE: "grafane.settings"}):
            fresh_settings.configure()
        assert fresh_settings.configured is True
        assert fresh_settings.settings_module == "grafane.settings"

    def test_explicit_module_takes_priority_over_env_var(self, fresh_settings):
        """Explicit module path takes priority over env var."""
        with patch.dict(os.environ, {ENVIRONMENT_VARIABLE: "some.other.module"}):
            fresh_settings.configure("grafane.settings")
        assert fresh_settings.settings_module == "grafane.settings"

    def test_configure_warns_on_reconfigure(self, fresh_settings, caplog):
        """Reconfiguring logs a warning."""
        import logging

        caplog.set_level(logging.WARNING)

        fresh_settings.configure()
        fresh_settings.configure()

        assert "already configured" in caplog.text

    def test_configure_invalid_module_raises(self, fresh_settings):
        """configure() with non-existent module raises MissingInfluxDBSettings."""
        with pytest.raises(MissingInfluxDBSettings) as exc_info:
            fresh_settings.configure("nonexistent.module")
        assert "Could not import" in str(exc_info.value)

    def test_auto_configure_on_attribute_access(self, fresh_settings):
        """Accessing a setting auto-configures if not configured."""
        assert fresh_settings.configured is False
        _ = fresh_settings.INFLUXDB_SETTINGS
        assert fresh_settings.configured is True

    def test_access_influxdb_settings(self, fresh_settings):
        """Can access INFLUXDB_SETTINGS after configure."""
        fresh_settings.configure()
        influxdb_settings = fresh_settings.INFLUXDB_SETTINGS
        assert isinstance(influxdb_settings, dict)
        assert "default" in influxdb_settings

    def test_access_uuid(self, fresh_settings):
        """Can access UUID after configure."""
        fresh_settings.configure()
        uuid = fresh_settings.UUID
        assert isinstance(uuid, str)
        assert len(uuid) == 12  # Last segment of UUID

    def test_access_testing(self, fresh_settings):
        """TESTING setting is controlled by env var."""
        with patch.dict(os.environ, {"TESTING": "1"}):
            fresh_settings.configure()
            assert fresh_settings.TESTING is True

        fresh_settings.reset()

        with patch.dict(os.environ, {"TESTING": ""}, clear=False):
            # Remove TESTING from env
            env = os.environ.copy()
            env.pop("TESTING", None)
            with patch.dict(os.environ, env, clear=True):
                fresh_settings.configure()
                assert fresh_settings.TESTING is False

    def test_access_nonexistent_setting_raises(self, fresh_settings):
        """Accessing non-existent setting raises AttributeError."""
        fresh_settings.configure()
        with pytest.raises(AttributeError) as exc_info:
            _ = fresh_settings.NONEXISTENT_SETTING
        assert "not found" in str(exc_info.value)

    def test_reset_clears_state(self, fresh_settings):
        """reset() clears all configuration state."""
        fresh_settings.configure()
        assert fresh_settings.configured is True

        fresh_settings.reset()
        assert fresh_settings.configured is False
        assert fresh_settings.settings_module is None


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_missing_influxdb_settings_raises(self, fresh_settings, tmp_path):
        """Settings module without INFLUXDB_SETTINGS raises error."""
        # Create a temporary module without INFLUXDB_SETTINGS
        module_dir = tmp_path / "test_settings_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        (module_dir / "empty_settings.py").write_text("# No INFLUXDB_SETTINGS here\n")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg.empty_settings")
            assert "must define INFLUXDB_SETTINGS" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_influxdb_settings_not_dict_raises(self, fresh_settings, tmp_path):
        """INFLUXDB_SETTINGS must be a dict."""
        module_dir = tmp_path / "test_settings_pkg2"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        (module_dir / "bad_settings.py").write_text(
            "INFLUXDB_SETTINGS = 'not a dict'\n"
        )

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg2.bad_settings")
            assert "must be a dict" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_empty_influxdb_settings_raises(self, fresh_settings, tmp_path):
        """Empty INFLUXDB_SETTINGS raises error."""
        module_dir = tmp_path / "test_settings_pkg3"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        (module_dir / "empty_db_settings.py").write_text("INFLUXDB_SETTINGS = {}\n")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg3.empty_db_settings")
            assert "cannot be empty" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_missing_required_keys_raises(self, fresh_settings, tmp_path):
        """Database config missing required keys raises error."""
        module_dir = tmp_path / "test_settings_pkg4"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        # missing: port, database, username, password
    }
}
"""
        (module_dir / "incomplete_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg4.incomplete_settings")
            assert "missing required keys" in str(exc_info.value)
            assert exc_info.value.errors is not None
            assert len(exc_info.value.errors) > 0
        finally:
            sys.path.remove(str(tmp_path))

    def test_invalid_port_type_raises(self, fresh_settings, tmp_path):
        """Port must be an integer."""
        module_dir = tmp_path / "test_settings_pkg5"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': '8086',  # Should be int
        'database': 'test',
        'username': 'admin',
        'password': 'secret',
    }
}
"""
        (module_dir / "bad_port_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg5.bad_port_settings")
            assert "port must be an int" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_invalid_metrics_type_raises(self, fresh_settings, tmp_path):
        """Metrics must be a list."""
        module_dir = tmp_path / "test_settings_pkg6"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'test',
        'username': 'admin',
        'password': 'secret',
        'metrics': 'cpu,memory',  # Should be list
    }
}
"""
        (module_dir / "bad_metrics_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("test_settings_pkg6.bad_metrics_settings")
            assert "metrics must be a list" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_valid_settings_passes(self, fresh_settings, tmp_path):
        """Valid settings pass validation."""
        module_dir = tmp_path / "test_settings_pkg7"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'test',
        'username': 'admin',
        'password': 'secret',
        'metrics': ['cpu', 'memory'],
    },
    'analytics': {
        'host': 'analytics.local',
        'port': 8086,
        'database': 'analytics',
        'username': 'analytics',
        'password': 'analytics_pass',
        'metrics': ['page_views'],
    },
}
"""
        (module_dir / "valid_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("test_settings_pkg7.valid_settings")
            assert fresh_settings.configured is True
            assert "default" in fresh_settings.INFLUXDB_SETTINGS
            assert "analytics" in fresh_settings.INFLUXDB_SETTINGS
        finally:
            sys.path.remove(str(tmp_path))


class TestConfigureFunction:
    """Tests for the module-level configure() function."""

    def test_configure_sets_global_settings(self, reset_global_settings):
        """configure() function sets the global settings instance."""
        configure()
        assert settings.configured is True

    def test_configure_with_module(self, reset_global_settings):
        """configure() accepts a module path."""
        configure("grafane.settings")
        assert settings.settings_module == "grafane.settings"


class TestUserSettingsOverride:
    """Tests for user settings overriding defaults."""

    def test_user_settings_override_influxdb_settings(self, fresh_settings, tmp_path):
        """User INFLUXDB_SETTINGS overrides default."""
        module_dir = tmp_path / "user_settings_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'custom_db': {
        'host': 'custom.host.com',
        'port': 9999,
        'database': 'custom_db',
        'username': 'custom_user',
        'password': 'custom_pass',
        'metrics': ['custom_metric'],
    },
}
"""
        (module_dir / "user_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("user_settings_pkg.user_settings")

            # User's INFLUXDB_SETTINGS should be used
            assert "custom_db" in fresh_settings.INFLUXDB_SETTINGS
            assert "default" not in fresh_settings.INFLUXDB_SETTINGS

            # UUID should still come from default settings
            assert fresh_settings.UUID is not None
        finally:
            sys.path.remove(str(tmp_path))

    def test_uuid_not_overridable(self, fresh_settings, tmp_path):
        """User cannot override UUID setting."""
        module_dir = tmp_path / "uuid_override_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
UUID = 'user-defined-uuid'
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'test',
        'username': 'admin',
        'password': 'secret',
    },
}
"""
        (module_dir / "uuid_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("uuid_override_pkg.uuid_settings")

            # UUID should NOT be the user-defined value
            assert fresh_settings.UUID != "user-defined-uuid"
        finally:
            sys.path.remove(str(tmp_path))

    def test_testing_controlled_by_env_only(self, fresh_settings, tmp_path):
        """TESTING is controlled by env var, not settings module."""
        module_dir = tmp_path / "testing_override_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
TESTING = True  # User tries to set TESTING
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'test',
        'username': 'admin',
        'password': 'secret',
    },
}
"""
        (module_dir / "testing_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            # Ensure TESTING env var is not set
            env = os.environ.copy()
            env.pop("TESTING", None)
            with patch.dict(os.environ, env, clear=True):
                fresh_settings.configure("testing_override_pkg.testing_settings")
                # TESTING should be False (from env), not True (from settings)
                assert fresh_settings.TESTING is False
        finally:
            sys.path.remove(str(tmp_path))


class TestV2SettingsValidation:
    """Tests for InfluxDB v2 settings validation."""

    def test_valid_v2_settings_passes(self, fresh_settings, tmp_path):
        """Valid v2 settings pass validation."""
        module_dir = tmp_path / "v2_settings_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'version': 2,
        'url': 'http://localhost:8086',
        'token': 'my-token',
        'org': 'my-org',
        'bucket': 'my-bucket',
        'metrics': [],
    },
}
"""
        (module_dir / "v2_settings.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("v2_settings_pkg.v2_settings")
            assert fresh_settings.configured is True
            assert "default" in fresh_settings.INFLUXDB_SETTINGS
        finally:
            sys.path.remove(str(tmp_path))

    def test_v2_missing_required_keys_raises(self, fresh_settings, tmp_path):
        """V2 config missing url/token/org/bucket raises error."""
        module_dir = tmp_path / "v2_incomplete_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'version': 2,
        'url': 'http://localhost:8086',
        # missing: token, org, bucket
    },
}
"""
        (module_dir / "v2_incomplete.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("v2_incomplete_pkg.v2_incomplete")
            assert "missing required keys" in str(exc_info.value)
            assert "token" in str(exc_info.value)
            assert "org" in str(exc_info.value)
            assert "bucket" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_v2_missing_token_raises(self, fresh_settings, tmp_path):
        """V2 config missing token raises error."""
        module_dir = tmp_path / "v2_no_token_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'version': 2,
        'url': 'http://localhost:8086',
        'org': 'my-org',
        'bucket': 'my-bucket',
    },
}
"""
        (module_dir / "v2_no_token.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(MissingInfluxDBSettings) as exc_info:
                fresh_settings.configure("v2_no_token_pkg.v2_no_token")
            assert "missing required keys" in str(exc_info.value)
            assert "token" in str(exc_info.value)
        finally:
            sys.path.remove(str(tmp_path))

    def test_mixed_v1_v2_settings_passes(self, fresh_settings, tmp_path):
        """Mixed v1 and v2 databases pass validation."""
        module_dir = tmp_path / "mixed_versions_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'legacy': {
        'version': 1,
        'host': 'localhost',
        'port': 8086,
        'database': 'metrics_v1',
        'username': 'admin',
        'password': 'secret',
        'metrics': ['cpu', 'memory'],
    },
    'modern': {
        'version': 2,
        'url': 'http://localhost:8086',
        'token': 'my-token',
        'org': 'my-org',
        'bucket': 'metrics_v2',
        'metrics': ['events', 'traces'],
    },
    'fallback': {
        'version': 1,
        'host': 'localhost',
        'port': 8086,
        'database': 'default',
        'username': 'admin',
        'password': 'secret',
        'metrics': [],  # Empty = fallback
    },
}
"""
        (module_dir / "mixed_versions.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("mixed_versions_pkg.mixed_versions")
            assert fresh_settings.configured is True
            assert "legacy" in fresh_settings.INFLUXDB_SETTINGS
            assert "modern" in fresh_settings.INFLUXDB_SETTINGS
            assert "fallback" in fresh_settings.INFLUXDB_SETTINGS
        finally:
            sys.path.remove(str(tmp_path))

    def test_v2_with_metrics_list(self, fresh_settings, tmp_path):
        """V2 settings with metrics list pass validation."""
        module_dir = tmp_path / "v2_with_metrics_pkg"
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text("")
        settings_content = """
INFLUXDB_SETTINGS = {
    'v2_db': {
        'version': 2,
        'url': 'http://localhost:8086',
        'token': 'my-token',
        'org': 'my-org',
        'bucket': 'my-bucket',
        'metrics': ['page_views', 'sessions', 'events'],
    },
}
"""
        (module_dir / "v2_with_metrics.py").write_text(settings_content)

        sys.path.insert(0, str(tmp_path))
        try:
            fresh_settings.configure("v2_with_metrics_pkg.v2_with_metrics")
            assert fresh_settings.configured is True
            assert fresh_settings.INFLUXDB_SETTINGS["v2_db"]["metrics"] == [
                "page_views",
                "sessions",
                "events",
            ]
        finally:
            sys.path.remove(str(tmp_path))
