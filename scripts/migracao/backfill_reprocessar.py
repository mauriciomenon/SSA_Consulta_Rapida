"""Reprocessa (backfill) planilhas em um diretório usando o importador robusto e smart upsert.

Uso:
  python scripts/migracao/backfill_reprocessar.py \
      --dir docs_entrada \
      --db data/ssas.db \
      --pattern "*.xlsx" \
      --smart-upsert \
      --dry-run

Características:
- Ordena arquivos por data inferida no nome (DD-MM-YYYY ou YYYY-MM-DD) ou mtime como fallback.
- Suporta --since "2025-09-10" para ignorar arquivos mais antigos.
- Mostra estatísticas agregadas e individuais (--verbose para detalhar cada import).
- Em caso de erro de inserção de um arquivo, registra e prossegue (relatório final inclui falhas).
- Usa sempre `config/schema_unified.sql` se --reset-db for passado.

Limitações:
- Não tenta detectar conflitos avançados além do smart upsert já implementado no módulo database.
- Não remove dados antigos; foco é enriquecer colunas novas.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Garantir raiz do projeto no sys.path quando executado diretamente
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from armazenamento import database  # noqa: E402
from utils.robust_importer import import_excel_robust  # noqa: E402

logger = logging.getLogger("backfill_reprocessar")

DATE_PATTERNS = [
    re.compile(r"(\d{2})-(\d{2})-(\d{4})"),  # DD-MM-YYYY
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),  # YYYY-MM-DD
]


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill de planilhas SSA")
    p.add_argument("--dir", default="docs_entrada", help="Diretório com planilhas")
    p.add_argument("--db", default="data/ssas.db", help="Banco alvo")
    p.add_argument("--pattern", default="*.xlsx", help="Glob de seleção de arquivos")
    p.add_argument(
        "--smart-upsert", action="store_true", help="Aplicar smart upsert (numero_ssa)"
    )
    p.add_argument("--dry-run", action="store_true", help="Não insere no banco")
    p.add_argument(
        "--limit", type=int, default=None, help="Limitar número de arquivos processados"
    )
    p.add_argument(
        "--since",
        type=str,
        default=None,
        help="Considerar apenas arquivos >= data (YYYY-MM-DD)",
    )
    p.add_argument(
        "--reset-db", action="store_true", help="Recria schema_unified antes de começar"
    )
    p.add_argument("--verbose", action="store_true", help="Logs adicionais por arquivo")
    p.add_argument(
        "--mappings",
        default="config/column_mappings.json",
        help="Arquivo de mapeamento de colunas",
    )
    p.add_argument(
        "--report-path",
        default=None,
        help="Salvar relatório JSON neste caminho específico (senão gera nome automático em reports/)",
    )
    return p.parse_args(argv)


def infer_date_from_name(name: str) -> Optional[datetime]:
    for pat in DATE_PATTERNS:
        m = pat.search(name)
        if m:
            if pat.pattern.startswith("(\\d{2})-"):
                # DD-MM-YYYY
                d, mth, y = m.groups()
                try:
                    return datetime(int(y), int(mth), int(d))
                except ValueError:
                    return None
            else:
                # YYYY-MM-DD
                y, mth, d = m.groups()
                try:
                    return datetime(int(y), int(mth), int(d))
                except ValueError:
                    return None
    return None


@dataclass
class FileResult:
    path: Path
    rows_in: int = 0
    rows_out: int = 0
    mapped_cols: int = 0
    success: bool = True
    error: str | None = None
    skipped: bool = False
    inserted: int = 0
    stats_raw: dict = field(default_factory=dict)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    root = Path(args.dir)
    if not root.exists():
        logger.error("Diretório não existe: %s", root)
        return 2

    if args.reset_db:
        logger.info("Recriando schema unificado no banco: %s", args.db)
        database.reset_database(args.db, mode="file")
        database.initialize_database(args.db, "schema_unified.sql")

    cutoff = None
    if args.since:
        try:
            cutoff = datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            logger.error("Formato inválido para --since (esperado YYYY-MM-DD)")
            return 2

    files = sorted(root.glob(args.pattern))

    # Ordenar por data inferida (fallback mtime)
    def sort_key(p: Path):
        dt = infer_date_from_name(p.name)
        if not dt:
            dt = datetime.fromtimestamp(p.stat().st_mtime)
        return dt, p.name

    files = sorted(files, key=sort_key)

    selected: List[Path] = []
    for f in files:
        if cutoff:
            dt = infer_date_from_name(f.name)
            if dt and dt < cutoff:
                continue
        selected.append(f)
        if args.limit and len(selected) >= args.limit:
            break

    if not selected:
        logger.info(
            "Nenhum arquivo elegível para processar (pattern=%s, since=%s). Nada a fazer.",
            args.pattern,
            args.since,
        )
        # Mesmo assim gerar relatório vazio se --report-path informado
        if args.report_path:
            os.makedirs(os.path.dirname(args.report_path) or ".", exist_ok=True)
            with open(args.report_path, "w", encoding="utf-8") as fh:
                json.dump({"summary": {"files_processed": 0}, "results": []}, fh)
            logger.info("Relatório vazio salvo em: %s", args.report_path)
        return 0

    logger.info(
        "Processando %d arquivos (limit=%s, since=%s)",
        len(selected),
        args.limit,
        args.since,
    )

    results: List[FileResult] = []

    for path in selected:
        fr = FileResult(path=path)
        try:
            if args.verbose:
                logger.info("[START] %s", path.name)
            df, stats = import_excel_robust(str(path), mappings_path=args.mappings)
            fr.rows_in = stats.get("total_rows_in", 0)
            fr.rows_out = stats.get("total_rows_out", 0)
            fr.mapped_cols = stats.get("mapped_columns_count", 0)
            fr.stats_raw = stats
            if args.dry_run:
                fr.success = True
            else:
                if df.empty:
                    fr.success = True
                    fr.inserted = 0
                else:
                    if args.smart_upsert:
                        ok = database.insert_dataframe_with_smart_upsert(
                            df, args.db, "ssa_table"
                        )
                    else:
                        ok = database.insert_dataframe_to_db(df, args.db, "ssa_table")
                    fr.success = ok
                    if ok:
                        fr.inserted = fr.rows_out
        except Exception as e:  # pragma: no cover
            fr.success = False
            fr.error = str(e)
            logger.error("Falha ao processar %s: %s", path.name, e)
        finally:
            if args.verbose:
                logger.info(
                    "[END] %s => success=%s mapped_cols=%d",
                    path.name,
                    fr.success,
                    fr.mapped_cols,
                )
        results.append(fr)

    # Agregado
    total_in = sum(r.rows_in for r in results)
    total_out = sum(r.rows_out for r in results)
    total_inserted = sum(r.inserted for r in results)
    failures = [r for r in results if not r.success]

    summary = {
        "files_processed": len(results),
        "files_failed": len(failures),
        "total_rows_in": total_in,
        "total_rows_out": total_out,
        "total_inserted": total_inserted,
        "avg_mapped_cols": round(sum(r.mapped_cols for r in results) / len(results), 2),
    }
    logger.info("Resumo Backfill: %s", json.dumps(summary, ensure_ascii=False))

    # Salvar relatório detalhado
    os.makedirs("reports", exist_ok=True)
    if args.report_path:
        report_path = args.report_path
        os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    else:
        report_path = os.path.join(
            "reports",
            f"backfill_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        )
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "summary": summary,
                "results": [
                    {
                        "file": str(r.path),
                        "rows_in": r.rows_in,
                        "rows_out": r.rows_out,
                        "mapped_cols": r.mapped_cols,
                        "success": r.success,
                        "error": r.error,
                        "inserted": r.inserted,
                    }
                    for r in results
                ],
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
    logger.info("Relatório detalhado salvo em: %s", report_path)

    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))
