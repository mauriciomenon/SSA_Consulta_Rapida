#!/usr/bin/env python3
"""
Analise detalhada de problemas de importacao.

Analisa o log de importacao e o banco de dados resultante
para gerar relatorio completo de problemas.
"""

import sys
import os
from datetime import datetime

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from armazenamento.database import query_db  # noqa: E402

print("="*80)
print("ANALISE DETALHADA DE IMPORTACAO")
print("="*80)
print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# ============================================================================
# 1. Analise do Banco de Dados
# ============================================================================

print("\n[1/4] Analisando banco de dados...")

db_path = 'data/ssas.db'
if not os.path.exists(db_path):
    print("  [ERRO] Banco de dados nao encontrado")
    sys.exit(1)

df = query_db(db_path, 'ssas')

if df is None or df.empty:
    print("  [ERRO] Banco vazio")
    sys.exit(1)

print(f"  [OK] {len(df)} registros carregados")
print(f"  [OK] {len(df.columns)} colunas")

# ============================================================================
# 2. Analise de Dados Ausentes
# ============================================================================

print("\n[2/4] Analisando dados ausentes...")

missing_report = []

for col in df.columns:
    missing_count = df[col].isna().sum()
    if missing_count > 0:
        pct = (missing_count / len(df)) * 100
        missing_report.append({
            'coluna': col,
            'ausentes': missing_count,
            'total': len(df),
            'percentual': pct
        })

if missing_report:
    print(f"  [AVISO] {len(missing_report)} colunas com dados ausentes")

    # Ordena por quantidade de ausentes
    missing_report.sort(key=lambda x: x['ausentes'], reverse=True)

    # Mostra top 10
    print("\n  Top 10 colunas com mais dados ausentes:")
    for i, item in enumerate(missing_report[:10], 1):
        print(f"    {i:2d}. {item['coluna']:30s} - {item['ausentes']:6d}/{item['total']:6d} ({item['percentual']:5.1f}%)")
else:
    print("  [OK] Nenhuma coluna com dados ausentes")

# ============================================================================
# 3. Analise de Duplicatas
# ============================================================================

print("\n[3/4] Analisando duplicatas...")

if 'numero_ssa' in df.columns:
    duplicates = df[df.duplicated(subset=['numero_ssa'], keep=False)]

    if not duplicates.empty:
        print(f"  [AVISO] {len(duplicates)} registros duplicados")

        ssa_counts = duplicates['numero_ssa'].value_counts()
        print("\n  Top 10 SSAs mais duplicadas:")
        for i, (ssa, count) in enumerate(ssa_counts.head(10).items(), 1):
            print(f"    {i:2d}. SSA {ssa}: {count} ocorrencias")
    else:
        print("  [OK] Sem duplicatas")
else:
    print("  [AVISO] Coluna 'numero_ssa' nao encontrada")

# ============================================================================
# 4. Analise de Arquivos de Origem
# ============================================================================

print("\n[4/4] Analisando arquivos de origem...")

if 'arquivo_origem' in df.columns:
    file_counts = df['arquivo_origem'].value_counts()
    print(f"  [OK] {len(file_counts)} arquivos unicos importados")

    print("\n  Top 10 arquivos com mais registros:")
    for i, (arquivo, count) in enumerate(file_counts.head(10).items(), 1):
        print(f"    {i:2d}. {arquivo}: {count} registros")

    # Arquivos com poucos registros (possivel problema)
    few_records = file_counts[file_counts < 10]
    if not few_records.empty:
        print(f"\n  [AVISO] {len(few_records)} arquivos com menos de 10 registros:")
        for arquivo, count in few_records.items():
            print(f"    - {arquivo}: {count} registros")
else:
    print("  [AVISO] Coluna 'arquivo_origem' nao encontrada")

# ============================================================================
# 5. Analise de data_cadastro (problema critico identificado)
# ============================================================================

print("\n[CRITICO] Analise de data_cadastro...")

if 'data_cadastro' in df.columns:
    missing_cadastro = df['data_cadastro'].isna().sum()

    if missing_cadastro > 0:
        print(f"  [ERRO] {missing_cadastro} registros sem data_cadastro")

        # Identifica SSAs afetadas
        ssas_sem_data = df[df['data_cadastro'].isna()]['numero_ssa'].head(20).tolist()
        print("\n  Primeiras 20 SSAs sem data_cadastro:")
        for i, ssa in enumerate(ssas_sem_data, 1):
            arquivo = df[df['numero_ssa'] == ssa]['arquivo_origem'].iloc[0] if 'arquivo_origem' in df.columns else 'N/A'
            print(f"    {i:2d}. SSA {ssa} (arquivo: {arquivo})")
    else:
        print("  [OK] Todos os registros tem data_cadastro")
else:
    print("  [ERRO] Coluna 'data_cadastro' nao encontrada no banco!")

# ============================================================================
# Resumo
# ============================================================================

print("\n" + "="*80)
print("RESUMO")
print("="*80)

print(f"\nTotal de registros: {len(df)}")
print(f"Total de colunas: {len(df.columns)}")

if missing_report:
    print(f"\nColunas com dados ausentes: {len(missing_report)}")
    total_missing = sum(item['ausentes'] for item in missing_report)
    print(f"Total de valores ausentes: {total_missing:,}")

if 'numero_ssa' in df.columns and not duplicates.empty:
    print(f"\nRegistros duplicados: {len(duplicates)}")
    print(f"SSAs unicas duplicadas: {len(ssa_counts)}")

if 'arquivo_origem' in df.columns:
    print(f"\nArquivos importados: {len(file_counts)}")
    print(f"Media de registros por arquivo: {len(df) / len(file_counts):.1f}")

# Gera arquivo de relatorio
report_file = f"temp/import_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

with open(report_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("RELATORIO DETALHADO DE ANALISE DE IMPORTACAO\n")
    f.write("="*80 + "\n")
    f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Total de registros: {len(df)}\n")
    f.write(f"Total de colunas: {len(df.columns)}\n")
    f.write("="*80 + "\n\n")

    # Dados ausentes
    if missing_report:
        f.write("COLUNAS COM DADOS AUSENTES\n")
        f.write("-"*80 + "\n\n")
        for item in missing_report:
            f.write(f"Coluna: {item['coluna']}\n")
            f.write(f"  Ausentes: {item['ausentes']} / {item['total']} ({item['percentual']:.1f}%)\n\n")

    # Duplicatas
    if 'numero_ssa' in df.columns and not duplicates.empty:
        f.write("\nDUPLICATAS\n")
        f.write("-"*80 + "\n\n")
        for ssa, count in ssa_counts.items():
            f.write(f"SSA {ssa}: {count} ocorrencias\n")

    # Arquivos
    if 'arquivo_origem' in df.columns:
        f.write("\nARQUIVOS IMPORTADOS\n")
        f.write("-"*80 + "\n\n")
        for arquivo, count in file_counts.items():
            f.write(f"{arquivo}: {count} registros\n")

print(f"\n[OK] Relatorio salvo em: {report_file}")

print("\n" + "="*80)
print("[CONCLUIDO] Analise completa")
print("="*80)
