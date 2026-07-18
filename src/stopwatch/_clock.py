"""Clock abstractions used by stopwatch."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ._duration import DurationLike, as_duration


@runtime_checkable
class Clock(Protocol):
    """A monotonic nanosecond clock."""

    @property
    def name(self) -> str: ...

    def now_ns(self) -> int: ...


@dataclass(frozen=True, slots=True)
class SystemClock:
    name: str

    def now_ns(self) -> int:
        functions = {
            "wall": time.perf_counter_ns,
            "process": time.process_time_ns,
            "thread": time.thread_time_ns,
        }
        try:
            return functions[self.name]()
        except KeyError as error:
            raise ValueError(f"unknown clock: {self.name!r}") from error


class ManualClock:
    """A deterministic clock intended for tests and simulations."""

    def __init__(self, initial: DurationLike = 0, *, name: str = "manual") -> None:
        self._now_ns = as_duration(initial).nanoseconds
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def now_ns(self) -> int:
        return self._now_ns

    def advance(self, amount: DurationLike) -> None:
        duration = as_duration(amount)
        if duration.nanoseconds < 0:
            raise ValueError("a clock cannot advance by a negative duration")
        self._now_ns += duration.nanoseconds


def resolve_clock(clock: str | Clock) -> Clock:
    if isinstance(clock, str):
        if clock not in {"wall", "process", "thread"}:
            raise ValueError(f"unknown clock: {clock!r}")
        return SystemClock(clock)
    if not isinstance(clock, Clock):
        raise TypeError("clock must be a clock name or implement Clock")
    return clock
