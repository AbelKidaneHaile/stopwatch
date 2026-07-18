"""Tests for dependency-free CLI helpers."""

from stopwatch.cli import main


def test_parse_and_format_commands(capsys) -> None:
    assert main(["parse", "1.5s"]) == 0
    assert capsys.readouterr().out.strip() == "1500000000"
    assert main(["format", "1500000ns", "--unit", "ms", "--precision", "1"]) == 0
    assert capsys.readouterr().out.strip() == "1.5 ms"
