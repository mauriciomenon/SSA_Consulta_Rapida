#!/usr/bin/env python3
"""
Script de importação de emergência - sem dependências pesadas
"""

import argparse
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from armazenamento.database_lock import database_writer_lock
from armazenamento.database_publication import (
    restore_journal_mode,
    snapshot_database_for_replace,
)


def create_basic_table(cursor):
    """Cria tabela básica sem usar pandas"""
    cursor.execute("""DROP TABLE IF EXISTS ssa_table""")
    cursor.execute("""
    CREATE TABLE ssa_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_ssa INTEGER,
        situacao TEXT,
        derivada_de TEXT,
        localizacao_codigo TEXT,
        descricao_localizacao TEXT,
        equipamento TEXT,
        semana_cadastro INTEGER,
        data_cadastro TEXT,
        descricao_ssa TEXT,
        descricao_execucao TEXT,
        setor_emissor TEXT,
        setor_executor TEXT,
        solicitante TEXT,
        responsavel_programacao TEXT,
        responsavel_execucao TEXT,
        servico_origem TEXT,
        sistema_origem TEXT,
        grau_prioridade_emissao TEXT,
        grau_prioridade_planejamento TEXT,
        execucao_simples TEXT,
        semana_programada INTEGER,
        prazo_limite TEXT,
        tempo_disponivel TEXT,
        data_limite TEXT,
        tempo_excedido TEXT,
        desde TEXT,
        tempo_total TEXT,
        desde_1 TEXT,
        total_tempo_tpe_planejado TEXT,
        total_tempo_tex_planejado TEXT,
        total_tempo_tpo_planejado TEXT,
        total_horas_programadas TEXT,
        semana_executada INTEGER,
        num_reprogramacoes INTEGER,
        execucao_parcial TEXT,
        anomalia TEXT,
        registros_espera TEXT,
        num_reprobaciones INTEGER,
        situacao_espera TEXT,
        numero_desvios INTEGER,
        ate TEXT,
        justificativa TEXT,
        total_tempo_tex_executada TEXT,
        parciais TEXT,
        situacao_da_parcial TEXT
    )
    """)


def emergency_import(db_path: str = "data/ssas.db", force: bool = False):
    """Importação de emergência usando apenas SQLite"""
    db_path = os.path.realpath(db_path)
    with database_writer_lock(db_path, timeout=0):
        return _emergency_import_locked(db_path, force)


def _emergency_import_locked(db_path: str, force: bool):
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    existed = os.path.exists(db_path)
    if existed and not force:
        print(
            f"ERRO: {db_path} ja existe. "
            "Use --force para arquiva-lo como .bak antes de recriar."
        )
        return False
    candidate_fd, candidate_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(db_path)}.tmp-", dir=parent_dir
    )
    os.close(candidate_fd)
    try:
        return _create_and_publish(db_path, candidate_path, existed)
    finally:
        for suffix in ("-wal", "-shm", "-journal", ""):
            candidate_file = candidate_path + suffix
            if os.path.lexists(candidate_file):
                os.unlink(candidate_file)


