#!/usr/bin/env python
"""
Script para gerar base de teste com 10 SSAs completas para validacao.

Cria arquivo: data/ssas_test.db

Uso:
    python scripts/generate_test_database.py

2025-10-31T08:10:00
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Output path
TEST_DB_PATH = os.path.join(project_root, 'data', 'ssas_test.db')
TABLE_NAME = 'ssas'


def generate_test_ssas():
    """Gera 10 SSAs completas com todos os campos preenchidos."""

    # Data base
    base_date = datetime(2025, 10, 1)

    ssas = []

    for i in range(1, 11):
        data_cadastro = base_date + timedelta(days=i-1)
        data_cadastro_str = data_cadastro.strftime('%d/%m/%Y')
        prazo_limite = data_cadastro + timedelta(days=15)
        prazo_limite_str = prazo_limite.strftime('%d/%m/%Y')

        # Semana do cadastro (numero da semana no ano)
        semana = data_cadastro.isocalendar()[1]

        # Varia situacao
        situacoes = ['ABERTA', 'EM ANDAMENTO', 'FECHADA', 'PENDENTE', 'CANCELADA']
        situacao = situacoes[i % len(situacoes)]

        # Varia setor
        setores_exec = ['TI', 'MANUTENCAO', 'ALMOXARIFADO', 'COMPRAS', 'FINANCEIRO']
        setores_emis = ['ADMINISTRACAO', 'PRODUCAO', 'QUALIDADE', 'LOGISTICA', 'VENDAS']
        setor_executor = setores_exec[i % len(setores_exec)]
        setor_emissor = setores_emis[i % len(setores_emis)]

        # Descricoes com termos de busca variad os
        descricoes_ssa = [
            'Servico de manutencao preventiva em equipamentos',
            'Instalacao de sistema web de gestao',
            'Conserto de ar condicionado na sala de reunioes',
            'Desenvolvimento de relatorio de vendas',
            'Calibracao de instrumentos de medicao',
            'Atualizacao de software de controle',
            'Reparo de rede eletrica no pavilhao 2',
            'Implementacao de backup automatizado',
            'Limpeza e organizacao do almoxarifado',
            'Treinamento de equipe em sistema ERP'
        ]

        descricoes_exec = [
            'Executar servico conforme especificado',
            'Realizar instalacao e configuracao completa',
            'Efetuar conserto com troca de pecas',
            'Desenvolver solucao personalizada',
            'Calibrar conforme normas tecnicas',
            'Atualizar versao e testar funcionalidades',
            'Reparar instalacao eletrica',
            'Implementar rotina de backup diario',
            'Organizar e catalogar itens',
            'Ministrar treinamento pratico'
        ]

        solicitantes = [
            'Joao Silva',
            'Maria Santos',
            'Pedro Oliveira',
            'Ana Costa',
            'Carlos Ferreira',
            'Lucia Alves',
            'Roberto Mendes',
            'Patricia Rocha',
            'Fernando Lima',
            'Julia Martins'
        ]

        # Prioridades
        prioridades = ['ALTA', 'MEDIA', 'BAIXA', 'URGENTE', 'NORMAL']
        prioridade_emissao = prioridades[i % len(prioridades)]
        prioridade_planejamento = prioridades[(i+1) % len(prioridades)]

        # Observacoes
        observacoes = [
            'Agendar com antecedencia',
            'Material disponivel em estoque',
            'Requer aprovacao da diretoria',
            'Coordenar com equipe externa',
            'Verificar disponibilidade de recursos',
            'Documentar todas as etapas',
            'Solicitar orcamento previo',
            'Acompanhar execucao de perto',
            'Garantir qualidade do servico',
            'Registrar resultado em sistema'
        ]

        ssa = {
            'numero_ssa': 1000 + i,
            'situacao': situacao,
            'semana_cadastro': f'{semana:02d}',
            'data_cadastro': data_cadastro_str,
            'data_cadastro_str': data_cadastro_str,
            'descricao_ssa': descricoes_ssa[i-1],
            'descricao_execucao': descricoes_exec[i-1],
            'descricao_servico': descricoes_ssa[i-1],  # Alias
            'setor_executor': setor_executor,
            'setor_emissor': setor_emissor,
            'solicitante': solicitantes[i-1],
            'servico_origem': f'ORIGEM-{i}',
            'grau_prioridade_emissao': prioridade_emissao,
            'grau_prioridade_planejamento': prioridade_planejamento,
            'prazo_limite': prazo_limite_str,
            'prazo_limite_str': prazo_limite_str,
            'observacao': observacoes[i-1],
            'tipo_servico': 'CORRETIVO' if i % 2 == 0 else 'PREVENTIVO',
            'status_aprovacao': 'APROVADA' if i % 3 == 0 else 'PENDENTE',
        }

        ssas.append(ssa)

    return pd.DataFrame(ssas)


def create_test_database():
    """Cria base de teste SQLite."""

    print(f"Gerando base de teste em: {TEST_DB_PATH}")

    # Garante diretorio
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)

    # Remove arquivo existente
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        print(f"Arquivo existente removido")

    # Gera dados
    df = generate_test_ssas()

    print(f"\nSSAs geradas: {len(df)}")
    print(f"Colunas: {len(df.columns)}")
    print(f"\nAmostra dos dados:")
    print(df[['numero_ssa', 'situacao', 'descricao_ssa', 'setor_executor']].head())

    # Salva no SQLite
    conn = sqlite3.connect(TEST_DB_PATH)
    df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
    conn.commit()

    # Verifica
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cursor.fetchone()[0]
    print(f"\nRegistros salvos no banco: {count}")

    # Mostra algumas consultas de exemplo
    print("\n--- Consultas de Exemplo ---")

    # Exemplo 1: SSAs ABERTAS
    cursor.execute(f"SELECT numero_ssa, situacao, descricao_ssa FROM {TABLE_NAME} WHERE situacao = 'ABERTA'")
    abertas = cursor.fetchall()
    print(f"\nSSAs ABERTAS: {len(abertas)}")
    for ssa in abertas:
        print(f"  #{ssa[0]} - {ssa[1]} - {ssa[2][:50]}...")

    # Exemplo 2: Setor TI
    cursor.execute(f"SELECT numero_ssa, setor_executor, descricao_ssa FROM {TABLE_NAME} WHERE setor_executor = 'TI'")
    ti = cursor.fetchall()
    print(f"\nSetor TI: {len(ti)}")
    for ssa in ti:
        print(f"  #{ssa[0]} - {ssa[1]} - {ssa[2][:50]}...")

    # Exemplo 3: Busca por termo "sistema"
    cursor.execute(f"SELECT numero_ssa, descricao_ssa FROM {TABLE_NAME} WHERE descricao_ssa LIKE '%sistema%'")
    sistema = cursor.fetchall()
    print(f"\nContem 'sistema': {len(sistema)}")
    for ssa in sistema:
        print(f"  #{ssa[0]} - {ssa[1][:50]}...")

    conn.close()

    print(f"\n{'-'*60}")
    print(f"Base de teste criada com sucesso!")
    print(f"Arquivo: {TEST_DB_PATH}")
    print(f"\nPara usar na GUI:")
    print(f"  python gui/gui_ssa.py")
    print(f"  (Edite DB_PATH no codigo para apontar para ssas_test.db)")
    print(f"{'-'*60}\n")


if __name__ == '__main__':
    create_test_database()
