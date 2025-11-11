#!/usr/bin/env python3
"""
Parser do log de rescan para extrair problemas detalhados.

Extrai:
- Arquivos processados (sucesso/falha)
- Erros de validacao com linhas afetadas
- Registros removidos e SSAs especificas
- Erros de banco de dados
"""

import re
from collections import defaultdict
from datetime import datetime

print("="*80)
print("ANALISE DO LOG DE RESCAN")
print("="*80)

# Le o log
log_file = 'temp/rescan_complete_output.txt'

try:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        log_lines = f.readlines()
except FileNotFoundError:
    print(f"[ERRO] Arquivo {log_file} nao encontrado")
    exit(1)

print(f"[OK] {len(log_lines)} linhas no log")

# Estruturas para armazenar problemas
problemas = {
    'validation_errors': [],      # Erros de validacao (data_cadastro, etc)
    'database_errors': [],          # Erros de banco (too many SQL variables, etc)
    'removed_records': [],          # Registros removidos (sem SSA/descricao)
    'extraction_errors': [],        # Erros de extracao
    'files_skipped': [],            # Arquivos pulados
    'files_processed': []           # Arquivos processados
}

# Padroes regex para extrair informacoes
patterns = {
    'validation': r'Validacao - (.+?\.xlsx): Regra (\w+) atingiu (\d+) linha\(s\) \(ex\.: (.+?)\)',
    'removed': r'Removendo (\d+) linha\(s\) com dados obrigatorios ausentes em \'(.+?\.xlsx)\' \(amostra: (.+?)\)',
    'db_error': r'ERROR.*database.*: (.+)',
    'sql_vars': r'too many SQL variables',
    'extraction_error': r'Erro de extracao em \'(.+?\.xlsx)\': (.+)',
    'removed_invalid': r'Removidos (\d+) registros inv.lidos \(sem n.mero SSA nem descri..o\)',
    'critical_data': r'Dados com problemas criticos em \'(.+?\.xlsx)\': \["(.+?)"\]'
}

# Parse do log
for i, line in enumerate(log_lines, 1):
    # Validacao
    match = re.search(patterns['validation'], line)
    if match:
        arquivo, regra, qtd, exemplos = match.groups()
        problemas['validation_errors'].append({
            'linha_log': i,
            'arquivo': arquivo,
            'regra': regra,
            'quantidade': int(qtd),
            'exemplos': exemplos.split(', ')
        })

    # Registros removidos
    match = re.search(patterns['removed'], line)
    if match:
        qtd, arquivo, ssas = match.groups()
        problemas['removed_records'].append({
            'linha_log': i,
            'arquivo': arquivo,
            'quantidade': int(qtd),
            'ssas': ssas.split(', ')
        })

    # Erro de SQL variables
    if re.search(patterns['sql_vars'], line):
        # Busca o arquivo nas linhas anteriores
        for j in range(max(0, i-10), i):
            if 'docs_entrada' in log_lines[j] and '.xlsx' in log_lines[j]:
                arquivo_match = re.search(r'([^\\]+\.xlsx)', log_lines[j])
                if arquivo_match:
                    problemas['database_errors'].append({
                        'linha_log': i,
                        'arquivo': arquivo_match.group(1),
                        'erro': 'too many SQL variables'
                    })
                    break

    # Erro de extracao
    match = re.search(patterns['extraction_error'], line)
    if match:
        arquivo, erro = match.groups()
        problemas['extraction_errors'].append({
            'linha_log': i,
            'arquivo': arquivo,
            'erro': erro
        })
        problemas['files_skipped'].append(arquivo)

    # Registros invalidos removidos
    match = re.search(patterns['removed_invalid'], line)
    if match:
        qtd = match.group(1)
        # Busca o arquivo nas linhas anteriores
        for j in range(max(0, i-3), i):
            if '.xlsx' in log_lines[j]:
                arquivo_match = re.search(r'([^\\]+\.xlsx)', log_lines[j])
                if arquivo_match:
                    problemas['removed_records'].append({
                        'linha_log': i,
                        'arquivo': arquivo_match.group(1),
                        'quantidade': int(qtd),
                        'motivo': 'Sem numero SSA nem descricao'
                    })
                    break

# Analise por arquivo
print("\n[INFO] Processando estatisticas por arquivo...")

files_with_problems = defaultdict(list)

