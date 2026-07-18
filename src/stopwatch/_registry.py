"""Thread-safe collection, aggregation, reporting, and decorators."""

from __future__ import annotations

import csv
import inspect
import json
import math
import random
import warnings
from collections import deque
from collections.abc import AsyncGenerator, Callable, Generator, Iterable, Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any, Literal, ParamSpec, Protocol, TypeVar, overload

from ._clock import Clock
from ._config import is_enabled
from ._duration import Duration, DurationLike
from ._models import JsonScalar, Measurement, TimerStats
from ._stopwatch import BudgetAction, Stopwatch

P = ParamSpec("P")
R = TypeVar("R")
Retention = Literal["none", "all"] | int


class MeasurementSink(Protocol):
    def record(self, measurement: Measurement) -> None: ...


_active_stopwatch: ContextVar[Stopwatch | None] = ContextVar("stopwatch_active", default=None)


@dataclass(slots=True)
class _Accumulator:
    count: int = 0
    successes: int = 0
    errors: int = 0
    total_ns: int = 0
    minimum_ns: int = 0
    maximum_ns: int = 0
    mean_ns: float = 0.0
    m2: float = 0.0
    last_ns: int = 0

    def add(self, measurement: Measurement) -> None:
        value = measurement.duration.nanoseconds
        self.count += 1
        self.successes += measurement.status in {"ok", "budget_exceeded"}
        self.errors += measurement.status in {"error", "cancelled"}
        self.total_ns += value
        self.minimum_ns = value if self.count == 1 else min(self.minimum_ns, value)
        self.maximum_ns = value if self.count == 1 else max(self.maximum_ns, value)
        delta = value - self.mean_ns
        self.mean_ns += delta / self.count
        self.m2 += delta * (value - self.mean_ns)
        self.last_ns = value


class _RegistryScope:
    def __init__(self, stopwatch: Stopwatch, *, sampled: bool = True) -> None:
        self.stopwatch = stopwatch
        self.sampled = sampled
        self._token: Token[Stopwatch | None] | None = None

    def __getattr__(self, name: str) -> object:
        return getattr(self.stopwatch, name)

    def __enter__(self) -> Stopwatch:
        timer = self.stopwatch.__enter__()
        if self.sampled:
            self._token = _active_stopwatch.set(timer)
        return timer

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object) -> bool:
        try:
            return self.stopwatch.__exit__(exc_type, exc, traceback)
        finally:
            if self._token is not None:
                _active_stopwatch.reset(self._token)

    async def __aenter__(self) -> Stopwatch:
        return self.__enter__()

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object
    ) -> bool:
        return self.__exit__(exc_type, exc, traceback)


