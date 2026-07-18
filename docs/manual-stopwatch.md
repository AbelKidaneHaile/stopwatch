# Manual stopwatch

Use `Stopwatch` when code needs explicit control over start, stop, pause, resume, laps, or reset behavior.

## Basic lifecycle

```python
from stopwatch import Stopwatch

timer = Stopwatch("generate report")
timer.start()
generate_report()
measurement = timer.stop()

print(measurement.duration)
```

`start()` returns the stopwatch, so construction and startup can be chained:

```python
timer = Stopwatch("generate report").start()
```

`stop()` is idempotent. Cleanup code can safely call it more than once and receives the same measurement object:

```python
first = timer.stop()
second = timer.stop()
assert first is second
```

## States and invalid operations

The lifecycle is:

```text
IDLE → RUNNING ⇄ PAUSED → STOPPED
```

```python
from stopwatch import InvalidStopwatchState, StopwatchState

timer = Stopwatch("job")
assert timer.state is StopwatchState.IDLE

try:
    timer.pause()
except InvalidStopwatchState:
    print("Only a running stopwatch can be paused")
```

Invalid operations raise immediately. In particular:

- `start()` requires `IDLE`.
- `pause()` requires `RUNNING`.
- `resume()` requires `PAUSED`.
- `lap()` requires `RUNNING`.
- `stop()` cannot stop `IDLE`.

## Read live elapsed time

Reading `elapsed` never changes the state:

```python
timer = Stopwatch("job").start()

do_first_part()
print("So far:", timer.elapsed)

do_second_part()
print("Total:", timer.stop().duration)
```

## Pause and resume

Active duration excludes pauses. Wall duration includes the entire start-to-stop span.

```python
timer = Stopwatch("interactive import").start()

download_data()

timer.pause()
input("Review the data, then press Enter")
timer.resume()

process_data()
result = timer.stop()

print("Active:", result.duration)
print("Paused:", result.paused_duration)
print("Wall:", result.wall_duration)
```

Use the exception-safe paused context when possible:

```python
with timer.paused():
    wait_for_operator()
```

The timer resumes in `finally` even if the paused block raises.

## Record laps and splits

A lap contains its interval duration and the cumulative active split:

```python
timer = Stopwatch("ETL pipeline").start()

records = extract()
extract_lap = timer.lap("extract", tags={"rows": len(records)})

cleaned = transform(records)
transform_lap = timer.lap("transform", tags={"rows": len(cleaned)})

load(cleaned)
load_lap = timer.lap("load")

result = timer.stop()

print(extract_lap.duration)   # time since start
print(transform_lap.duration) # time since previous lap
print(transform_lap.split)    # active time since start
```

Inspect laps before or after stopping:

```python
timer.laps
timer.last_lap
timer.find_laps("transform")
result.laps
```

Duplicate names are allowed, which is useful in loops:

```python
for batch in batches:
    process(batch)
    timer.lap("batch", tags={"size": len(batch)})
```

Calling `lap()` while paused raises because a paused lap would be ambiguous.

## Reset and restart

```python
timer.stop()
timer.reset()    # return to IDLE; clear result and laps
timer.restart()  # reset and immediately start
```

Protect active data by making destructive resets explicit:

```python
timer.reset(force=True)
```

Without `force=True`, resetting a running or paused timer raises `InvalidStopwatchState`.

## Attach names and safe tags

```python
timer = Stopwatch(
    "http.request",
    tags={
        "method": "GET",
        "route": "/customers/{customer_id}",
        "service": "billing",
    },
).start()
```

Tag values must be JSON scalars. Prefer low-cardinality templates over raw identifiers or full URLs.

## Choose a clock

The default `wall` clock measures elapsed time, including sleep and I/O waits:

```python
timer = Stopwatch("download", clock="wall")
```

CPU clocks exclude sleep:

```python
Stopwatch("compression", clock="process")
Stopwatch("worker calculation", clock="thread")
```

Measure multiple clocks at once:

```python
with Stopwatch("compress archive", clocks=("wall", "process")) as timer:
    compress_files()

result = timer.result
print("Primary:", result.duration)
print("Wall:", result.clocks["wall"])
print("CPU:", result.clocks["process"])
```

The first clock is the primary clock used for `duration`. CPU time is most meaningful when unrelated work is not
running concurrently in the same process or thread.

## Use Stopwatch as a context manager

```python
try:
    with Stopwatch("send invoice") as timer:
        send_invoice()
except ConnectionError:
    pass

assert timer.result is not None
print(timer.result.status)      # "error"
print(timer.result.error_type)  # "ConnectionError"
```

The original exception is re-raised with its traceback. Only its type is recorded by default.
