# Performance budgets

A performance budget compares a finished duration with an explicit limit. Budgets work with `watch()`, `Stopwatch`,
`TimerRegistry.watch()`, `timed`, and `TimerRegistry.timed()`.

## Record a breach

The default `record` policy changes the successful measurement status to `budget_exceeded` without printing or
raising:

```python
from stopwatch import watch

with watch("database.query", budget="100ms") as timing:
    rows = query_database()

result = timing.result
if result.budget_exceeded:
    print("Actual:", result.duration)
    print("Budget:", result.budget)
```

## Warn without interrupting work

```python
with watch("database.query", budget="100ms", on_exceed="warn"):
    rows = query_database()
```

This emits a `RuntimeWarning` after the ending clock has been read.

## Log a breach

```python
import logging

logging.basicConfig(level=logging.WARNING)

with watch("database.query", budget="100ms", on_exceed="log"):
    rows = query_database()
```

The message is sent to the `stopwatch` logger. The package never calls `logging.basicConfig()` itself.

## Raise for a hard limit

```python
from stopwatch import DurationBudgetExceeded

try:
    with watch("serialize response", budget="250ms", on_exceed="raise"):
        serialize_response(data)
except DurationBudgetExceeded as error:
    print("Operation:", error.name)
    print("Actual:", error.actual)
    print("Budget:", error.budget)
```

Hard limits are useful in controlled tests or coarse service-level checks. Ordinary timing can be noisy, so avoid
overly tight thresholds on shared CI machines.

## Call custom policy code

```python
def handle_breach(measurement):
    alert_queue.put(
        {
            "operation": measurement.name,
            "duration_ms": measurement.duration.milliseconds,
            "budget_ms": measurement.budget.milliseconds,
        }
    )

with watch(
    "invoice generation",
    budget="500ms",
    on_exceed=handle_breach,
):
    generate_invoice()
```

The callback runs only when the budget is exceeded. Keep it lightweight so observability does not slow application
cleanup.

## Accepted budget values

Budget parameters accept a duration string, `Duration`, `datetime.timedelta`, or integer nanoseconds:

```python
from datetime import timedelta
from stopwatch import Duration

watch("one", budget="250ms")
watch("two", budget=Duration.from_milliseconds(250))
watch("three", budget=timedelta(milliseconds=250))
watch("four", budget=250_000_000)
```

Strings are usually the clearest configuration format. Integers always mean nanoseconds.

## Preserve application exceptions

An application exception remains primary even if the operation also exceeds its budget:

```python
try:
    with watch("operation", budget="100ms", on_exceed="raise"):
        raise DatabaseError("query failed")
except DatabaseError:
    handle_database_failure()
```

The result records `status="error"` and `budget_exceeded=True`. The budget policy emits a warning instead of replacing
the `DatabaseError` with `DurationBudgetExceeded`.

## Budget a repeated operation

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

@timings.timed("cache.lookup", budget="5ms", on_exceed="record")
def lookup(key):
    return cache.get(key)
```

Budget-exceeded calls count as successful calls in aggregate statistics because the application operation completed.
Inspect retained measurements to count individual breaches:

```python
breaches = [item for item in timings.measurements if item.budget_exceeded]
```
