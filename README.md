# Grafane

A very opinionated InfluxDB client inspired by Grafana's query builder.

## Setup

### Installation

```bash
poetry add grafane
```

### Configuration

Grafane supports multi-database setups with a Django-style configuration system.

**Recommended:** Create a settings module in your project:

```python
# myproject/settings.py
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'metrics',
        'username': 'admin',
        'password': 'secret',
        'metrics': [],
    },
}
```

Then configure Grafane:

```python
import grafane
grafane.configure('myproject.settings')
```

Alternatively, set the environment variable:

```bash
export GRAFANE_SETTINGS_MODULE=myproject.settings
```

### Environment Variables (Default Configuration)

If no settings module is configured, Grafane uses these environment variables for a single default database:

| Variable | Default | Description |
|----------|---------|-------------|
| `INFLUXDB_HOST` | `0.0.0.0` | InfluxDB host |
| `INFLUXDB_PORT` | `8086` | InfluxDB port |
| `INFLUXDB_DB` | `metrics` | Database name |
| `INFLUXDB_USER` | `admin` | Username |
| `INFLUXDB_USER_PASSWORD` | `admin123` | Password |
| `TESTING` | `0` | If set, appends `-testing` to metric names |

For multi-database setups, use a settings module instead (see Configuration above).

## Quick Start

```python
import grafane

# Configure with your settings module (optional if using env vars)
grafane.configure('myproject.settings')

# Create a client for a metric
c = grafane.Grafane(metric='temperature')

# Write
c.report({'value': 23.5}, {'room': 'living'})

# Read
results = c.select(fields='value').filter_by('room', '=', 'living').execute_query()
```

## Multi-Database Setup

Configure multiple InfluxDB databases in your settings module:

```python
# myproject/settings.py
INFLUXDB_SETTINGS = {
    'default': {
        'host': 'localhost',
        'port': 8086,
        'database': 'metrics',
        'username': 'admin',
        'password': 'secret',
        'metrics': [],  # Empty = fallback for unmatched metrics
    },
    'analytics': {
        'host': 'analytics.example.com',
        'port': 8086,
        'database': 'analytics',
        'username': 'analytics_user',
        'password': 'analytics_pass',
        'metrics': ['page_views', 'sessions', 'events'],
    },
    'monitoring': {
        'host': 'monitoring.example.com',
        'port': 8086,
        'database': 'monitoring',
        'username': 'monitoring_user',
        'password': 'monitoring_pass',
        'metrics': ['cpu', 'memory', 'disk'],
    },
}
```

### Database Configuration Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `host` | str | Yes | InfluxDB host |
| `port` | int | Yes | InfluxDB port |
| `database` | str | Yes | Database name |
| `username` | str | Yes | Username |
| `password` | str | Yes | Password |
| `metrics` | list | No | Metrics routed to this database (empty = fallback) |

### InfluxDB v2 Support

Grafane supports InfluxDB v2 with the same API. Install the v2 client:

```bash
pip install grafane[v2]
# or
poetry add grafane --extras v2
```

Configure v2 databases in your settings module:

```python
# myproject/settings.py
INFLUXDB_SETTINGS = {
    'default': {
        'version': 2,
        'url': 'http://localhost:8086',
        'token': 'my-api-token',
        'org': 'my-org',
        'bucket': 'my-bucket',
        'metrics': [],
    },
}
```

**v2 Configuration Keys:**

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `version` | int | Yes | Set to `2` for InfluxDB v2 |
| `url` | str | Yes | InfluxDB v2 URL |
| `token` | str | Yes | API token |
| `org` | str | Yes | Organization |
| `bucket` | str | Yes | Bucket name |
| `metrics` | list | No | Metrics routed to this bucket (empty = fallback) |

**Mixed v1/v2 Setup:**

You can configure both v1 and v2 databases in the same settings:

```python
INFLUXDB_SETTINGS = {
    'legacy': {
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
}
```

### Metric Routing

Grafane automatically routes metrics to the correct database based on the `metrics` list:

```python
from grafane import Grafane

# Routes to 'analytics' (has 'page_views' in metrics list)
c = Grafane('page_views')

# Routes to 'monitoring' (has 'cpu' in metrics list)
c = Grafane('cpu')

# Routes to 'default' (fallback - empty metrics list)
c = Grafane('unknown_metric')

# Explicit database selection (bypasses routing)
c = Grafane('any_metric', db='analytics')
```

**Routing rules:**
1. If `db=` parameter is provided, use that database
2. If metric is in exactly one database's `metrics` list, use that database
3. If metric is in multiple databases' `metrics` lists, raises error (use `db=` to resolve)
4. If metric is not found, use the fallback database (database with empty `metrics` list)
5. If no fallback exists, raises error

## Write

### report()

```python
c.report(fields, tags, timestamp=False)
```

### report_points()

```python
c.report_points([
    {'fields': {'value': 1.2}, 'tags': {'tag1': 'a'}},
    {'fields': {'value': 1.8}, 'tags': {'tag1': 'b'}},
])
```

If no timestamp is provided, defaults to `datetime.now(pytz.utc)`.

## Read

### Chainable Query API

All query methods return `self` and can be chained:

```python
results = (
    c.select(fields=['value', 'value2'], aggregation='mean')
    .filter_by('tag1', '=', 'value1')
    .time_block('1h')
    .fill_with('none')
    .execute_query()
)
```

### select()

```python
# Single field
c.select(fields='value')

# Multiple fields
c.select(fields=['value', 'value2'])

# With aggregation
c.select(fields='value', aggregation='sum')

# Multiple fields with different aggregations
c.select(fields=['value', 'value2'], aggregation=['sum', 'mean'])
```

### filter_by()

Filter by tag with an operator:

```python
c.filter_by('tag1', '=', 'value1')
```

Supported operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `=~` (regex)

### filter_value_in()

Match tags against multiple values:

```python
c.filter_value_in('tag1', ['value1', 'value2'])
```

### filter_time_range()

```python
from datetime import datetime

time_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
c.filter_time_range(time_range)
```

Accepts tuple or list of datetime objects. Order doesn't matter.

### time_block()

Group results by time intervals:

```python
c.select(fields='value', aggregation='mean').time_block('1h')
```

### fill_with()

Fill empty time blocks:

```python
c.fill_with('none')
```

Options: `none`, `null`, `0`, `previous`, `linear`

### group_by()

Group by tag values (requires aggregation):

```python
c.select(fields='value', aggregation='sum').group_by('tag1')
```

### Iteration, Length, and Boolean

```python
# Iterate directly
for row in c.select(fields='value'):
    print(row)

# Check result count
count = len(c.select(fields='value'))

# Boolean check
if c.select(fields='value').filter_by('tag1', '=', 'x'):
    print("Has results")
```

## Drop Measurement

```python
c = Grafane(metric='test')
c.drop_measurement()
```

## Development

### Docker Setup

Start services:

```bash
ahoy docker up
```

Services:
- **metrics** (InfluxDB 1.8): http://localhost:8086
- **grafana**: http://localhost:3000 (passwordless, admin access)

### Jupyter Notebooks

```bash
ahoy notebooks run
```

Notebooks are stored in `.notebooks/` directory.

### Environment Files

Copy `.env.copy` to `.env`:

```bash
cp .env.copy .env
```

Contents:

```bash
INFLUXDB_DATA_ENGINE=tsm1
INFLUXDB_DB=metrics
INFLUXDB_USER=admin
INFLUXDB_PASSWORD=admin123
```
