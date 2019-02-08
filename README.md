# Grafane

A very opionated influxdb client inspired in grafana's query builder.

## Setup

```
pip install grafane
```

In order to query influxdb this library expects the following environment variables to be set:


+ `INFLUXDB_HOST`: Defaults to **0.0.0.0**
+ `INFLUXDB_PORT`: Defaults to **8086**
+ `INFLUXDB_DB`: Defaults to **metrics**
+ `INFLUXDB_USER`: Defaults to **admin**
+ `INFLUXDB_USER_PASSWORD`: Defaults to **admin123**

## Write

With:

```python
points = [
    {
        'fields': {
            'value': 1.2,
        },
        'tags': {
            'tag1': 'value1',
            'tag2': 'value2'
        }
    },
    {
        'fields': {
            'value': 1.86,
        },
        'tags': {
            'tag1': 'value2',
            'tag2': 'value1'
        }
    },
    {
        'fields': {
            'value': 1.4,
        },
        'tags': {
            'tag1': 'value3',
            'tag2': 'value2'
        }
    },
    {
        'fields': {
            'value': 1.8,
        },
        'tags': {
            'tag1': 'value1',
            'tag2': 'value2'
        }
    },
]
```

You can do either do multiple single queries:

```python
from grafane import Grafane
c = Grafane(metric='generic') # Metric defaults to generic
for p in points:
	c.report(p['fields'], p['tags'])
```

Or a single query with multiple points:

```python
c.report_points(points)
```

if you don't provide `time` for a point it defaults to:

```python
>>> datetime.utcnow().replace(tzinfo=pytz.utc)
datetime.datetime(2019, 2, 8, 19, 32, 38, 788003, tzinfo=<UTC>)
```

## Read

### Select

![](docs/select.png)

```python
c.select(fields='value')
```

### Select multiple fields

![](docs/select_multiple.png)

```python
c.select(fields=['value', 'value2']
```

### Select w/ aggregation

![](docs/select_w_aggregation.png)

```python
c.select(fields='value', aggregation='sum'))
```

### Select multiple fields w/ aggregation

![](docs/select_multiple_w_aggregation.png)

```python
c.select(fields='value', aggregation='sum'))
```

