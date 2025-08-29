#!/usr/bin/env python3
"""
Relatório: SSAs IEE3 derivadas executadas (STE)

Objetivo:
- Filtro 1: SSAs com setor_executor == 'IEE3' e situacao != 'STE'.
- Filtro 2: SSAs emitidas por 'IEE3' (setor_emissor == 'IEE3'), executor em {'MEL3','MEL4'}, e situacao == 'STE'.
- Resultado: lista de SSAs derivadas (do Filtro 2) cujas 'derivada_de' correspondem às SSAs do Filtro 1 (por equivalência de número SSA),
  identificando SSAs derivadas emitidas pela IEE3 que já foram executadas (STE).

Observações:
- Reaproveita utilidades existentes para conexão ao banco, normalização de SSA e exibição tabular.
- Otimizado para consultas longas: aplica filtros diretamente em SQL com índices e usa conjuntos para matching.
- Inclui um main para execução direta no console (sem alterar CLI/GUI existentes).
"""

from __future__ import annotations

import os
import sys
import pandas as pd
from typing import Dict, Tuple

try:
    # Caminhos relativos ao projeto
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, PROJECT_ROOT)
except Exception:
    PROJECT_ROOT = os.getcwd()

# Reutiliza componentes do projeto
from armazenamento.database import get_db_connection, normalize_numero_ssa
from interface.enhanced_table_printer import EnhancedTablePrinter
from core.config_manager import load_settings, load_display_mappings_integrity


def _resolve_db_defaults() -> Tuple[str, str]:
    """Resolve db_path e table_name padrão do projeto."""
    db_path = os.path.join(PROJECT_ROOT, 'data', 'ssas.db')
    table_name = 'ssa_table'
    return db_path, table_name


def _query_filtro_1(
    db_path: str,
    table_name: str,
    *,
    setor_executor_val: str,
    situacao_executada_val: str,
) -> pd.DataFrame:
    """
    Filtro 1: setor_executor == 'IEE3' AND situacao != 'STE'.
    Retorna colunas essenciais para correlação e exibição.
    """
    # Normaliza valores para comparação case-insensitive
    setor_executor_val = (setor_executor_val or '').upper()
    situacao_executada_val = (situacao_executada_val or '').upper()

    sql = f"""
        SELECT
            numero_ssa,
            situacao,
            setor_emissor,
            setor_executor,
            derivada_de,
            descricao_ssa,
            data_cadastro
        FROM {table_name}
        WHERE UPPER(COALESCE(setor_executor, '')) = ?
          AND UPPER(COALESCE(situacao, '')) != ?
    """
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=(setor_executor_val, situacao_executada_val))
    return df


def _query_filtro_2(
    db_path: str,
    table_name: str,
    *,
    setor_emissor_val: str,
    setores_executor_derivadas: list[str],
    situacao_executada_val: str,
) -> pd.DataFrame:
    """
    Filtro 2: setor_emissor == 'IEE3' AND setor_executor in ('MEL3','MEL4') AND situacao == 'STE'.
    Retorna colunas essenciais para correlação e exibição.
    """
    setor_emissor_val = (setor_emissor_val or '').upper()
    setores = [s.upper() for s in (setores_executor_derivadas or []) if s]
    situacao_executada_val = (situacao_executada_val or '').upper()

    if not setores:
        # Sem lista de executores, não há resultados válidos
        return pd.DataFrame(columns=[
            'numero_ssa_derivada', 'situacao_derivada', 'derivada_de', 'descricao_derivada',
            'setor_emissor', 'setor_executor_derivada', 'data_cadastro_derivada'
        ])

    placeholders = ','.join(['?'] * len(setores))
    sql = f"""
        SELECT
            numero_ssa AS numero_ssa_derivada,
            situacao   AS situacao_derivada,
            derivada_de,
            descricao_ssa AS descricao_derivada,
            setor_emissor,
            setor_executor AS setor_executor_derivada,
            data_cadastro  AS data_cadastro_derivada
        FROM {table_name}
        WHERE UPPER(COALESCE(setor_emissor, '')) = ?
          AND UPPER(COALESCE(setor_executor, '')) IN ({placeholders})
          AND UPPER(COALESCE(situacao, '')) = ?
          AND derivada_de IS NOT NULL
    """
    params = [setor_emissor_val] + setores + [situacao_executada_val]
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    return df


