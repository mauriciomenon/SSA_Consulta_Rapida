#!/usr/bin/env python3
"""
Teste de importacao DETALHADO com relatorio completo de problemas.

Captura:
- Arquivo
- Linha (numero da linha no Excel)
- Coluna (nome da coluna)
- Valor problematico
- Tipo de erro
- Descricao do problema
"""

import os
import subprocess
import sys
import traceback
from datetime import datetime

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Lista para armazenar problemas encontrados
problemas = []
MAX_PROBLEMAS = 1000


def registrar_problema(arquivo, linha, coluna, valor, tipo_erro, descricao):
    """Registra um problema encontrado durante importacao."""
    if len(problemas) >= MAX_PROBLEMAS:
        return
    problemas.append(
        {
            "arquivo": os.path.basename(arquivo),
            "linha": linha,
            "coluna": coluna,
            "valor": valor,
            "tipo_erro": tipo_erro,
            "descricao": descricao,
        }
    )


def test_import_cli():
    """Testa importacao via CLI com relatorio detalhado."""
    print("=" * 80)
    print("TESTE DE IMPORTACAO DETALHADO - CLI")
    print("=" * 80)

    try:
        # Limpa banco existente
        db_path = "data/ssas.db"
        if os.path.exists(db_path):
            print(f"\n[INFO] Removendo banco existente: {db_path}")
            os.remove(db_path)
            print("  [OK] Banco removido")

        # Lista arquivos a importar
        docs_dir = "docs_entrada"
        arquivos = [f for f in os.listdir(docs_dir) if f.endswith(".xlsx")]
        print(f"\n[INFO] Encontrados {len(arquivos)} arquivos .xlsx")

        assert len(arquivos) > 0, "Nenhum arquivo para importar"

        # Mostra primeiros 10
        print("\n[INFO] Primeiros 10 arquivos:")
        for i, arquivo in enumerate(arquivos[:10], 1):
            print(f"  {i}. {arquivo}")

        if len(arquivos) > 10:
            print(f"  ... e mais {len(arquivos) - 10} arquivos")

        # Importa via CLI
        print(f"\n[INFO] Iniciando importacao de {len(arquivos)} arquivos...")
        print("[INFO] Isso pode demorar varios minutos - NAO INTERROMPER")
        print("[INFO] Monitorando processo...")

        import time

        start_time = time.time()

        # Executa main.py --rescan com captura de saida
        process = subprocess.run(
            [sys.executable, "main.py", "--rescan"],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )

        print("\n[SAIDA DO PROCESSO]")
        print("-" * 80)

        linha_count = 0
        for line in (process.stdout or "").splitlines():
            print(line)
            linha_count += 1
            if ("ERROR" in line or "Validacao" in line) and "linha(s)" in line.lower():
                registrar_problema(
                    arquivo="(extrair do log)",
                    linha="(ver log)",
                    coluna="(ver log)",
                    valor="(ver log)",
                    tipo_erro="Validacao",
                    descricao=line,
                )
        if process.stderr:
            print("\n[STDERR]")
            print(process.stderr)

        elapsed = time.time() - start_time
        print("-" * 80)
        print(f"[INFO] Processo terminou em {elapsed:.1f}s")
        print(f"[INFO] Codigo de retorno: {process.returncode}")
        print(f"[INFO] Linhas de output: {linha_count}")

        if process.returncode != 0:
            raise RuntimeError(f"Importacao falhou com codigo {process.returncode}")
        print("\n[SUCESSO] Importacao via CLI concluida")
        return True
    except Exception as e:
        print(f"\n[ERRO] Falha no teste de importacao via CLI: {e}")
        traceback.print_exc()
        raise AssertionError(f"Falha no teste de importacao via CLI: {e}") from e


