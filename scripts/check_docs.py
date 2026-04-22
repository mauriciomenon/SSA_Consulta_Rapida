"""check_docs.py
Validador de documentação Markdown.

Objetivo:
  Garantir que nenhum arquivo .md relevante esteja vazio ou com conteúdo
  placeholder inadequado, aplicando regras simples e rápidas para gate em CI.

Características:
  * Busca recursiva a partir da raiz (exclui diretórios ignorados).
  * Regras: linhas mínimas, densidade de conteúdo, detecção de placeholders.
  * Saída humana padrão + opção --json.
  * Código de saída:
      0 -> sucesso sem issues
      1 -> issues encontradas (falha de qualidade)
      2 -> erro interno (exceção inesperada)
  * Pode filtrar diretórios e excluir padrões.

Uso rápido:
  python scripts/check_docs.py
  python scripts/check_docs.py --min-lines 6 --fail-on-issues --json

Futuras extensões (não implementadas agora):
  - Validação de links quebrados.
  - Análise de seções obrigatórias por tipo.
  - Integração com agregador de índice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MIN_LINES = 5
DEFAULT_MIN_NONEMPTY = 3
PLACEHOLDER_PATTERNS = [
    r"^TODO$",
    r"^TBD$",
    r"^EM\s+BRANCO$",
    r"^PREENCHER$",
    r"^lorem ipsum.*$",
    r"^conteudo pendente$",
    r"^conteúdo pendente$",
]
COMPILED_PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS
]
IGNORE_DIRS = {
    ".git",
    ".opencode",
    "__pycache__",
    "build",
    "dist",
    "data",
    "node_modules",
    "venv",
    ".venv",
    ".tox",
    ".mypy_cache",
    ".trunk",
    ".specstory",
    "local_ai_private",
}
MARKDOWN_EXT = ".md"

# Arquivos conhecidos (placeholders / templates) permitidos vazios para não quebrar smoke.
ALLOW_EMPTY_FILES = {
    "WARP.md",
    "docs/VARREDURA_METODOS_COMPLETA.md",
    "docs/BUILD_ANALYSIS.md",
    "docs/ORGANIZACAO_DOCS.md",
    "docs/LOG_CONFIGURACAO_COPILOT_COMPLETA_20250907.md",
    "docs/ONBOARDING.md",
    "launchers/GUIA_PRIVACIDADE_IMPLEMENTACAO_LIMPO.md",
    "launchers/ESTRUTURA_GERAL_v3.10.md",
    "launchers/ARQUIVOS_NAO_COMMITTAR.md",
    "launchers/GESTAO_ARTEFATOS_BUILD.md",
    ".github/copilot-instructions.md",
}


@dataclass
class DocIssue:
    path: str
    issue_type: str
    detail: str
    lines: int
    nonempty: int

    def to_dict(self) -> Dict[str, object]:  # noqa: D401
        return asdict(self)


@dataclass
class ScanStats:
    total_files: int
    checked_files: int
    issues_count: int
    min_lines: int
    min_nonempty: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def list_markdown_files(base: Path) -> Iterable[Path]:
    if base.name in IGNORE_DIRS:
        return
    for root, dirs, files in os.walk(base):
        root_path = Path(root)
        # Filtra dirs ignorados in-place (evita caminhada profunda neles)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.lower().endswith(MARKDOWN_EXT):
                yield root_path / f


def read_file_lines(path: Path) -> List[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:  # noqa: BLE001
        return [f"__ERROR__ {e}"]


def has_placeholder(lines: Sequence[str]) -> Optional[str]:
    lowered = [line.strip().lower() for line in lines if line.strip()]
    for pattern, regex in zip(
        PLACEHOLDER_PATTERNS, COMPILED_PLACEHOLDER_PATTERNS, strict=False
    ):
        for original in lowered:
            if regex.fullmatch(original):
                return pattern
    return None


def evaluate_file(path: Path, min_lines: int, min_nonempty: int) -> Optional[DocIssue]:
    lines = read_file_lines(path)
    rel_str: str | None = None
    try:
        rel_path = path.resolve().relative_to(REPO_ROOT.resolve())
        rel_str = rel_path.as_posix()
    except ValueError:
        rel_path = None
    allow_empty_file = bool(
        rel_str in ALLOW_EMPTY_FILES
        or (rel_path == Path(path.name) and path.name in ALLOW_EMPTY_FILES)
    )
    if allow_empty_file:
        return None
    if not lines:
        return DocIssue(str(path), "empty", "arquivo sem linhas", 0, 0)
    total = len(lines)
    nonempty = sum(1 for line in lines if line.strip())
    if total < min_lines:
        return DocIssue(
            str(path), "too_few_lines", f"linhas={total} < {min_lines}", total, nonempty
        )
    if nonempty < min_nonempty:
        return DocIssue(
            str(path),
            "too_sparse",
            f"não-vazias={nonempty} < {min_nonempty}",
            total,
            nonempty,
        )
    placeholder = has_placeholder(lines)
    if placeholder:
        return DocIssue(
            str(path),
            "placeholder",
            f"padrao detectado: {placeholder}",
            total,
            nonempty,
        )
    return None


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida arquivos Markdown do repositório."
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=DEFAULT_MIN_LINES,
        help="Mínimo de linhas totais por arquivo",
    )
    parser.add_argument(
        "--min-nonempty",
        type=int,
        default=DEFAULT_MIN_NONEMPTY,
        help="Mínimo de linhas não vazias",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Retorna código 1 se encontrar issues",
    )
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    parser.add_argument("--output", help="Arquivo para gravar JSON (quando --json)")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe arquivos analisados e status simplificado",
    )
    parser.add_argument(
        "--paths", nargs="*", help="Lista opcional de caminhos/dirs para filtrar"
    )
    parser.add_argument(
        "--exclude", nargs="*", help="Padrões simples (substring) a excluir"
    )
    return parser.parse_args(argv)


def match_exclude(path: Path, excludes: Optional[Sequence[str]]) -> bool:
    if not excludes:
        return False
    path_str = str(path)
    return any(excl in path_str for excl in excludes)


def filter_targets(paths: Optional[Sequence[str]]) -> List[Path]:
    if not paths:
        return list(list_markdown_files(REPO_ROOT))
    result: List[Path] = []
    for p in paths:
        target = REPO_ROOT / p
        if target.is_dir():
            result.extend(list_markdown_files(target))
        elif target.is_file() and target.name.lower().endswith(MARKDOWN_EXT):
            result.append(target)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(argv)
    try:
        candidates = filter_targets(ns.paths)
        checked: List[Path] = []
        issues: List[DocIssue] = []
        for md in candidates:
            if match_exclude(md, ns.exclude):
                continue
            issue = evaluate_file(md, ns.min_lines, ns.min_nonempty)
            if issue:
                issues.append(issue)
            checked.append(md)
            if ns.verbose:
                status = issue.issue_type if issue else "ok"
                print(f"[DOC] {md.relative_to(REPO_ROOT)} :: {status}", flush=True)

        stats = ScanStats(
            total_files=len(candidates),
            checked_files=len(checked),
            issues_count=len(issues),
            min_lines=ns.min_lines,
            min_nonempty=ns.min_nonempty,
        )

        if ns.json:
            payload = {
                "stats": stats.to_dict(),
                "issues": [i.to_dict() for i in issues],
            }
            serialized = json.dumps(payload, indent=2, ensure_ascii=False)
            print(serialized, flush=True)
            if ns.output:
                try:
                    Path(ns.output).parent.mkdir(parents=True, exist_ok=True)
                    Path(ns.output).write_text(serialized, encoding="utf-8")
                except Exception as write_err:  # noqa: BLE001
                    print(
                        json.dumps(
                            {"warning": f"falha ao gravar output: {write_err}"},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
        else:
            print("=== CHECK DOCS REPORT ===")
            print(f"Arquivos candidatos: {stats.total_files}")
            print(f"Arquivos verificados: {stats.checked_files}")
            print(f"Issues: {stats.issues_count}")
            if issues:
                print("\nDetalhes:")
                for i in issues[:50]:
                    print(
                        f" - {i.path} :: {i.issue_type} :: {i.detail} (linhas={i.lines}, não-vazias={i.nonempty})"
                    )
                if len(issues) > 50:
                    print(f"... +{len(issues) - 50} adicionais")
            else:
                print("Nenhuma issue encontrada.")

        if issues and ns.fail_on_issues:
            return 1
        return 0
    except Exception as e:  # noqa: BLE001
        if ns.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"[ERRO] Falha inesperada: {e}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
