#!/usr/bin/env python3
"""Validate configuration JSON files under the config/ directory.

Goals / Design:
  * Fast, zero external deps, pure stdlib.
  * Provide a first governance gate for config integrity (structure + basic semantics).
  * Exit codes:
        0 -> no errors (warnings allowed unless --fail-on-warn)
        1 -> validation errors (or warnings promoted to errors with --fail-on-warn)
        2 -> fatal internal failure (e.g. unreadable file, JSON parse error)
  * Optional JSON output (machine friendly) via --json.
  * Conservative semantic checks: only rules we can assert confidently from current repo state.

Implemented File-Specific Rules (heuristic but explicit):
  version.json:
    - Must contain keys: version_short (\\d+\\.\\d+ pattern) & version_long (non-empty, includes version_short)

  settings.json / default_settings.json:
    - Must contain display_settings, user_preferences, default_filters
    - display_settings.column_widths values must be int > 0
    - If display_settings.column_visibility present, values must be boolean
    - default_filters must be a list

  cli_enhancements.json:
    - All values except 'version' must be boolean
    - version string length > 0

  display_mappings.json:
    - All values non-empty strings
    - No duplicate label values (warn if duplicates)

  column_mappings.json:
    - Each value is a non-empty list of unique non-empty strings

  column_priority.json:
    - essential / always_visible / priority_order all lists of strings (no duplicates per list)
    - short_labels values are non-empty strings
    - fixed_widths values are positive integers
    - Warn if any column in always_visible not in essential (may be intentional, so warn only)

  gui_*_preferences.json:
    - display_columns / hidden_columns lists of strings without duplicates
    - No intersection between display_columns & hidden_columns
    - column_display_names maps to non-empty strings
    - column_widths values positive integers
    - version & description present

Generic rules applied to all JSON files scanned:
  * File must parse as JSON (UTF-8)
  * Top-level must be an object/dict

Future extensibility:
  - Add schema fragments or stricter cross-file consistency (e.g., columns referenced share the same canonical set) when definitions stabilize.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class Issue:
    file: str
    level: str  # 'error' | 'warn' | 'fatal'
    message: str
    rule: str

    def to_dict(self) -> Dict[str, Any]:  # stable ordering
        return asdict(self)


def load_json(path: Path, issues: List[Issue]) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        issues.append(
            Issue(str(path), "fatal", f"Não foi possível ler arquivo: {exc}", "io.read")
        )
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        issues.append(Issue(str(path), "fatal", f"Erro de JSON: {exc}", "json.parse"))
        return None


def expect_keys(
    obj: Dict[str, Any], required: List[str], file: Path, issues: List[Issue], rule: str
) -> None:
    for k in required:
        if k not in obj:
            issues.append(
                Issue(str(file), "error", f"Chave obrigatória ausente: {k}", rule)
            )


def validate_version(file: Path, data: Dict[str, Any], issues: List[Issue]) -> None:
    expect_keys(
        data, ["version_short", "version_long"], file, issues, "version.required"
    )
    vs = data.get("version_short")
    if isinstance(vs, str):
        if not re.match(r"^\d+\.\d+$", vs):
            issues.append(
                Issue(
                    str(file),
                    "error",
                    f"version_short formato inválido: {vs}",
                    "version.pattern",
                )
            )
    else:
        issues.append(
            Issue(str(file), "error", "version_short deve ser string", "version.type")
        )
    vl = data.get("version_long")
    if isinstance(vl, str):
        if vs and isinstance(vs, str) and vs not in vl:
            issues.append(
                Issue(
                    str(file),
                    "warn",
                    "version_long não contém version_short",
                    "version.consistency",
                )
            )
        if not vl.strip():
            issues.append(
                Issue(str(file), "error", "version_long vazio", "version.empty")
            )
    else:
        issues.append(
            Issue(str(file), "error", "version_long deve ser string", "version.type")
        )


def validate_settings(file: Path, data: Dict[str, Any], issues: List[Issue]) -> None:
    expect_keys(
        data,
        ["display_settings", "user_preferences", "default_filters"],
        file,
        issues,
        "settings.required",
    )
    ds = data.get("display_settings")
    if isinstance(ds, dict):
        cw = ds.get("column_widths")
        if isinstance(cw, dict):
            for k, v in cw.items():
                if not isinstance(v, int) or v <= 0:
                    issues.append(
                        Issue(
                            str(file),
                            "error",
                            f"column_widths[{k}] deve ser inteiro > 0",
                            "settings.column_widths.type",
                        )
                    )
        cv = ds.get("column_visibility")
        if cv is not None:
            if not isinstance(cv, dict):
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        "column_visibility deve ser objeto",
                        "settings.column_visibility.type",
                    )
                )
            else:
                for k, v in cv.items():
                    if not isinstance(v, bool):
                        issues.append(
                            Issue(
                                str(file),
                                "error",
                                f"column_visibility[{k}] deve ser booleano",
                                "settings.column_visibility.bool",
                            )
                        )
    else:
        issues.append(
            Issue(
                str(file),
                "error",
                "display_settings deve ser objeto",
                "settings.display_settings.type",
            )
        )
    if not isinstance(data.get("user_preferences"), dict):
        issues.append(
            Issue(
                str(file),
                "error",
                "user_preferences deve ser objeto",
                "settings.user_preferences.type",
            )
        )
    if not isinstance(data.get("default_filters"), list):
        issues.append(
            Issue(
                str(file),
                "error",
                "default_filters deve ser lista",
                "settings.default_filters.type",
            )
        )


def validate_cli_enhancements(
    file: Path, data: Dict[str, Any], issues: List[Issue]
) -> None:
    for k, v in data.items():
        if k == "version":
            if not isinstance(v, str) or not v.strip():
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        "version deve ser string não vazia",
                        "cli_enhancements.version",
                    )
                )
        else:
            if not isinstance(v, bool):
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"{k} deve ser booleano",
                        "cli_enhancements.bool",
                    )
                )


def validate_display_mappings(
    file: Path, data: Dict[str, Any], issues: List[Issue]
) -> None:
    # 'data' já é Dict[str, Any] garantido por scan_configs; checagem dinâmica redundante removida
    # Mantemos lógica simples – se futuramente o chamador mudar e passar algo diferente, a validação
    # de topo em scan_configs já terá registrado erro.
    labels = list(data.values())
    for k, v in data.items():
        if not isinstance(v, str) or not v.strip():
            issues.append(
                Issue(
                    str(file),
                    "error",
                    f"Label para '{k}' inválido",
                    "display_mappings.value",
                )
            )
    seen = {}
    for lbl in labels:
        seen.setdefault(lbl, 0)
        seen[lbl] += 1
    dups = [label for label, count in seen.items() if count > 1]
    for d in dups:
        issues.append(
            Issue(
                str(file), "warn", f"Label duplicado: {d}", "display_mappings.duplicate"
            )
        )


def validate_column_mappings(
    file: Path, data: Dict[str, Any], issues: List[Issue]
) -> None:
    # data é garantidamente dict no chamador; aqui focamos apenas nas listas dos valores
    for k, v in data.items():  # v deve ser lista não vazia de strings únicas não vazias
        if not isinstance(v, list) or not v:  # noqa: SIM102 (checagem necessária para conteúdo)
            issues.append(
                Issue(
                    str(file),
                    "error",
                    f"'{k}' deve mapear para lista não vazia",
                    "column_mappings.list",
                )
            )
            continue
        seen = set()
        for idx, alias in enumerate(v):
            if not isinstance(alias, str) or not alias.strip():
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"'{k}' alias #{idx} inválido",
                        "column_mappings.alias",
                    )
                )
            elif alias in seen:
                issues.append(
                    Issue(
                        str(file),
                        "warn",
                        f"'{k}' alias duplicado: {alias}",
                        "column_mappings.duplicate",
                    )
                )
            else:
                seen.add(alias)


def validate_column_priority(
    file: Path, data: Dict[str, Any], issues: List[Issue]
) -> None:
    list_keys = ["essential", "always_visible", "priority_order"]
    for lk in list_keys:
        val = data.get(lk)
        if not isinstance(val, list):
            issues.append(
                Issue(
                    str(file), "error", f"'{lk}' deve ser lista", "column_priority.list"
                )
            )
            continue
        if len(val) != len(set(val)):
            issues.append(
                Issue(
                    str(file),
                    "warn",
                    f"'{lk}' possui duplicatas",
                    "column_priority.duplicates",
                )
            )
    short_labels = data.get("short_labels")
    if not isinstance(short_labels, dict):
        issues.append(
            Issue(
                str(file),
                "error",
                "short_labels deve ser objeto",
                "column_priority.short_labels.type",
            )
        )
    else:
        for k, v in short_labels.items():
            if not isinstance(v, str) or not v.strip():
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"short_labels[{k}] inválido",
                        "column_priority.short_labels.value",
                    )
                )
    fixed_widths = data.get("fixed_widths")
    if not isinstance(fixed_widths, dict):
        issues.append(
            Issue(
                str(file),
                "error",
                "fixed_widths deve ser objeto",
                "column_priority.fixed_widths.type",
            )
        )
    else:
        for k, v in fixed_widths.items():
            if not isinstance(v, int) or v <= 0:
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"fixed_widths[{k}] deve ser inteiro > 0",
                        "column_priority.fixed_widths.value",
                    )
                )
    essential = data.get("essential") or []
    always_visible = data.get("always_visible") or []
    for col in always_visible:
        if col not in essential:
            issues.append(
                Issue(
                    str(file),
                    "warn",
                    f"'{col}' em always_visible não listado em essential",
                    "column_priority.alignment",
                )
            )


def validate_gui_preferences(
    file: Path, data: Dict[str, Any], issues: List[Issue]
) -> None:
    display = data.get("display_columns")
    hidden = data.get("hidden_columns")
    if not isinstance(display, list) or not all(isinstance(c, str) for c in display):
        issues.append(
            Issue(
                str(file),
                "error",
                "display_columns deve ser lista de strings",
                "gui_prefs.display_columns.type",
            )
        )
    if not isinstance(hidden, list) or not all(isinstance(c, str) for c in hidden):
        issues.append(
            Issue(
                str(file),
                "error",
                "hidden_columns deve ser lista de strings",
                "gui_prefs.hidden_columns.type",
            )
        )
    if isinstance(display, list) and isinstance(hidden, list):
        overlap = sorted(set(display) & set(hidden))
        if overlap:
            issues.append(
                Issue(
                    str(file),
                    "error",
                    f"Colunas em conflito display/hidden: {overlap}",
                    "gui_prefs.columns.overlap",
                )
            )
        if len(display) != len(set(display)):
            issues.append(
                Issue(
                    str(file),
                    "warn",
                    "display_columns possui duplicatas",
                    "gui_prefs.display_columns.duplicates",
                )
            )
    cdn = data.get("column_display_names")
    if not isinstance(cdn, dict):
        issues.append(
            Issue(
                str(file),
                "error",
                "column_display_names deve ser objeto",
                "gui_prefs.column_display_names.type",
            )
        )
    else:
        for k, v in cdn.items():
            if not isinstance(v, str) or not v.strip():
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"column_display_names[{k}] inválido",
                        "gui_prefs.column_display_names.value",
                    )
                )
    cwidths = data.get("column_widths", {})
    if not isinstance(cwidths, dict):
        issues.append(
            Issue(
                str(file),
                "error",
                "column_widths deve ser objeto",
                "gui_prefs.column_widths.type",
            )
        )
    else:
        for k, v in cwidths.items():
            if not isinstance(v, int) or v <= 0:
                issues.append(
                    Issue(
                        str(file),
                        "error",
                        f"column_widths[{k}] deve ser inteiro > 0",
                        "gui_prefs.column_widths.value",
                    )
                )
    for meta_key in ("version", "description"):
        if meta_key not in data:
            issues.append(
                Issue(
                    str(file),
                    "error",
                    f"Campo meta ausente: {meta_key}",
                    "gui_prefs.meta.required",
                )
            )


VALIDATORS = {
    "version.json": validate_version,
    "settings.json": validate_settings,
    "default_settings.json": validate_settings,
    "cli_enhancements.json": validate_cli_enhancements,
    "display_mappings.json": validate_display_mappings,
    "column_mappings.json": validate_column_mappings,
    "column_priority.json": validate_column_priority,
    "gui_main_preferences.json": validate_gui_preferences,
    "gui_poc_preferences.json": validate_gui_preferences,
}


def scan_configs(config_dir: Path) -> Tuple[List[Issue], Dict[str, Any]]:
    issues: List[Issue] = []
    results: Dict[str, Any] = {}
    for path in sorted(config_dir.glob("*.json")):
        data = load_json(path, issues)
        if data is None:
            continue  # fatal already recorded
        if not isinstance(data, dict):
            issues.append(
                Issue(
                    str(path),
                    "error",
                    "Top-level JSON deve ser objeto",
                    "generic.top_level_object",
                )
            )
            continue
        results[path.name] = data
        validator = VALIDATORS.get(path.name)
        if validator:
            try:
                validator(path, data, issues)
            except Exception as exc:  # noqa: BLE001
                issues.append(
                    Issue(
                        str(path),
                        "fatal",
                        f"Exceção durante validação: {exc}",
                        "validator.exception",
                    )
                )
    return issues, results


def summarize(issues: List[Issue]) -> Dict[str, int]:
    counts = {"fatal": 0, "error": 0, "warn": 0}
    for i in issues:
        counts[i.level] = counts.get(i.level, 0) + 1
    return counts


def render_text(issues: List[Issue], counts: Dict[str, int]) -> str:
    if not issues:
        return " Nenhum problema encontrado."
    # Sort by severity then file
    order = {"fatal": 0, "error": 1, "warn": 2}
    issues_sorted = sorted(
        issues, key=lambda x: (order.get(x.level, 99), x.file, x.rule)
    )
    lines = []
    for it in issues_sorted:
        lines.append(f"[{it.level.upper():5}] {it.file}: {it.message} ({it.rule})")
    lines.append("")
    lines.append(
        f"Resumo: fatal={counts['fatal']} errors={counts['error']} warns={counts['warn']}"
    )
    return "\n".join(lines)


def compute_exit_code(counts: Dict[str, int], fail_on_warn: bool) -> int:
    if counts.get("fatal", 0) > 0:
        return 2
    if counts.get("error", 0) > 0:
        return 1
    if fail_on_warn and counts.get("warn", 0) > 0:
        return 1
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Valida arquivos de configuração JSON em ./config"
    )
    p.add_argument(
        "--config-dir",
        default="config",
        help="Diretório com arquivos .json (default: config)",
    )
    p.add_argument("--json", action="store_true", help="Saída em JSON estruturado")
    p.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Retorna código de erro se houver avisos",
    )
    return p.parse_args(argv)


def main(argv: List[str]) -> int:  # pragma: no cover - entrypoint simplicity
    args = parse_args(argv)
    config_dir = Path(args.config_dir)
    if not config_dir.is_dir():
        print(
            json.dumps(
                {"error": f"Diretório não encontrado: {config_dir}"}, ensure_ascii=False
            )
            if args.json
            else f"ERRO: diretório não encontrado: {config_dir}",
            file=sys.stderr,
        )
        return 2
    issues, _ = scan_configs(config_dir)
    counts = summarize(issues)
    exit_code = compute_exit_code(counts, args.fail_on_warn)
    if args.json:
        payload = {
            "issues": [i.to_dict() for i in issues],
            "summary": counts,
            "exit_code": exit_code,
            "fail_on_warn": args.fail_on_warn,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(issues, counts))
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
