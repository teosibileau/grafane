import os
import uuid

INFLUXDB_SETTINGS = {
    'uuid': str(uuid.UUID(int=uuid.getnode())).split('-')[-1],
    'db_host': os.environ.get('INFLUXDB_HOST', '0.0.0.0'),
    'db_port': os.environ.get('INFLUXDB_PORT', 8086),
    'db_name': os.environ.get('INFLUXDB_DB', 'metrics'),
    'db_user': os.environ.get('INFLUXDB_USER', 'admin'),
    'db_pass': os.environ.get('INFLUXDB_USER_PASSWORD', 'admin123')
}

TESTING = os.environ.get('TESTING', 'False')
TESTING = True if TESTING == 'True' else False
