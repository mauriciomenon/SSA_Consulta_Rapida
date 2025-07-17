# build.py (v1.2)
import os
import sys
import shutil
import subprocess

# --- Configurações do Build ---
APP_NAME = "SSA_Consulta_Rapida"
ENTRY_POINT = "main.py"
DIST_DIR = "dist"
BUILD_DIR = "build"
FINAL_ZIP_NAME = f"{APP_NAME}_v1.2"

# Estrutura de pastas e arquivos a serem incluídos
DIST_STRUCTURE = {
    "dirs": ['docs_entrada', 'docs_saida'],
    "files": {
        'config': ['config/column_mappings.json', 'config/display_mappings.json']
    }
}

def run_pyinstaller():
    """Executa o PyInstaller para criar o executável."""
    print("--- Iniciando o PyInstaller para criar o .exe ---")
    
    # Removida a flag '--noconsole'.
    command = [
        sys.executable,
        '-m', 'PyInstaller',
        '--onefile',
        '--clean',
        f'--name={APP_NAME}',
        ENTRY_POINT
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        print(">>> Sucesso: O executável foi criado.")
        return True
    except subprocess.CalledProcessError as e:
        print("--- ERRO DURANTE A EXECUÇÃO DO PYINSTALLER ---")
        print(f"Comando: {' '.join(command)}")
        print(f"Código de Saída: {e.returncode}")
        print("\n--- Saída de Erro (stderr) ---")
        print(e.stderr)
        print(">>> Falha: Não foi possível criar o executável.")
        return False

def create_distribution_package():
    """Cria a pasta de distribuição final e o arquivo .zip."""
    print("\n--- Criando o pacote de distribuição final ---")
    
    exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    if not os.path.exists(exe_path):
        print(f"ERRO: O executável '{exe_path}' não foi encontrado. Abortando.")
        return

    package_root_dir = os.path.join(DIST_DIR, FINAL_ZIP_NAME)

    if os.path.exists(package_root_dir):
        shutil.rmtree(package_root_dir)
    os.makedirs(package_root_dir)
    print(f"Criada a pasta de pacote: '{package_root_dir}'")

    shutil.copy(exe_path, os.path.join(package_root_dir, f"{APP_NAME}.exe"))
    print(f"Copiado '{APP_NAME}.exe' para o pacote.")

    # CORREÇÃO: Criando a estrutura completa de pastas e arquivos.
    print("Criando estrutura de pastas e arquivos de configuração...")
    for dir_name in DIST_STRUCTURE['dirs']:
        os.makedirs(os.path.join(package_root_dir, dir_name), exist_ok=True)
    
    for dir_name, files in DIST_STRUCTURE['files'].items():
        dest_dir = os.path.join(package_root_dir, dir_name)
        os.makedirs(dest_dir, exist_ok=True)
        for file_path in files:
            if os.path.exists(file_path):
                shutil.copy(file_path, dest_dir)
            else:
                print(f"AVISO: Arquivo de configuração '{file_path}' não encontrado. Ele não será incluído.")

    print("Estrutura de pastas do pacote criada.")

    print(f"\nCompactando o pacote em '{FINAL_ZIP_NAME}.zip'...")
    shutil.make_archive(base_name=os.path.join(DIST_DIR, FINAL_ZIP_NAME),
                        format='zip',
                        root_dir=DIST_DIR,
                        base_dir=FINAL_ZIP_NAME)
    print(f">>> Sucesso: Pacote '{FINAL_ZIP_NAME}.zip' criado na pasta '{DIST_DIR}'.")

def cleanup():
    """Limpa as pastas e arquivos temporários do build."""
    print("\n--- Limpando arquivos temporários ---")
    
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
    package_root_dir = os.path.join(DIST_DIR, FINAL_ZIP_NAME)
    if os.path.exists(package_root_dir):
        shutil.rmtree(package_root_dir)
    print("Limpeza concluída.")

if __name__ == "__main__":
    if run_pyinstaller():
        create_distribution_package()
    cleanup()