for error in problemas['validation_errors']:
    files_with_problems[error['arquivo']].append(
        f"Validacao: {error['regra']} - {error['quantidade']} linhas afetadas"
    )

for error in problemas['removed_records']:
    files_with_problems[error['arquivo']].append(
        f"Removidos: {error['quantidade']} registros"
    )

for error in problemas['database_errors']:
    files_with_problems[error['arquivo']].append(
        f"Erro BD: {error['erro']}"
    )

for error in problemas['extraction_errors']:
    files_with_problems[error['arquivo']].append(
        f"Erro extracao: {error['erro'][:50]}..."
    )

# Exibe resumo
print("\n" + "="*80)
print("RESUMO DE PROBLEMAS")
print("="*80)

print(f"\nErros de validacao: {len(problemas['validation_errors'])}")
print(f"Registros removidos: {len(problemas['removed_records'])}")
print(f"Erros de banco de dados: {len(problemas['database_errors'])}")
print(f"Erros de extracao: {len(problemas['extraction_errors'])}")
print(f"Arquivos pulados: {len(set(problemas['files_skipped']))}")

print(f"\nArquivos com problemas: {len(files_with_problems)}")

# Top 10 arquivos com mais problemas
print("\n" + "="*80)
print("TOP 10 ARQUIVOS COM MAIS PROBLEMAS")
print("="*80)

sorted_files = sorted(files_with_problems.items(), key=lambda x: len(x[1]), reverse=True)

for i, (arquivo, issues) in enumerate(sorted_files[:10], 1):
    print(f"\n{i}. {arquivo}")
    print(f"   {len(issues)} problema(s):")
    for issue in issues[:5]:  # Mostra ate 5 problemas
        print(f"     - {issue}")
    if len(issues) > 5:
        print(f"     ... e mais {len(issues) - 5} problema(s)")

# Gera relatorio detalhado
report_file = f"temp/rescan_problems_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

with open(report_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("RELATORIO DETALHADO DE PROBLEMAS DE IMPORTACAO\n")
    f.write("="*80 + "\n")
    f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Linhas no log: {len(log_lines)}\n")
    f.write("="*80 + "\n\n")

    # Erros de validacao
    f.write("ERROS DE VALIDACAO\n")
    f.write("-"*80 + "\n\n")
    for error in problemas['validation_errors']:
        f.write(f"Arquivo: {error['arquivo']}\n")
        f.write(f"  Regra: {error['regra']}\n")
        f.write(f"  Linhas afetadas: {error['quantidade']}\n")
        f.write(f"  Exemplos de SSAs: {', '.join(error['exemplos'])}\n")
        f.write(f"  Linha do log: {error['linha_log']}\n\n")

    # Registros removidos
    f.write("\nREGISTROS REMOVIDOS\n")
    f.write("-"*80 + "\n\n")
    for error in problemas['removed_records']:
        f.write(f"Arquivo: {error['arquivo']}\n")
        f.write(f"  Quantidade: {error['quantidade']}\n")
        if 'ssas' in error:
            f.write(f"  SSAs: {', '.join(error['ssas'])}\n")
        if 'motivo' in error:
            f.write(f"  Motivo: {error['motivo']}\n")
        f.write(f"  Linha do log: {error['linha_log']}\n\n")

    # Erros de banco de dados
    f.write("\nERROS DE BANCO DE DADOS\n")
    f.write("-"*80 + "\n\n")
    for error in problemas['database_errors']:
        f.write(f"Arquivo: {error['arquivo']}\n")
        f.write(f"  Erro: {error['erro']}\n")
        f.write(f"  Linha do log: {error['linha_log']}\n\n")

    # Erros de extracao
    f.write("\nERROS DE EXTRACAO\n")
    f.write("-"*80 + "\n\n")
    for error in problemas['extraction_errors']:
        f.write(f"Arquivo: {error['arquivo']}\n")
        f.write(f"  Erro: {error['erro']}\n")
        f.write(f"  Linha do log: {error['linha_log']}\n\n")

    # Resumo por arquivo
    f.write("\nRESUMO POR ARQUIVO\n")
    f.write("-"*80 + "\n\n")
    for arquivo, issues in sorted_files:
        f.write(f"\n{arquivo}:\n")
        for issue in issues:
            f.write(f"  - {issue}\n")

print(f"\n[OK] Relatorio salvo em: {report_file}")

print("\n" + "="*80)
print("[CONCLUIDO] Analise do log completa")
print("="*80)
