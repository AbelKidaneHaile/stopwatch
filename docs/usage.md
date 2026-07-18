# Quick start

This page introduces the most common workflows. The rest of the user guide explains each API in depth.

## Time one block

```python
from stopwatch import watch

with watch("load configuration") as timing:
    configuration = load_configuration()

print(timing.elapsed)
print(timing.result.status)
```

`timing.elapsed` is available during and after the block. `timing.result` becomes a finished immutable
`Measurement` when the block exits.

To print automatically to standard error:

```python
with watch("load configuration", show=True):
    configuration = load_configuration()
```

## Control a stopwatch manually

```python
from stopwatch import Stopwatch

timer = Stopwatch("daily import").start()

rows = download_rows()
timer.lap("download")

customers = parse_rows(rows)
timer.lap("parse")

save_customers(customers)
timer.lap("save")

result = timer.stop()

for lap in result.laps:
    print(f"{lap.name:12} lap={lap.duration} split={lap.split}")
```

See [Manual stopwatch](manual-stopwatch.md) for pause/resume, states, reset/restart, clocks, and lifecycle errors.

## Time a function

```python
from stopwatch import timed

@timed("invoice.calculate")
def calculate_invoice(invoice):
    return invoice.calculate_total()
```

Async functions are detected automatically:

```python
@timed("customer.fetch")
async def fetch_customer(customer_id: str):
    return await client.fetch(customer_id)
```

See [Contexts and decorators](instrumentation.md) for generators, async generators, callbacks, and exception behavior.

## Aggregate repeated operations

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

@timings.timed("customer.lookup")
def find_customer(customer_id: str):
    return database.fetch_customer(customer_id)

for customer_id in customer_ids:
    find_customer(customer_id)

statistics = timings.stats("customer.lookup")
print("Calls:", statistics.count)
print("Mean:", statistics.mean)
print("P95:", statistics.p95)
print("Maximum:", statistics.maximum)
```

## Create a nested report

```python
timings = TimerRegistry(retention="all")

with timings.watch("customer import"):
    with timings.watch("download"):
        rows = download_rows()

    with timings.watch("parse"):
        customers = parse_rows(rows)

    with timings.watch("save"):
        save_customers(customers)

print(timings.report(view="tree"))
```

Possible output:

```text
customer import: 1.82 s
└── download: 840.2 ms
└── parse: 311.6 ms
└── save: 641.8 ms
```

## Enforce a performance budget

```python
from stopwatch import DurationBudgetExceeded, watch

try:
    with watch("serialize response", budget="250ms", on_exceed="raise"):
        body = serialize_response(data)
except DurationBudgetExceeded as error:
    print("Actual:", error.actual)
    print("Budget:", error.budget)
```

See [Budgets](budgets.md) for non-raising policies and application-error precedence.

## Export timings

```python
timings.to_json("timings.json")
timings.to_csv("timings.csv")
```

For event streaming:

```python
from stopwatch import TimerRegistry
from stopwatch.sinks import JsonLinesSink, LoggingSink

timings = TimerRegistry(
    sinks=[
        JsonLinesSink("timings.jsonl"),
        LoggingSink("application.performance"),
    ]
)
```

See [Sinks and exports](sinks-and-exports.md) for every built-in sink and custom integrations.
