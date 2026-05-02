from __future__ import annotations

from pathlib import Path

from main import _get_project_root


PROJECT_ROOT = Path(_get_project_root())


def read_repo_text(*parts: str) -> str:
    path = PROJECT_ROOT.joinpath(*parts)
    if not path.is_file():
        raise AssertionError(f"arquivo ausente: {path}")
    return path.read_text(encoding="utf-8")


def position_of(text: str, needle: str) -> int:
    position = text.find(needle)
    if position < 0:
        raise AssertionError(f"trecho ausente: {needle}")
    return position


def assert_before(text: str, first: str, second: str) -> None:
    first_position = position_of(text, first)
    second_position = position_of(text, second)
    assert first_position < second_position, f"ordem invalida: {first} antes de {second}"


def section_between(text: str, start: str, end: str) -> str:
    start_position = position_of(text, start) + len(start)
    end_position = text.find(end, start_position)
    if end_position < 0:
        raise AssertionError(f"fim de secao ausente: {end}")
    return text[start_position:end_position]


def assert_no_unguarded_string_position_helpers(test_source: str) -> None:
    offenders: list[str] = []
    for line_number, line in enumerate(test_source.splitlines(), start=1):
        if ".index(" in line or (".split(" in line and "[1]" in line):
            offenders.append(f"{line_number}: {line.strip()}")
    assert offenders == [], "uso fragil de index/split em teste: " + "; ".join(offenders)
