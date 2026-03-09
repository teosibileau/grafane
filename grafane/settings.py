"""Default Grafane settings.

This module provides default configuration values for Grafane.
Users can override INFLUXDB_SETTINGS by creating their own settings module
and calling `grafane.configure('myproject.settings')`.

Settings subscribability:
- UUID: Not subscribable (generated internally)
- INFLUXDB_SETTINGS: Subscribable (can be overridden by user settings)
- TESTING: Not subscribable (controlled by TESTING env var only)
"""

import os
import uuid as uuid_module

# Unique identifier for this machine/instance (not subscribable)
UUID = str(uuid_module.UUID(int=uuid_module.getnode())).split("-")[-1]

# InfluxDB database configurations (subscribable)
# Users can override this in their settings module
INFLUXDB_SETTINGS = {
    "default": {
        "version": 2,
        "url": os.environ.get("INFLUXDB_V2_URL", "http://localhost:8086"),
        "token": os.environ.get("INFLUXDB_V2_TOKEN", "my-super-secret-token"),
        "org": os.environ.get("INFLUXDB_V2_ORG", "my-org"),
        "bucket": os.environ.get("INFLUXDB_V2_BUCKET", "metrics"),
        "metrics": [],  # Empty list means this is the fallback database
    },
}

# Testing mode flag (not subscribable - controlled by env var only)
# This is kept here for backward compatibility with client.py
# Will be removed when client.py is updated to use the config system
TESTING = bool(os.environ.get("TESTING", 0))
