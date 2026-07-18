"""Precise duration values and human-friendly parsing/formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from functools import total_ordering
from types import NotImplementedType
from typing import Self

_UNITS = {
    "ns": 1,
    "us": 1_000,
    "µs": 1_000,
    "μs": 1_000,
    "ms": 1_000_000,
    "s": 1_000_000_000,
    "m": 60_000_000_000,
    "h": 3_600_000_000_000,
}
_TOKEN = re.compile(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(ns|us|µs|μs|ms|s|m|h)", re.IGNORECASE)


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class Duration:
    """An immutable duration stored as an integer number of nanoseconds."""

    nanoseconds: int

    def __post_init__(self) -> None:
        if isinstance(self.nanoseconds, bool) or not isinstance(self.nanoseconds, int):
            raise TypeError("nanoseconds must be an integer")

    @classmethod
    def zero(cls) -> Self:
        return cls(0)

    @classmethod
    def from_nanoseconds(cls, value: int) -> Self:
        return cls(value)

    @classmethod
    def from_microseconds(cls, value: int | float) -> Self:
        return cls(round(float(value) * 1_000))

    @classmethod
    def from_milliseconds(cls, value: int | float) -> Self:
        return cls(round(float(value) * 1_000_000))

    @classmethod
    def from_seconds(cls, value: int | float) -> Self:
        return cls(round(float(value) * 1_000_000_000))

    @classmethod
    def from_timedelta(cls, value: timedelta) -> Self:
        return cls(round(value.total_seconds() * 1_000_000_000))

    @classmethod
    def parse(cls, value: str) -> Self:
        """Parse one or more unit-bearing components, for example ``1m 20.5s``."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("duration must be a non-empty string")
        position = 0
        total = 0.0
        matches = 0
        while position < len(value):
            match = _TOKEN.match(value, position)
            if match is None:
                if value[position:].strip():
                    raise ValueError(f"invalid duration near {value[position:]!r}")
                break
            number, unit = match.groups()
            total += float(number) * _UNITS[unit.lower()]
            matches += 1
            position = match.end()
        if not matches:
            raise ValueError(f"invalid duration: {value!r}")
        return cls(round(total))

    @property
    def ns(self) -> int:
        return self.nanoseconds

    @property
    def microseconds(self) -> float:
        return self.nanoseconds / 1_000

    @property
    def us(self) -> float:
        return self.microseconds

    @property
    def milliseconds(self) -> float:
        return self.nanoseconds / 1_000_000

    @property
    def ms(self) -> float:
        return self.milliseconds

    @property
    def seconds(self) -> float:
        return self.nanoseconds / 1_000_000_000

    @property
    def minutes(self) -> float:
        return self.seconds / 60

    @property
    def hours(self) -> float:
        return self.minutes / 60

    def to_timedelta(self) -> timedelta:
        return timedelta(microseconds=self.nanoseconds / 1_000)

    def format(self, *, unit: str | None = None, precision: int | None = None, style: str = "auto") -> str:
        """Format using an automatic unit, a fixed unit, clock style, or compact style."""
        if precision is not None and precision < 0:
            raise ValueError("precision must be non-negative")
        if style == "clock":
            sign = "-" if self.nanoseconds < 0 else ""
            total_ms = abs(self.nanoseconds) / 1_000_000
            hours, remainder = divmod(total_ms, 3_600_000)
            minutes, remainder = divmod(remainder, 60_000)
            seconds = remainder / 1_000
            decimals = 3 if precision is None else precision
            width = 2 + (1 if decimals else 0) + decimals
            return f"{sign}{int(hours):02d}:{int(minutes):02d}:{seconds:0{width}.{decimals}f}"
        if style == "compact":
            sign = "-" if self.nanoseconds < 0 else ""
            seconds = abs(self.seconds)
            if seconds >= 3600:
                hours = int(seconds // 3600)
                minutes = int(seconds % 3600 // 60)
                remainder = seconds % 60
                return f"{sign}{hours}h{minutes}m{remainder:.1f}s".replace(".0s", "s")
            if seconds >= 60:
                minutes = int(seconds // 60)
                remainder = seconds % 60
                return f"{sign}{minutes}m{remainder:.1f}s".replace(".0s", "s")
            return self.format(precision=precision)
        if style != "auto":
            raise ValueError("style must be 'auto', 'clock', or 'compact'")

        normalized = unit.lower().replace("μ", "µ") if unit else None
        if normalized is not None and normalized not in _UNITS:
            raise ValueError(f"unknown duration unit: {unit!r}")
        if normalized is None:
            magnitude = abs(self.nanoseconds)
            if magnitude < 1_000:
                normalized = "ns"
            elif magnitude < 1_000_000:
                normalized = "µs"
            elif magnitude < 1_000_000_000:
                normalized = "ms"
            elif magnitude < 60_000_000_000:
                normalized = "s"
            else:
                return self.format(style="compact", precision=precision)
        divisor = _UNITS[normalized]
        number = self.nanoseconds / divisor
        decimals = precision if precision is not None else (0 if number == int(number) else 3)
        rendered = f"{number:.{decimals}f}"
        if precision is None and "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return f"{rendered} {normalized}"

    def __str__(self) -> str:
        return self.format()

    def __eq__(self, other: object) -> bool:
        converted = _coerce(other)
        if not isinstance(converted, Duration):
            return False
        return self.nanoseconds == converted.nanoseconds

    def __lt__(self, other: object) -> bool:
        converted = _coerce(other)
        if not isinstance(converted, Duration):
            return NotImplemented
        return self.nanoseconds < converted.nanoseconds

    def __hash__(self) -> int:
        return hash(self.nanoseconds)

    def __add__(self, other: object) -> Duration:
        converted = _coerce(other)
        if not isinstance(converted, Duration):
            return NotImplemented
        return Duration(self.nanoseconds + converted.nanoseconds)

    def __sub__(self, other: object) -> Duration:
        converted = _coerce(other)
        if not isinstance(converted, Duration):
            return NotImplemented
        return Duration(self.nanoseconds - converted.nanoseconds)

    def __mul__(self, factor: int | float) -> Duration:
        if isinstance(factor, bool) or not isinstance(factor, (int, float)):
            return NotImplemented
        return Duration(round(self.nanoseconds * float(factor)))

    __rmul__ = __mul__

    def __truediv__(self, divisor: object) -> Duration | float:
        if isinstance(divisor, Duration):
            return self.nanoseconds / divisor.nanoseconds
        if isinstance(divisor, bool) or not isinstance(divisor, (int, float)):
            return NotImplemented
        return Duration(round(self.nanoseconds / float(divisor)))


def _coerce(value: object) -> Duration | NotImplementedType:
    if isinstance(value, Duration):
        return value
    if isinstance(value, timedelta):
        return Duration.from_timedelta(value)
    return NotImplemented


DurationLike = Duration | timedelta | int | str


def as_duration(value: DurationLike) -> Duration:
    """Normalize values accepted by budget and clock APIs."""
    if isinstance(value, Duration):
        return value
    if isinstance(value, timedelta):
        return Duration.from_timedelta(value)
    if isinstance(value, bool):
        raise TypeError("boolean values are not durations")
    if isinstance(value, int):
        return Duration(value)
    if isinstance(value, str):
        return Duration.parse(value)
    raise TypeError(f"unsupported duration value: {type(value).__name__}")
