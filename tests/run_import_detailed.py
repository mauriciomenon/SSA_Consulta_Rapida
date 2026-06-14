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
import argparse
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

# Adiciona o diretorio raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Lista para armazenar problemas encontrados
problemas = []
MAX_PROBLEMAS = 1000


def _xlsx_files(docs_dir: Path) -> list[Path]:
    return sorted(
        (path for path in docs_dir.iterdir() if path.suffix.casefold() == ".xlsx"),
        key=lambda path: path.name.casefold(),
    )


def _write_smoke_xlsx(docs_dir: Path) -> Path:
    import pandas as pd

    docs_dir.mkdir(parents=True, exist_ok=True)
    target = docs_dir / "smoke_import.xlsx"
    pd.DataFrame(
        [
            {
                "Numero SSA": "202600001",
                "Descricao": "Smoke import SSA",
                "Emitida Em": "2026-06-14 10:00:00",
                "Executor": "IEE3",
                "Emissor": "IEE3",
                "Situacao": "APL",
            }
        ]
    ).to_excel(target, index=False)
    return target


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


def _progress_callback(event_type, data):
    if event_type == "start":
        print(f"[INFO] Total de arquivos: {data.get('total', 0)}")
    elif event_type == "file_start":
        print(f"[INFO] Processando: {data.get('filename', '')}")
    elif event_type == "file_success":
        print(f"[OK] {data.get('filename', '')}: {data.get('records', 0)} registros")
    elif event_type == "file_error":
        message = str(data.get("error", "Unknown"))
        print(f"[ERRO] {data.get('filename', '')}: {message}")
        registrar_problema(
            arquivo=str(data.get("filename", "")),
            linha="(ver log)",
            coluna="(ver log)",
            valor="(ver log)",
            tipo_erro="Importacao",
            descricao=message,
        )
    elif event_type == "finish":
        print(
            f"[INFO] Concluido: {data.get('processed', 0)}/{data.get('total', 0)}"
        )


def test_import_cli(docs_dir: Path, db_path: Path, *, reset_db: bool = False):
    """Testa importacao via CLI com relatorio detalhado."""
    print("=" * 80)
    print("TESTE DE IMPORTACAO DETALHADO")
    print("=" * 80)

    try:
        if reset_db and db_path.exists():
            print(f"\n[INFO] Removendo banco informado: {db_path}")
            db_path.unlink()
            print("  [OK] Banco removido")

        # Lista arquivos a importar
        docs_dir.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        arquivos = [f.name for f in _xlsx_files(docs_dir)]
        print(f"\n[INFO] Encontrados {len(arquivos)} arquivos .xlsx")

        if not arquivos:
            print("[ERRO] Nenhum arquivo .xlsx para importar no diretorio informado.")
            return False

        # Mostra primeiros 10
        print("\n[INFO] Primeiros 10 arquivos:")
        for i, arquivo in enumerate(arquivos[:10], 1):
            print(f"  {i}. {arquivo}")

        if len(arquivos) > 10:
            print(f"  ... e mais {len(arquivos) - 10} arquivos")

        print(f"\n[INFO] Iniciando importacao de {len(arquivos)} arquivos...")
        print("[INFO] Isso pode demorar varios minutos - NAO INTERROMPER")
        print("[INFO] Monitorando processo...")

        import time
        from core.app_logic import run_importer_logic

        start_time = time.time()

        success = run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(db_path.parent),
            db_name=db_path.name,
            table_name="ssa_table",
            force_import=False,
            progress_callback=_progress_callback,
        )

        elapsed = time.time() - start_time
        print("-" * 80)
        print(f"[INFO] Processo terminou em {elapsed:.1f}s")

        if not success:
            print("\n[INFO] Importacao concluida sem atualizacao de dados")
            return False
        else:
            print("\n[SUCESSO] Importacao concluida")
        return True
    except Exception as e:
        print(f"\n[ERRO] Falha no teste de importacao: {e}")
        traceback.print_exc()
        raise AssertionError(f"Falha no teste de importacao: {e}") from e


def analyze_database(db_path: Path):
    """Analisa banco de dados apos importacao."""
    print("\n" + "=" * 80)
    print("ANALISE DO BANCO DE DADOS")
    print("=" * 80)

    try:
        from armazenamento.database import query_db

        if not db_path.exists():
            print("\n[ERRO] Banco de dados nao foi criado")
            return False

        # Carrega dados
        print("\n[INFO] Carregando dados do banco...")
        df = query_db(str(db_path), "ssas")

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


def main(argv: list[str] | None = None):
    """Executa teste completo de importacao."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", help="Diretorio de entrada. Omitido usa temp.")
    parser.add_argument("--db-path", help="Banco de teste. Omitido usa temp.")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Remove o DB informado antes de importar. Nunca e automatico.",
    )
    args = parser.parse_args(argv)
    temp_context = None
    if args.docs_dir or args.db_path:
        if not (args.docs_dir and args.db_path):
            parser.error("--docs-dir e --db-path devem ser informados juntos")
        docs_dir = Path(args.docs_dir).expanduser()
        db_path = Path(args.db_path).expanduser()
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="ssa_import_detailed_")
        temp_root = Path(temp_context.name)
        docs_dir = temp_root / "docs_entrada"
        db_path = temp_root / "data" / "ssas.db"
        _write_smoke_xlsx(docs_dir)

    print("\n" + "=" * 80)
    print("TESTE COMPLETO DE IMPORTACAO COM RELATORIO DETALHADO")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Docs: {docs_dir}")
    print(f"DB: {db_path}")
    print("=" * 80)

    try:
        results = {}

        # 1. Teste importacao
        results["import_cli"] = test_import_cli(
            docs_dir,
            db_path,
            reset_db=bool(args.reset_db),
        )

        # 2. Analise do banco
        if results["import_cli"] and db_path.exists():
            results["analyze_db"] = analyze_database(db_path)
        elif results["import_cli"]:
            print("\n[ERRO] Importacao reportou sucesso, mas o DB nao foi criado")
            results["analyze_db"] = False
        else:
            results["analyze_db"] = True

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
        if all(results.values()):
            print("\n[SUCESSO] Importacao completa mas com problemas registrados")
            print("           Ver relatorio para detalhes")
            return 0
        print("\n[FALHA] Importacao falhou")
        return 1
    finally:
        if temp_context is not None:
            temp_context.cleanup()


if __name__ == "__main__":
    sys.exit(main())
