#!/usr/bin/env python3
"""CLI para importar planilha Excel SSA de forma robusta.

Uso básico:
  python -m scripts.import_excel_file --file "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx" \
      --db data/ssas.db --table ssas

Opções:
  --dry-run        Apenas processa a planilha e mostra estatísticas (não insere)
  --reset-db       Recria schema antes de inserir (usa config/schema.sql)
  --smart-upsert   Usa caminho de upsert inteligente (numero_ssa) ao invés de insert simples
  --verbose        Aumenta log
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

# Garantir que raiz do projeto esteja no sys.path quando script executado diretamente
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.robust_importer import import_excel_robust  # type: ignore  # noqa: E402
from armazenamento import database  # type: ignore  # noqa: E402

logger = logging.getLogger("import_excel_file")


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
    p.add_argument("--dry-run", action="store_true", help="Não insere no banco, só mostra estatísticas")
    p.add_argument("--reset-db", action="store_true", help="Recria schema antes de inserir")
    p.add_argument("--smart-upsert", action="store_true", help="Usa logica de upsert por numero_ssa")
    p.add_argument("--mappings", default="config/column_mappings.json", help="Arquivo de mapeamento de colunas")
    p.add_argument("--verbose", action="store_true", help="Modo verboso")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    if not os.path.exists(args.file):
        logger.error("Arquivo não encontrado: %s", args.file)
        return 2

    logger.info("Importando planilha: %s", args.file)
    df, stats = import_excel_robust(args.file, mappings_path=args.mappings)

    logger.info("Estatísticas de importação:\n%s", json.dumps(stats, ensure_ascii=False, indent=2))

    if args.dry_run:
        logger.info("Dry-run: nenhuma inserção realizada.")
        return 0

    if args.reset_db:
        logger.info("Recriando schema do banco: %s", args.db)
        database.reset_database(args.db, mode='file')
        database.initialize_database(args.db, 'schema.sql')

    if df.empty:
        logger.warning("DataFrame resultante vazio – nada a inserir.")
        return 0

    logger.info("Inserindo %s linhas normalizadas (smart=%s)", len(df), args.smart_upsert)

    success = True
    if args.smart_upsert:
        success = database.insert_dataframe_with_smart_upsert(df, args.db, args.table)
    else:
        success = database.insert_dataframe_to_db(df, args.db, args.table)

    if not success:
        logger.error("Falha na inserção dos dados.")
        return 3

    # Pequena verificação após inserção
    try:
        loaded = database.query_db(args.db, args.table)
        logger.info("Banco agora contém %s linhas (tabela=%s)", len(loaded), args.table)
    except Exception as e:  # pragma: no cover
        logger.warning("Não foi possível contar linhas após inserção: %s", e)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
