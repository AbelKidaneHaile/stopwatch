# Contexts and decorators

Use scopes and decorators when timing should begin and end automatically. All paths use the same `Stopwatch` and
`Measurement` implementation, so lifecycle and error behavior stay consistent.

## Time a synchronous block

```python
from stopwatch import watch

with watch("database.query") as timing:
    rows = database.query("SELECT ...")

result = timing.result
print(result.duration)
```

The scope starts on entry and stops on exit. Pass `show=True` for a one-line result on standard error:

```python
with watch("cache warmup", show=True):
    warm_cache()
```

## Receive the finished measurement

Callbacks run after the ending clock is read, so callback time is not included:

```python
def report_slow_operation(measurement):
    if measurement.duration.milliseconds > 500:
        local_queue.put(measurement.to_dict())

with watch("invoice generation", on_result=report_slow_operation):
    generate_invoice()
```

Keep callbacks lightweight. Queue remote or blocking work rather than performing network I/O directly.

## Handle exceptions safely

Measurements are produced on failure without suppressing or replacing the original exception:

```python
try:
    with watch("send invoice") as timing:
        send_invoice()
except ConnectionError:
    retry_later()

print(timing.result.status)      # "error"
print(timing.result.error_type)  # "ConnectionError"
```

Exception messages are not captured because they may contain credentials, SQL, paths, or personal data.

## Time an async block

```python
async with watch("fetch customers") as timing:
    customers = await fetch_customers()

print(timing.result.duration)
```

A normal `with` also works inside an async function, but `async with` makes intent explicit. If the task is cancelled,
the result uses `status="cancelled"` and the cancellation is re-raised.

## Decorate a synchronous function

```python
from stopwatch import timed

@timed("image.resize")
def resize_image(image, width: int, height: int):
    return image.resize((width, height))
```

Without parentheses, the stable module and qualified function name becomes the timer name:

```python
@timed
def calculate_total(invoice):
    return invoice.calculate_total()
```

The wrapper uses `functools.wraps`, preserving the function name, module, docstring, annotations, signature, and
`__wrapped__` reference.

## Decorate an async function

```python
@timed("http.fetch_customer")
async def fetch_customer(customer_id: str):
    response = await client.get(f"/customers/{customer_id}")
    return response.json()
```

The awaited coroutine is timed—not merely creation of the coroutine object.

## Decorate generators

Generator work occurs during iteration, so the decorator keeps the timing scope open until exhaustion, closure, or an
exception:

```python
@timed("database.rows", generator_mode="lifetime")
def rows():
    yield from database_rows()

generator = rows()  # no work has been timed yet
for row in generator:
    process(row)
```

Lifetime mode measures the complete iteration lifetime, including time while the generator is suspended at a `yield`.
This is useful for end-to-end streaming latency. Use a manually controlled `Stopwatch` inside the generator if only
individual production steps should count.

Async generators are handled the same way:

```python
@timed("events.stream", generator_mode="lifetime")
async def events():
    async for event in broker.events():
        yield event
```

## Add tags and budgets to decorators

```python
@timed(
    "invoice.calculate",
    tags={"service": "billing", "version": 2},
    budget="100ms",
    on_exceed="warn",
)
def calculate_invoice(invoice):
    return invoice.calculate()
```

Decorator tags are static. For per-call tags, create a registry scope inside the function or use separate named
operations. Function arguments are intentionally not captured automatically.

## Collect decorator results in a registry

Use `registry.timed()` when results need to be queried or reported:

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

@timings.timed("image.resize")
def resize_image(image, width, height):
    return image.resize((width, height))

for image in images:
    resize_image(image, 512, 512)

print(timings.stats("image.resize").mean)
```

See [Registries and statistics](registries.md) for retention, reports, filtering, and concurrency.

## Visible versus silent instrumentation

Instrumentation is silent by default. This is appropriate for libraries and production applications. Choose output
explicitly:

```python
with watch("operation", show=True):
    run_operation()
```

For repeated or structured output, prefer a registry sink rather than `show=True`.