def analyze_database():
    """Analisa banco de dados apos importacao."""
    print("\n" + "=" * 80)
    print("ANALISE DO BANCO DE DADOS")
    print("=" * 80)

    try:
        from armazenamento.database import query_db

        db_path = "data/ssas.db"
        if not os.path.exists(db_path):
            print("\n[ERRO] Banco de dados nao foi criado")
            return False

        # Carrega dados
        print("\n[INFO] Carregando dados do banco...")
        df = query_db(db_path, "ssas")

        if df is None or df.empty:
            print("  [ERRO] Banco vazio")
            return False

        print(f"  [OK] {len(df)} registros carregados")

        # Analise basica
        print("\n[INFO] Colunas no banco:")
        for i, col in enumerate(df.columns, 1):
            non_null = df[col].notna().sum()
            pct = (non_null / len(df)) * 100
            print(f"  {i:2d}. {col:30s} - {non_null:6d}/{len(df):6d} ({pct:5.1f}%)")

        # Verifica dados ausentes criticos
        print("\n[INFO] Verificando dados ausentes criticos...")
        critical_columns = ["numero_ssa", "descricao_ssa", "situacao"]

        for col in critical_columns:
            if col in df.columns:
                missing = df[col].isna().sum()
                if missing > 0:
                    print(f"  [AVISO] {col}: {missing} valores ausentes")

                    # Registra amostras
                    missing_indices = df[df[col].isna()].index[:5].tolist()
                    for idx in missing_indices:
                        numero = (
                            df.loc[idx, "numero_ssa"]
                            if "numero_ssa" in df.columns
                            else "N/A"
                        )
                        registrar_problema(
                            arquivo="(importado)",
                            linha=idx + 2,  # +2 porque Excel comeca em 1 e tem header
                            coluna=col,
                            valor="<vazio>",
                            tipo_erro="Dado ausente",
                            descricao=f"Coluna critica '{col}' vazia para numero_ssa={numero}",
                        )
                else:
                    print(f"  [OK] {col}: sem valores ausentes")

        # Verifica duplicatas
        print("\n[INFO] Verificando duplicatas...")
        if "numero_ssa" in df.columns:
            duplicatas = df[df.duplicated(subset=["numero_ssa"], keep=False)]
            if not duplicatas.empty:
                print(f"  [AVISO] {len(duplicatas)} registros duplicados")

                # Mostra amostras
                ssa_duplicadas = duplicatas["numero_ssa"].unique()[:5]
                for ssa in ssa_duplicadas:
                    count = (duplicatas["numero_ssa"] == ssa).sum()
                    print(f"    - SSA {ssa}: {count} ocorrencias")

                    registrar_problema(
                        arquivo="(importado)",
                        linha="N/A",
                        coluna="numero_ssa",
                        valor=ssa,
                        tipo_erro="Duplicata",
                        descricao=f"SSA {ssa} aparece {count} vezes",
                    )
            else:
                print("  [OK] Sem duplicatas")

        return True

    except Exception as e:
        print(f"\n[ERRO] Falha na analise: {e}")
        traceback.print_exc()
        return False


def generate_report():
    """Gera relatorio detalhado de problemas."""
    print("\n" + "=" * 80)
    print("RELATORIO DE PROBLEMAS")
    print("=" * 80)

    if not problemas:
        print("\n[INFO] Nenhum problema registrado durante importacao!")
        return

    print(f"\n[INFO] Total de problemas: {len(problemas)}")

    # Agrupa por tipo de erro
    tipos = {}
    for p in problemas:
        tipo = p["tipo_erro"]
        if tipo not in tipos:
            tipos[tipo] = []
        tipos[tipo].append(p)

    print("\n[INFO] Problemas por tipo:")
    for tipo, items in tipos.items():
        print(f"  - {tipo}: {len(items)} ocorrencias")

    # Cria arquivo de relatorio em LocalTemp (local-only, gitignored)
    import os

    os.makedirs("LocalTemp", exist_ok=True)
    report_file = (
        f"LocalTemp/import_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("RELATORIO DETALHADO DE PROBLEMAS DE IMPORTACAO\n")
        f.write("=" * 80 + "\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total de problemas: {len(problemas)}\n")
        f.write("=" * 80 + "\n\n")

        for i, p in enumerate(problemas, 1):
            f.write(f"PROBLEMA #{i}\n")
            f.write(f"  Arquivo:    {p['arquivo']}\n")
            f.write(f"  Linha:      {p['linha']}\n")
            f.write(f"  Coluna:     {p['coluna']}\n")
            f.write(f"  Valor:      {p['valor']}\n")
            f.write(f"  Tipo erro:  {p['tipo_erro']}\n")
            f.write(f"  Descricao:  {p['descricao']}\n")
            f.write("-" * 80 + "\n\n")

    print(f"\n[INFO] Relatorio salvo em: {report_file}")

    # Mostra primeiros 5 problemas
    print("\n[INFO] Primeiros 5 problemas:")
    for i, p in enumerate(problemas[:5], 1):
        print(f"\n  PROBLEMA #{i}:")
        print(f"    Arquivo:   {p['arquivo']}")
        print(f"    Linha:     {p['linha']}")
        print(f"    Coluna:    {p['coluna']}")
        print(f"    Valor:     {p['valor']}")
        print(f"    Tipo:      {p['tipo_erro']}")
        print(f"    Descricao: {p['descricao']}")

    if len(problemas) > 5:
        print(f"\n  ... e mais {len(problemas) - 5} problemas (ver relatorio completo)")


def main():
    """Executa teste completo de importacao."""
    print("\n" + "=" * 80)
    print("TESTE COMPLETO DE IMPORTACAO COM RELATORIO DETALHADO")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {}

    # 1. Teste importacao CLI
    results["import_cli"] = test_import_cli()

    # 2. Analise do banco
    if results["import_cli"]:
        results["analyze_db"] = analyze_database()
    else:
        results["analyze_db"] = False

    # 3. Gera relatorio
    generate_report()

    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)

    for test, result in results.items():
        status = "[PASSOU]" if result else "[FALHOU]"
        print(f"  {status} {test}")

    print(f"\n  Total de problemas registrados: {len(problemas)}")

    if all(results.values()) and len(problemas) == 0:
        print("\n[SUCESSO] Importacao completa sem problemas!")
        return 0
    elif all(results.values()):
        print("\n[SUCESSO] Importacao completa mas com problemas registrados")
        print("           Ver relatorio para detalhes")
        return 0
    else:
        print("\n[FALHA] Importacao falhou")
        return 1


if __name__ == "__main__":
    sys.exit(main())
