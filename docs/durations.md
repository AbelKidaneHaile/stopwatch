# Durations

`Duration` is the package's immutable time value. It stores one authoritative integer number of nanoseconds and
provides readable conversions and formatting at the edges of an application.

```python
from stopwatch import Duration

duration = Duration.parse("482.7ms")
print(duration.nanoseconds)  # 482700000
print(duration)              # 482.7 ms
```

## Construct durations

Use the constructor when a value is already expressed in nanoseconds:

```python
duration = Duration(500)
duration = Duration.from_nanoseconds(500)
```

Use an explicit factory for other units:

```python
from datetime import timedelta

Duration.zero()
Duration.from_microseconds(25)
Duration.from_milliseconds(250)
Duration.from_seconds(1.5)
Duration.from_timedelta(timedelta(seconds=2))
```

## Parse configuration values

`Duration.parse()` accepts one or more number/unit components:

```python
Duration.parse("250ns")
Duration.parse("20us")
Duration.parse("20µs")
Duration.parse("14ms")
Duration.parse("1.5s")
Duration.parse("2m")
Duration.parse("1h 20m 5s")
```

Supported units are `ns`, `us`/`µs`/`μs`, `ms`, `s`, `m`, and `h`. Months and years are intentionally unsupported
because they are calendar concepts rather than fixed durations.

Invalid or partially parsed strings raise `ValueError`:

```python
Duration.parse("ten seconds")  # ValueError
Duration.parse("1s later")     # ValueError
```

## Convert units

Full property names are canonical; concise aliases are provided for common subsecond units:

```python
duration = Duration.parse("1.5s")

duration.nanoseconds   # 1500000000
duration.ns            # 1500000000
duration.microseconds  # 1500000.0
duration.us            # 1500000.0
duration.milliseconds  # 1500.0
duration.ms            # 1500.0
duration.seconds       # 1.5
duration.minutes       # 0.025
duration.hours
duration.to_timedelta()
```

Conversions return floating-point values for units that may contain fractions. `nanoseconds` remains the exact source
of truth.

## Arithmetic and comparison

```python
from datetime import timedelta

download = Duration.parse("250ms")
parse = Duration.parse("750ms")

total = download + parse
difference = parse - download
doubled = download * 2
average = total / 4
ratio = total / download

assert total == timedelta(seconds=1)
assert download < parse
assert total >= Duration.parse("900ms")
```

Dividing by a number returns a `Duration`. Dividing by another `Duration` returns a unitless `float` ratio.

## Format durations

Automatic formatting chooses a readable unit:

```python
str(Duration(721))                  # "721 ns"
str(Duration.parse("14.8us"))      # "14.8 µs"
str(Duration.parse("8.31ms"))      # "8.31 ms"
str(Duration.parse("1.42s"))       # "1.42 s"
str(Duration.parse("2m 18s"))      # "2m18s"
```

Choose a fixed unit and precision for tables or protocols:

```python
duration = Duration.parse("482.731ms")

duration.format(unit="ms")                # "482.731 ms"
duration.format(unit="ms", precision=2)   # "482.73 ms"
duration.format(unit="s", precision=3)    # "0.483 s"
```

Use clock style for elapsed-time displays:

```python
Duration.parse("1m 28.421s").format(style="clock")
# "00:01:28.421"
```

Use compact style for dashboards and logs:

```python
Duration.parse("1h 2m 3.4s").format(style="compact")
# "1h2m3.4s"
```

## Use durations in structured output

Store integer nanoseconds when persisting data:

```python
payload = {
    "duration_ns": duration.nanoseconds,
    "duration_display": str(duration),
}
```

The integer supports exact comparisons and future reformatting. The display string is for humans only.
