# API reference

The public API is exported from `stopwatch`. Implementation modules beginning with `_` are private and may change
without notice.

## Convenience APIs

### watch

::: stopwatch.watch
    options:
      show_root_heading: true
      show_source: false

### timed

::: stopwatch.timed
    options:
      show_root_heading: true
      show_source: false

### configure

::: stopwatch.configure
    options:
      show_root_heading: true
      show_source: false

## Values and results

### Duration

::: stopwatch.Duration
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### Lap

::: stopwatch.Lap
    options:
      show_root_heading: true
      show_source: false

### Measurement

::: stopwatch.Measurement
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### TimerStats

::: stopwatch.TimerStats
    options:
      show_root_heading: true
      show_source: false

## Timing lifecycle

### Stopwatch

::: stopwatch.Stopwatch
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### StopwatchState

::: stopwatch.StopwatchState
    options:
      show_root_heading: true
      show_source: false

## Collection

### TimerRegistry

::: stopwatch.TimerRegistry
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### MeasurementSink

::: stopwatch.MeasurementSink
    options:
      show_root_heading: true
      show_source: false

## Clocks

### Clock

::: stopwatch.Clock
    options:
      show_root_heading: true
      show_source: false

### SystemClock

::: stopwatch.SystemClock
    options:
      show_root_heading: true
      show_source: false

### ManualClock

::: stopwatch.ManualClock
    options:
      show_root_heading: true
      show_source: false
      members_order: source

## Exceptions

### StopwatchError

::: stopwatch.StopwatchError
    options:
      show_root_heading: true
      show_source: false

### InvalidStopwatchState

::: stopwatch.InvalidStopwatchState
    options:
      show_root_heading: true
      show_source: false

### DurationBudgetExceeded

::: stopwatch.DurationBudgetExceeded
    options:
      show_root_heading: true
      show_source: false

## Built-in sinks

### NullSink

::: stopwatch.sinks.NullSink
    options:
      show_root_heading: true
      show_source: false

### InMemorySink

::: stopwatch.sinks.InMemorySink
    options:
      show_root_heading: true
      show_source: false

### CallbackSink

::: stopwatch.sinks.CallbackSink
    options:
      show_root_heading: true
      show_source: false

### ConsoleSink

::: stopwatch.sinks.ConsoleSink
    options:
      show_root_heading: true
      show_source: false

### LoggingSink

::: stopwatch.sinks.LoggingSink
    options:
      show_root_heading: true
      show_source: false

### JsonLinesSink

::: stopwatch.sinks.JsonLinesSink
    options:
      show_root_heading: true
      show_source: false

### CompositeSink

::: stopwatch.sinks.CompositeSink
    options:
      show_root_heading: true
      show_source: false
