"""Command-line interface for stopwatch."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ._duration import Duration


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stopwatch", description="Measure commands and work with duration values.")
    parser.add_argument("--version", action="version", version="stopwatch 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)

    format_command = commands.add_parser("format", help="Format a duration")
    format_command.add_argument("duration")
    format_command.add_argument("--unit", choices=("ns", "us", "µs", "ms", "s", "m", "h"))
    format_command.add_argument("--precision", type=int)
    format_command.add_argument("--style", choices=("auto", "clock", "compact"), default="auto")

    parse_command = commands.add_parser("parse", help="Parse a duration into integer nanoseconds")
    parse_command.add_argument("duration")

    run_command = commands.add_parser("run", help="Measure a child process")
    run_command.add_argument("program", nargs=argparse.REMAINDER)

    report_command = commands.add_parser("report", help="Summarize a JSON or JSON Lines export")
    report_command.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "format":
        print(Duration.parse(args.duration).format(unit=args.unit, precision=args.precision, style=args.style))
        return 0
    if args.command == "parse":
        print(Duration.parse(args.duration).nanoseconds)
        return 0
    if args.command == "run":
        program = list(args.program)
        if program and program[0] == "--":
            program.pop(0)
        if not program:
            _parser().error("run requires a command after '--'")
        started_at = datetime.now(UTC)
        started_ns = time.perf_counter_ns()
        completed = subprocess.run(program, check=False)
        elapsed = Duration(time.perf_counter_ns() - started_ns)
        ended_at = datetime.now(UTC)
        print(f"Command:  {' '.join(program)}")
        print(f"Status:   {completed.returncode}")
        print(f"Duration: {elapsed}")
        print(f"Started:  {started_at.isoformat()}")
        print(f"Ended:    {ended_at.isoformat()}")
        return completed.returncode
    if args.command == "report":
        content = args.path.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
            records = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            records = [json.loads(line) for line in content.splitlines() if line.strip()]
        print(f"{'Timer':32} {'Calls':>7} {'Total':>12} {'Mean':>12} {'Errors':>7}")
        for record in records:
            name = str(record.get("name", "unnamed"))
            if "count" in record:
                count = int(record["count"])
                total = Duration(int(record.get("total_ns", 0)))
                mean = Duration(int(record.get("mean_ns", 0)))
                errors = int(record.get("error_count", 0))
            else:
                count = 1
                total = mean = Duration(int(record.get("duration_ns", 0)))
                errors = int(record.get("status") in {"error", "cancelled"})
            print(f"{name[:32]:32} {count:7d} {str(total):>12} {str(mean):>12} {errors:7d}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
