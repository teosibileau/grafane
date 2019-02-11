import unittest
import pytz
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.parser import parse
from freezegun import freeze_time
from . import Grafane


class BaseInfluxDBTestCase:
    @property
    def points(self):
        return [
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


class GrafaneTestCase(BaseInfluxDBTestCase, unittest.TestCase):
    def setUp(self):
        self.client = Grafane()
        self.tearDown()

    def test_select(self):
        points = self.points
        self.client.report_points(points)
        self.client.select()
        results = self.client.execute_query()
        self.assertEqual(len(results), len(points))
        for i in range(len(results)):
            self.assertEqual(
                results[i]['value'],
                points[i]['fields']['value']
            )
        self.tearDown()

    def test_select_multiple(self):
        points = self.points
        self.client.report_points(points)
        self.client.select(fields=['value', 'value2'])
        results = self.client.execute_query()
        self.assertEqual(len(results), len(points))
        for i in range(len(results)):
            self.assertEqual(
                results[i]['value'],
                points[i]['fields']['value']
            )
            self.assertEqual(
                results[i]['value2'],
                points[i]['fields']['value2']
            )
        self.tearDown()

    def test_select_multiple_with_sum_count(self):
        points = self.points
        self.client.report_points(points)
        self.client.select(['value', 'value2'], ['sum', 'count'])
        results = self.client.execute_query()
        self.assertEqual(len(results), 1)
        self.assertTrue('sum' in results[0])
        self.assertEqual(
            round(Decimal(results[0]['sum']), 2),
            round(Decimal(sum([p['fields']['value'] for p in points])), 2)
        )
        self.assertTrue('count' in results[0])
        self.assertEqual(
            results[0]['count'],
            len(points)
        )
        self.tearDown()

    def test_select_with_sum(self):
        points = self.points
        self.client.report_points(points)
        self.client.select('value', 'sum')
        results = self.client.execute_query()
        self.assertEqual(len(results), 1)
        self.assertTrue('sum' in results[0])
        self.assertEqual(
            round(Decimal(results[0]['sum']), 2),
            round(Decimal(sum([p['fields']['value'] for p in points])), 2)
        )
        self.tearDown()

    def test_select_with_count(self):
        points = self.points
        self.client.report_points(points)
        self.client.select('value', 'count')
        results = self.client.execute_query()
        self.assertEqual(len(results), 1)
        self.assertTrue('count' in results[0])
        self.assertEqual(
            results[0]['count'],
            len(points)
        )
        self.tearDown()

    def test_select_with_max(self):
        points = self.points
        self.client.report_points(points)
        self.client.select('value', 'max')
        results = self.client.execute_query()
        self.assertEqual(len(results), 1)
        self.assertTrue('max' in results[0])
        self.assertEqual(
            results[0]['max'],
            max([p['fields']['value'] for p in points])
        )
        self.tearDown()

    def test_select_with_min(self):
        points = self.points
        self.client.report_points(points)
        self.client.select('value', 'min')
        results = self.client.execute_query()
        self.assertEqual(len(results), 1)
        self.assertTrue('min' in results[0])
        self.assertEqual(
            results[0]['min'],
            min([p['fields']['value'] for p in points])
        )
        self.tearDown()

    def test_time_range_filter(self):
        points = self.points
        dts = (
            datetime(
                2018, 10, day + 1, 10
            ).replace(
                tzinfo=None
            )
            for day in range(len(points))
        )
        utc = []
        for i in range(len(points)):
            with freeze_time(dts):
                u = datetime.utcnow()
                u = u.replace(tzinfo=pytz.utc)
                utc.append(u)
                self.client.report(
                    points[i]['fields'],
                    points[i]['tags']
                )
        for i in range(len(utc)):
            self.client.filter_time_range([
                utc[i] - timedelta(hours=12)
            ])
            results = self.client.execute_query()
            self.assertEqual(len(results), (len(utc) - i))
        self.tearDown()

    def test_time_block_groupby(self):
        points = self.points
        dts = (
            datetime(
                2018,
                1,
                1,
                hour + 1
            ) for hour in range(len(points))
        )
        for i in range(len(points)):
            with freeze_time(dts):
                self.client.report(
                    points[i]['fields'],
                    points[i]['tags']
                )
        groups = [1, 2, 4]
        for g in groups:
            self.client.select('value', 'sum')
            self.client.time_block('%sh' % g)
            self.client.fill_with('none')
            results = self.client.execute_query()
            dts = [parse(r['time']) for r in results]
            deltas = [
                x - dts[i - 1]
                for i, x in enumerate(dts)
            ][1:]
            deltas = list(set(deltas))
            self.assertEqual(len(deltas), 1)
            self.assertEqual(deltas[0], timedelta(hours=g))
        self.tearDown()

    def test_group_by_tag(self):
        points = self.points
        self.client.report_points(points)
        tag_occurances = {}
        for p in points:
            for t in p['tags'].keys():
                if t not in tag_occurances:
                    tag_occurances[t] = {}
                if p['tags'][t] not in tag_occurances[t]:
                    tag_occurances[t][p['tags'][t]] = 0
                tag_occurances[t][p['tags'][t]] += 1
        for tag in tag_occurances.keys():
            self.client.select('value', 'count')
            self.client.group_by(tag)
            results = self.client.execute_query()
            self.assertEqual(
                len(results),
                len(tag_occurances[tag].keys())
            )
            for r in results:
                self.assertEqual(
                    tag_occurances[tag][r['tags'][tag]],
                    r['count']
                )
        self.tearDown()

    def tearDown(self):
        self.client.drop_measurement()
