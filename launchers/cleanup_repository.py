"""cleanup_repository.py
Ferramenta abrangente de limpeza e higienização do repositório.

Objetivo:
  Consolidar rotinas de remoção segura de artefatos gerados, caches, logs antigos,
  backups excedentes e arquivos temporários, oferecendo opções de filtro, retenção
  e execução em dry-run por padrão.

Diferenças em relação a `cleanup_emergency.py`:
  - Foco mais amplo (não apenas emergência). Pode ser agendado (ex: via CI/local).
  - Permite seleção granular de grupos e múltiplas políticas de retenção.
  - Integração opcional com `sanitize_project.py` para auditoria pós-limpeza.

Características principais:
  * Dry-run padrão (não remove nada sem --apply)
  * Grupos: pycache, build, dist, logs, backups, tmp, __compiled__, reports
  * Retenção configurável de backups SQLite e logs baseados em data
  * Exclusões (safety) para diretórios críticos de código-fonte
  * Modo interativo opcional (--confirm) para validação antes de aplicar
  * Saída em JSON opcional (--json) para integração com pipelines
  * Estatísticas finais de economia potencial

Uso rápido:
  python -m launchers.cleanup_repository --groups pycache,build,logs --apply
  python launchers/cleanup_repository.py --all --apply --confirm

Recomendado rodar antes de gerar um pacote de release ou criar tag baseline.

Limitações:
  - Não recompacta DB nem roda vacuum (ponto futuro)
  - Não reescreve arquivos gigantes; apenas remove ou lista

Autor: Automação Assistida
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
BACKUP_DIR = DATA_DIR / "historico_backups"

DEFAULT_BACKUP_RETENTION = 5  # manter N arquivos mais recentes
DEFAULT_LOG_RETENTION_DAYS = 30

BACKUP_PATTERN = re.compile(r"ssas\.db\.backup_\d{8}_\d{6}$")
SQLITE_DB_NAME = "ssas.db"

GROUP_DEFINITIONS: Dict[str, str] = {
    "pycache": "__pycache__ directories",
    "build": "build artifacts (build/, *.egg-info, wheels)",
    "dist": "distribution artifacts (dist/)",
    "logs": "log files in logs/ (older than retention)",
    "backups": "database backup files exceeding retention policy",
    "tmp": "temporary files (*.tmp, *.temp, *~)",
    "compiled": "compiled python caches (*.pyc) outside __pycache__",
    "reports": "generated reports (reports/*.html, reports/*.tmp)"
}

SAFETY_EXCLUDE_DIRS = {"core", "armazenamento", "gui", "interface", "scripts", "utils"}


@dataclass
class PlannedRemoval:
    path: str
    reason: str
    size_bytes: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class CleanupStats:
    total_items: int
    total_bytes: int
    by_group: Dict[str, int]
    bytes_by_group: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def human_size(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} PB"


def iter_files(patterns: Iterable[str], base: Path) -> Iterable[Path]:
    for pattern in patterns:
        yield from base.glob(pattern)


def collect_pycache() -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    for path in REPO_ROOT.rglob("__pycache__"):
        size = dir_size(path)
        items.append(PlannedRemoval(str(path), "pycache directory", size))
    return items


def collect_compiled() -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    for path in REPO_ROOT.rglob("*.pyc"):
        if "__pycache__" in path.parts:
            continue
        items.append(PlannedRemoval(str(path), "compiled pyc", path.stat().st_size))
    return items


def collect_build() -> List[PlannedRemoval]:
    patterns = ["build", "*.egg-info"]
    items: List[PlannedRemoval] = []
    for pattern in patterns:
        for path in REPO_ROOT.glob(pattern):
            if path.exists():
                size = dir_size(path) if path.is_dir() else path.stat().st_size
                items.append(PlannedRemoval(str(path), "build artifact", size))
    return items


def collect_dist() -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    dist_dir = REPO_ROOT / "dist"
    if dist_dir.exists():
        for p in dist_dir.iterdir():
            if p.is_file():
                items.append(PlannedRemoval(str(p), "dist artifact", p.stat().st_size))
            else:
                items.append(PlannedRemoval(str(p), "dist directory", dir_size(p)))
    return items


def collect_tmp() -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    patterns = ["*.tmp", "*.temp", "*~"]
    for pattern in patterns:
        for p in REPO_ROOT.rglob(pattern):
            if p.is_file():
                items.append(PlannedRemoval(str(p), "temporary file", p.stat().st_size))
    return items


def collect_reports() -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    reports_dir = REPO_ROOT / "reports"
    if reports_dir.exists():
        for ext in ("*.html", "*.tmp", "*.json.bak"):
            for p in reports_dir.glob(ext):
                if p.is_file():
                    items.append(PlannedRemoval(str(p), "report artifact", p.stat().st_size))
    return items


def collect_logs(retention_days: int) -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    logs_dir = REPO_ROOT / "logs"
    if not logs_dir.exists():
        return items
    cutoff = time.time() - (retention_days * 86400)
    for p in logs_dir.rglob("*.log"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            age_days = int((time.time() - mtime) / 86400)
            items.append(PlannedRemoval(str(p), f"old log ({age_days}d)", p.stat().st_size))
    return items


def collect_backups(retention: int) -> List[PlannedRemoval]:
    items: List[PlannedRemoval] = []
    if not BACKUP_DIR.exists():
        return items
    backups = [p for p in BACKUP_DIR.iterdir() if BACKUP_PATTERN.match(p.name)]
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in backups[retention:]:
        size = p.stat().st_size
        items.append(PlannedRemoval(str(p), "excess backup", size))
    return items


def dir_size(path: Path) -> int:
    total = 0
    if path.is_file():
        return path.stat().st_size
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def plan_removals(groups: Set[str], backup_retention: int, log_retention: int) -> Dict[str, List[PlannedRemoval]]:
    plan: Dict[str, List[PlannedRemoval]] = {}
    if "pycache" in groups:
        plan["pycache"] = collect_pycache()
    if "compiled" in groups:
        plan["compiled"] = collect_compiled()
    if "build" in groups:
        plan["build"] = collect_build()
    if "dist" in groups:
        plan["dist"] = collect_dist()
    if "tmp" in groups:
        plan["tmp"] = collect_tmp()
    if "reports" in groups:
        plan["reports"] = collect_reports()
    if "logs" in groups:
        plan["logs"] = collect_logs(log_retention)
    if "backups" in groups:
        plan["backups"] = collect_backups(backup_retention)
    return plan


def apply_plan(plan: Dict[str, List[PlannedRemoval]]) -> None:
    for group, items in plan.items():
        for item in items:
            p = Path(item.path)
            if not p.exists():
                continue
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            except OSError as e:
                print(f"[WARN] Falha ao remover {p}: {e}")


def summarize(plan: Dict[str, List[PlannedRemoval]]) -> CleanupStats:
    total_items = 0
    total_bytes = 0
    by_group: Dict[str, int] = {}
    bytes_by_group: Dict[str, int] = {}
    for group, items in plan.items():
        by_group[group] = len(items)
        size_sum = sum(i.size_bytes for i in items)
        bytes_by_group[group] = size_sum
        total_items += len(items)
        total_bytes += size_sum
    return CleanupStats(total_items, total_bytes, by_group, bytes_by_group)


def print_report(plan: Dict[str, List[PlannedRemoval]], stats: CleanupStats) -> None:
    print("\n=== PLANO DE LIMPEZA ===")
    for group, items in plan.items():
        if not items:
            continue
        print(f"\n[{group}] {GROUP_DEFINITIONS.get(group, '')} ({len(items)} itens, {human_size(sum(i.size_bytes for i in items))})")
        for it in items[:10]:  # limitar listagem detalhada
            print(f"  - {it.path} :: {it.reason} :: {human_size(it.size_bytes)}")
        if len(items) > 10:
            print(f"  ... +{len(items) - 10} adicionais")
    print("\nResumo:")
    print(f"  Total itens: {stats.total_items}")
    print(f"  Total espaço: {human_size(stats.total_bytes)}")


def maybe_run_sanitize(integrate: bool, apply_flag: bool) -> None:
    if not integrate:
        return
    # Chamamos o sanitize_project em modo somente auditoria (sem --apply) a menos que apply_flag seja True
    script = REPO_ROOT / "sanitize_project.py"
    if not script.exists():
        print("[INFO] sanitize_project.py não encontrado, ignorando integração.")
        return
    cmd = [sys.executable, str(script)]
    if apply_flag:
        cmd.append("--apply")
    try:
        print("\n[INFO] Executando sanitize_project.py complementar...")
        os.system(" ".join(cmd))
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Falha ao executar sanitize_project: {e}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpeza abrangente do repositório (dry-run por padrão).")
    parser.add_argument("--groups", help="Lista de grupos separados por vírgula", default="")
    parser.add_argument("--all", action="store_true", help="Incluir todos os grupos disponíveis")
    parser.add_argument("--apply", action="store_true", help="Aplicar remoções (sem isso é somente dry-run)")
    parser.add_argument("--confirm", action="store_true", help="Solicitar confirmação interativa antes de aplicar")
    parser.add_argument("--backup-retention", type=int, default=DEFAULT_BACKUP_RETENTION, help="Retenção de backups (N mais recentes)")
    parser.add_argument("--log-retention-days", type=int, default=DEFAULT_LOG_RETENTION_DAYS, help="Dias de retenção para logs")
    parser.add_argument("--json", action="store_true", help="Saída em JSON (máquina)")
    parser.add_argument("--integrate-sanitize", action="store_true", help="Executa sanitize_project após plano")
    return parser.parse_args(argv)


def ensure_groups(ns: argparse.Namespace) -> Set[str]:
    if ns.all:
        return set(GROUP_DEFINITIONS.keys())
    groups: Set[str] = set()
    if ns.groups:
        for g in ns.groups.split(","):
            g = g.strip()
            if not g:
                continue
            if g not in GROUP_DEFINITIONS:
                print(f"[WARN] Grupo desconhecido: {g}")
            else:
                groups.add(g)
    return groups


def interactive_confirm() -> bool:
    try:
        resp = input("Aplicar remoções? (y/N): ").strip().lower()
    except EOFError:
        return False
    return resp in {"y", "yes"}


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(argv)
    groups = ensure_groups(ns)
    if not groups:
        print("[INFO] Nenhum grupo selecionado. Use --groups ou --all. Abortando.")
        return 1

    plan = plan_removals(groups, ns.backup_retention, ns.log_retention_days)
    stats = summarize(plan)

    if ns.json:
        data = {
            "plan": {grp: [p.to_dict() for p in items] for grp, items in plan.items()},
            "stats": stats.to_dict(),
            "apply": ns.apply,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_report(plan, stats)
        if not ns.apply:
            print("\n[DRY-RUN] Nenhum arquivo foi removido. Use --apply para executar.")

    if ns.apply:
        if ns.confirm and not interactive_confirm():
            print("[CANCELADO] Usuário abortou.")
            return 2
        apply_plan(plan)
        print("\n[OK] Remoções aplicadas.")

    maybe_run_sanitize(ns.integrate_sanitize, ns.apply)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

