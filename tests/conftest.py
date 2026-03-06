"""Shared pytest fixtures for Grafane tests."""

import pytest

from grafane.config import settings
from grafane.router import router


@pytest.fixture(autouse=True)
def reset_grafane_state():
    """Reset Grafane settings and router state before each test.

    This fixture runs automatically before each test to ensure clean state.
    """
    # Reset settings to unconfigured state
    settings.reset()

    # Clear router's client cache
    router.clear_cache()

    yield

    # Cleanup after test
    settings.reset()
    router.clear_cache()


@pytest.fixture
def configured_settings():
    """Configure Grafane with default settings and return the settings object.

    Use this fixture when you need access to the configured settings.
    """
    settings.configure()
    return settings


@pytest.fixture
def multi_db_settings(tmp_path):
    """Create a multi-database settings configuration for testing.

    This creates a temporary settings module with multiple databases
    and metrics routing configuration.
    """
    import sys

    module_dir = tmp_path / "multi_db_settings_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")

    settings_content = """
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'default_db',
        'username': 'admin',
        'password': 'admin',
        'metrics': [],  # Fallback database
    },
    'analytics': {
        'host': 'localhost',
        'port': 8086,
        'database': 'analytics_db',
        'username': 'admin',
        'password': 'admin',
        'metrics': ['page_views', 'sessions', 'events'],
    },
    'monitoring': {
        'host': 'localhost',
        'port': 8086,
        'database': 'monitoring_db',
        'username': 'admin',
        'password': 'admin',
        'metrics': ['cpu', 'memory', 'disk'],
    },
}
"""
    (module_dir / "settings.py").write_text(settings_content)

    sys.path.insert(0, str(tmp_path))
    try:
        settings.configure("multi_db_settings_pkg.settings")
        yield settings
    finally:
        sys.path.remove(str(tmp_path))
        settings.reset()
        router.clear_cache()


@pytest.fixture
def conflicting_metrics_settings(tmp_path):
    """Create settings where a metric exists in multiple databases.

    This is used to test MultipleConfigError scenarios.
    """
    import sys

    module_dir = tmp_path / "conflicting_settings_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")

    settings_content = """
INFLUXDB_SETTINGS = {
    'db1': {
        'host': 'localhost',
        'port': 8086,
        'database': 'db1',
        'username': 'admin',
        'password': 'admin',
        'metrics': ['shared_metric', 'metric_a'],
    },
    'db2': {
        'host': 'localhost',
        'port': 8086,
        'database': 'db2',
        'username': 'admin',
        'password': 'admin',
        'metrics': ['shared_metric', 'metric_b'],
    },
}
"""
    (module_dir / "settings.py").write_text(settings_content)

    sys.path.insert(0, str(tmp_path))
    try:
        settings.configure("conflicting_settings_pkg.settings")
        yield settings
    finally:
        sys.path.remove(str(tmp_path))
        settings.reset()
        router.clear_cache()


@pytest.fixture
def no_fallback_settings(tmp_path):
    """Create settings without a fallback database (no empty metrics list).

    This is used to test MetricNotFoundError scenarios.
    """
    import sys

    module_dir = tmp_path / "no_fallback_settings_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")

    settings_content = """
INFLUXDB_SETTINGS = {
    'specific_db': {
        'host': 'localhost',
        'port': 8086,
        'database': 'specific_db',
        'username': 'admin',
        'password': 'admin',
        'metrics': ['known_metric'],
    },
}
"""
    (module_dir / "settings.py").write_text(settings_content)

    sys.path.insert(0, str(tmp_path))
    try:
        settings.configure("no_fallback_settings_pkg.settings")
        yield settings
    finally:
        sys.path.remove(str(tmp_path))
        settings.reset()
        router.clear_cache()
