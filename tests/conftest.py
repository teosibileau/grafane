"""Shared pytest fixtures for Grafane tests."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

from grafane.config import settings
from grafane.router import router

# Load .env file from project root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


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


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )
    config.addinivalue_line("markers", "v2: marks tests requiring InfluxDB v2")


@pytest.fixture
def v2_settings(tmp_path):
    """Create settings for InfluxDB v2 using metrics-v2 compose service.

    Uses environment variables from .env file:
    - INFLUXDB_V2_URL (default: http://localhost:8087)
    - INFLUXDB_V2_TOKEN
    - INFLUXDB_V2_ORG
    - INFLUXDB_V2_BUCKET

    Requires: docker-compose up metrics-v2
    """
    module_dir = tmp_path / "v2_settings_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")

    v2_url = os.environ.get("INFLUXDB_V2_URL", "http://localhost:8087")
    v2_token = os.environ.get("INFLUXDB_V2_TOKEN", "my-super-secret-token")
    v2_org = os.environ.get("INFLUXDB_V2_ORG", "my-org")
    v2_bucket = os.environ.get("INFLUXDB_V2_BUCKET", "metrics")

    settings_content = f"""
INFLUXDB_SETTINGS = {{
    'default': {{
        'version': 2,
        'url': '{v2_url}',
        'token': '{v2_token}',
        'org': '{v2_org}',
        'bucket': '{v2_bucket}',
        'metrics': [],
    }},
}}
"""
    (module_dir / "settings.py").write_text(settings_content)

    sys.path.insert(0, str(tmp_path))
    try:
        settings.configure("v2_settings_pkg.settings")
        yield settings
    finally:
        sys.path.remove(str(tmp_path))
        settings.reset()
        router.clear_cache()


@pytest.fixture
def mixed_v1_v2_settings(tmp_path):
    """Create settings with both v1 and v2 databases.

    - v1: metrics compose service (port 8086)
    - v2: metrics-v2 compose service (port 8087)

    Requires: docker-compose up metrics metrics-v2
    """
    module_dir = tmp_path / "mixed_settings_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")

    v1_host = os.environ.get("INFLUXDB_HOST", "localhost")
    v1_port = os.environ.get("INFLUXDB_PORT", "8086")
    v1_db = os.environ.get("INFLUXDB_DB", "metrics")
    v1_user = os.environ.get("INFLUXDB_USER", "admin")
    v1_pass = os.environ.get("INFLUXDB_PASSWORD", "admin123")

    v2_url = os.environ.get("INFLUXDB_V2_URL", "http://localhost:8087")
    v2_token = os.environ.get("INFLUXDB_V2_TOKEN", "my-super-secret-token")
    v2_org = os.environ.get("INFLUXDB_V2_ORG", "my-org")
    v2_bucket = os.environ.get("INFLUXDB_V2_BUCKET", "metrics")

    settings_content = f"""
INFLUXDB_SETTINGS = {{
    'legacy': {{
        'version': 1,
        'host': '{v1_host}',
        'port': {v1_port},
        'database': '{v1_db}',
        'username': '{v1_user}',
        'password': '{v1_pass}',
        'metrics': ['cpu', 'memory', 'disk'],
    }},
    'modern': {{
        'version': 2,
        'url': '{v2_url}',
        'token': '{v2_token}',
        'org': '{v2_org}',
        'bucket': '{v2_bucket}',
        'metrics': ['events', 'traces'],
    }},
    'default': {{
        'version': 1,
        'host': '{v1_host}',
        'port': {v1_port},
        'database': '{v1_db}',
        'username': '{v1_user}',
        'password': '{v1_pass}',
        'metrics': [],
    }},
}}
"""
    (module_dir / "settings.py").write_text(settings_content)

    sys.path.insert(0, str(tmp_path))
    try:
        settings.configure("mixed_settings_pkg.settings")
        yield settings
    finally:
        sys.path.remove(str(tmp_path))
        settings.reset()
        router.clear_cache()