def _create_and_publish(db_path: str, candidate_path: str, existed: bool) -> bool:
    conn = sqlite3.connect(candidate_path)
    cursor = conn.cursor()

    try:
        create_basic_table(cursor)

        # Simula importação básica - insere alguns registros de teste
        test_data = [
            (
                12345,
                "Pendente",
                None,
                "LOC001",
                "Localização Teste",
                "Equipamento A",
                1,
                "2025-01-15",
                "Teste SSA 1",
                "Execução teste",
                "Emissor",
                "Executor",
                "Solicitante",
                "Prog",
                "Exec",
                "Origem",
                "Sistema",
                "Alta",
                "Media",
                "Não",
                2,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                0,
                None,
                None,
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
            ),
            (
                12346,
                "Em Execução",
                None,
                "LOC002",
                "Localização Teste 2",
                "Equipamento B",
                1,
                "2025-01-16",
                "Teste SSA 2",
                "Execução teste 2",
                "Emissor2",
                "Executor2",
                "Solicitante2",
                "Prog2",
                "Exec2",
                "Origem2",
                "Sistema2",
                "Media",
                "Alta",
                "Sim",
                3,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                0,
                None,
                None,
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
            ),
        ]

        cursor.executemany(
            """
        INSERT INTO ssa_table (
            numero_ssa, situacao, derivada_de, localizacao_codigo, descricao_localizacao,
            equipamento, semana_cadastro, data_cadastro, descricao_ssa, descricao_execucao,
            setor_emissor, setor_executor, solicitante, responsavel_programacao, responsavel_execucao,
            servico_origem, sistema_origem, grau_prioridade_emissao, grau_prioridade_planejamento,
            execucao_simples, semana_programada, prazo_limite, tempo_disponivel, data_limite,
            tempo_excedido, desde, tempo_total, desde_1, total_tempo_tpe_planejado,
            total_tempo_tex_planejado, total_tempo_tpo_planejado, total_horas_programadas,
            semana_executada, num_reprogramacoes, execucao_parcial, anomalia, registros_espera,
            num_reprobaciones, situacao_espera, numero_desvios, ate, justificativa,
            total_tempo_tex_executada, parciais, situacao_da_parcial
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            test_data,
        )

        conn.commit()

        # Verifica quantos registros foram inseridos
        count = cursor.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        if cursor.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise sqlite3.DatabaseError("Banco candidato falhou no quick_check")
    except Exception as e:
        print(f"Erro durante importação: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

    suffixes = ("-wal", "-shm", "-journal")
    if any(os.path.lexists(candidate_path + suffix) for suffix in suffixes):
        raise OSError("DB candidato manteve sidecar SQLite apos fechamento")
    moved: list[tuple[str, str]] = []
    backup_created = False
    original_mode: str | None = None
    backup_path = f"{db_path}.bak-{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    try:
        if any(os.path.lexists(backup_path + suffix) for suffix in (*suffixes, "")):
            raise FileExistsError(f"Backup de emergencia ja existe: {backup_path}")
        if existed:
            original_mode = snapshot_database_for_replace(db_path, backup_path)
            backup_created = True
        for suffix in (() if existed else suffixes):
            src = db_path + suffix
            if os.path.lexists(src):
                dst = backup_path + suffix
                os.replace(src, dst)
                moved.append((src, dst))
        os.replace(candidate_path, db_path)
    except (OSError, sqlite3.Error) as exc:
        rollback_errors: list[str] = []
        for src, dst in reversed(moved):
            if os.path.exists(src):
                rollback_errors.append(f"{src}: caminho ocupado; backup preservado em {dst}")
                continue
            try:
                os.replace(dst, src)
            except OSError as rollback_exc:
                rollback_errors.append(f"{dst}: {rollback_exc}")
        if original_mode is not None:
            try:
                restore_journal_mode(db_path, original_mode)
            except (OSError, sqlite3.Error) as restore_exc:
                rollback_errors.append(f"journal: {restore_exc}")
        if (
            backup_created
            and not rollback_errors
            and os.path.exists(db_path)
            and os.path.exists(backup_path)
        ):
            try:
                os.unlink(backup_path)
            except OSError as cleanup_exc:
                rollback_errors.append(
                    f"{backup_path}: backup preservado apos falha de limpeza: {cleanup_exc}"
                )
        detail = (
            f" Rollback incompleto: {'; '.join(rollback_errors)}"
            if rollback_errors
            else " Arquivos ja movidos restaurados."
        )
        raise OSError(f"Falha ao publicar banco de teste: {exc}.{detail}") from exc

    if moved or existed:
        label = "Banco existente" if existed else "Sidecars orfaos"
        print(f"{label} arquivado(s) em {backup_path}")
    print(f"Banco criado com sucesso! {count} registros inseridos.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Importacao de emergencia - cria banco com dados de TESTE."
    )
    parser.add_argument(
        "--db", default="data/ssas.db", help="Caminho do banco a criar"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Arquiva banco existente como .bak-<timestamp> antes de recriar",
    )
    args = parser.parse_args()
    print("Importação de emergência iniciada...")
    print("ATENCAO: este script insere dados de TESTE, nao dados reais.")
    success = emergency_import(args.db, force=args.force)
    if success:
        print(" Banco de dados criado com dados de teste")
        print(" Agora você pode testar o CLI e GUI")
    else:
        print(" Falha na criação do banco de dados")
    sys.exit(0 if success else 1)
