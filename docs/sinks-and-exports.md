# Sinks and exports

Registries separate measurement from presentation. Aggregate exports describe series statistics; sinks receive each
individual measurement as it finishes.

## Export aggregate JSON

```python
json_text = timings.to_json()
print(json_text)
```

Write the same payload to a UTF-8 file:

```python
timings.to_json("timings.json", indent=2)
```

Each row contains integer-nanosecond statistics and counts. `to_json()` returns the serialized string even when it also
writes a file.

## Export aggregate CSV

```python
timings.to_csv("timings.csv")
```

CSV is useful for spreadsheets and aggregate analysis. For nested event relationships, use retained measurements or a
JSON Lines sink because those formats preserve IDs and parent IDs.

## Inspect measurement serialization

```python
measurement.to_dict()
measurement.to_json(indent=2)
measurement.format()
str(measurement)
```

Create a new immutable measurement with additional safe tags:

```python
tagged = measurement.with_tags(service="billing", region="eu-west")
```

The original is unchanged. Laps and statistics also support dictionary serialization:

```python
measurement.laps[0].to_dict()
timings.stats("operation").to_dict()
```

## Add a JSON Lines sink

JSON Lines appends one measurement per line and is suitable for streaming or large event files:

```python
from stopwatch import TimerRegistry
from stopwatch.sinks import JsonLinesSink

timings = TimerRegistry(
    sinks=[JsonLinesSink("timings.jsonl")],
)

with timings.watch("database.query"):
    query_database()
```

Create the parent directory before constructing a sink whose path uses one. Each line is valid JSON and can be
processed independently.

## Log structured measurements

```python
import logging
from stopwatch.sinks import LoggingSink

timings = TimerRegistry(
    sinks=[
        LoggingSink(
            logger="application.performance",
            level="INFO",
        )
    ]
)
```

The sink logs the message `duration` and attaches `measurement.to_dict()` to the record's `stopwatch` attribute. A
formatter or log handler can serialize that field. The package never changes global logging configuration.

## Print individual measurements

```python
from stopwatch.sinks import ConsoleSink

timings = TimerRegistry(sinks=[ConsoleSink()])
```

By default, output goes to standard error. Supply another text stream when needed:

```python
import sys

ConsoleSink(stream=sys.stdout)
```

## Retain events in a sink

```python
from stopwatch.sinks import InMemorySink

sink = InMemorySink()
timings = TimerRegistry(retention="none", sinks=[sink])

with timings.watch("work"):
    do_work()

print(sink.measurements)
```

`sink.measurements` returns an immutable tuple snapshot. Be aware that this sink retains every event and is therefore
unbounded.

## Use callbacks

```python
from stopwatch.sinks import CallbackSink

sink = CallbackSink(lambda measurement: local_queue.put(measurement))
timings = TimerRegistry(sinks=[sink])
```

Callbacks run after timing ends but inline with scope cleanup. Queue slow work rather than doing network I/O directly.

## Combine sinks

A registry already accepts multiple sinks:

```python
timings = TimerRegistry(
    sinks=[
        LoggingSink("performance"),
        JsonLinesSink("timings.jsonl"),
    ]
)
```

`CompositeSink` is useful when a preassembled sink must be passed as one object:

```python
from stopwatch.sinks import CompositeSink

sink = CompositeSink(
    [
        LoggingSink("performance"),
        JsonLinesSink("timings.jsonl"),
    ]
)
```

Use `NullSink` to explicitly discard records:

```python
from stopwatch.sinks import NullSink

timings.add_sink(NullSink())
```

## Implement a custom sink

A sink needs one method:

```python
from stopwatch import Measurement

class DatabaseSink:
    def __init__(self, connection):
        self.connection = connection

    def record(self, measurement: Measurement) -> None:
        self.connection.execute(
            "INSERT INTO timings (name, duration_ns, status) VALUES (?, ?, ?)",
            (
                measurement.name,
                measurement.duration.nanoseconds,
                measurement.status,
            ),
        )
```

Register it at construction or later:

```python
timings = TimerRegistry(sinks=[DatabaseSink(connection)])
timings.add_sink(DatabaseSink(other_connection))
```

## Handle sink failures

Sink failures warn by default so observability does not unexpectedly break application behavior:

```python
TimerRegistry(on_sink_error="warn")
```

Make failures strict:

```python
TimerRegistry(on_sink_error="raise")
```

Or handle exceptions programmatically:

```python
def sink_failed(error: Exception) -> None:
    fallback_logger.warning("Timing sink failed: %s", error)

TimerRegistry(on_sink_error=sink_failed)
```

The registry invokes sinks after the ending clock is read, so exporter work is not included in the measured duration.
