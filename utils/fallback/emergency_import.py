#!/usr/bin/env python3
"""
Script de importação de emergência - sem dependências pesadas
"""

import os
import sqlite3


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


def emergency_import():
    """Importação de emergência usando apenas SQLite"""
    db_path = "data/ssas.db"
    os.makedirs("data", exist_ok=True)

    # Remove banco anterior se existir
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
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
        print(f"Banco criado com sucesso! {count} registros inseridos.")

        return True

    except Exception as e:
        print(f"Erro durante importação: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("Importação de emergência iniciada...")
    success = emergency_import()
    if success:
        print(" Banco de dados criado com dados de teste")
        print(" Agora você pode testar o CLI e GUI")
    else:
        print(" Falha na criação do banco de dados")
