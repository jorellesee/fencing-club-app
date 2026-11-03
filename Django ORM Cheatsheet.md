# Django ORM cheatsheet

Examples use this app's models: `TrainingSession`, `Attendance`, `Member`, `Coach`.
Try any of them in `python manage.py shell`, after:

```python
from django.db.models import Q, F, Count, Sum, Avg, Min, Max, Exists, OuterRef, Subquery, Window
from django.utils import timezone
from club.models import TrainingSession, Attendance, Member, Coach
now = timezone.now()
```

---

## 1. QuerySets and laziness

```python
qs = TrainingSession.objects.all()   # a QuerySet: a query not yet run
qs = qs.filter(weapon='sabre')       # each method returns a NEW QuerySet
print(qs.query)                      # the SQL it will run
```

The SQL runs only when the results are used:

| Runs the query | |
|---|---|
| `for s in qs:` / `{% for %}` | loops |
| `list(qs)`, `len(qs)`, `bool(qs)` | |
| `qs[0]`, `qs.first()`, `qs.last()` | |
| `qs.count()`, `qs.exists()` | a small query of its own each |

Once run, a QuerySet keeps its results: looping over it again doesn't query again.
Chaining another method (`qs.filter(...)`) makes a new query.

---

## 2. Getting rows

```python
TrainingSession.objects.all()
TrainingSession.objects.get(pk=5)              # exactly one, or raises
TrainingSession.objects.filter(weapon='sabre') # WHERE
TrainingSession.objects.exclude(weapon='sabre')# WHERE NOT
TrainingSession.objects.first()                # one or None, in ordering
TrainingSession.objects.filter(pk=5).exists()  # True / False, cheapest check
TrainingSession.objects.filter(weapon='foil').count()
```

`get()` raises `TrainingSession.DoesNotExist` (none) or
`MultipleObjectsReturned` (more than one). In a view, use
`get_object_or_404(queryset, pk=pk)` instead.

Several conditions in one `filter()` are joined with AND:

```python
TrainingSession.objects.filter(weapon='sabre', capacity=1)
```

---

## 3. Field lookups: `field__lookup=value`

| Lookup | SQL | Example |
|---|---|---|
| (none) / `exact` | `=` | `filter(weapon='foil')` |
| `iexact` | case-insensitive `=` | `filter(name__iexact='junior foil')` |
| `contains` / `icontains` | `LIKE '%x%'` | `filter(name__icontains='foil')` |
| `startswith` / `endswith` | `LIKE 'x%'` | `filter(name__startswith='Mon')` |
| `gt` `gte` `lt` `lte` | `>` `>=` `<` `<=` | `filter(start__gte=now)` |
| `in` | `IN (...)` | `filter(weapon__in=['foil', 'epee'])` |
| `range` | `BETWEEN` | `filter(start__range=(a, b))` |
| `isnull` | `IS NULL` | `filter(coach__isnull=True)` |
| `date`, `year`, `month`, `week_day`, `hour` | parts of a date | `filter(start__date=today)`, `filter(start__week_day=2)` |

---

## 4. Following relationships with `__`

Double underscores follow a ForeignKey and add the JOIN:

```python
# Forwards: session -> coach
TrainingSession.objects.filter(coach__name='Lim')

# Backwards: session -> its attendance rows -> their member
TrainingSession.objects.filter(attendance__member__name='Ann')

# Chained with a lookup at the end
Attendance.objects.filter(session__start__gte=now)
```

Going backwards uses the `related_name` (`attendance`, `sessions`, `members`), or
`modelname_set` on an object when there isn't one.

Backwards across a many-relationship can repeat rows (one per match). Add
`.distinct()` if so.

On one object:

```python
session = TrainingSession.objects.get(pk=5)
session.coach                 # the Coach (a query, unless select_related)
session.attendance.all()      # its Attendance rows
coach.sessions.filter(start__gte=now)
```

---

## 5. `Q`: OR, NOT, and reusable conditions

```python
Q(weapon='foil') | Q(weapon='epee')     # OR
Q(start__gte=now) & Q(capacity=1)       # AND
~Q(capacity=1)                          # NOT

TrainingSession.objects.filter(Q(weapon='foil') | Q(coach__name='Lim'))

INDIVIDUAL = Q(capacity=1)              # name it, reuse it
TrainingSession.objects.exclude(INDIVIDUAL)
```

