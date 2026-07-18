"""Immutable result models."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType

from ._duration import Duration

type JsonScalar = str | int | float | bool | None


def immutable_tags(tags: dict[str, JsonScalar] | None = None) -> MappingProxyType[str, JsonScalar]:
    values = dict(tags or {})
    for key, value in values.items():
        if not isinstance(key, str):
            raise TypeError("tag keys must be strings")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"tag {key!r} must contain a JSON scalar")
    return MappingProxyType(values)


@dataclass(frozen=True, slots=True)
class Lap:
    index: int
    name: str | None
    duration: Duration
    split: Duration
    recorded_at: datetime | None
    tags: MappingProxyType[str, JsonScalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "name": self.name,
            "duration_ns": self.duration.nanoseconds,
            "split_ns": self.split.nanoseconds,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "tags": dict(self.tags),
        }


@dataclass(frozen=True, slots=True)
class Measurement:
    id: str
    name: str | None
    duration: Duration
    wall_duration: Duration
    paused_duration: Duration
    started_at: datetime | None
    ended_at: datetime | None
    status: str
    error_type: str | None
    laps: tuple[Lap, ...]
    tags: MappingProxyType[str, JsonScalar]
    parent_id: str | None
    trace_id: str
    clock_name: str
    clocks: MappingProxyType[str, Duration]
    budget: Duration | None = None
    budget_exceeded: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "id": self.id,
            "name": self.name,
            "duration_ns": self.duration.nanoseconds,
            "duration_display": str(self.duration),
            "wall_duration_ns": self.wall_duration.nanoseconds,
            "paused_duration_ns": self.paused_duration.nanoseconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "error_type": self.error_type,
            "laps": [lap.to_dict() for lap in self.laps],
            "tags": dict(self.tags),
            "parent_id": self.parent_id,
            "trace_id": self.trace_id,
            "clock_name": self.clock_name,
            "clocks_ns": {name: value.nanoseconds for name, value in self.clocks.items()},
            "budget_ns": self.budget.nanoseconds if self.budget else None,
            "budget_exceeded": self.budget_exceeded,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def format(self) -> str:
        name = self.name or "unnamed"
        suffix = f" [{self.status}]" if self.status != "ok" else ""
        return f"{name}: {self.duration}{suffix}"

    def with_tags(self, **tags: JsonScalar) -> Measurement:
        return replace(self, tags=immutable_tags({**self.tags, **tags}))

    def __str__(self) -> str:
        return self.format()


@dataclass(frozen=True, slots=True)
class TimerStats:
    """An immutable aggregate statistics snapshot."""

    name: str
    count: int
    success_count: int
    error_count: int
    total: Duration
    minimum: Duration
    maximum: Duration
    mean: Duration
    variance_ns2: float
    standard_deviation: Duration
    last: Duration
    median: Duration | None
    p50: Duration | None
    p75: Duration | None
    p90: Duration | None
    p95: Duration | None
    p99: Duration | None
    percentiles_exact: bool

    def to_dict(self) -> dict[str, object]:
        def ns(value: Duration | None) -> int | None:
            return value.nanoseconds if value is not None else None

        return {
            "name": self.name,
            "count": self.count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_ns": ns(self.total),
            "minimum_ns": ns(self.minimum),
            "maximum_ns": ns(self.maximum),
            "mean_ns": ns(self.mean),
            "variance_ns2": self.variance_ns2,
            "standard_deviation_ns": ns(self.standard_deviation),
            "last_ns": ns(self.last),
            "median_ns": ns(self.median),
            "p50_ns": ns(self.p50),
            "p75_ns": ns(self.p75),
            "p90_ns": ns(self.p90),
            "p95_ns": ns(self.p95),
            "p99_ns": ns(self.p99),
            "percentiles_exact": self.percentiles_exact,
        }
