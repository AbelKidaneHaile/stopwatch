"""Deterministic tests for stopwatch lifecycle semantics."""

from dataclasses import FrozenInstanceError

import pytest

from stopwatch import (
    Duration,
    DurationBudgetExceeded,
    InvalidStopwatchState,
    ManualClock,
    Stopwatch,
    StopwatchState,
    watch,
)


def test_manual_lifecycle_laps_and_idempotent_stop() -> None:
    clock = ManualClock()
    timer = Stopwatch("pipeline", clock=clock, tags={"source": "crm"}).start()
    clock.advance("25ms")
    first = timer.lap("extract")
    clock.advance("75ms")
    second = timer.lap("load")
    result = timer.stop()

    assert first.duration == Duration.parse("25ms")
    assert second.duration == Duration.parse("75ms")
    assert second.split == Duration.parse("100ms")
    assert result.duration == Duration.parse("100ms")
    assert result.wall_duration == result.duration
    assert result.tags == {"source": "crm"}
    assert timer.stop() is result
    assert timer.state is StopwatchState.STOPPED


def test_pause_resume_and_paused_context() -> None:
    clock = ManualClock()
    timer = Stopwatch("job", clock=clock).start()
    clock.advance("10ms")
    with timer.paused():
        clock.advance("40ms")
    clock.advance("20ms")
    result = timer.stop()
    assert result.duration == Duration.parse("30ms")
    assert result.paused_duration == Duration.parse("40ms")
    assert result.wall_duration == Duration.parse("70ms")


def test_elapsed_does_not_mutate_state() -> None:
    clock = ManualClock()
    timer = Stopwatch(clock=clock).start()
    clock.advance("5ms")
    assert timer.elapsed == Duration.parse("5ms")
    assert timer.elapsed == Duration.parse("5ms")
    assert timer.state is StopwatchState.RUNNING


def test_invalid_transitions_are_strict() -> None:
    timer = Stopwatch(clock=ManualClock())
    with pytest.raises(InvalidStopwatchState):
        timer.pause()
    with pytest.raises(InvalidStopwatchState):
        timer.stop()
    timer.start()
    with pytest.raises(InvalidStopwatchState):
        timer.start()
    timer.pause()
    with pytest.raises(InvalidStopwatchState):
        timer.lap()
    with pytest.raises(InvalidStopwatchState):
        timer.reset()


def test_restart_clears_result_and_laps() -> None:
    clock = ManualClock()
    timer = Stopwatch(clock=clock).start()
    clock.advance("1ms")
    timer.lap()
    old_id = timer.stop().id
    timer.restart()
    assert timer.id != old_id
    assert timer.laps == ()
    assert timer.result is None


def test_context_records_error_without_suppressing_it() -> None:
    timer = watch("failure", clock=ManualClock())
    with pytest.raises(ValueError, match="bad"):
        with timer:
            raise ValueError("bad")
    assert timer.result is not None
    assert timer.result.status == "error"
    assert timer.result.error_type == "ValueError"


def test_measurements_are_immutable_and_serializable() -> None:
    clock = ManualClock()
    with Stopwatch("serialize", clock=clock) as timer:
        clock.advance("2ms")
    result = timer.result
    assert result is not None
    with pytest.raises(FrozenInstanceError):
        result.status = "changed"  # ty: ignore[invalid-assignment]
    assert result.to_dict()["duration_ns"] == 2_000_000
    assert '"name": "serialize"' in result.to_json()


def test_budget_raise_and_application_error_precedence() -> None:
    clock = ManualClock()
    with pytest.raises(DurationBudgetExceeded):
        with Stopwatch("slow", clock=clock, budget="5ms", on_exceed="raise"):
            clock.advance("10ms")

    timer = Stopwatch("broken", clock=clock, budget="5ms", on_exceed="raise")
    with pytest.warns(RuntimeWarning), pytest.raises(KeyError):
        with timer:
            clock.advance("10ms")
            raise KeyError("original")


def test_result_callback_runs_after_measurement() -> None:
    clock = ManualClock()
    seen = []
    with Stopwatch("callback", clock=clock, on_result=seen.append):
        clock.advance("3ms")
    assert len(seen) == 1
    assert seen[0].duration == Duration.parse("3ms")