Q objects go before keyword arguments: `filter(INDIVIDUAL, coach__isnull=False)`.

---

## 6. `F`: refer to another field

Compare or compute with a column's own value, in the database:

```python
# Sessions where the end is before the start (bad data)
TrainingSession.objects.filter(end__lt=F('start'))

# Add a day to every session in a series, in one UPDATE
TrainingSession.objects.filter(series=s).update(start=F('start') + timedelta(days=1))
```

---

## 7. Ordering, slicing, distinct

```python
qs.order_by('start')            # ASC
qs.order_by('-start')           # DESC
qs.order_by('coach__name', 'start')
qs.order_by()                   # no ordering, not even Meta.ordering
qs[:10]                         # LIMIT 10
qs[10:20]                       # OFFSET 10 LIMIT 10
qs.reverse()
qs.distinct()
```

Negative indexes (`qs[-1]`) aren't allowed. Use `.last()` or reverse the order.

---

## 8. Only some columns: `values`, `values_list`, `only`

```python
qs.values('name', 'start')               # dicts: {'name': ..., 'start': ...}
qs.values_list('name', 'start')          # tuples
qs.values_list('location', flat=True)    # plain list of one field
qs.values_list('location', flat=True).distinct()   # each location once

qs.only('name', 'start')    # model objects, other fields loaded on access
qs.defer('notes')           # model objects, without this field
```

`values()` can follow relationships too: `values('coach__name')`.

---

## 9. Aggregating

### `aggregate()`: one answer for the whole QuerySet

```python
TrainingSession.objects.aggregate(total=Count('id'), first=Min('start'))
# {'total': 42, 'first': datetime(...)}
```

### `annotate()`: an extra value on every row

```python
TrainingSession.objects.annotate(member_count=Count('attendance'))
# each session has .member_count

# Count only some related rows
TrainingSession.objects.annotate(
    present_count=Count('attendance', filter=Q(attendance__status='present'))
)

# Then filter or order on it
Coach.objects.annotate(n=Count('sessions')).filter(n__gt=5).order_by('-n')
```

### GROUP BY: `values()` then `annotate()`

```python
TrainingSession.objects.values('location').annotate(n=Count('id')).order_by('location')
# [{'location': 'BT', 'n': 4}, ...]
```

Gotchas:
- Two `Count`s across different relationships in one query multiply each other.
  Use `Count(..., distinct=True)` or a subquery.
- Django drops `Meta.ordering` from a query that groups, so add `.order_by()`
  yourself.

---

## 10. Subqueries

### `__in` with another QuerySet

```python
on_ann = Attendance.objects.filter(member__name='Ann').values('session')
TrainingSession.objects.filter(id__in=on_ann)
```

### `Exists` and `OuterRef`: a check per row

```python
has_present = Attendance.objects.filter(session=OuterRef('pk'), status='present')
TrainingSession.objects.filter(Exists(has_present))
TrainingSession.objects.annotate(marked=Exists(has_present))
```

`OuterRef('pk')` means "the outer query's row".

### `Subquery`: one value from another query

```python
latest = Attendance.objects.filter(member=OuterRef('pk')).order_by('-session__start')
Member.objects.annotate(last_status=Subquery(latest.values('status')[:1]))
```

---

## 11. Avoiding N+1 queries

| Use | For | How |
|---|---|---|
| `select_related('coach')` | ForeignKey / OneToOne (one object) | a JOIN in the same query |
| `prefetch_related('attendance__member')` | reverse FK / ManyToMany (many objects) | one extra query per relationship |

```python
for s in TrainingSession.objects.select_related('coach'):
    s.coach.name                  # no extra query

for s in TrainingSession.objects.prefetch_related('attendance__member'):
    [a.member.name for a in s.attendance.all()]   # no extra queries
```

A `.filter()` on a prefetched relationship (`s.attendance.filter(...)`) ignores
the prefetch and queries again. Filter in Python, or use `Prefetch()`:

```python
from django.db.models import Prefetch
TrainingSession.objects.prefetch_related(
    Prefetch('attendance', queryset=Attendance.objects.filter(status='present'), to_attr='present')
)
# s.present is a list
```

---

## 12. Creating

