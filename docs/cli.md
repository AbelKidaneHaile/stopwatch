# Command-line interface

Installing `advanced-stopwatch` provides a `stopwatch` executable. The same interface is available through
`python -m stopwatch`.

```bash
stopwatch --help
python -m stopwatch --help
```

## Format a duration

```bash
stopwatch format 14821243ns
```

Output:

```text
14.821 ms
```

Choose a unit and precision:

```bash
stopwatch format 14821243ns --unit ms --precision 2
# 14.82 ms
```

Choose clock or compact style:

```bash
stopwatch format "1m 28.421s" --style clock
# 00:01:28.421

stopwatch format "1m 28.4s" --style compact
# 1m28.4s
```

## Parse a duration

```bash
stopwatch parse "1m 20.5s"
```

Output is the authoritative integer number of nanoseconds:

```text
80500000000
```

This is useful in shell scripts and configuration validation.

## Time a command

Place the child command after `--`:

```bash
stopwatch run -- python import_customers.py
```

Possible output:

```text
Command:  python import_customers.py
Status:   0
Duration: 8.421 s
Started:  2026-07-19T08:23:11.482000+00:00
Ended:    2026-07-19T08:23:19.903000+00:00
```

The CLI returns the child process exit code, so failure remains visible to shell scripts and CI:

```bash
stopwatch run -- python failing_script.py
echo $?
```

This measures only total child-process wall time. Internal breakdowns require application instrumentation with
`watch()`, `timed`, or `TimerRegistry`.

## Report aggregate JSON

Create the file in Python:

```python
timings.to_json("timings.json")
```

Then display it:

```bash
stopwatch report timings.json
```

## Report JSON Lines events

Create event data with a sink:

```python
from stopwatch.sinks import JsonLinesSink

timings = TimerRegistry(sinks=[JsonLinesSink("timings.jsonl")])
```

Display it with the same report command:

```bash
stopwatch report timings.jsonl
```

The command detects a JSON array/object or line-delimited JSON automatically.

## Use the module entry point

Every example can replace `stopwatch` with `python -m stopwatch`:

```bash
python -m stopwatch parse 250ms
python -m stopwatch format 250000000ns
python -m stopwatch run -- python job.py
python -m stopwatch report timings.json
```

This is useful when multiple Python environments exist and the executable search path is ambiguous.
