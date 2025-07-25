# utils/setup_project_structure.py
"""
Utilitário para verificar e criar a estrutura de diretórios do projeto.
"""

import os

# Definindo os diretórios necessários do projeto
REQUIRED_DIRS = [
    'docs_entrada',  # Pasta para os arquivos Excel de entrada
    'data',          # Pasta para o banco de dados e cache
    'docs_saida',    # Pasta para os arquivos exportados
    'config',        # Pasta para arquivos de configuração
    'dist',          # Pasta para distribuição/executáveis (se usado)
    'tests',         # Pasta para testes
    'gui'            # <--- ADICIONADO: Pasta para arquivos da Interface Gráfica
    # Adicione outras pastas aqui se necessário no futuro
]

def setup_dirs(base_path: str = "."):
    """
    Verifica se os diretórios necessários existem e os cria se não existirem.

    Args:
        base_path (str): O caminho base onde os diretórios serão verificados/criados.
                         Por padrão, usa o diretório atual ('.').
    """
    print("Verificando/criando estrutura de pastas...")
    for dir_name in REQUIRED_DIRS:
        dir_path = os.path.join(base_path, dir_name)
        try:
            os.makedirs(dir_path, exist_ok=True)
            # print(f"Diretório '{dir_path}' verificado/criado.") # Opcional: log detalhado
        except OSError as e:
            # Um erro ao criar o diretório é crítico para o funcionamento do programa
            print(f"ERRO CRÍTICO: Não foi possível criar/verificar o diretório '{dir_path}': {e}")
            # Dependendo da política do seu aplicativo, você pode querer encerrar aqui:
            # raise RuntimeError(f"Falha ao criar estrutura de diretórios: {e}") from e
    print("Estrutura de pastas verificada.")

# Se este script for executado diretamente, chama a função de setup
# (Útil para testar o script de setup isoladamente)
if __name__ == "__main__":
    setup_dirs()
