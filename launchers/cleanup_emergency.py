"""cleanup_emergency.py

Script de limpeza emergencial SEGURA para o repositório.

Objetivo: Remover artefatos gerados que possam estar poluindo o ambiente
sem nunca tocar em código-fonte, banco principal ativo ou documentação.

O que pode limpar (sob demanda):
 - __pycache__
 - Arquivos *.pyc
 - Diretório de build temporário (./build/dist, ./build/build, ./build/*.spec)
 - Caches de ferramentas (ex.: .pytest_cache se vier a existir)
 - Backups antigos do banco acima de um limite de retenção

NUNCA remove: `data/ssas.db` atual, diretórios `docs/`, `config/`, `scripts/`, backups mais recentes (retém últimos N), nem arquivos fora da lista de padrões controlados.

Uso rápido:
  python launchers/cleanup_emergency.py --dry-run
  python launchers/cleanup_emergency.py --apply --retain-backups 5

Recomendação: executar primeiro em modo dry-run e revisar saída.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BACKUP_DIR = DATA_DIR / "historico_backups"


def find_paths(patterns: Iterable[str]) -> List[Path]:
    matches: List[Path] = []
    for pattern in patterns:
        for p in ROOT.rglob(pattern):
            # Segurança: ignorar se dentro de .git ou fora do repo root esperado
            if any(part.startswith('.git') for part in p.parts):
                continue
            matches.append(p)
    return matches


def list_pycache() -> List[Path]:
    return [p for p in ROOT.rglob("__pycache__") if p.is_dir()]


def list_pyc_files() -> List[Path]:
    return [p for p in ROOT.rglob("*.pyc") if p.is_file()]


def list_build_artifacts() -> List[Path]:
    patterns = ["*.spec"]
    build_dir = ROOT / "build"
    collected: List[Path] = []
    if build_dir.exists():
        for sub in ["dist", "build"]:
            d = build_dir / sub
            if d.exists():
                collected.append(d)
    for p in find_paths(patterns):
        collected.append(p)
    return collected


def list_tool_caches() -> List[Path]:
    candidates = [ROOT / ".pytest_cache"]
    return [c for c in candidates if c.exists()]


def list_old_backups(retain: int) -> List[Path]:
    if not BACKUP_DIR.exists():
        return []
    backups = sorted([p for p in BACKUP_DIR.iterdir() if p.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)
    if retain <= 0:
        return backups  # tudo (extremo – usar com cuidado)
    return backups[retain:]


def human_size(bytes_: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(bytes_)
    for u in units:
        if size < 1024:
            return f"{size:.1f} {u}"
        size /= 1024
    return f"{size:.1f} TB"


def calc_total_size(paths: Iterable[Path]) -> int:
    total = 0
    for p in paths:
        try:
            if p.is_file():
                total += p.stat().st_size
            elif p.is_dir():
                for sub in p.rglob('*'):
                    if sub.is_file():
                        total += sub.stat().st_size
        except OSError:
            pass
    return total


def remove_path(p: Path) -> None:
    if p.is_file():
        p.unlink(missing_ok=True)
    elif p.is_dir():
        # remove tree
        for sub in sorted(p.rglob('*'), reverse=True):
            try:
                if sub.is_file():
                    sub.unlink(missing_ok=True)
                elif sub.is_dir():
                    sub.rmdir()
            except OSError:
                pass
        try:
            p.rmdir()
        except OSError:
            pass


def build_plan(retain_backups: int) -> dict:
    pycache_dirs = list_pycache()
    pyc_files = list_pyc_files()
    build_items = list_build_artifacts()
    caches = list_tool_caches()
    old_backups = list_old_backups(retain_backups)

    plan = {
        "__pycache__": pycache_dirs,
        "pyc": pyc_files,
        "build_artifacts": build_items,
        "tool_caches": caches,
        "old_backups": old_backups,
    }
    return plan


def print_plan(plan: dict) -> None:
    for key, items in plan.items():
        total_size = human_size(calc_total_size(items))
        print(f"[PLAN] {key}: {len(items)} itens, {total_size}")
        for p in items[:15]:
            print(f"   - {p.relative_to(ROOT)}")
        if len(items) > 15:
            print(f"   ... (+{len(items)-15} mais)")


def apply_plan(plan: dict) -> None:
    for key, items in plan.items():
        print(f"[EXEC] Removendo grupo: {key} ({len(items)} itens)")
        for p in items:
            remove_path(p)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpeza emergencial segura.")
    parser.add_argument("--apply", action="store_true", help="Executa remoções (sem esta flag é dry-run)")
    parser.add_argument("--retain-backups", type=int, default=7, help="Quantos backups recentes manter (default: 7)")
    parser.add_argument("--include-backups", action="store_true", help="Considera limpeza de backups antigos (respeita retenção)")
    parser.add_argument("--no-color", action="store_true", help="Desabilita cores ANSI")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    plan = build_plan(args.retain_backups)
    if not args.include_backups:
        plan["old_backups"] = []  # neutraliza se não solicitado

    print("== MODO", "EXECUCAO" if args.apply else "DRY-RUN")
    print(f"Root: {ROOT}")
    print(f"Retenção de backups: {args.retain_backups} (aplicando: {bool(args.include_backups)})")

    print_plan(plan)

    if not args.apply:
        print("\nNenhuma remoção feita (usar --apply para executar).")
        return 0

    # Confirmação simples
    resp = input("Confirma execução? (digite 'SIM' para continuar): ").strip().upper()
    if resp != "SIM":
        print("Abortado.")
        return 1

    started = time.time()
    apply_plan(plan)
    dur = time.time() - started
    print(f"Concluído em {dur:.2f}s")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
        raise SystemExit(130)

