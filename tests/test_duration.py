"""Tests for the Duration value object."""

from datetime import timedelta

import pytest

from stopwatch import Duration


@pytest.mark.parametrize(
    ("text", "nanoseconds"),
    [
        ("250ns", 250),
        ("20us", 20_000),
        ("20µs", 20_000),
        ("14ms", 14_000_000),
        ("1.5s", 1_500_000_000),
        ("1h 20m 5s", 4_805_000_000_000),
    ],
)
def test_parse(text: str, nanoseconds: int) -> None:
    assert Duration.parse(text).nanoseconds == nanoseconds


def test_construction_conversion_and_aliases() -> None:
    duration = Duration.from_milliseconds(1_500)
    assert duration.ns == 1_500_000_000
    assert duration.us == 1_500_000
    assert duration.ms == 1_500
    assert duration.seconds == 1.5
    assert duration.minutes == 0.025
    assert duration.to_timedelta() == timedelta(seconds=1.5)


def test_arithmetic_and_comparison() -> None:
    first = Duration.parse("250ms")
    second = Duration.parse("750ms")
    assert first + second == timedelta(seconds=1)
    assert second - first == Duration.parse("500ms")
    assert first * 2 == Duration.parse("500ms")
    assert second / 3 == first
    assert second / first == 3
    assert first < timedelta(seconds=1)


def test_formatting() -> None:
    assert Duration(721).format() == "721 ns"
    assert Duration.parse("14.8us").format() == "14.8 µs"
    assert Duration.parse("8.31ms").format() == "8.31 ms"
    assert Duration.parse("1.5s").format(unit="ms", precision=2) == "1500.00 ms"
    assert Duration.parse("1m 28.421s").format(style="clock") == "00:01:28.421"
    assert Duration.parse("1m 28.4s").format(style="compact") == "1m28.4s"


@pytest.mark.parametrize("value", ["", "ten seconds", "1s rubbish"])
def test_invalid_parse(value: str) -> None:
    with pytest.raises(ValueError):
        Duration.parse(value)
