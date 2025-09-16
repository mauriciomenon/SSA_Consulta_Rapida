#!/usr/bin/env python3
"""Ferramenta de limpeza manual assistida (modo guiado / interativo).

Objetivo:
  Complementar `cleanup_repository.py` e `cleanup_emergency.py` oferecendo um
  caminho controlado para apagar seletivamente artefatos gerados durante
  desenvolvimento quando o usuário quer validar antes de cada ação.

Características:
  * Dry-run por padrão (não remove nada sem --apply ou confirmação interativa)
  * Seleção de grupos: pycache, builds, dist, logs, backups antigos, tmp, reports
  * Modo interativo (--interactive) pergunta antes de cada grupo
  * Filtros de idade para logs e backups (--max-backups, --days-logs)
  * Saída opcional em JSON (--json) para integração automatizada
  * Códigos de saída: 0 sucesso / 1 erros de remoção / 2 erro interno (exceção não tratada)

Quando usar este script:
  - Revisões pontuais (ex: quero remover só logs) sem rodar limpeza global.
  - Antes de criar baseline mas desejando validar cada ação.
  - Investigação: gerar relatório do que seria apagado (dry-run).

Evitar usar quando:
  - Necessário limpeza completa (usar `cleanup_repository.py`).
  - Situação emergencial de espaço (usar `cleanup_emergency.py`).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
BACKUP_DIR = DATA_DIR / "historico_backups"


# --------------------------- Data Structures ---------------------------------
@dataclass
class TargetItem:
    path: Path
    size: int
    category: str

    def to_dict(self) -> Dict:
        return {"path": str(self.path), "size": self.size, "category": self.category}


# --------------------------- Discovery Logic ----------------------------------
def iter_pycache(root: Path) -> Iterable[TargetItem]:
    for p in root.rglob("__pycache__"):
        if p.is_dir():
            size = dir_size(p)
            yield TargetItem(p, size, "pycache")


def iter_build_dirs(root: Path) -> Iterable[TargetItem]:
    for name in ("build", "dist"):
        p = root / name
        if p.exists() and p.is_dir():
            yield TargetItem(p, dir_size(p), name)


def iter_logs(root: Path, max_age_days: int) -> Iterable[TargetItem]:
    threshold = datetime.now() - timedelta(days=max_age_days)
    logs_dir = root / "logs"
    if logs_dir.exists():
        for file in logs_dir.glob("**/*"):
            if file.is_file():
                try:
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < threshold:
                        yield TargetItem(file, file.stat().st_size, "logs")
                except OSError:
                    continue


def iter_tmp(root: Path) -> Iterable[TargetItem]:
    for name in ("tmp", "temp", ".tmp"):
        p = root / name
        if p.exists() and p.is_dir():
            yield TargetItem(p, dir_size(p), "tmp")


def iter_reports(root: Path) -> Iterable[TargetItem]:
    reports_dir = root / "reports"
    if reports_dir.exists():
        for f in reports_dir.glob("**/*"):
            if f.is_file():
                yield TargetItem(f, f.stat().st_size, "reports")


def iter_old_backups(backup_dir: Path, max_keep: int) -> Iterable[TargetItem]:
    if not backup_dir.exists():
        return
    backups = [p for p in backup_dir.glob("ssas.db.backup_*") if p.is_file()]
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    for old in backups[max_keep:]:
        yield TargetItem(old, old.stat().st_size, "backups_old")


def dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


# --------------------------- Core Cleanup -------------------------------------
def gather_targets(args) -> List[TargetItem]:
    targets: List[TargetItem] = []
    root = REPO_ROOT
    if args.pycache:
        targets.extend(iter_pycache(root))
    if args.builds:
        targets.extend(iter_build_dirs(root))
    if args.logs:
        targets.extend(iter_logs(root, args.days_logs))
    if args.tmp:
        targets.extend(iter_tmp(root))
    if args.reports:
        targets.extend(iter_reports(root))
    if args.backups:
        targets.extend(iter_old_backups(BACKUP_DIR, args.max_backups))
    # Ordena por categoria -> tamanho desc
    targets.sort(key=lambda t: (t.category, -t.size))
    return targets


def human_size(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def confirm(prompt: str) -> bool:
    try:
        return input(prompt + " [y/N]: ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def apply_removals(targets: List[TargetItem], args) -> Dict[str, List[str]]:
    removed, errors = [], []
    for item in targets:
        # Interativo: pergunta por categoria quando vê a primeira vez
        if args.interactive:
            if not confirm(f"Remover categoria '{item.category}' em {item.path}?"):
                continue
        if args.dry_run and not args.apply:
            continue
        try:
            if item.path.is_dir():
                shutil.rmtree(item.path)
            else:
                item.path.unlink(missing_ok=True)
            removed.append(str(item.path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{item.path}: {exc}")
    return {"removed": removed, "errors": errors}


# --------------------------- CLI Argparse -------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Limpeza manual assistida (seletiva, segura).")
    g = p.add_argument_group("Seleção de grupos")
    g.add_argument("--pycache", action="store_true", help="Incluir diretórios __pycache__")
    g.add_argument("--builds", action="store_true", help="Incluir pastas build/ e dist/")
    g.add_argument("--logs", action="store_true", help="Incluir logs antigos (baseado em --days-logs)")
    g.add_argument("--tmp", action="store_true", help="Incluir diretórios tmp/temp")
    g.add_argument("--reports", action="store_true", help="Incluir arquivos em reports/")
    g.add_argument("--backups", action="store_true", help="Incluir backups antigos (excede --max-backups)")

    p.add_argument("--days-logs", type=int, default=14, help="Idade mínima (dias) para logs serem removidos (default: 14)")
    p.add_argument("--max-backups", type=int, default=5, help="Quantidade de backups recentes a manter (default: 5)")
    p.add_argument("--apply", action="store_true", help="Aplica remoções efetivamente (sem isto é só dry-run)")
    p.add_argument("--interactive", action="store_true", help="Pede confirmação para cada categoria")
    p.add_argument("--json", action="store_true", help="Saída em JSON estruturado")
    p.add_argument("--no-color", action="store_true", help="Desabilita cores ANSI na saída texto")
    p.add_argument("--dry-run", action="store_true", help="Força modo dry-run mesmo se --apply for passado (prioridade)")
    return p


def colorize(s: str, code: str, enable: bool) -> str:
    if not enable:
        return s
    return f"\033[{code}m{s}\033[0m"


def main(argv: List[str] | None = None) -> int:  # pragma: no cover - orquestração
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        targets = gather_targets(args)
        total_size = sum(t.size for t in targets)
        total_count = len(targets)
        if args.json:
            result = {"targets": [t.to_dict() for t in targets], "total_count": total_count, "total_size": total_size, "dry_run": (args.dry_run or not args.apply)}
        else:
            use_color = not args.no_color and sys.stdout.isatty()
            header = f"Encontrados {total_count} itens em {len({t.category for t in targets})} categorias | Tamanho total: {human_size(total_size)}"
            print(colorize(header, "36", use_color))
            current_cat = None
            for t in targets:
                if t.category != current_cat:
                    current_cat = t.category
                    print(colorize(f"\n[{current_cat}]", "33", use_color))
                print(f"  - {human_size(t.size):>8}  {t.path}")
            mode = "DRY-RUN" if (args.dry_run or not args.apply) else "APLICAÇÃO"
            print(colorize(f"\nModo: {mode}", "35", use_color))

        removal_info = apply_removals(targets, args)
        success = len(removal_info["errors"]) == 0
        exit_code = 0 if success else 1
        if args.json:
            result.update(removal_info)
            result["exit_code"] = exit_code
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if removal_info["removed"]:
                print(colorize(f"\nRemovidos: {len(removal_info['removed'])}", "32", True))
            if removal_info["errors"]:
                print(colorize(f"Erros: {len(removal_info['errors'])}", "31", True))
                for e in removal_info["errors"]:
                    print("  !", e)
        return exit_code
    except KeyboardInterrupt:  # pragma: no cover
        print("\nInterrompido pelo usuário.")
        return 2
    except Exception as exc:  # noqa: BLE001
        if args.json:
            print(json.dumps({"fatal": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERRO fatal: {exc}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