def _build_result(
    f1: pd.DataFrame,
    f2: pd.DataFrame,
    *,
    sort_by: str | None = 'numero_ssa',
    ascending: bool = True,
) -> pd.DataFrame:
    """
    Constrói o resultado: SSAs do Filtro 1 (IEE3 executor, !STE) que possuem
    alguma SSA derivada no Filtro 2 (IEE3 emissor, MEL3/MEL4, STE).

    Retorna as SSAs originais (de f1) enriquecidas com informação resumida
    sobre a(s) derivada(s) encontrada(s).
    """
    if f1.empty or f2.empty:
        return pd.DataFrame(columns=[
            'numero_ssa', 'situacao', 'descricao_ssa',
            'setor_emissor', 'setor_executor', 'data_cadastro',
            'derivada_ste_numero', 'derivada_ste_executor'
        ])

    # Normaliza chaves de comparação
    # - f1: numero_ssa -> chave canônica
    # - f2: derivada_de -> chave canônica de origem
    f1 = f1.copy()
    f1['__key__'] = f1['numero_ssa'].apply(normalize_numero_ssa)
    f1_key_set = set([k for k in f1['__key__'].tolist() if k])

    f2 = f2.copy()
    f2['__orig_key__'] = f2['derivada_de'].apply(normalize_numero_ssa)

    # Filtra derivadas que referenciam alguma SSA do Filtro 1
    matched_derivadas = f2[f2['__orig_key__'].isin(f1_key_set)].copy()
    if matched_derivadas.empty:
        return pd.DataFrame(columns=[
            'numero_ssa', 'situacao', 'descricao_ssa',
            'setor_emissor', 'setor_executor', 'data_cadastro',
            'derivada_ste_numero', 'derivada_ste_executor'
        ])

    # Agrega info da(s) derivada(s) por chave de origem
    agg = (
        matched_derivadas
        .groupby('__orig_key__')
        .agg({
            'numero_ssa_derivada': lambda s: ','.join(str(x) for x in s.head(3)),
            'setor_executor_derivada': lambda s: ','.join(sorted(set(str(x) for x in s))[:3])
        })
        .rename(columns={
            'numero_ssa_derivada': 'derivada_ste_numero',
            'setor_executor_derivada': 'derivada_ste_executor'
        })
    )

    # Junta com f1 mantendo apenas chaves presentes na agregação
    res = f1.merge(agg, left_on='__key__', right_index=True, how='inner')

    # Seleciona colunas para exibição
    cols = [
        c for c in [
            'numero_ssa', 'situacao', 'descricao_ssa',
            'setor_emissor', 'setor_executor', 'data_cadastro',
            'derivada_ste_numero', 'derivada_ste_executor'
        ] if c in res.columns
    ]

    res = res[cols].reset_index(drop=True)

    # Ordenação (opcional) já dentro da função para reuso em outros contextos
    if sort_by and sort_by in res.columns:
        try:
            res = res.sort_values(by=[sort_by], ascending=ascending, na_position='last', kind='mergesort')
        except Exception:
            pass
    return res


