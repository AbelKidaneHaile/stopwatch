# stopwatch

**Precise, structured timing for Python—from one block of code to application-wide performance instrumentation.**

`stopwatch` is a zero-dependency toolkit for measuring operations you deliberately name. It combines a strict manual
stopwatch with immutable duration values, laps and pauses, sync and async instrumentation, decorators, nested
registries, bounded statistics, performance budgets, structured exports, and a command-line interface.

```python
from stopwatch import watch

with watch("load customers") as timing:
    customers = load_customers()

print(timing.result)
# load customers: 482.7 ms
```

## Why use stopwatch?

Use `stopwatch` when you want to answer questions such as:

- How long did this named operation take?
- Which stage of this pipeline is slow?
- How often does this database call run, and what is its P95 latency?
- Did an operation exceed its performance budget?
- How much wall time and CPU time did a task consume?
- How can timing data be logged or exported without changing application code?

It is deliberately different from two related tools:

| Tool | Best use |
| --- | --- |
| `timeit` | Repeated, controlled microbenchmarks of small snippets |
| Profiler | Discovering unknown hotspots across a program |
| `stopwatch` | Explicitly named operations in scripts, services, pipelines, tests, and applications |

## Start here

1. [Install `advanced-stopwatch`](installation.md). The distribution name differs from the import name.
2. Follow the [quick start](usage.md) for one-off, manual, decorated, and aggregated timings.
3. Use the focused guides for production patterns and complete examples.

## User guide

- [Durations](durations.md): parsing, conversion, arithmetic, comparison, and formatting.
- [Manual stopwatch](manual-stopwatch.md): lifecycle, live elapsed time, pauses, laps, clocks, and errors.
- [Contexts and decorators](instrumentation.md): sync, async, functions, generators, exceptions, and callbacks.
- [Registries and statistics](registries.md): repeated timings, nesting, retention, filtering, and reports.
- [Budgets](budgets.md): record, warn, log, raise, and callback policies.
- [Sinks and exports](sinks-and-exports.md): logging, JSON Lines, CSV, callbacks, and custom sinks.
- [Testing and configuration](testing-and-configuration.md): deterministic clocks, sampling, tags, and disabling.
- [Command-line interface](cli.md): parse, format, time commands, and report exports.
- [Practical recipes](recipes.md): complete examples for scripts, pipelines, databases, web services, and workers.
- [API reference](api.md): generated reference for every public object.

## Design guarantees

- Elapsed durations use monotonic integer-nanosecond clocks.
- Results and tags are immutable once a measurement finishes.
- Context managers never suppress application exceptions.
- Exception messages, arguments, return values, and local variables are not captured.
- Core runtime functionality has no third-party dependencies.
- Registry retention is bounded by default.
- Importing the package starts no threads, processes, or network connections.
