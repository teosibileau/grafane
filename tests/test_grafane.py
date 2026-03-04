from unittest.mock import MagicMock
import pytest
import pytz
import warnings
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.parser import parse
from freezegun import freeze_time
from grafane import Grafane


@pytest.fixture
def points():
    return [
        {
            "fields": {
                "value": 1.2,
                "value2": 1.3,
            },
            "tags": {"tag1": "value1", "tag2": "value2"},
        },
        {
            "fields": {
                "value": 1.86,
                "value2": 2.3,
            },
            "tags": {"tag1": "value2", "tag2": "value1"},
        },
        {
            "fields": {
                "value": 1.4,
                "value2": 1.1,
            },
            "tags": {"tag1": "value3", "tag2": "value2"},
        },
        {
            "fields": {
                "value": 1.8,
                "value2": 1.95,
            },
            "tags": {"tag1": "value1", "tag2": "value2"},
        },
    ]


@pytest.fixture(autouse=True)
def client():
    client = Grafane()
    yield client
    client.drop_measurement()


def test_select(client, points):
    client.report_points(points)
    client.select()
    results = client.execute_query()
    assert len(results) == len(points)
    for i in range(len(results)):
        assert results[i]["value"] == points[i]["fields"]["value"]


def test_select_multiple(client, points):
    client.report_points(points)
    client.select(fields=["value", "value2"])
    results = client.execute_query()
    assert len(results) == len(points)
    for i in range(len(results)):
        assert results[i]["value"] == points[i]["fields"]["value"]
        assert results[i]["value2"] == points[i]["fields"]["value2"]


def test_select_multiple_with_sum_count(client, points):
    client.report_points(points)
    client.select(["value", "value2"], ["sum", "count"])
    results = client.execute_query()
    assert len(results) == 1
    assert "sum" in results[0]
    assert round(Decimal(results[0]["sum"]), 2) == round(
        Decimal(sum([p["fields"]["value"] for p in points])), 2
    )
    assert "count" in results[0]
    assert results[0]["count"] == len(points)


def test_select_with_sum(client, points):
    client.report_points(points)
    client.select("value", "sum")
    results = client.execute_query()
    assert len(results) == 1
    assert "sum" in results[0]
    assert round(Decimal(results[0]["sum"]), 2) == round(
        Decimal(sum([p["fields"]["value"] for p in points])), 2
    )


def test_select_with_count(client, points):
    client.report_points(points)
    client.select("value", "count")
    results = client.execute_query()
    assert len(results) == 1
    assert "count" in results[0]
    assert results[0]["count"] == len(points)


def test_select_with_max(client, points):
    client.report_points(points)
    client.select("value", "max")
    results = client.execute_query()
    assert len(results) == 1
    assert "max" in results[0]
    assert results[0]["max"] == max([p["fields"]["value"] for p in points])


def test_select_with_min(client, points):
    client.report_points(points)
    client.select("value", "min")
    results = client.execute_query()
    assert len(results) == 1
    assert "min" in results[0]
    assert results[0]["min"] == min([p["fields"]["value"] for p in points])


def test_time_range_filter(client, points):
    dts = (
        datetime(2018, 10, day + 1, 10).replace(tzinfo=None)
        for day in range(len(points))
    )
    utc = []
    for i in range(len(points)):
        with freeze_time(dts):
            u = datetime.utcnow()
            u = u.replace(tzinfo=pytz.utc)
            utc.append(u)
            client.report(points[i]["fields"], points[i]["tags"])
    for i in range(len(utc)):
        client.filter_time_range([utc[i] - timedelta(hours=12)])
        results = client.execute_query()
        assert len(results) == (len(utc) - i)


def test_time_block_groupby(client, points):
    dts = (datetime(2018, 1, 1, hour + 1) for hour in range(len(points)))
    for i in range(len(points)):
        with freeze_time(dts):
            client.report(points[i]["fields"], points[i]["tags"])
    groups = [1, 2, 4]
    for g in groups:
        client.select("value", "sum")
        client.time_block("%sh" % g)
        client.fill_with("none")
        results = client.execute_query()
        dts = [parse(r["time"]) for r in results]
        deltas = [x - dts[i - 1] for i, x in enumerate(dts)][1:]
        deltas = list(set(deltas))
        assert len(deltas) == 1
        assert deltas[0] == timedelta(hours=g)


def test_group_by_tag(client, points):
    client.report_points(points)
    tag_occurances = {}
    for p in points:
        for t in p["tags"].keys():
            if t not in tag_occurances:
                tag_occurances[t] = {}
            if p["tags"][t] not in tag_occurances[t]:
                tag_occurances[t][p["tags"][t]] = 0
            tag_occurances[t][p["tags"][t]] += 1
    for tag in tag_occurances.keys():
        client.select("value", "count")
        client.group_by(tag)
        results = client.execute_query()
        assert len(results) == len(tag_occurances[tag].keys())
        for r in results:
            assert tag_occurances[tag][r["tags"][tag]] == r["count"]


