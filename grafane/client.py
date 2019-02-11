import time
import pytz
from datetime import datetime
from .settings import INFLUXDB_SETTINGS, TESTING
from influxdb import InfluxDBClient


class MissingInfluxDBSettings(Exception):
    def __init__(self, message, errors):
        super(MissingInfluxDBSettings, self).__init__(message)
        self.errors = errors


class WrongArgumentType(Exception):
    def __init__(self, message, errors):
        super(WrongArgumentType, self).__init__(message)
        self.errors = errors


class Grafane(InfluxDBClient):
    def __init__(self, metric='generic'):
        self.ignore_query = False
        if INFLUXDB_SETTINGS.get('uuid', False):
            self.uuid = INFLUXDB_SETTINGS.get('uuid', False)
            if self.uuid:
                super(Grafane, self).__init__(
                    host=INFLUXDB_SETTINGS['db_host'],
                    port=INFLUXDB_SETTINGS['db_port'],
                    username=INFLUXDB_SETTINGS['db_user'],
                    password=INFLUXDB_SETTINGS['db_pass'],
                    database=INFLUXDB_SETTINGS['db_name'],
                    ssl=False
                )
            else:
                raise MissingInfluxDBSettings(
                    'missing uuid in INFLUXDB_SETTINGS',
                    ['missing uuid']
                )
        else:
            raise MissingInfluxDBSettings('please set INFLUXDB_SETTINGS',
                                          ['missing settings dict'])
        self.metric = metric
        if TESTING:
            self.metric = '%s-testing' % self.metric
        self.reset_query()

    def reset_query(self):
        self.results = None
        self.fields = []
        self.aggregation = []
        self.group = []
        self.filter = []
        self.time_range = []
        self.fill = False
        self.rebuild_query()

    def rebuild_query(self):
        if not len(self.fields):
            self.fields = ['value']
        if len(self.aggregation):
            for i in range(len(self.fields)):
                if self.aggregation[i] not in self.fields[i]:
                    self.fields[i] = '%s("%s")' % (
                        self.aggregation[i],
                        self.fields[i]
                    )
        else:
            self.fields = ['%s' % f for f in self.fields]
        self.sql = 'SELECT %s FROM "%s"' % (
            ', '.join(self.fields),
            self.metric
        )
        if len(self.filter):
            self.sql = '%s WHERE %s' % (
                self.sql,
                ' AND '.join(self.filter)
            )
        if len(self.group):
            self.sql = '%s GROUP BY %s' % (
                self.sql,
                ','.join(self.group)
            )
        if self.fill:
            self.sql = '%s fill(%s)' % (self.sql, self.fill)

    def select(self, fields=['value'], aggregation=[]):
        self.fields, self.aggregation = [], []
        # Validate fields
        if type(fields) == list:
            self.fields = fields
        elif type(fields) == str:
            self.fields = [fields]
        else:
            raise WrongArgumentType(
                'Fields must be either a list or a string',
                [type(self.fields)]
            )
        # Validate Aggregation
        if len(aggregation):
            if type(aggregation) == list:
                if len(aggregation) == len(self.fields):
                    self.aggregation = aggregation
                elif len(aggregation) == 1:
                    self.aggregation = [
                        aggregation[0] for i in range(len(self.fields))
                    ]
                else:
                    raise WrongArgumentType(
                        'Aggregation as a list should be either' +
                        'the same len as fields or 1',
                        ['lenght: %s' % len(aggregation)]
                    )
            elif type(aggregation) == str:
                self.aggregation = [
                    aggregation for i in range(len(self.fields))
                ]
            else:
                raise WrongArgumentType(
                    'Aggregation should either be a list or a string',
                    [type(aggregation)]
                )
        # Rebuild query
        self.rebuild_query()

    def time_block(self, block):
        block = 'time(%s)' % block
        for g in self.group:
            if 'time(' in g:
                self.group.remove(g)
        self.group = [block] + self.group
        self.rebuild_query()

    def set_time_range(self, block):
        for f in self.filter:
            if 'time' in f:
                self.filter.remove(f)
        self.filter = [block] + self.filter
        self.rebuild_query()

    def filter_time_range(self, r):
        if type(r) not in [list, tuple]:
            raise WrongArgumentType(
                'Time range should be provided as a list or a tuple'
            )
        if len(r) == 2:
            if r[0] > r[1]:
                f, t = r[1], r[0]
            else:
                f, t = r[0], r[1]
        else:
            f = r[0]
            t = False
        conditions = []
        if t:
            t = time.mktime(t.timetuple())
            t = int(t) * 1000
            t = '(time <= %sms)' % int(t)
            conditions.append(t)
        f = time.mktime(f.timetuple())
        f = int(f) * 1000
        f = '(time >= %sms)' % int(f)
        conditions.append(f)
        block = ' AND '.join(conditions)
        self.set_time_range(block)

    def filter_value_in(self, tag, values):
        if values:
            filters = ['("%s" = \'%s\')' % (tag, v) for v in values]
            filters = '(%s)' % (' OR '.join(filters))
            self.filter.append(filters)
        self.rebuild_query()

    def filter_by_from_dict(self, filter_by):
        if type(filter_by) not in [list, dict]:
            raise WrongArgumentType(
                'Time range should be provided as a list or a tuple'
            )
        if type(filter_by) == dict:
            filter_by = [filter_by]
        validate = ['tag', 'operator', 'value']
        for f in filter_by:
            for v in validate:
                if v not in f:
                    raise WrongArgumentType('Missing filter_by[%s] key' % v)
            self.filter_by(**f)

    def filter_by(self, tag, operator, value):
        f = '("%s" %s \'%s\')' % (tag, operator, value)
        if f not in self.filter:
            self.filter.append(f)
            self.rebuild_query()

    def fill_with(self, fill=False):
        f = ['none', 'null', '0', 'previous', 'linear']
        if fill and fill in f:
            self.fill = fill
        else:
            self.fill = False
        self.rebuild_query()

    def group_by(self, group):
        # Enforce aggregation
        if len(self.aggregation) == 0:
            raise WrongArgumentType(
                'In order to group results, aggregate first'
            )
        # If group is a string, wrap in a list
        if isinstance(group, str):
            group = [group]
        for g in group:
            self.group.append('"%s"' % g)
        # Remove duplicates
        self.group = list(set(self.group))
        self.rebuild_query()

    def report(self, fields, tags, timestamp=False):
        tags['origin'] = self.uuid
        d = {
            'fields': fields,
            'tags': tags,
            'measurement': self.metric,
        }
        if timestamp:
            d['time'] = timestamp
        return self.report_points([d])

    def report_points(self, points=[]):
        for i in range(len(points)):
            p = points[i]
            if 'time' not in p:
                u = datetime.utcnow()
                u = u.replace(tzinfo=pytz.utc)
                p['time'] = u
            p['time'] = str(p['time'])
            if 'origin' not in p['tags']:
                p['tags']['origin'] = self.uuid
            if 'measurement' not in p:
                p['measurement'] = self.metric
            points[i] = p
        if len(points):
            r = self.write_points(points)
            return r
        return False

    def query(self, query, params=None, epoch=None,
              expected_response_code=200, database=None,
              raise_errors=True, chunked=False, chunk_size=0,
              method="GET"):
        results = super(
            Grafane, self
        ).query(query, params, epoch, expected_response_code,
                database, raise_errors, chunked, chunk_size, method)
        self.reset_query()
        return results

    def execute_query(self, uuid=None):
        if uuid:
            self.filter_by('origin', '=', uuid)
        tagged_response = len(list(set(
            g for g in self.group if 'time(' not in g
        ))) > 0
        self.results = self.query(self.sql)
        if not tagged_response:
            return list(self.results.get_points())
        else:
            r = []
            for row in self.results.raw['series']:
                for v in row['values']:
                    i = {
                        'tags': row['tags']
                    }
                    for c in range(len(row['columns'])):
                        i[row['columns'][c]] = v[c]
                r.append(i)
            return r

    def drop_measurement(self, metric=False):
        if not metric:
            metric = self.metric
        super(Grafane, self).drop_measurement(metric)
