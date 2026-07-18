# Testing and configuration

The package supports deterministic clocks, process-wide registry controls, sampling, and conservative metadata
defaults for production instrumentation.

## Test without sleeping

Do not use `time.sleep()` in stopwatch tests. `ManualClock` advances instantly and deterministically:

```python
from stopwatch import Duration, ManualClock, Stopwatch

clock = ManualClock()
timer = Stopwatch("test", clock=clock).start()

clock.advance("25ms")
timer.lap("first")

clock.advance("75ms")
result = timer.stop()

assert result.duration == Duration.parse("100ms")
assert result.laps[0].duration == Duration.parse("25ms")
```

## Test pause behavior

```python
clock = ManualClock()
timer = Stopwatch("paused test", clock=clock).start()

clock.advance("10ms")
timer.pause()
clock.advance("40ms")
timer.resume()
clock.advance("20ms")

result = timer.stop()

assert result.duration == Duration.parse("30ms")
assert result.paused_duration == Duration.parse("40ms")
assert result.wall_duration == Duration.parse("70ms")
```

## Start a manual clock at a nonzero value

```python
clock = ManualClock("10s", name="test-clock")
assert clock.name == "test-clock"
assert clock.now_ns() == Duration.parse("10s").nanoseconds
```

Advancing by a negative duration raises `ValueError`.

## Implement a custom clock

Any object satisfying the public `Clock` protocol can be injected:

```python
class HardwareClock:
    @property
    def name(self) -> str:
        return "hardware"

    def now_ns(self) -> int:
        return read_hardware_counter_ns()

timer = Stopwatch("device operation", clock=HardwareClock())
```

Clocks must be monotonic and return integer nanoseconds. Clock names must be unique when measuring multiple clocks.

Built-in named clocks can also be instantiated directly:

```python
from stopwatch import SystemClock

SystemClock("wall").now_ns()
SystemClock("process").now_ns()
SystemClock("thread").now_ns()
```

## Disable registry instrumentation

Disable collection at runtime:

```python
from stopwatch import configure

configure(enabled=False)
```

Re-enable it later:

```python
configure(enabled=True)
```

Or configure before import with an environment variable:

```bash
STOPWATCH_ENABLED=0 python application.py
```

Values `0`, `false`, `no`, and `off` disable collection, case-insensitively.

The global switch affects `TimerRegistry` scopes and registry-backed decorators. An explicitly constructed `Stopwatch`
or standalone `watch()` remains active so direct manual measurements do not silently disappear.

## Sample high-volume instrumentation

Set a registry-wide rate:

```python
timings = TimerRegistry(sample_rate=0.01)
```

Override it for one scope or decorator:

```python
with timings.watch("request", sample_rate=0.1):
    handle_request()

@timings.timed("worker.task", sample_rate=0.05)
def process_task(task):
    return process(task)
```

Rates range from `0.0` (record nothing) to `1.0` (record everything). Invalid rates raise `ValueError`.

Use a sample key for a repeatable decision within a process:

```python
with timings.watch("request", sample_rate=0.1, sample_key=request_id):
    handle_request()
```

Python hash randomization means the same key is not guaranteed to produce the same choice in a different process.

## Select a detail level

Scopes accept `detail="minimal"`, `"standard"`, or `"full"`:

```python
with timings.watch("operation", detail="standard"):
    run_operation()
```

Version 0.1 validates these values and currently records the standard structured measurement for all three. The
levels reserve a stable API for future capture-cost controls without changing instrumentation call sites.

## Use privacy-safe tags

Safe tags are small, low-cardinality JSON scalars:

```python
tags = {
    "method": "GET",
    "route": "/customers/{customer_id}",
    "service": "billing",
    "cached": True,
}
```

Do not automatically attach:

- Function arguments or return values
- Exception messages
- SQL statements
- Full URLs or file paths
- Authorization headers
- User or customer identifiers
- Stack traces, locals, or environment variables

The package captures none of these by default.

## Test exception measurements

```python
import pytest

timer = Stopwatch("failure", clock=ManualClock())

with pytest.raises(ValueError):
    with timer:
        raise ValueError("sensitive message")

assert timer.result.status == "error"
assert timer.result.error_type == "ValueError"
assert "sensitive message" not in timer.result.to_json()
```

## Test budgets carefully

```python
from stopwatch import DurationBudgetExceeded

clock = ManualClock()

with pytest.raises(DurationBudgetExceeded):
    with Stopwatch(
        "budgeted",
        clock=clock,
        budget="50ms",
        on_exceed="raise",
    ):
        clock.advance("51ms")
```

Injected clocks make budget tests exact. Real-clock performance tests remain environment-dependent and should use
generous limits or dedicated benchmark infrastructure.