def generate_derivadas_exec_report(
    *,
    db_path: str,
    table_name: str,
    setor_executor_base: str,
    situacao_executada: str,
    setor_emissor_base: str,
    setores_executor_derivadas: list[str],
    sort_by: str | None = 'numero_ssa',
    ascending: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Executa os dois filtros e produz o resultado correlacionado.

    Returns dict with:
      - filtro1: DataFrame (IEE3 executor, não-STE)
      - filtro2: DataFrame (IEE3 emissor, MEL3/MEL4 executor, STE)
      - resultado: DataFrame (derivadas executadas que referenciam SSAs do filtro1)
    """
    f1 = _query_filtro_1(
        db_path, table_name,
        setor_executor_val=setor_executor_base,
        situacao_executada_val=situacao_executada,
    )
    f2 = _query_filtro_2(
        db_path, table_name,
        setor_emissor_val=setor_emissor_base,
        setores_executor_derivadas=setores_executor_derivadas,
        situacao_executada_val=situacao_executada,
    )
    resultado = _build_result(f1, f2, sort_by=sort_by, ascending=ascending)

    return {
        'filtro1': f1,
        'filtro2': f2,
        'resultado': resultado
    }


def run_relatorio(db_path: str | None = None, table_name: str | None = None) -> Dict[str, pd.DataFrame]:
    """Wrapper de compatibilidade que executa o relatório com parâmetros padrão.

    Padrões:
      - setor_executor_base = 'IEE3' (Filtro 1, !STE)
      - situacao_executada = 'STE'
      - setor_emissor_base = 'IEE3' (Filtro 2)
      - setores_executor_derivadas = ['MEL3', 'MEL4'] (Filtro 2)
    """
    if db_path is None or table_name is None:
        db_path, table_name = _resolve_db_defaults()

    return generate_derivadas_exec_report(
        db_path=db_path,
        table_name=table_name,
        setor_executor_base='IEE3',
        situacao_executada='STE',
        setor_emissor_base='IEE3',
        setores_executor_derivadas=['MEL3', 'MEL4'],
        sort_by='numero_ssa',
        ascending=True,
    )


def _print_section(title: str):
    print("\n" + title)
    print("=" * max(10, len(title)))


def main():
    """Entrada de console: executa o relatório e imprime tabelas resumidas."""
    db_path, table_name = _resolve_db_defaults()

    # Executa relatório
    data = run_relatorio(db_path, table_name)
    f1 = data['filtro1']
    f2 = data['filtro2']
    res = data['resultado']

    # Carrega configurações e mapeamentos de exibição
    try:
        settings = load_settings()
    except Exception:
        settings = { 'display_settings': {}, 'user_preferences': {} }
    display_map = load_display_mappings_integrity()

    printer = EnhancedTablePrinter()

    # Resumo
    print("Relatório: SSAs derivadas (IEE3 -> MEL3/MEL4) executadas (STE)")
    print("- Banco:", db_path)
    print(f"- Filtro 1 (IEE3 executor, não-STE): {len(f1)} registro(s)")
    print(f"- Filtro 2 (IEE3 emissor, MEL3/MEL4, STE): {len(f2)} registro(s)")
    print(f"- Resultado (derivadas executadas que referenciam Filtro 1): {len(res)} registro(s)")

    # Exibe Filtro 1 (com total de hits)
    _print_section(f"Filtro 1 — IEE3 executor e situação != STE ({len(f1)} SSAs)")
    try:
        if not f1.empty:
            sample_f1 = f1.copy()
            # Mantém colunas úteis e limita a amostra para evitar saídas muito grandes
            cols_f1 = [c for c in ['numero_ssa', 'situacao', 'setor_executor', 'descricao_ssa', 'data_cadastro'] if c in sample_f1.columns]
            sample_f1 = sample_f1[cols_f1].head(7)
            printer.print_dataframe_enhanced(sample_f1, display_map, settings)
        else:
            print("Nenhum registro no Filtro 1.")
    except Exception as e:
        print(f"Falha ao exibir Filtro 1: {e}")

    # Exibe Filtro 2 (com total de hits)
    _print_section(f"Filtro 2 — IEE3 emissor, MEL3/MEL4 executor, STE ({len(f2)} SSAs)")
    try:
        if not f2.empty:
            sample_f2 = f2.copy()
            # Adapta nomes para exibição compatível
            sample_f2 = sample_f2.rename(columns={
                'numero_ssa_derivada': 'numero_ssa',
                'situacao_derivada': 'situacao',
                'descricao_derivada': 'descricao_ssa',
                'setor_executor_derivada': 'setor_executor',
                'data_cadastro_derivada': 'data_cadastro'
            })
            cols_f2 = [c for c in ['numero_ssa', 'situacao', 'setor_emissor', 'setor_executor', 'derivada_de', 'descricao_ssa', 'data_cadastro'] if c in sample_f2.columns]
            sample_f2 = sample_f2[cols_f2].head(7)
            printer.print_dataframe_enhanced(sample_f2, display_map, settings)
        else:
            print("Nenhum registro no Filtro 2.")
    except Exception as e:
        print(f"Falha ao exibir Filtro 2: {e}")

    # Exibe Resultado (com total de hits) ordenado por numero_ssa crescente
    _print_section(f"Verificar Possibilidade de Execução e Encerramento ({len(res)} SSAs)")
    try:
        if not res.empty:
            # Ordena por numero_ssa crescente
            try:
                res_sorted = res.sort_values(by=['numero_ssa'], ascending=True, na_position='last', kind='mergesort')
            except Exception:
                res_sorted = res
            cols_res = [
                c for c in [
                    'numero_ssa', 'situacao', 'setor_executor', 'descricao_ssa', 'data_cadastro',
                    'derivada_ste_numero', 'derivada_ste_executor'
                ] if c in res.columns
            ]
            to_show = res_sorted[cols_res].copy()
            printer.print_dataframe_enhanced(to_show, display_map, settings)
        else:
            print("Nenhuma derivada executada correspondente encontrada.")
    except Exception as e:
        print(f"Falha ao exibir Resultado: {e}")


if __name__ == '__main__':
    # Execução direta no console
    main()
