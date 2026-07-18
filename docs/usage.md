# Usage

The project README contains the complete guide, from one-off scopes through registries, budgets, exports, and the
command-line interface. The API reference is generated from the package's typed public objects and docstrings.

```python
from stopwatch import TimerRegistry

timings = TimerRegistry()

with timings.watch("request"):
    with timings.watch("database"):
        load_records()

print(timings.report(view="tree"))
```
