# Practical recipes

These examples combine the core APIs into realistic application patterns.

## Command-line data application

Measure the whole program and its major stages, then print a report at the end:

```python
from stopwatch import TimerRegistry

timings = TimerRegistry(retention="all")

def main() -> None:
    with timings.watch("application"):
        with timings.watch("read input"):
            records = read_input()

        with timings.watch("validate"):
            valid_records = validate(records)

        with timings.watch("write output"):
            write_output(valid_records)

    print(timings.report(view="tree"))

if __name__ == "__main__":
    main()
```

This gives named structure without the setup or output volume of a profiler.

## ETL pipeline with laps

Use one stopwatch when stages always occur sequentially and belong to one operation:

```python
from stopwatch import Stopwatch

timer = Stopwatch("daily data pipeline").start()

raw = download_data()
timer.lap("download", tags={"rows": len(raw)})

normalized = normalize_data(raw)
timer.lap("normalize", tags={"rows": len(normalized)})

validated = validate_data(normalized)
timer.lap("validate", tags={"rows": len(validated)})

save_data(validated)
timer.lap("save")

result = timer.stop()

for lap in result.laps:
    print(f"{lap.name:12} {str(lap.duration):>12}")
```

Persist the complete event for later analysis:

```python
from pathlib import Path

Path("pipeline-timing.json").write_text(
    result.to_json(indent=2),
    encoding="utf-8",
)
```

## Repeated database operation

Use a decorator and registry when the same operation runs many times:

```python
from stopwatch import TimerRegistry

timings = TimerRegistry(retention=2048)

@timings.timed("database.customer_lookup")
def find_customer(customer_id: str):
    return database.fetch_customer(customer_id)

for customer_id in customer_ids:
    try:
        find_customer(customer_id)
    except DatabaseError:
        handle_lookup_failure(customer_id)

stats = timings.stats("database.customer_lookup")

print("Calls:", stats.count)
print("Errors:", stats.error_count)
print("Mean:", stats.mean)
print("P95:", stats.p95)
print("Maximum:", stats.maximum)
```

The original database exception propagates, while the failed call is still included in registry statistics.

## Async web request breakdown

Use low-cardinality route templates rather than full URLs containing IDs:

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

async def handle_request(request):
    async with timings.watch(
        "http.request",
        tags={
            "method": request.method,
            "route": request.route_template,
        },
    ):
        async with timings.watch("http.authenticate"):
            user = await authenticate(request)

        async with timings.watch("http.database"):
            records = await load_records(user)

        with timings.watch("http.serialize"):
            body = serialize(records)

        return Response(body)
```

Avoid this:

```python
tags={"route": "/users/839283/orders/7291"}
```

Prefer this:

```python
tags={"route": "/users/{user_id}/orders/{order_id}"}
```

## Concurrent async children

Decorated child coroutines inherit the active parent context:

```python
import asyncio

timings = TimerRegistry(retention="all")

@timings.timed("fetch.users")
async def fetch_users():
    return await users_client.fetch()

@timings.timed("fetch.orders")
async def fetch_orders():
    return await orders_client.fetch()

@timings.timed("fetch.inventory")
async def fetch_inventory():
    return await inventory_client.fetch()

async def fetch_dashboard():
    async with timings.watch("fetch dashboard"):
        return await asyncio.gather(
            fetch_users(),
            fetch_orders(),
            fetch_inventory(),
        )
```

The child durations may add up to more than the parent duration because they overlap. Use the timeline view to make
that concurrency visible:

```python
print(timings.report(view="timeline"))
```

## Compare CPU time with wall time

Measure both clocks to get an initial signal about whether work is CPU-heavy or wait-heavy:

```python
from stopwatch import watch

with watch("process image archive", clocks=("wall", "process")) as timing:
    process_archive()

result = timing.result

print("Wall:", result.clocks["wall"])
print("CPU: ", result.clocks["process"])
```

An I/O-heavy operation may show much more wall time than CPU time. A CPU-heavy single-process operation often shows
similar values. This is a first signal, not a complete performance diagnosis.

## Pause around human interaction

Exclude intentional operator wait time from the active duration:

```python
timer = Stopwatch("reviewed import").start()

data = download_data()

with timer.paused():
    input("Review downloaded data and press Enter")

process_data(data)
result = timer.stop()

print("Processing time:", result.duration)
print("Operator wait:", result.paused_duration)
```

## Alert on slow operations

Use a result callback for a one-off measurement:

```python
from stopwatch import Duration, watch

slow_threshold = Duration.parse("500ms")

def report_if_slow(measurement):
    if measurement.duration > slow_threshold:
        alert_queue.put(
            {
                "operation": measurement.name,
                "duration_ms": measurement.duration.milliseconds,
            }
        )

with watch("invoice generation", on_result=report_if_slow):
    generate_invoice()
```

For a formal threshold with standardized status and policy handling, use a [performance budget](budgets.md).

## Time threaded workers

Decorate the worker function so each invocation receives an independent stopwatch:

```python
from concurrent.futures import ThreadPoolExecutor
from stopwatch import TimerRegistry

timings = TimerRegistry()

@timings.timed("worker.process_item")
def process_item(item):
    return transform(item)

with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(process_item, items))

print(timings.report(sort_by="p95"))
```

Do not share and mutate one `Stopwatch` instance from multiple threads.

## Export events and aggregates together

Use a sink for individual events and registry export for the aggregate summary:

```python
from stopwatch import TimerRegistry
from stopwatch.sinks import JsonLinesSink, LoggingSink

timings = TimerRegistry(
    retention=2048,
    sinks=[
        JsonLinesSink("timings.jsonl"),
        LoggingSink("application.performance"),
    ],
)

run_application(timings)

timings.to_json("timing-summary.json")
timings.to_csv("timing-summary.csv")
```

The JSON Lines file answers event-level questions. The JSON and CSV summaries answer aggregate questions without
reprocessing every event.

## Sample a high-volume request path

```python
timings = TimerRegistry(sample_rate=0.01)

async def handle_request(request):
    async with timings.watch(
        "http.request",
        sample_key=request.request_id,
        tags={
            "method": request.method,
            "route": request.route_template,
        },
    ):
        return await dispatch(request)
```

The registry chooses whether to retain and aggregate the measurement before recording it. Keep the same key for
related work when a repeatable within-process decision is useful.
