"""Dependency-free measurement sinks."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from threading import RLock
from typing import Protocol, TextIO

from ._models import Measurement


class NullSink:
    """Discard all measurements."""

    def record(self, measurement: Measurement) -> None:
        del measurement


class InMemorySink:
    """Retain measurements in insertion order."""

    def __init__(self) -> None:
        self._measurements: list[Measurement] = []
        self._lock = RLock()

    @property
    def measurements(self) -> tuple[Measurement, ...]:
        with self._lock:
            return tuple(self._measurements)

    def record(self, measurement: Measurement) -> None:
        with self._lock:
            self._measurements.append(measurement)


class CallbackSink:
    def __init__(self, callback: Callable[[Measurement], None]) -> None:
        self.callback = callback

    def record(self, measurement: Measurement) -> None:
        self.callback(measurement)


class ConsoleSink:
    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream or sys.stderr

    def record(self, measurement: Measurement) -> None:
        print(measurement, file=self.stream)


class LoggingSink:
    def __init__(self, logger: str | logging.Logger = "stopwatch", level: str | int = logging.INFO) -> None:
        self.logger = logging.getLogger(logger) if isinstance(logger, str) else logger
        self.level = (
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO) if isinstance(level, str) else level
        )

    def record(self, measurement: Measurement) -> None:
        self.logger.log(self.level, "duration", extra={"stopwatch": measurement.to_dict()})


class JsonLinesSink:
    """Append one structured measurement per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def record(self, measurement: Measurement) -> None:
        line = json.dumps(measurement.to_dict(), sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


class _Sink(Protocol):
    def record(self, measurement: Measurement) -> None: ...


class CompositeSink:
    def __init__(self, sinks: Iterable[_Sink]) -> None:
        self.sinks = tuple(sinks)

    def record(self, measurement: Measurement) -> None:
        for sink in self.sinks:
            sink.record(measurement)
