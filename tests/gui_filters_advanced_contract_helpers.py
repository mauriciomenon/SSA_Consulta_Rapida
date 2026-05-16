import ast
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from gui.ssa import gui_filters_advanced_logic as adv_logic
from gui.ssa import gui_filters_advanced_state_reader as adv_state_reader
from gui.ssa import gui_filters_advanced_ui as adv_ui


@dataclass(frozen=True)
class AdvancedFilterSources:
    ui: str
    state_reader: str
    logic: str


@lru_cache(maxsize=8)
def get_has_active_block(ui_source: str) -> str:
    module = ast.parse(ui_source)
    for node in module.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "_has_active_advanced_filters"
        ):
            source = ast.get_source_segment(ui_source, node)
            assert source is not None
            return source
    raise AssertionError("_has_active_advanced_filters not found")


def extract_produced_filter_keys(source: str) -> set[str]:
    module = _parse_source(source)
    return _extract_data_assignment_keys(module) | _extract_state_reader_dict_keys(
        module
    )


@lru_cache(maxsize=1)
def read_advanced_filter_sources() -> AdvancedFilterSources:
    return AdvancedFilterSources(
        ui=Path(adv_ui.__file__).read_text(encoding="utf-8"),
        state_reader=Path(adv_state_reader.__file__).read_text(encoding="utf-8"),
        logic=Path(adv_logic.__file__).read_text(encoding="utf-8"),
    )


def extract_assigned_literal_dict(source: str, variable_name: str) -> dict:
    value = _extract_assigned_literal(source, variable_name)
    return value if isinstance(value, dict) else {}


def extract_detector_filter_keys(active_block_source: str) -> set[str]:
    return _extract_regex_keys(r'data\.get\("([^"]+)"\)', active_block_source)


def extract_logic_filter_keys(logic_source: str) -> set[str]:
    return _extract_regex_keys(r'filters\.get\("([^"]+)"\)', logic_source)


def extract_week_exclude_keys(logic_source: str) -> set[str]:
    return _extract_regex_keys(
        r'"(semana_(?:emissao|execucao)_exclude)"',
        logic_source,
    )


def extract_column_group_include_exclude_keys(source: str) -> set[str]:
    value = _extract_assigned_literal(source, "column_groups")
    if not isinstance(value, list):
        return set()
    keys: set[str] = set()
    for item in value:
        if not isinstance(item, tuple) or len(item) != 3:
            continue
        _, include_key, exclude_key = item
        if isinstance(include_key, str):
            keys.add(include_key)
        if isinstance(exclude_key, str):
            keys.add(exclude_key)
    return keys


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_regex_keys(pattern: str, source: str) -> set[str]:
    return set(re.findall(pattern, source))


def _extract_data_assignment_keys(module: ast.Module) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "data"
                ):
                    key = _literal_string(target.slice)
                    if key is not None:
                        keys.add(key)
    return keys


def _extract_state_reader_dict_keys(module: ast.Module) -> set[str]:
    keys: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "AdvancedFilterStateReader":
            for child in ast.walk(node):
                if isinstance(child, ast.Dict):
                    for key_node in child.keys:
                        key = _literal_string(key_node)
                        if key is not None:
                            keys.add(key)
    return keys


def _extract_assigned_literal(source: str, variable_name: str):
    module = _parse_source(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == variable_name:
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    return None
    return None


@lru_cache(maxsize=8)
def _parse_source(source: str) -> ast.Module:
    return ast.parse(source)