class TimerRegistry:
    """A thread-safe, bounded collector of named timing measurements."""

    def __init__(
        self,
        *,
        retention: Retention = 2048,
        sinks: Iterable[MeasurementSink] = (),
        on_sink_error: Literal["warn", "raise"] | Callable[[Exception], None] = "warn",
        sample_rate: float = 1.0,
        allowed_tag_keys: set[str] | None = None,
    ) -> None:
        if retention not in {"none", "all"} and (isinstance(retention, bool) or not isinstance(retention, int)):
            raise TypeError("retention must be 'none', 'all', or an integer")
        if isinstance(retention, int) and retention < 0:
            raise ValueError("retention must be non-negative")
        if not 0 <= sample_rate <= 1:
            raise ValueError("sample_rate must be between 0 and 1")
        self.retention = retention
        self.sample_rate = sample_rate
        self.allowed_tag_keys = frozenset(allowed_tag_keys) if allowed_tag_keys is not None else None
        self._sinks = list(sinks)
        self._on_sink_error = on_sink_error
        self._lock = RLock()
        self._aggregates: dict[str, _Accumulator] = {}
        self._measurements: deque[Measurement] | list[Measurement]
        self._measurements = [] if retention == "all" else deque(maxlen=retention if isinstance(retention, int) else 0)

    def watch(
        self,
        name: str | None = None,
        *,
        tags: dict[str, JsonScalar] | None = None,
        clock: str | Clock = "wall",
        clocks: tuple[str | Clock, ...] | None = None,
        budget: DurationLike | None = None,
        on_exceed: BudgetAction = "record",
        sample_rate: float | None = None,
        sample_key: object | None = None,
        show: bool = False,
        detail: Literal["minimal", "standard", "full"] = "standard",
    ) -> _RegistryScope:
        if detail not in {"minimal", "standard", "full"}:
            raise ValueError("detail must be 'minimal', 'standard', or 'full'")
        selected_tags = dict(tags or {})
        if self.allowed_tag_keys is not None:
            unexpected = set(selected_tags) - self.allowed_tag_keys
            if unexpected:
                raise ValueError(f"tag keys are not allowed: {sorted(unexpected)!r}")
        rate = self.sample_rate if sample_rate is None else sample_rate
        if not 0 <= rate <= 1:
            raise ValueError("sample_rate must be between 0 and 1")
        sampled = is_enabled() and self._sample(rate, sample_key)
        parent = _active_stopwatch.get() if sampled else None
        timer = Stopwatch(
            name,
            clock=clock,
            clocks=clocks,
            tags=selected_tags,
            budget=budget,
            on_exceed=on_exceed,
            on_result=self.record if sampled else None,
            show=show,
            parent_id=parent.id if parent else None,
            trace_id=parent.trace_id if parent else None,
        )
        return _RegistryScope(timer, sampled=sampled)

    @overload
    def timed(self, function: Callable[P, R], /) -> Callable[P, R]: ...

    @overload
    def timed(
        self,
        name: str | None = None,
        *,
        tags: Mapping[str, JsonScalar] | None = None,
        budget: DurationLike | None = None,
        on_exceed: BudgetAction = "record",
        sample_rate: float | None = None,
        generator_mode: Literal["lifetime", "iteration"] = "lifetime",
    ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def timed(
        self,
        name: str | Callable[..., Any] | None = None,
        *,
        tags: Mapping[str, JsonScalar] | None = None,
        budget: DurationLike | None = None,
        on_exceed: BudgetAction = "record",
        sample_rate: float | None = None,
        generator_mode: Literal["lifetime", "iteration"] = "lifetime",
    ) -> Any:
        if generator_mode not in {"lifetime", "iteration"}:
            raise ValueError("generator_mode must be 'lifetime' or 'iteration'")

        def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
            qualified_name = getattr(function, "__qualname__", function.__class__.__qualname__)
            timer_name = name if isinstance(name, str) else f"{function.__module__}.{qualified_name}"
            timer_tags = dict(tags or {})
            if inspect.isasyncgenfunction(function):

                @wraps(function)
                async def async_generator(*args: P.args, **kwargs: P.kwargs) -> AsyncGenerator[Any, None]:
                    with self.watch(
                        timer_name, tags=timer_tags, budget=budget, on_exceed=on_exceed, sample_rate=sample_rate
                    ):
                        async for item in function(*args, **kwargs):
                            yield item

                return async_generator
            if inspect.iscoroutinefunction(function):

                @wraps(function)
                async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                    with self.watch(
                        timer_name, tags=timer_tags, budget=budget, on_exceed=on_exceed, sample_rate=sample_rate
                    ):
                        return await function(*args, **kwargs)

                return async_wrapper
            if inspect.isgeneratorfunction(function):

                @wraps(function)
                def generator(*args: P.args, **kwargs: P.kwargs) -> Generator[Any, None, None]:
                    with self.watch(
                        timer_name, tags=timer_tags, budget=budget, on_exceed=on_exceed, sample_rate=sample_rate
                    ):
                        yield from function(*args, **kwargs)

                return generator

            @wraps(function)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with self.watch(
                    timer_name, tags=timer_tags, budget=budget, on_exceed=on_exceed, sample_rate=sample_rate
                ):
                    return function(*args, **kwargs)

            return wrapper

        if not isinstance(name, (str, type(None))):
            function = name
            name = None
            return decorate(function)
        return decorate

    def record(self, measurement: Measurement) -> None:
        name = measurement.name or "unnamed"
        with self._lock:
            accumulator = self._aggregates.setdefault(name, _Accumulator())
            accumulator.add(measurement)
            if self.retention != "none" and self.retention != 0:
                self._measurements.append(measurement)
        for sink in tuple(self._sinks):
            try:
                sink.record(measurement)
            except Exception as error:  # sink boundaries must not fail silently
                self._handle_sink_error(error)

    def add_sink(self, sink: MeasurementSink) -> None:
        with self._lock:
            self._sinks.append(sink)

    @property
    def measurements(self) -> tuple[Measurement, ...]:
        with self._lock:
            return tuple(self._measurements)

    @overload
    def stats(self, name: str) -> TimerStats: ...

    @overload
    def stats(self, name: None = None) -> dict[str, TimerStats]: ...

    def stats(self, name: str | None = None) -> TimerStats | dict[str, TimerStats]:
        with self._lock:
            if name is not None:
                try:
                    return self._make_stats(name, self._aggregates[name])
                except KeyError as error:
                    raise KeyError(f"no measurements named {name!r}") from error
            return {key: self._make_stats(key, value) for key, value in sorted(self._aggregates.items())}

    def snapshot(self) -> tuple[TimerStats, ...]:
        values = self.stats()
        assert isinstance(values, dict)
        return tuple(values.values())

    def clear(self) -> None:
        with self._lock:
            self._aggregates.clear()
            self._measurements.clear()

    def reset(self, name: str) -> None:
        with self._lock:
            self._aggregates.pop(name, None)
            retained = [item for item in self._measurements if item.name != name]
            self._measurements.clear()
            self._measurements.extend(retained)

    def merge(self, other: TimerRegistry | Iterable[Measurement]) -> None:
        values = other.measurements if isinstance(other, TimerRegistry) else other
        for measurement in values:
            self.record(measurement)

    def filter(
        self, *, prefix: str | None = None, tags: Mapping[str, JsonScalar] | None = None
    ) -> tuple[Measurement, ...]:
        requested = dict(tags or {})
        return tuple(
            item
            for item in self.measurements
            if (prefix is None or (item.name or "").startswith(prefix))
            and all(item.tags.get(key) == value for key, value in requested.items())
        )

    def report(self, *, sort_by: str = "total", view: Literal["table", "tree", "timeline"] = "table") -> str:
        if view not in {"table", "tree", "timeline"}:
            raise ValueError("view must be 'table', 'tree', or 'timeline'")
        if view in {"tree", "timeline"}:
            return self._tree_report(timeline=view == "timeline")
        values = list(self.snapshot())
        keys: dict[str, Callable[[TimerStats], str | int]] = {
            "name": lambda item: item.name,
            "count": lambda item: item.count,
            "total": lambda item: item.total.nanoseconds,
            "mean": lambda item: item.mean.nanoseconds,
            "p95": lambda item: item.p95.nanoseconds if item.p95 else -1,
            "max": lambda item: item.maximum.nanoseconds,
            "errors": lambda item: item.error_count,
        }
        if sort_by not in keys:
            raise ValueError(f"unsupported sort column: {sort_by!r}")
        values.sort(key=keys[sort_by], reverse=sort_by != "name")
        header = f"{'Timer':32} {'Calls':>7} {'Total':>12} {'Mean':>12} {'P95':>12} {'Max':>12} {'Errors':>7}"
        rows = [header, "-" * len(header)]
        for item in values:
            p95 = str(item.p95) if item.p95 else "n/a"
            rows.append(
                f"{item.name[:32]:32} {item.count:7d} {str(item.total):>12} {str(item.mean):>12} "
                f"{p95:>12} {str(item.maximum):>12} {item.error_count:7d}"
            )
        return "\n".join(rows)

    def to_json(self, path: str | Path | None = None, *, indent: int | None = 2) -> str:
        payload = json.dumps([item.to_dict() for item in self.snapshot()], indent=indent, sort_keys=True)
        if path is not None:
            Path(path).write_text(payload + "\n", encoding="utf-8")
        return payload

    def to_csv(self, path: str | Path) -> None:
        rows = [item.to_dict() for item in self.snapshot()]
        with Path(path).open("w", encoding="utf-8", newline="") as stream:
            if not rows:
                return
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _sample(rate: float, key: object | None) -> bool:
        if rate <= 0:
            return False
        if rate >= 1:
            return True
        if key is not None:
            return (hash(key) & ((1 << 53) - 1)) / (1 << 53) < rate
        return random.random() < rate

    def _make_stats(self, name: str, accumulator: _Accumulator) -> TimerStats:
        samples = sorted(item.duration.nanoseconds for item in self._measurements if (item.name or "unnamed") == name)

        def percentile(fraction: float) -> Duration | None:
            if not samples:
                return None
            position = (len(samples) - 1) * fraction
            lower = math.floor(position)
            upper = math.ceil(position)
            value = (
                samples[lower]
                if lower == upper
                else samples[lower] + (samples[upper] - samples[lower]) * (position - lower)
            )
            return Duration(round(value))

        variance = accumulator.m2 / accumulator.count if accumulator.count else 0.0
        return TimerStats(
            name=name,
            count=accumulator.count,
            success_count=accumulator.successes,
            error_count=accumulator.errors,
            total=Duration(accumulator.total_ns),
            minimum=Duration(accumulator.minimum_ns),
            maximum=Duration(accumulator.maximum_ns),
            mean=Duration(round(accumulator.mean_ns)),
            variance_ns2=variance,
            standard_deviation=Duration(round(math.sqrt(variance))),
            last=Duration(accumulator.last_ns),
            median=percentile(0.5),
            p50=percentile(0.5),
            p75=percentile(0.75),
            p90=percentile(0.9),
            p95=percentile(0.95),
            p99=percentile(0.99),
            percentiles_exact=self.retention == "all",
        )

    def _tree_report(self, *, timeline: bool) -> str:
        measurements = self.measurements
        if not measurements:
            return "No retained measurements."
        children: dict[str | None, list[Measurement]] = {}
        ids = {item.id for item in measurements}
        for item in measurements:
            parent = item.parent_id if item.parent_id in ids else None
            children.setdefault(parent, []).append(item)
        rows: list[str] = []

        def visit(item: Measurement, depth: int) -> None:
            marker = "└── " if depth else ""
            bar = " " + "─" * min(24, max(1, round(item.duration.milliseconds / 10))) if timeline else ""
            rows.append(f"{'    ' * max(0, depth - 1)}{marker}{item.name or 'unnamed'}: {item.duration}{bar}")
            for child in children.get(item.id, []):
                visit(child, depth + 1)

        for root in children.get(None, []):
            visit(root, 0)
        return "\n".join(rows)

    def _handle_sink_error(self, error: Exception) -> None:
        if callable(self._on_sink_error):
            self._on_sink_error(error)
        elif self._on_sink_error == "raise":
            raise error
        else:
            warnings.warn(f"measurement sink failed: {error}", RuntimeWarning, stacklevel=3)


_default_registry = TimerRegistry()


def default_registry() -> TimerRegistry:
    return _default_registry
