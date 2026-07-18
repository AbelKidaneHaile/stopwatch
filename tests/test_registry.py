"""Tests for registries, decorators, nesting, sinks, and exports."""

import asyncio
import json

import pytest

from stopwatch import Duration, ManualClock, TimerRegistry
from stopwatch.sinks import InMemorySink, JsonLinesSink


def test_registry_statistics_retention_and_report() -> None:
    clock = ManualClock()
    registry = TimerRegistry(retention="all")
    for amount in ("10ms", "20ms", "30ms"):
        with registry.watch("work", clock=clock):
            clock.advance(amount)
    stats = registry.stats("work")
    assert stats.count == 3
    assert stats.total == Duration.parse("60ms")
    assert stats.mean == Duration.parse("20ms")
    assert stats.minimum == Duration.parse("10ms")
    assert stats.maximum == Duration.parse("30ms")
    assert stats.p95 is not None
    assert stats.percentiles_exact
    assert "work" in registry.report()


def test_nested_scopes_capture_parent_and_trace() -> None:
    clock = ManualClock()
    registry = TimerRegistry(retention="all")
    with registry.watch("parent", clock=clock):
        clock.advance("1ms")
        with registry.watch("child", clock=clock):
            clock.advance("2ms")
    child, parent = registry.measurements
    assert child.parent_id == parent.id
    assert child.trace_id == parent.trace_id
    assert "child" in registry.report(view="tree")


def test_sync_decorator_preserves_metadata_and_records_errors() -> None:
    registry = TimerRegistry(retention="all")

    @registry.timed("add")
    def add(left: int, right: int) -> int:
        """Add values."""
        return left + right

    assert add(2, 3) == 5
    assert add.__name__ == "add"
    assert add.__doc__ == "Add values."
    assert registry.stats("add").count == 1

    @registry.timed("fail")
    def fail() -> None:
        raise RuntimeError

    with pytest.raises(RuntimeError):
        fail()
    assert registry.stats("fail").error_count == 1


def test_async_decorator_times_awaited_coroutine() -> None:
    registry = TimerRegistry(retention="all")

    @registry.timed("async-work")
    async def work() -> int:
        await asyncio.sleep(0)
        return 42

    assert asyncio.run(work()) == 42
    assert registry.stats("async-work").count == 1


def test_generator_decorator_times_iteration_not_creation() -> None:
    registry = TimerRegistry(retention="all")

    @registry.timed("rows")
    def rows():
        yield 1
        yield 2

    generated = rows()
    assert registry.measurements == ()
    assert list(generated) == [1, 2]
    assert registry.stats("rows").count == 1


def test_sampling_filter_clear_and_allowed_tags() -> None:
    registry = TimerRegistry(retention="all", sample_rate=0, allowed_tag_keys={"method"})
    with registry.watch("ignored"):
        pass
    assert registry.snapshot() == ()
    with pytest.raises(ValueError):
        registry.watch("bad", tags={"customer_id": 1})

    recorded = TimerRegistry(retention="all")
    with recorded.watch("database.query", tags={"method": "GET"}):
        pass
    assert len(recorded.filter(prefix="database", tags={"method": "GET"})) == 1
    recorded.clear()
    assert recorded.snapshot() == ()


def test_sinks_and_exports(tmp_path) -> None:
    memory = InMemorySink()
    jsonl_path = tmp_path / "timings.jsonl"
    registry = TimerRegistry(retention="all", sinks=[memory, JsonLinesSink(jsonl_path)])
    with registry.watch("export"):
        pass
    assert len(memory.measurements) == 1
    assert json.loads(jsonl_path.read_text())["name"] == "export"

    json_path = tmp_path / "summary.json"
    csv_path = tmp_path / "summary.csv"
    registry.to_json(json_path)
    registry.to_csv(csv_path)
    assert json.loads(json_path.read_text())[0]["name"] == "export"
    assert "export" in csv_path.read_text()
