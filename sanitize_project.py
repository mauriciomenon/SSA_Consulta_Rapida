"""sanitize_project.py

Ferramenta de auditoria e saneamento leve do repositório.

Objetivos:
 - Detectar nomes de arquivos fora do padrão (acentos, espaços, maiúsculas excessivas).
 - Identificar arquivos Markdown potencialmente problemáticos (vazios ou só título).
 - Listar diretórios __pycache__ e arquivos *.pyc.
 - Opcionalmente (com --apply) propor ou executar renomeação segura.
 - Nunca alterar conteúdo lógico sem confirmação explícita.

Uso:
  python sanitize_project.py               # relatório (dry-run)
  python sanitize_project.py --apply       # aplica renomeações simples
  python sanitize_project.py --fix-docs    # injeta placeholder TODO em docs vazios

Padrões Aplicados:
 - snake_case ASCII para arquivos Python / scripts / docs técnicos.
 - Prefixos documentais conforme README_DOCS.
"""

from __future__ import annotations

import argparse
import os
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent
MD_EXT = ".md"

def normalize_ascii(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # substituir espaços e hifens por underscore
    s = re.sub(r"[\s-]+", "_", only_ascii)
    # lowercase
    s = s.lower()
    # remover chars não permitidos exceto . _
    s = re.sub(r"[^a-z0-9._]", "", s)
    # normalizar múltiplos underscores
    s = re.sub(r"__+", "_", s)
    return s


def is_markdown_empty_or_title_only(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    lines = [line.rstrip() for line in text.splitlines()]
    meaningful = [line for line in lines if line.strip()]
    if not meaningful:
        return True
    if len(meaningful) == 1 and meaningful[0].startswith("#"):
        return True
    return False


def collect_markdown_issues(base: Path) -> List[Path]:
    issues: List[Path] = []
    for p in base.rglob("*.md"):
        if is_markdown_empty_or_title_only(p):
            issues.append(p)
    return issues


def collect_bad_names(base: Path) -> List[Tuple[Path, str]]:
    problems: List[Tuple[Path, str]] = []
    allowed_upper_docs = {"README.md", "LICENSE"}
    for p in base.rglob("*"):
        if p.is_dir():
            continue
        name = p.name
        # pular .git / virtual envs
        if any(part.startswith('.git') for part in p.parts):
            continue
        if name in allowed_upper_docs:
            continue
        ascii_norm = normalize_ascii(name)
        if ascii_norm != name.lower():
            problems.append((p, ascii_norm))
    return problems


def collect_pycache(base: Path) -> List[Path]:
    return [p for p in base.rglob("__pycache__") if p.is_dir()]


def rename_file(src: Path, normalized: str) -> Path:
    target = src.with_name(normalized)
    if target.exists():
        # conflito simple: adicionar sufixo incremental
        stem, suffix = os.path.splitext(normalized)
        i = 1
        while target.exists():
            target = src.with_name(f"{stem}_{i}{suffix}")
            i += 1
    src.rename(target)
    return target


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Auditoria e saneamento do repositório")
    ap.add_argument("--apply", action="store_true", help="Aplica renomeações de nomes problemáticos")
    ap.add_argument("--fix-docs", action="store_true", help="Adiciona placeholder TODO em docs vazios/título único")
    ap.add_argument("--limit", type=int, default=50, help="Limite máximo de itens listados por categoria")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Root: {ROOT}")
    bad_names = collect_bad_names(ROOT)
    md_issues = collect_markdown_issues(ROOT)
    pycache_dirs = collect_pycache(ROOT)

    print("\n=== RELATÓRIO ===")
    print(f"Nomes potencialmente inconsistentes: {len(bad_names)}")
    for p, norm in bad_names[: args.limit]:
        print(f"  - {p.relative_to(ROOT)} -> {norm}")
    if len(bad_names) > args.limit:
        print("  ... (truncado)")

    print(f"Docs vazios / só título: {len(md_issues)}")
    for p in md_issues[: args.limit]:
        print(f"  - {p.relative_to(ROOT)}")
    if len(md_issues) > args.limit:
        print("  ... (truncado)")

    print(f"Diretórios __pycache__: {len(pycache_dirs)}")
    for d in pycache_dirs[: args.limit]:
        print(f"  - {d.relative_to(ROOT)}")
    if len(pycache_dirs) > args.limit:
        print("  ... (truncado)")

    if not args.apply and not args.fix_docs:
        print("\nModo dry-run (nenhuma alteração). Use --apply e/ou --fix-docs para modificar.")
        return 0

    if args.apply:
        print("\n== APLICANDO RENOMEAÇÕES ==")
        for p, norm in bad_names:
            new_path = rename_file(p, norm)
            print(f"  Renomeado: {p.name} -> {new_path.name}")

    if args.fix_docs:
        print("\n== AJUSTANDO DOCS VAZIOS ==")
        for p in md_issues:
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            if text.strip():
                # se for só título, acrescentar placeholder
                lines = text.splitlines()
                if len([line for line in lines if line.strip()]) == 1:
                    p.write_text(text + "\n\nTODO: completar conteúdo deste documento.\n", encoding="utf-8")
            else:
                p.write_text("# TODO\n\nTODO: completar conteúdo deste documento.\n", encoding="utf-8")
            print(f"  Placeholder adicionado: {p.relative_to(ROOT)}")

    print("\nConcluído.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