```python
s = TrainingSession.objects.create(name='Sabre', start=a, end=b)   # INSERT, returns it

s = TrainingSession(name='Sabre', start=a, end=b)
s.save()                                                          # same, in two steps

row, created = Attendance.objects.get_or_create(
    session=s, member=m, defaults={'status': 'enrolled'}
)
row, created = Attendance.objects.update_or_create(
    session=s, member=m, defaults={'status': 'present'}
)

Attendance.objects.bulk_create([Attendance(session=s, member=m, status='enrolled') for m in members])
```

`bulk_create` is one query, but it skips `save()` and signals.

---

## 13. Updating

```python
# One object
s.name = 'Renamed'
s.save()                              # saves every field
s.save(update_fields=['name'])        # saves only these

# Many rows, one UPDATE, skips save()
TrainingSession.objects.filter(location='forn').update(location='BT')   # returns count
```

---

## 14. Deleting

```python
s.delete()
TrainingSession.objects.filter(start__lt=cutoff).delete()   # returns (count, by model)
```

`on_delete` decides what happens to rows pointing at what's deleted:
`CASCADE` deletes them too (Attendance), `SET_NULL` clears the link (a session's
coach), `PROTECT` refuses.

---

## 15. Transactions

```python
from django.db import transaction

with transaction.atomic():
    ...   # all of it is saved, or, if anything raises, none of it
```

Use it when two or more writes must happen together, or a check and a write
must not be interleaved with another request (`services.enrol`).

---

## 16. Window functions

```python
from django.db.models.functions import RowNumber, Rank, Lag, Lead

Attendance.objects.annotate(
    nth=Window(RowNumber(), partition_by=F('member'), order_by=F('session__start').asc())
)
# ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY start)

# The latest row per member: filter on a window (Django 4.2+)
Attendance.objects.annotate(
    latest=Window(RowNumber(), partition_by=F('member'), order_by=F('session__start').desc())
).filter(latest=1)
```

Aggregates work as window functions too, for running totals:
`Window(Count('id'), partition_by=..., order_by=...)`.

---

## 17. Raw SQL, when you need it

```python
TrainingSession.objects.raw('SELECT * FROM club_trainingsession WHERE capacity = %s', [1])

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT location, COUNT(*) FROM club_trainingsession GROUP BY location')
    cursor.fetchall()
```

Always pass values as parameters (`%s` and a list), never in an f-string.
A raw query can't be chained with `.filter()`, so keep the app's queries in the
ORM and use raw SQL for one-off reports.

---

## 18. SQL to ORM at a glance

| SQL | Django |
|---|---|
| `SELECT * FROM t` | `Model.objects.all()` |
| `WHERE a = 1 AND b = 2` | `.filter(a=1, b=2)` |
| `WHERE a = 1 OR b = 2` | `.filter(Q(a=1) \| Q(b=2))` |
| `WHERE NOT a = 1` | `.exclude(a=1)` |
| `WHERE x IN (...)` | `.filter(x__in=[...])` |
| `WHERE x IS NULL` | `.filter(x__isnull=True)` |
| `WHERE a < b` (two columns) | `.filter(a__lt=F('b'))` |
| `JOIN ... WHERE coach.name = 'Lim'` | `.filter(coach__name='Lim')` |
| `SELECT DISTINCT x` | `.values_list('x', flat=True).distinct()` |
| `ORDER BY x DESC` | `.order_by('-x')` |
| `LIMIT 10 OFFSET 20` | `[20:30]` |
| `COUNT(*)` | `.count()` |
| `GROUP BY x` + `COUNT` | `.values('x').annotate(n=Count('id'))` |
| `HAVING COUNT(*) > 5` | `.annotate(n=Count(...)).filter(n__gt=5)` |
| `WHERE EXISTS (...)` | `.filter(Exists(...))` |
| `WHERE id IN (SELECT ...)` | `.filter(id__in=Other.objects.filter(...).values('...'))` |
| `UPDATE t SET x = 1 WHERE ...` | `.filter(...).update(x=1)` |
| `DELETE FROM t WHERE ...` | `.filter(...).delete()` |
| `INSERT INTO t ...` | `Model.objects.create(...)` |

---

## 19. Debugging

```python
print(qs.query)            # the SQL (values shown unquoted; for reading only)
qs.explain()               # the database's query plan

# Every query a block of code ran (shell, with DEBUG on)
from django.db import connection, reset_queries
reset_queries(); list(qs); connection.queries
```

In tests, `with self.assertNumQueries(3): ...` fails if a page starts running more
queries than it should.
