# Grafane

A very opinionated InfluxDB client that uses the [official python client](https://github.com/influxdata/influxdb-python) and is inspired by Grafana's query builder.

## Setup

### Installation

```bash
poetry add grafane
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INFLUXDB_HOST` | `0.0.0.0` | InfluxDB host |
| `INFLUXDB_PORT` | `8086` | InfluxDB port |
| `INFLUXDB_DB` | `metrics` | Database name |
| `INFLUXDB_USER` | `admin` | Username |
| `INFLUXDB_USER_PASSWORD` | `admin123` | Password |
| `TESTING` | `0` | If set, appends `-testing` to metric names |

## Quick Start

```python
from grafane import Grafane

# Write
c = Grafane(metric='temperature')
c.report({'value': 23.5}, {'room': 'living'})

# Read
results = c.select(fields='value').filter_by('room', '=', 'living').execute_query()
```

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
