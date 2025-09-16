#!/usr/bin/env python3
"""
Script para reorganizar automaticamente todos os arquivos do projeto
nas pastas corretas conforme ESTRUTURA_PROJETO.md
"""

import os
import shutil
from pathlib import Path

def reorganize_project():
    """Reorganiza todos os arquivos do projeto nas pastas corretas."""

    # Definindo categorização dos arquivos
    manutencao_patterns = [
        "backup_", "limpar_", "verificar_", "check_", "analyze_", "debug_",
        "diagnosticar_", "emergency_", "verificacao_completa", "investigar_",
        "parar_importacao", "gerenciar_banco", "quick_diagnosis"
    ]

    desenvolvimento_patterns = [
        "teste_", "test_", "monitor_", "otimizacao_", "validar_", "relatorio_",
        "analisar_", "detector_", "add_protections", "correcao_", "solucao_",
        "update_db_schema", "build"
    ]

    # Arquivos que devem ficar na raiz
    keep_in_root = [
        "main.py", "__init__.py", "pyproject.toml", "requirements.txt",
        "LICENSE", "README.md", "build.py"
    ]

    # Pastas que já existem e devem ser preservadas
    existing_folders = [
        "armazenamento", "core", "extracao", "exportacao", "gui",
        "interface", "utils", "tests", "data", "__pycache__"
    ]

    # Criar pastas se não existirem
    os.makedirs("scripts_manutencao", exist_ok=True)
    os.makedirs("scripts_desenvolvimento", exist_ok=True)

    moved_count = 0

    # Listar todos os arquivos .py na raiz
    for file_path in Path(".").glob("*.py"):
        filename = file_path.name

        # Pular arquivos que devem ficar na raiz
        if filename in keep_in_root:
            print(f"✅ Mantendo na raiz: {filename}")
            continue

        # Determinar destino baseado nos padrões
        destination = None

        # Verificar se é arquivo de manutenção
        if any(pattern in filename.lower() for pattern in manutencao_patterns):
            destination = "scripts_manutencao"
        # Verificar se é arquivo de desenvolvimento
        elif any(pattern in filename.lower() for pattern in desenvolvimento_patterns):
            destination = "scripts_desenvolvimento"
        else:
            # Arquivos que não se encaixam nos padrões vão para desenvolvimento
            destination = "scripts_desenvolvimento"

        # Mover arquivo
        dest_path = Path(destination) / filename
        if not dest_path.exists():
            try:
                shutil.move(str(file_path), str(dest_path))
                print(f"📁 {filename} -> {destination}/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Erro ao mover {filename}: {e}")
        else:
            print(f"⚠️  {filename} já existe em {destination}/")

    print(f"\n✅ Reorganização concluída! {moved_count} arquivos movidos.")

    # Verificar estrutura final
    print("\n📊 Estrutura final:")
    print(f"  📁 scripts_manutencao/: {len(list(Path('scripts_manutencao').glob('*.py')))} arquivos")
    print(f"  📁 scripts_desenvolvimento/: {len(list(Path('scripts_desenvolvimento').glob('*.py')))} arquivos")
    print(f"  📁 Raiz: {len([f for f in Path('.').glob('*.py') if f.name not in ['__init__.py']])} arquivos Python")

def show_current_structure():
    """Mostra a estrutura atual antes da reorganização."""
    print("📊 Estrutura ANTES da reorganização:")
    root_py_files = [f for f in Path('.').glob('*.py') if f.name != '__init__.py']
    print(f"  📁 Raiz: {len(root_py_files)} arquivos Python")

    if Path('scripts_manutencao').exists():
        manut_files = list(Path('scripts_manutencao').glob('*.py'))
        print(f"  📁 scripts_manutencao/: {len(manut_files)} arquivos")

    if Path('scripts_desenvolvimento').exists():
        dev_files = list(Path('scripts_desenvolvimento').glob('*.py'))
        print(f"  📁 scripts_desenvolvimento/: {len(dev_files)} arquivos")

    print(f"\nArquivos na raiz que serão reorganizados:")
    for i, file_path in enumerate(root_py_files[:10]):  # Mostra os primeiros 10
        print(f"  - {file_path.name}")
    if len(root_py_files) > 10:
        print(f"  ... e mais {len(root_py_files)-10} arquivos")

if __name__ == "__main__":
    print("🔄 Reorganizador Automático do Projeto SSA")
    print("=" * 50)

    show_current_structure()

    input("\nPressione ENTER para continuar com a reorganização...")

    reorganize_project()

    print("\n🎉 Reorganização concluída!")
