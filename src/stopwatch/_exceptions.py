"""Exceptions raised by stopwatch."""

from __future__ import annotations

from ._duration import Duration


class StopwatchError(Exception):
    """Base class for package exceptions."""


class InvalidStopwatchState(StopwatchError):
    """Raised when an operation is invalid for the stopwatch state."""


class DurationBudgetExceeded(StopwatchError):
    """Raised when a measurement exceeds its configured performance budget."""

    def __init__(self, name: str | None, actual: Duration, budget: Duration) -> None:
        self.name = name
        self.actual = actual
        self.budget = budget
        label = name or "operation"
        super().__init__(f"{label!r} took {actual}, exceeding its {budget} budget by {actual - budget}")
