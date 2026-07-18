"""Stopwatch lifecycle implementation."""

from __future__ import annotations

import asyncio
import logging
import sys
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, Self
from uuid import uuid4

from ._clock import Clock, SystemClock, resolve_clock
from ._duration import Duration, DurationLike, as_duration
from ._exceptions import DurationBudgetExceeded, InvalidStopwatchState
from ._models import JsonScalar, Lap, Measurement, immutable_tags

BudgetAction = Literal["record", "warn", "log", "raise"] | Callable[[Measurement], None]


class StopwatchState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class Stopwatch:
    """A strict, reusable stopwatch with pauses, laps, budgets, and immutable results."""

    def __init__(
        self,
        name: str | None = None,
        *,
        clock: str | Clock = "wall",
        clocks: tuple[str | Clock, ...] | None = None,
        tags: dict[str, JsonScalar] | None = None,
        budget: DurationLike | None = None,
        on_exceed: BudgetAction = "record",
        on_result: Callable[[Measurement], None] | None = None,
        show: bool = False,
        parent_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        if not isinstance(name, (str, type(None))):
            raise TypeError("name must be a string or None")
        requested = clocks or (clock,)
        resolved = tuple(resolve_clock(item) for item in requested)
        if not resolved:
            raise ValueError("at least one clock is required")
        names = [item.name for item in resolved]
        if len(set(names)) != len(names):
            raise ValueError("clock names must be unique")
        if not callable(on_exceed) and on_exceed not in {"record", "warn", "log", "raise"}:
            raise ValueError("invalid on_exceed policy")

        self.name = name
        self.id = uuid4().hex
        self.trace_id = trace_id or self.id
        self.parent_id = parent_id
        self.tags = immutable_tags(tags)
        self._clocks = resolved
        self._primary = resolved[0]
        self._span_clock: Clock = self._primary if not isinstance(self._primary, SystemClock) else SystemClock("wall")
        self._budget = as_duration(budget) if budget is not None else None
        self._on_exceed = on_exceed
        self._on_result = on_result
        self._show = show
        self._state = StopwatchState.IDLE
        self._started: dict[str, int] = {}
        self._last_resumed: dict[str, int] = {}
        self._active: dict[str, int] = {}
        self._pause_started: dict[str, int] = {}
        self._paused: dict[str, int] = {}
        self._span_started_ns = 0
        self._last_lap_ns = 0
        self._laps: list[Lap] = []
        self._started_at: datetime | None = None
        self._result: Measurement | None = None

    @property
    def state(self) -> StopwatchState:
        return self._state

    @property
    def result(self) -> Measurement | None:
        return self._result

    @property
    def elapsed(self) -> Duration:
        if self._state is StopwatchState.IDLE:
            return Duration.zero()
        if self._state is StopwatchState.STOPPED:
            assert self._result is not None
            return self._result.duration
        value = self._active[self._primary.name]
        if self._state is StopwatchState.RUNNING:
            value += self._primary.now_ns() - self._last_resumed[self._primary.name]
        return Duration(value)

    @property
    def laps(self) -> tuple[Lap, ...]:
        return tuple(self._laps)

    @property
    def last_lap(self) -> Lap | None:
        return self._laps[-1] if self._laps else None

    def find_laps(self, name: str) -> tuple[Lap, ...]:
        return tuple(lap for lap in self._laps if lap.name == name)

    def start(self) -> Self:
        if self._state is not StopwatchState.IDLE:
            raise InvalidStopwatchState(f"cannot start a stopwatch in state {self._state.value!r}")
        readings = self._read_clocks()
        self._started = readings.copy()
        self._last_resumed = readings.copy()
        self._active = dict.fromkeys(readings, 0)
        self._paused = dict.fromkeys(readings, 0)
        self._span_started_ns = self._span_clock.now_ns()
        self._last_lap_ns = 0
        self._started_at = datetime.now(UTC)
        self._state = StopwatchState.RUNNING
        return self

    def pause(self) -> Self:
        if self._state is not StopwatchState.RUNNING:
            raise InvalidStopwatchState("pause() requires a running stopwatch")
        readings = self._read_clocks()
        for name, now in readings.items():
            self._active[name] += now - self._last_resumed[name]
        self._pause_started = readings
        self._state = StopwatchState.PAUSED
        return self

    def resume(self) -> Self:
        if self._state is not StopwatchState.PAUSED:
            raise InvalidStopwatchState("resume() requires a paused stopwatch")
        readings = self._read_clocks()
        for name, now in readings.items():
            self._paused[name] += now - self._pause_started[name]
        self._last_resumed = readings
        self._state = StopwatchState.RUNNING
        return self

    @contextmanager
    def paused(self) -> Iterator[Self]:
        self.pause()
        try:
            yield self
        finally:
            if self._state is StopwatchState.PAUSED:
                self.resume()

    def lap(self, name: str | None = None, *, tags: dict[str, JsonScalar] | None = None) -> Lap:
        if self._state is not StopwatchState.RUNNING:
            raise InvalidStopwatchState("lap() requires a running stopwatch")
        split = self.elapsed
        lap = Lap(
            index=len(self._laps) + 1,
            name=name,
            duration=Duration(split.nanoseconds - self._last_lap_ns),
            split=split,
            recorded_at=datetime.now(UTC),
            tags=immutable_tags(tags),
        )
        self._laps.append(lap)
        self._last_lap_ns = split.nanoseconds
        return lap

    def stop(
        self,
        *,
        status: str = "ok",
        error_type: str | None = None,
        _application_error: bool = False,
    ) -> Measurement:
        if self._state is StopwatchState.STOPPED:
            assert self._result is not None
            return self._result
        if self._state is StopwatchState.IDLE:
            raise InvalidStopwatchState("cannot stop an idle stopwatch")

        readings = self._read_clocks()
        if self._state is StopwatchState.RUNNING:
            for name, now in readings.items():
                self._active[name] += now - self._last_resumed[name]
        else:
            for name, now in readings.items():
                self._paused[name] += now - self._pause_started[name]
        span_ended_ns = self._span_clock.now_ns()
        ended_at = datetime.now(UTC)
        self._state = StopwatchState.STOPPED

        duration = Duration(self._active[self._primary.name])
        budget_exceeded = self._budget is not None and duration > self._budget
        if budget_exceeded and status == "ok":
            status = "budget_exceeded"
        clock_values = MappingProxyType({name: Duration(value) for name, value in self._active.items()})
        self._result = Measurement(
            id=self.id,
            name=self.name,
            duration=duration,
            wall_duration=Duration(span_ended_ns - self._span_started_ns),
            paused_duration=Duration(self._paused[self._primary.name]),
            started_at=self._started_at,
            ended_at=ended_at,
            status=status,
            error_type=error_type,
            laps=tuple(self._laps),
            tags=self.tags,
            parent_id=self.parent_id,
            trace_id=self.trace_id,
            clock_name=self._primary.name,
            clocks=clock_values,
            budget=self._budget,
            budget_exceeded=budget_exceeded,
        )
        if self._on_result is not None:
            self._on_result(self._result)
        if self._show:
            print(self._result, file=sys.stderr)
        if budget_exceeded:
            self._handle_budget(self._result, allow_raise=not _application_error)
        return self._result

    def reset(self, *, force: bool = False) -> Self:
        if self._state in {StopwatchState.RUNNING, StopwatchState.PAUSED} and not force:
            raise InvalidStopwatchState("resetting an active stopwatch requires force=True")
        self._state = StopwatchState.IDLE
        self._started.clear()
        self._last_resumed.clear()
        self._active.clear()
        self._pause_started.clear()
        self._paused.clear()
        self._laps.clear()
        self._result = None
        self._started_at = None
        self.id = uuid4().hex
        if self.parent_id is None:
            self.trace_id = self.id
        return self

    def restart(self) -> Self:
        return self.reset(force=True).start()

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object) -> bool:
        status = "ok"
        error_type = None
        if exc_type is not None:
            status = "cancelled" if issubclass(exc_type, asyncio.CancelledError) else "error"
            error_type = exc_type.__name__
        self.stop(status=status, error_type=error_type, _application_error=exc_type is not None)
        return False

    async def __aenter__(self) -> Self:
        return self.__enter__()

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object
    ) -> bool:
        return self.__exit__(exc_type, exc, traceback)

    def _read_clocks(self) -> dict[str, int]:
        return {clock.name: clock.now_ns() for clock in self._clocks}

    def _handle_budget(self, measurement: Measurement, *, allow_raise: bool) -> None:
        assert measurement.budget is not None
        error = DurationBudgetExceeded(measurement.name, measurement.duration, measurement.budget)
        if not isinstance(self._on_exceed, str):
            self._on_exceed(measurement)
        elif self._on_exceed == "warn" or (self._on_exceed == "raise" and not allow_raise):
            warnings.warn(str(error), RuntimeWarning, stacklevel=3)
        elif self._on_exceed == "log":
            logging.getLogger("stopwatch").warning("%s", error)
        elif self._on_exceed == "raise":
            raise error
