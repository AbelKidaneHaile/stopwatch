"""Process-wide instrumentation defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from threading import RLock


def _environment_enabled() -> bool:
    value = os.getenv("STOPWATCH_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class _Configuration:
    enabled: bool


_configuration = _Configuration(enabled=_environment_enabled())
_lock = RLock()


def configure(*, enabled: bool | None = None) -> None:
    """Update global instrumentation defaults."""
    with _lock:
        if enabled is not None:
            _configuration.enabled = bool(enabled)


def is_enabled() -> bool:
    with _lock:
        return _configuration.enabled
