# Registries and statistics

`TimerRegistry` is a thread-safe collector for repeated measurements. It aggregates online statistics, optionally
retains individual measurements, tracks nested parent relationships, and generates reports.

## Collect repeated scopes

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

for item in items:
    with timings.watch("item.process"):
        process(item)

statistics = timings.stats("item.process")
print(statistics.count)
print(statistics.total)
print(statistics.mean)
```

## Collect decorated calls

```python
@timings.timed("database.customer_lookup")
def find_customer(customer_id: str):
    return database.fetch_customer(customer_id)

for customer_id in customer_ids:
    find_customer(customer_id)
```

Every invocation creates an independent stopwatch. Exceptions propagate while incrementing the error count.

## Read statistics

```python
stats = timings.stats("database.customer_lookup")

stats.name
stats.count
stats.success_count
stats.error_count
stats.total
stats.minimum
stats.maximum
stats.mean
stats.variance_ns2
stats.standard_deviation
stats.last
stats.median
stats.p50
stats.p75
stats.p90
stats.p95
stats.p99
stats.percentiles_exact
```

`variance_ns2` is a floating-point variance in square nanoseconds. All other timing statistics use `Duration`.

Retrieve every named aggregate:

```python
all_statistics = timings.stats()

for name, stats in all_statistics.items():
    print(name, stats.count, stats.mean)
```

`stats("missing")` raises `KeyError` rather than returning a misleading zero-valued result.

## Choose a retention policy

Online count, total, mean, minimum, maximum, and variance do not require sample retention.

```python
TimerRegistry(retention="none")
```

This uses the least memory, but percentile fields are `None` and individual measurements are unavailable.

```python
TimerRegistry(retention=2048)  # default
```

An integer retains the most recent measurements in a bounded ring. Percentiles describe the retained window and
`percentiles_exact` is `False` because older values may have been discarded.

```python
TimerRegistry(retention="all")
```

This retains every measurement and produces exact percentiles. Use it for tests, command-line programs, and bounded
analysis—not unbounded production services.

## Create nested timings

```python
timings = TimerRegistry(retention="all")

with timings.watch("request", tags={"route": "/customers/{id}"}):
    with timings.watch("authenticate"):
        user = authenticate()

    with timings.watch("database"):
        records = load_records(user)

    with timings.watch("render"):
        response = render_response(records)
```

Nested scopes inherit a trace ID and record their parent's measurement ID. Context variables isolate stacks across
threads and asyncio tasks.

```python
for measurement in timings.measurements:
    print(measurement.name, measurement.parent_id, measurement.trace_id)
```

Concurrent async children can overlap in time. The current tree and timeline views preserve the hierarchy but do not
claim that summing child durations equals parent duration.

## Generate reports

Table report:

```python
print(timings.report())
print(timings.report(sort_by="p95"))
```

Supported sort columns are `name`, `count`, `total`, `mean`, `p95`, `max`, and `errors`.

Tree report:

```python
print(timings.report(view="tree"))
```

Text timeline:

```python
print(timings.report(view="timeline"))
```

Tree and timeline reports require retained measurements. With `retention="none"`, use the aggregate table instead.

## Filter retained measurements

```python
database_events = timings.filter(prefix="database.")

billing_gets = timings.filter(
    prefix="http.",
    tags={"service": "billing", "method": "GET"},
)
```

Filtering returns an immutable tuple and does not alter the registry.

## Manage registry data

Create an immutable aggregate snapshot:

```python
snapshot = timings.snapshot()
```

Remove one series:

```python
timings.reset("database.customer_lookup")
```

Clear everything:

```python
timings.clear()
```

Merge retained worker measurements into a main-process registry:

```python
main_timings.merge(worker_timings)
```

Registries are not transparently shared between processes. Each worker should return retained measurements or export
them through an explicit interprocess sink.

## Enforce tag keys

```python
timings = TimerRegistry(
    allowed_tag_keys={"method", "route", "status", "service"},
)
```

An unexpected tag key raises `ValueError`. All tag values must be `str`, `int`, `float`, `bool`, or `None`.

Avoid high-cardinality values:

```python
# Avoid
tags={"customer_id": customer_id, "full_url": request.url}

# Prefer
tags={"route": "/customers/{customer_id}", "method": "GET"}
```

## Thread and async behavior

- A registry is safe for concurrent recording from threads.
- Each decorated call owns its stopwatch.
- One `Stopwatch` instance should not be mutated concurrently.
- Context-based nesting is isolated per thread and propagated into asyncio tasks.
- Sink implementations must document their own thread-safety.

```python
@timings.timed("worker.task")
def work(item):
    return process(item)

with ThreadPoolExecutor() as executor:
    results = list(executor.map(work, items))
```
