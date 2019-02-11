# Grafane

A very opinionated influxdb client that uses the [official python client](https://github.com/influxdata/influxdb-python) and is very much inspired in grafana's query builder.

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

## Drop measurement

```
c = Grafane(metric='test')
c.drop_measurement() # Drops test from influxdb
```
## Write

With:

```python
points = [
    {
        'fields': {
            'value': 1.2,
            'value2': 1.3,
        },
        'tags': {
            'tag1': 'value1',
                    'tag2': 'value2'
        }
    },
    {
        'fields': {
            'value': 1.86,
            'value2': 2.3,
        },
        'tags': {
            'tag1': 'value2',
                    'tag2': 'value1'
        }
    },
    {
        'fields': {
            'value': 1.4,
            'value2': 1.1,
        },
        'tags': {
            'tag1': 'value3',
                    'tag2': 'value2'
        }
    },
    {
        'fields': {
            'value': 1.8,
            'value2': 1.95,
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
In [6]: c.select(fields='value')                                                                                                                                                                            

In [7]: c.execute_query()                                                                                                                                                                                   
Out[7]: 
[{'time': '2019-02-10T20:37:13.786477056Z', 'value': 1.2},
 {'time': '2019-02-10T20:37:13.786508032Z', 'value': 1.86},
 {'time': '2019-02-10T20:37:13.786518016Z', 'value': 1.4},
 {'time': '2019-02-10T20:37:13.786535936Z', 'value': 1.8}]
```

### Select multiple fields

![](docs/select_multiple.png)

```python
In [16]: c.select(fields=['value', 'value2'])                                                                                                                                                               

In [17]: c.execute_query()                                                                                                                                                                                  
Out[17]: 
[{'time': '2019-02-10T20:42:37.22864512Z', 'value': 1.2, 'value2': 1.3},
 {'time': '2019-02-10T20:42:37.228871936Z', 'value': 1.86, 'value2': 2.3},
 {'time': '2019-02-10T20:42:37.228883968Z', 'value': 1.4, 'value2': 1.1},
 {'time': '2019-02-10T20:42:37.22889216Z', 'value': 1.8, 'value2': 1.95}]
```

### Select w/ aggregation

![](docs/select_w_aggregation.png)

```python
In [18]: c.select(fields='value', aggregation='sum')                                                                                                                                                        

In [19]: c.execute_query()                                                                                                                                                                                  
Out[19]: [{'time': '1970-01-01T00:00:00Z', 'sum': 6.26}]

```

### Select multiple fields w/ aggregation

![](docs/select_multiple_w_aggregation.png)

```python
In [20]: c.select(fields=['value', 'value2'], aggregation=['sum', 'mean'])                                                                                                                                  

In [21]: c.execute_query()                                                                                                                                                                                  
Out[21]: [{'time': '1970-01-01T00:00:00Z', 'sum': 6.26, 'mean': 1.6625}]
```

### Group aggregated results in time blocks

![](docs/select_group_by_timeblock.png)

```python
In [22]: c.select(fields=['value', 'value2'], aggregation=['sum', 'mean'])                                                                                                                                  

In [23]: c.time_block('1m')                                                                                                                                                                                 

In [24]: c.execute_query()                                                                                                                                                                                  
Out[24]: 
[{'time': '2019-02-10T20:42:00Z', 'sum': 6.26, 'mean': 1.6625},
 {'time': '2019-02-10T20:43:00Z', 'sum': None, 'mean': None},
 {'time': '2019-02-10T20:44:00Z', 'sum': None, 'mean': None},
 {'time': '2019-02-10T20:45:00Z', 'sum': None, 'mean': None},
 {'time': '2019-02-10T20:46:00Z', 'sum': None, 'mean': None},
 {'time': '2019-02-10T20:47:00Z', 'sum': None, 'mean': None}]
```
 
When grouping time blocks, in order to avoid empty rows you need to fill results with **None**

![](docs/select_group_by_timeblock_filled_w_none.png)

```python
In [29]: c.select(fields=['value', 'value2'], aggregation=['sum', 'mean'])                                                                                                                                  

In [30]: c.time_block('1m')                                                                                                                                                                                 

In [31]: c.fill_with('none')                                                                                                                                                                                

In [32]: c.execute_query()                                                                                                                                                                                  
Out[32]: [{'time': '2019-02-10T20:42:00Z', 'sum': 6.26, 'mean': 1.6625}]
```

### Group aggregated results by tag values

![](docs/group_by.png)

```python
In [34]: c.select(fields=['value', 'value2'], aggregation=['sum', 'mean'])                                                                                                                                  

In [35]: c.group_by('tag1')                                                                                                                                                                                 

In [36]: c.execute_query()                                                                                                                                                                                  
Out[36]: 
[{'tags': {'tag1': 'value1'},
  'time': '1970-01-01T00:00:00Z',
  'sum': 3,
  'mean': 1.625},
 {'tags': {'tag1': 'value2'},
  'time': '1970-01-01T00:00:00Z',
  'sum': 1.86,
  'mean': 2.3},
 {'tags': {'tag1': 'value3'},
  'time': '1970-01-01T00:00:00Z',
  'sum': 1.4,
  'mean': 1.1}]  
```
