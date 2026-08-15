from __future__ import annotations

import ast
from pathlib import Path

from main import _get_project_root


PROJECT_ROOT = Path(_get_project_root())


def read_repo_text(*parts: str) -> str:
    path = PROJECT_ROOT.joinpath(*parts)
    if not path.is_file():
        raise AssertionError(f"arquivo ausente: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AssertionError(f"falha ao ler arquivo: {path}: {exc}") from exc


def position_of(text: str, needle: str) -> int:
    position = text.find(needle)
    if position < 0:
        raise AssertionError(f"trecho ausente: {needle}")
    return position


def assert_before(text: str, first: str, second: str) -> None:
    first_position = position_of(text, first)
    second_position = position_of(text, second)
    if first_position >= second_position:
        raise AssertionError(f"ordem invalida: {first} antes de {second}")


def section_between(text: str, start: str, end: str) -> str:
    start_position = position_of(text, start) + len(start)
    end_position = text.find(end, start_position)
    if end_position < 0:
        raise AssertionError(f"fim de secao ausente: {end}")
    return text[start_position:end_position]


def assert_no_unguarded_string_position_helpers(test_source: str) -> None:
    try:
        tree = ast.parse(test_source)
    except SyntaxError as exc:
        raise AssertionError(f"codigo de teste invalido: {exc}") from exc

    offenders: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "index":
                offenders.append(f"{node.lineno}: chamada fragil a index()")
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "split"
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == 1
            ):
                offenders.append(f"{node.lineno}: acesso fragil a split()[1]")
            self.generic_visit(node)

    Visitor().visit(tree)
    if offenders:
        raise AssertionError(
            "uso fragil de index/split em teste: " + "; ".join(offenders)
        )
