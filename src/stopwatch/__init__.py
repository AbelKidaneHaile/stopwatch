"""Precise, structured timing for Python applications."""

from ._api import timed, watch
from ._clock import Clock, ManualClock, SystemClock
from ._config import configure
from ._duration import Duration
from ._exceptions import DurationBudgetExceeded, InvalidStopwatchState, StopwatchError
from ._models import Lap, Measurement, TimerStats
from ._registry import MeasurementSink, TimerRegistry
from ._stopwatch import Stopwatch, StopwatchState

__all__ = [
    "Clock",
    "Duration",
    "DurationBudgetExceeded",
    "InvalidStopwatchState",
    "Lap",
    "ManualClock",
    "Measurement",
    "MeasurementSink",
    "Stopwatch",
    "StopwatchError",
    "StopwatchState",
    "SystemClock",
    "TimerRegistry",
    "TimerStats",
    "configure",
    "timed",
    "watch",
]

__version__ = "0.1.0"
