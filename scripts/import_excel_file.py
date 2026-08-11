#!/usr/bin/env python3
"""CLI para importar planilha Excel SSA pelo extractor canonico.

Uso básico:
  python -m scripts.import_excel_file --file "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx" \
      --db data/ssas.db --table ssas

Opções:
  --dry-run        Apenas processa a planilha e mostra estatísticas (não insere)
  --reset-db       Rejeitado; recriacao segura pertence ao full rescan
  --smart-upsert   Usa caminho de upsert inteligente (numero_ssa) ao invés de insert simples
  --verbose        Aumenta log
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Bootstrap repo root when this script runs outside the project cwd.
try:
    from launchers.main_runtime import _get_project_root  # noqa: E402
except ModuleNotFoundError as exc:
    if exc.name != "launchers":
        raise
    BOOTSTRAP_ROOT = Path(__file__).resolve().parent.parent
    if str(BOOTSTRAP_ROOT) not in sys.path:
        sys.path.insert(0, str(BOOTSTRAP_ROOT))
    from launchers.main_runtime import _get_project_root  # noqa: E402

PROJECT_ROOT = Path(_get_project_root())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from armazenamento import database  # noqa: E402
from core.import_single_file import add_source_metadata_columns  # noqa: E402
from extracao.extractor import ExtractionError, extract_data_from_excel  # noqa: E402
from shared.db_names import ALL_SSA_TABLE_NAMES  # noqa: E402

logger = logging.getLogger("import_excel_file")
DEFAULT_MAPPINGS_PATH = PROJECT_ROOT / "config" / "column_mappings.json"


def _configure_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Importador robusto de SSA")
    p.add_argument("--file", required=True, help="Caminho da planilha .xlsx a importar")
    p.add_argument("--db", default="data/ssas.db", help="Caminho do banco SQLite")
    p.add_argument("--table", default="ssas", help="Nome da tabela alvo")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Não insere no banco, só mostra estatísticas",
    )
    p.add_argument(
        "--reset-db",
        action="store_true",
        help="Rejeitado neste utilitario; use o full rescan atomico",
    )
    p.add_argument(
        "--smart-upsert",
        action="store_true",
        help="Usa upsert por numero_ssa; obrigatorio nas tabelas SSA",
    )
    p.add_argument(
        "--mappings",
        default=str(DEFAULT_MAPPINGS_PATH),
        help="Arquivo de mapeamento de colunas",
    )
    p.add_argument("--verbose", action="store_true", help="Modo verboso")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    if not os.path.exists(args.file):
        logger.error("Arquivo não encontrado: %s", args.file)
        return 2

    if not database.is_valid_identifier(args.table):
        logger.error("Nome de tabela invalido: %s", args.table)
        return 2

    if args.reset_db:
        logger.error(
            "--reset-db foi desabilitado neste utilitario: use o full rescan "
            "com banco candidato e promocao validada."
        )
        return 2

    logger.info("Importando planilha: %s", args.file)
    try:
        df = extract_data_from_excel(args.file, mappings_path=args.mappings)
    except ExtractionError as exc:
        logger.error("Falha na extracao de %s: %s", args.file, exc)
        return 4

    invalid_summary_raw = df.attrs.get("invalid_row_summary")
    if invalid_summary_raw is not None and not isinstance(invalid_summary_raw, dict):
        logger.error("Extractor retornou invalid_row_summary invalido.")
        return 4
    invalid_summary = dict(invalid_summary_raw or {})
    event_records = df.attrs.get("ssa_event_records", [])
    if not isinstance(event_records, list):
        logger.error("Extractor retornou ssa_event_records invalido.")
        return 4
    rows_in_raw = df.attrs.get("row_count_before_invalid_filter")
    if rows_in_raw is None and df.empty:
        rows_in = 0
    elif not isinstance(rows_in_raw, int) or isinstance(rows_in_raw, bool):
        logger.error(
            "Extractor retornou row_count_before_invalid_filter invalido: %r",
            rows_in_raw,
        )
        return 4
    else:
        rows_in = rows_in_raw
    stats = {
        "total_rows_in": rows_in,
        "total_rows_out": len(df),
        "payload_removed": int(invalid_summary.get("payload_removed", 0)),
        "hierarchical_rows_captured": int(
            invalid_summary.get("hierarchical_rows_captured", 0)
        ),
        "hierarchical_records_captured": len(event_records),
    }

    logger.info(
        "Estatísticas de importação:\n%s",
        json.dumps(stats, ensure_ascii=False, indent=2),
    )

    if stats["payload_removed"] > 0:
        logger.error(
            "Importacao bloqueada: %s linha(s) sem identidade ainda possuem payload.",
            stats["payload_removed"],
        )
        return 4

    if df.empty and rows_in > 0:
        logger.error("Todas as linhas foram rejeitadas; nenhuma escrita sera feita.")
        return 4

    if args.dry_run:
        logger.info("Dry-run: nenhuma insercao realizada.")
        return 0

    if df.empty:
        logger.error("DataFrame resultante vazio; nada a inserir.")
        return 4

    if not args.smart_upsert and args.table.casefold() in ALL_SSA_TABLE_NAMES:
        logger.error(
            "Importacao bloqueada: tabelas SSA exigem --smart-upsert para evitar "
            "duplicidade em reimportacoes."
        )
        return 4

    if event_records and not args.smart_upsert:
        logger.error(
            "Importacao bloqueada: %s evento(s) hierarquico(s) exigem --smart-upsert.",
            len(event_records),
        )
        return 4

    logger.info(
        "Inserindo %s linhas normalizadas (smart=%s)", len(df), args.smart_upsert
    )

    success = True
    upsert_metrics: dict[str, int] = {}
    if args.smart_upsert:
        df = add_source_metadata_columns(df, args.file)
        df.attrs["ssa_event_records"] = event_records
        success = database.insert_dataframe_with_smart_upsert(
            df,
            args.db,
            args.table,
            metrics_out=upsert_metrics,
        )
    else:
        # Tabelas customizadas preservam o schema definido pelo chamador.
        success = database.insert_dataframe_to_db(df, args.db, args.table)

    if not success:
        logger.error("Falha na inserção dos dados.")
        return 3

    if args.smart_upsert:
        missing_metrics = {
            "ssa_inserted",
            "ssa_updated",
            "ssa_event_records_processed",
        }.difference(upsert_metrics)
        if missing_metrics:
            logger.error(
                "Upsert concluido sem metricas obrigatorias: %s.",
                ", ".join(sorted(missing_metrics)),
            )
            return 3

    processed_events = upsert_metrics.get("ssa_event_records_processed", 0)
    if event_records and processed_events != len(event_records):
        logger.error(
            "Upsert nao confirmou todos os eventos: esperado=%s, processado=%s.",
            len(event_records),
            processed_events,
        )
        return 3

    # Pequena verificação após inserção
    try:
        row_count = database.count_table_rows(args.db, args.table)
        logger.info("Banco agora contém %s linhas (tabela=%s)", row_count, args.table)
    except Exception as e:  # pragma: no cover
        logger.warning("Não foi possível contar linhas após inserção: %s", e)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
