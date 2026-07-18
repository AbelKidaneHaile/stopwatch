"""Convenience context-manager and decorator APIs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, ParamSpec, TypeVar, overload

from ._clock import Clock
from ._duration import DurationLike
from ._models import JsonScalar, Measurement
from ._registry import default_registry
from ._stopwatch import BudgetAction, Stopwatch

P = ParamSpec("P")
R = TypeVar("R")


def watch(
    name: str | None = None,
    *,
    tags: dict[str, JsonScalar] | None = None,
    clock: str | Clock = "wall",
    clocks: tuple[str | Clock, ...] | None = None,
    budget: DurationLike | None = None,
    on_exceed: BudgetAction = "record",
    on_result: Callable[[Measurement], None] | None = None,
    show: bool = False,
    detail: Literal["minimal", "standard", "full"] = "standard",
) -> Stopwatch:
    """Create a stopwatch for use in a synchronous or asynchronous ``with`` block."""
    if detail not in {"minimal", "standard", "full"}:
        raise ValueError("detail must be 'minimal', 'standard', or 'full'")
    return Stopwatch(
        name,
        tags=tags,
        clock=clock,
        clocks=clocks,
        budget=budget,
        on_exceed=on_exceed,
        on_result=on_result,
        show=show,
    )


@overload
def timed(function: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def timed(
    name: str | None = None,
    *,
    tags: Mapping[str, JsonScalar] | None = None,
    budget: DurationLike | None = None,
    on_exceed: BudgetAction = "record",
    sample_rate: float | None = None,
    generator_mode: Literal["lifetime", "iteration"] = "lifetime",
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def timed(
    name: str | Callable[..., Any] | None = None,
    *,
    tags: Mapping[str, JsonScalar] | None = None,
    budget: DurationLike | None = None,
    on_exceed: BudgetAction = "record",
    sample_rate: float | None = None,
    generator_mode: Literal["lifetime", "iteration"] = "lifetime",
) -> Any:
    """Time a sync, async, generator, or async-generator function."""
    registry = default_registry()
    if not isinstance(name, (str, type(None))):
        return registry.timed(name)
    return registry.timed(
        name,
        tags=tags,
        budget=budget,
        on_exceed=on_exceed,
        sample_rate=sample_rate,
        generator_mode=generator_mode,
    )