def test_filter_by(client, points):
    client.report_points(points)
    client.select("value", "count")
    client.filter_by(tag="tag1", operator="=", value="value1")
    results = client.execute_query()
    assert len(results) == 1
    assert results[0]["count"] == 2


def test_filter_by_from_dict_single(client, points):
    client.report_points(points)
    client.select("value", "count")
    client.filter_by_from_dict({"tag": "tag1", "operator": "=", "value": "value1"})
    results = client.execute_query()
    assert len(results) == 1
    assert results[0]["count"] == 2


def test_filter_by_from_dict_multiple(client, points):
    client.report_points(points)
    client.select("value", "count")
    client.filter_by_from_dict(
        [
            {"tag": "tag1", "operator": "=", "value": "value1"},
            {"tag": "tag2", "operator": "=", "value": "value2"},
        ]
    )
    results = client.execute_query()
    assert len(results) == 1
    assert results[0]["count"] == 2


def test_filter_by_from_dict_invalid_type(client):
    with pytest.raises(TypeError):
        client.filter_by_from_dict("invalid")


def test_filter_by_from_dict_invalid_tuple(client):
    with pytest.raises(TypeError):
        client.filter_by_from_dict(("tag", "=", "value"))


def test_filter_by_from_dict_missing_key(client, points):
    with pytest.raises(TypeError):
        client.filter_by_from_dict([{"tag": "tag1", "operator": "="}])


def test_execute_query_caches_results(client, points):
    client.report_points(points)
    client.select()
    result1 = client.execute_query()
    result2 = client.execute_query()
    assert result1 == result2
    assert client._results == result1


def test_execute_query_sets_executed_flag(client, points):
    client.report_points(points)
    client.select()
    assert client._executed is False
    client.execute_query()
    assert client._executed is True


def test_reset_query_clears_executed_flag(client, points):
    client.report_points(points)
    client.select()
    client.execute_query()
    assert client._executed is True
    client.reset_query()
    assert client._executed is False


def test_reset_query_clears_results(client, points):
    client.report_points(points)
    client.select()
    client.execute_query()
    assert client._results is not None
    client.reset_query()
    assert client._results is None


def test_iter_triggers_query_execution(client, points):
    client.report_points(points)
    client.select()
    results = []
    for row in client:
        results.append(row)
    assert len(results) == len(points)


def test_len_triggers_query_execution(client, points):
    client.report_points(points)
    client.select()
    assert len(client) == len(points)


def test_bool_triggers_query_execution(client, points):
    client.report_points(points)
    client.select()
    assert bool(client) is True


def test_bool_false_for_empty_results(client):
    client.select()
    assert bool(client) is False


def test_iter_reuses_cached_results(client, points):
    client.report_points(points)
    client.select()
    results1 = list(client)
    results2 = list(client)
    assert results1 == results2


def test_cache_invalidation_decorator_calls_function():
    """Decorator should call the wrapped function."""
    from grafane.client import cache_invalidation

    mock_func = MagicMock(return_value="result")
    decorated = cache_invalidation(mock_func)

    mock_self = MagicMock()
    result = decorated(mock_self)

    mock_func.assert_called_once_with(mock_self)
    assert result == "result"


def test_cache_invalidation_resets_when_executed():
    """Decorator should call reset_query when _executed is True."""
    from grafane.client import cache_invalidation

    mock_func = MagicMock(return_value="result")
    decorated = cache_invalidation(mock_func)

    mock_self = MagicMock()
    mock_self._executed = True

    result = decorated(mock_self)

    mock_self.reset_query.assert_called_once()
    assert result == "result"


def test_cache_invalidation_does_not_reset_when_not_executed():
    """Decorator should NOT call reset_query when _executed is False."""
    from grafane.client import cache_invalidation

    mock_func = MagicMock(return_value="result")
    decorated = cache_invalidation(mock_func)

    mock_self = MagicMock()
    mock_self._executed = False

    result = decorated(mock_self)

    mock_self.reset_query.assert_not_called()
    assert result == "result"


def test_cache_invalidation_passes_args():
    """Decorator should pass arguments to wrapped function."""
    from grafane.client import cache_invalidation

    mock_func = MagicMock(return_value="result")
    decorated = cache_invalidation(mock_func)

    mock_self = MagicMock()

    result = decorated(mock_self, "arg1", "arg2", key="value")

    mock_func.assert_called_once_with(mock_self, "arg1", "arg2", key="value")
    assert result == "result"


def test_chaining_select_and_filter(client, points):
    client.report_points(points)
    client.select(fields=["value"], aggregation=["count"]).filter_by(
        tag="tag1", operator="=", value="value1"
    )
    results = list(client)
    assert len(results) == 1
    assert results[0]["count"] == 2


def test_chaining_full(client, points):
    client.report_points(points)
    client.select(fields=["value"], aggregation=["sum"]).filter_by(
        tag="tag1", operator="=", value="value1"
    ).group_by("tag2")
    results = list(client)
    assert len(results) > 0


def test_filter_by_from_dict_deprecation_warning(client):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client.filter_by_from_dict(
            [{"tag": "tag1", "operator": "=", "value": "value1"}]
        )
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message)
