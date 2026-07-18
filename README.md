# stopwatch

[![PyPI](https://img.shields.io/pypi/v/advanced-stopwatch.svg)](https://pypi.org/project/advanced-stopwatch/)
[![Python](https://img.shields.io/pypi/pyversions/advanced-stopwatch.svg)](https://pypi.org/project/advanced-stopwatch/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Documentation:** <https://abelkidanehaile.github.io/stopwatch/>

Precise, structured timing for Python—from one block of code to application-wide performance instrumentation.

`stopwatch` is a zero-dependency toolkit for named durations. It starts with a strict manual stopwatch and scales to
laps, pauses, sync and async scopes, decorators, nested measurements, bounded statistics, performance budgets,
structured exports, and custom observability sinks. Durations are calculated with monotonic, integer-nanosecond
clocks; calendar time is used only for human-readable timestamps.

Use `stopwatch` when you already know which operation you want to measure. Use `timeit` for controlled
microbenchmarks and a profiler when you need to discover unknown hotspots.

## Installation

Install the published package from PyPI:

```bash
python -m pip install advanced-stopwatch
```

With [uv](https://docs.astral.sh/uv/):

```bash
uv add advanced-stopwatch
```

Python 3.12 or newer is required. The runtime package has no third-party dependencies.

The PyPI distribution is named `advanced-stopwatch` because the `stopwatch` project name is already occupied. After
installation, the import package and command-line executable are both simply `stopwatch`:

```python
import stopwatch
```

## Quick start

```python
from stopwatch import watch

with watch("load customers") as timing:
    customers = load_customers()

print(timing.elapsed)          # e.g. 482.7 ms
print(timing.result.status)    # ok
```

Scopes are silent by default. Pass `show=True` to print a result to standard error:

```python
with watch("load customers", show=True):
    customers = load_customers()
```

Both `with` and `async with` are supported:

```python
async with watch("fetch customers") as timing:
    customers = await fetch_customers()
```

Exceptions and cancellation are never suppressed. The resulting measurement records `error` or `cancelled` and only
the exception type—not its potentially sensitive message.

## Duration

`Duration` is an immutable integer-nanosecond value. It avoids spreading ambiguous floating-point seconds through an
application.

```python
from datetime import timedelta
from stopwatch import Duration

Duration.zero()
Duration.from_nanoseconds(500)
Duration.from_microseconds(25)
Duration.from_milliseconds(250)
Duration.from_seconds(1.5)
Duration.from_timedelta(timedelta(seconds=2))

duration = Duration.parse("1h 20m 5s")
Duration.parse("250ns")
Duration.parse("20us")         # "µs" and "μs" are also accepted
Duration.parse("14ms")
Duration.parse("1.5s")
```

Conversions are available through `nanoseconds`/`ns`, `microseconds`/`us`, `milliseconds`/`ms`, `seconds`, `minutes`,
`hours`, and `to_timedelta()`:

```python
print(duration.nanoseconds)
print(duration.milliseconds)
print(duration.to_timedelta())
```

Durations support addition, subtraction, scaling, averaging, ratios, hashing, and comparison with either another
`Duration` or `datetime.timedelta`:

```python
total = Duration.parse("250ms") + Duration.parse("750ms")
average = total / 4
ratio = total / Duration.parse("250ms")
assert total == timedelta(seconds=1)
```

Formatting can select a unit or presentation style:

```python
duration = Duration.parse("1m 28.421s")

duration.format()                          # 1m28.4s
duration.format(unit="ms", precision=2)   # 88421.00 ms
duration.format(style="clock")            # 00:01:28.421
duration.format(style="compact")          # 1m28.4s
str(Duration.parse("482.7ms"))             # 482.7 ms
```

## Manual stopwatch lifecycle

`Stopwatch` follows `IDLE → RUNNING ⇄ PAUSED → STOPPED`. Invalid transitions raise
`InvalidStopwatchState`; a repeated `stop()` safely returns the same result.

```python
from stopwatch import Stopwatch, StopwatchState

timer = Stopwatch("daily pipeline", tags={"source": "crm"}).start()

raw = extract()
timer.lap("extract", tags={"rows": len(raw)})

timer.pause()
review(raw)                    # excluded from active duration
timer.resume()

with timer.paused():
    wait_for_operator()

load(raw)
timer.lap("load")
measurement = timer.stop()

print(timer.state is StopwatchState.STOPPED)
print(measurement.duration)          # active time, excluding pauses
print(measurement.paused_duration)   # time spent paused
print(measurement.wall_duration)     # complete start-to-stop span
```

Useful lifecycle and inspection calls are:

```python
timer.elapsed                 # live, non-mutating Duration
timer.laps                    # immutable tuple of Lap values
timer.last_lap
timer.find_laps("load")
timer.result                  # None until stopped
timer.reset()                 # stopped → idle; clears prior data
timer.reset(force=True)       # required while active
timer.restart()               # force-reset and immediately start
```

Each `Lap` exposes `index`, `name`, interval `duration`, cumulative `split`, `recorded_at`, `tags`, and `to_dict()`.
Duplicate lap names are allowed.

### Clocks and deterministic tests

Wall time uses `time.perf_counter_ns()` by default. Process and thread CPU clocks exclude sleep:

```python
with watch("compress", clock="process") as timing:
    compress()

with watch("compress", clocks=("wall", "process")) as timing:
    compress()

print(timing.result.clocks["wall"])
print(timing.result.clocks["process"])
```

Inject any object implementing the public `Clock` protocol (`name` and `now_ns()`). `ManualClock` makes tests fast and
deterministic:

```python
from stopwatch import ManualClock, Stopwatch

clock = ManualClock()
timer = Stopwatch("test", clock=clock).start()
clock.advance("25ms")
timer.lap("first")
clock.advance("75ms")
assert timer.stop().duration == Duration.parse("100ms")
```

`SystemClock("wall")`, `SystemClock("process")`, and `SystemClock("thread")` expose the built-in clocks directly.

## Measurements

Stopping creates an immutable `Measurement` with these public fields:

```python
measurement.id
measurement.name
measurement.duration
measurement.wall_duration
measurement.paused_duration
measurement.started_at
measurement.ended_at
measurement.status
measurement.error_type
measurement.laps
measurement.tags
measurement.parent_id
measurement.trace_id
measurement.clock_name
measurement.clocks
measurement.budget
measurement.budget_exceeded
```

Serialize, display, or derive a safely tagged copy:

```python
print(measurement)
print(measurement.format())
payload = measurement.to_dict()
json_text = measurement.to_json(indent=2)
tagged = measurement.with_tags(service="billing")
```

Tags accept only JSON scalar values (`str`, `int`, `float`, `bool`, or `None`). Avoid high-cardinality or sensitive
values such as user IDs, full URLs, SQL, function arguments, and exception messages.

## Decorators

`timed` works with ordinary functions, coroutines, generators, and async generators. Generator lifetime is measured
during iteration, not when the generator object is created.

```python
from stopwatch import timed

@timed
def calculate() -> int:
    return 42

@timed("invoice.calculate", tags={"service": "billing"})
def calculate_invoice() -> int:
    return 42

@timed("customer.fetch")
async def fetch_customer() -> dict:
    return await client.get_customer()

@timed("rows", generator_mode="lifetime")
def rows():
    yield from database_rows()
```

Wrappers preserve the original name, module, docstring, annotations, signature, and `__wrapped__` metadata.

## Registry, nesting, and statistics

`TimerRegistry` collects repeated timings safely across threads. `contextvars` propagate nesting across synchronous
and async execution contexts.

```python
from stopwatch import TimerRegistry

timings = TimerRegistry(retention=2048)

with timings.watch("customer import", tags={"source": "crm"}):
    with timings.watch("download"):
        rows = download_rows()
    with timings.watch("parse"):
        customers = parse_rows(rows)
    with timings.watch("save"):
        save_customers(customers)

print(timings.report())
print(timings.report(view="tree"))
print(timings.report(view="timeline"))
```

Decorate through a registry when calls should be aggregated:

```python
@timings.timed("database.customer_lookup")
def find_customer(customer_id: str):
    return database.fetch_customer(customer_id)

@timings.timed("http.fetch", sample_rate=0.1)
async def fetch():
    return await client.get("/customers")
```

`retention="none"` keeps online aggregates only, an integer keeps a bounded ring of recent measurements, and
`retention="all"` retains exact samples for short scripts and tests. Percentiles are exact only with `"all"`; the
`TimerStats.percentiles_exact` flag makes this explicit.

```python
stats = timings.stats("database.customer_lookup")
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

all_stats = timings.stats()       # dict[str, TimerStats]
snapshot = timings.snapshot()     # immutable tuple
events = timings.measurements     # retained Measurement tuple
```

Registry management and query calls:

```python
timings.filter(prefix="database.", tags={"service": "billing"})
timings.reset("database.customer_lookup")
timings.merge(worker_registry)    # merges retained measurements
timings.add_sink(custom_sink)
timings.clear()
```

Use `allowed_tag_keys={"method", "route", "status"}` to enforce a tag allow-list. Set `sample_rate` on a registry or
individual scope/decorator; `sample_key` on `watch()` makes related decisions deterministic.

## Performance budgets

Budgets accept a `Duration`, `timedelta`, integer nanoseconds, or duration string:

```python
from stopwatch import DurationBudgetExceeded

with watch("database.query", budget="100ms", on_exceed="warn"):
    query_database()

with watch("serialize", budget="250ms", on_exceed="raise"):
    serialize_response()
```

`on_exceed` supports `"record"` (default), `"warn"`, `"log"`, `"raise"`, or a callback receiving the finished
measurement. `DurationBudgetExceeded` exposes `name`, `actual`, and `budget`. If application code also fails, its
original exception remains primary and the budget exception does not mask it.

## Sinks and exports

A sink implements one call:

```python
class MySink:
    def record(self, measurement):
        queue.put(measurement.to_dict())
```

Built-in sinks are imported from `stopwatch.sinks`:

```python
from stopwatch.sinks import (
    CallbackSink,
    CompositeSink,
    ConsoleSink,
    InMemorySink,
    JsonLinesSink,
    LoggingSink,
    NullSink,
)

registry = TimerRegistry(
    sinks=[
        LoggingSink("application.performance", level="INFO"),
        JsonLinesSink("timings.jsonl"),
        CallbackSink(send_to_local_queue),
    ],
    on_sink_error="warn",       # also "raise" or callback(exception)
)
```

`ConsoleSink(stream=None)` prints one line, `InMemorySink.measurements` returns an immutable snapshot,
`CompositeSink(sinks)` fans out, and `NullSink` discards records. The package never configures application logging or
starts background workers.

Export aggregate snapshots as JSON or CSV:

```python
json_text = timings.to_json()
timings.to_json("timings.json", indent=2)
timings.to_csv("timings.csv")
```

## Configuration

Disable registry collection process-wide at runtime or before import with an environment variable:

```python
from stopwatch import configure

configure(enabled=False)
configure(enabled=True)
```

```bash
STOPWATCH_ENABLED=0 python application.py
```

The switch affects registry scopes and decorators. Explicitly constructed `Stopwatch` and `watch()` scopes remain
available, which keeps manual measurements predictable.

## Command-line interface

The installed `stopwatch` command is also available as `python -m stopwatch`.

```bash
stopwatch format 14821243ns
# 14.821 ms

stopwatch parse "1m 20.5s"
# 80500000000

stopwatch run -- python import_customers.py

stopwatch report timings.json
stopwatch report timings.jsonl
```

`run` returns the child process exit status and reports its total duration and UTC timestamps. `report` accepts either
aggregate JSON from `TimerRegistry.to_json()` or event-oriented JSON Lines from `JsonLinesSink`.

## Development

```bash
git clone https://github.com/AbelKidaneHaile/stopwatch.git
cd stopwatch
uv sync
uv run pytest
uv run ruff check .
uv run ty check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [SECURITY.md](SECURITY.md) for responsible
disclosure. Documentation is published at <https://abelkidanehaile.github.io/stopwatch/>.

## License

MIT © Abel Kidane Haile. See [LICENSE](LICENSE).
