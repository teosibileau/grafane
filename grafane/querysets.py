import copy
import time
import warnings


class WrongArgumentType(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class InfluxQLQuerySet:
    """Builds InfluxQL query strings and parses results."""

    def __init__(self, metric: str):
        self.metric = metric
        self.reset()

    # === State Reset ===
    def reset(self):
        self.fields = []
        self.aggregation = []
        self.group = []
        self.filter = []
        self.time_range = []
        self.fill = False
        self.sql = ""
        self.rebuild()

    # === Query Building ===
    def rebuild(self):
        if not len(self.fields):
            self.fields = ["value"]
        if len(self.aggregation):
            for i in range(len(self.fields)):
                if self.aggregation[i] not in self.fields[i]:
                    self.fields[i] = '%s("%s")' % (self.aggregation[i], self.fields[i])
        else:
            self.fields = ["%s" % f for f in self.fields]
        self.sql = 'SELECT %s FROM "%s"' % (", ".join(self.fields), self.metric)
        if len(self.filter):
            self.sql = "%s WHERE %s" % (self.sql, " AND ".join(self.filter))
        if len(self.group):
            self.sql = "%s GROUP BY %s" % (self.sql, ",".join(self.group))
        if self.fill:
            self.sql = "%s fill(%s)" % (self.sql, self.fill)

    @property
    def query(self) -> str:
        return self.sql

    # === Fluent Methods ===
    def select(self, fields=["value"], aggregation=[]):
        self.fields, self.aggregation = [], []
        if isinstance(fields, list):
            self.fields = fields
        elif isinstance(fields, str):
            self.fields = [fields]
        else:
            raise WrongArgumentType(
                "Fields must be either a list or a string", [type(self.fields)]
            )
        if len(aggregation):
            if isinstance(aggregation, list):
                if len(aggregation) == len(self.fields):
                    self.aggregation = aggregation
                elif len(aggregation) == 1:
                    self.aggregation = [aggregation[0] for i in range(len(self.fields))]
                else:
                    raise WrongArgumentType(
                        "Aggregation as a list should be either"
                        + "the same len as fields or 1",
                        ["lenght: %s" % len(aggregation)],
                    )
            elif isinstance(aggregation, str):
                self.aggregation = [aggregation for i in range(len(self.fields))]
            else:
                raise WrongArgumentType(
                    "Aggregation should either be a list or a string",
                    [type(aggregation)],
                )
        self.rebuild()
        return self

    def filter_by(self, tag, operator, value):
        f = "(\"%s\" %s '%s')" % (tag, operator, value)
        if f not in self.filter:
            self.filter.append(f)
            self.rebuild()
        return self

    def filter_by_from_dict(self, filter_by):
        warnings.warn(
            "filter_by_from_dict is deprecated. Use chained filter_by() calls instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not isinstance(filter_by, (list, dict)):
            raise WrongArgumentType(
                "Filter should be provided as a list or a dictionary"
            )
        if isinstance(filter_by, dict):
            filter_by = [filter_by]
        validate = ["tag", "operator", "value"]
        for f in filter_by:
            for v in validate:
                if v not in f:
                    raise WrongArgumentType("Missing filter_by[%s] key" % v)
            self.filter_by(**f)
        return self

    def set_time_range(self, block):
        for f in self.filter:
            if "time" in f:
                self.filter.remove(f)
        self.filter = [block] + self.filter
        self.rebuild()

    def filter_time_range(self, r):
        if not isinstance(r, (list, tuple)):
            raise WrongArgumentType(
                "Time range should be provided as a list or a tuple"
            )
        r = copy.deepcopy(list(r))
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
            t = "(time <= %sms)" % int(t)
            conditions.append(t)
        f = time.mktime(f.timetuple())
        f = int(f) * 1000
        f = "(time >= %sms)" % int(f)
        conditions.append(f)
        block = " AND ".join(conditions)
        self.set_time_range(block)
        return self

    def time_block(self, block):
        block = "time(%s)" % block
        for g in self.group:
            if "time(" in g:
                self.group.remove(g)
        self.group = [block] + self.group
        self.rebuild()
        return self

    def group_by(self, group):
        if len(self.aggregation) == 0:
            raise WrongArgumentType("In order to group results, aggregate first")
        if isinstance(group, str):
            group = [group]
        for g in group:
            self.group.append('"%s"' % g)
        self.group = list(set(self.group))
        self.rebuild()
        return self

    def fill_with(self, fill=False):
        f = ["none", "null", "0", "previous", "linear"]
        if fill and fill in f:
            self.fill = fill
        else:
            self.fill = False
        self.rebuild()
        return self

    def filter_value_in(self, tag, values):
        if values:
            filters = ["(\"%s\" = '%s')" % (tag, v) for v in values]
            filters = "(%s)" % (" OR ".join(filters))
            self.filter.append(filters)
        self.rebuild()
        return self

    # === Result Parsing ===
    def parse_results(self, raw_results) -> list:
        """Parse InfluxDB ResultSet into list of dicts."""
        tagged_response = len([g for g in self.group if "time(" not in g]) > 0
        if not tagged_response:
            return list(raw_results.get_points())
        else:
            r = []
            for row in raw_results.raw["series"]:
                for v in row["values"]:
                    i = {"tags": row["tags"]}
                    for c in range(len(row["columns"])):
                        i[row["columns"][c]] = v[c]
                r.append(i)
            return r
