# Installation

## Install from PyPI

The **PyPI distribution** is named `advanced-stopwatch`:

=== "pip"

    ```bash
    python -m pip install advanced-stopwatch
    ```

=== "uv"

    ```bash
    uv add advanced-stopwatch
    ```

=== "Poetry"

    ```bash
    poetry add advanced-stopwatch
    ```

Python 3.12 or later is required. The runtime has no third-party dependencies.

## Distribution name versus import name

Only the installation name contains `advanced-`. Application code always imports `stopwatch`, and the installed CLI
command is also `stopwatch`:

```python
from stopwatch import Duration, Stopwatch, TimerRegistry, timed, watch
```

```bash
stopwatch --help
```

This split exists because the `stopwatch` project name was already occupied on PyPI:

| Context | Name |
| --- | --- |
| PyPI page | `advanced-stopwatch` |
| `pip`/`uv` dependency | `advanced-stopwatch` |
| Python import | `stopwatch` |
| CLI executable | `stopwatch` |
| GitHub repository | `stopwatch` |

## Verify the installation

```bash
python -c "import stopwatch; print(stopwatch.__version__)"
stopwatch format 1500000ns
```

Expected output:

```text
0.1.0
1.5 ms
```

## Install from source

Clone the repository and synchronize its development environment:

```bash
git clone https://github.com/AbelKidaneHaile/stopwatch.git
cd stopwatch
uv sync
```

Run the test suite:

```bash
uv run pytest
```

To install the checkout into another environment:

```bash
python -m pip install .
```

The source build still creates an `advanced-stopwatch` distribution containing the `stopwatch` import package.

## Upgrade or uninstall

```bash
python -m pip install --upgrade advanced-stopwatch
python -m pip uninstall advanced-stopwatch
```

With uv:

```bash
uv lock --upgrade-package advanced-stopwatch
uv remove advanced-stopwatch
```
