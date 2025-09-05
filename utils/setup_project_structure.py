# utils/setup_project_structure.py
"""
Utilitario para verificar e criar a estrutura de diretorios do projeto.
Silencioso por padrao: usa logging em vez de prints para nao poluir a CLI.
"""

import os
import logging

# Definindo os diretorios necessários do projeto
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
    Verifica se os diretorios necessários existem e os cria se nao existirem.

    Args:
        base_path (str): O caminho base onde os diretorios serão verificados/criados.
                         Por padrao, usa o diretório atual ('.').
    """
    logger = logging.getLogger("ssa")
    logger.debug("Verificando/criando estrutura de pastas...")
    for dir_name in REQUIRED_DIRS:
        dir_path = os.path.join(base_path, dir_name)
        try:
            os.makedirs(dir_path, exist_ok=True)
            # Mantém saída silenciosa; use logs se necessário
        except OSError as e:
            # Um erro ao criar o diretório é crítico para o funcionamento do programa
            logger.error(f"ERRO CRÍTICO: Não foi possível criar/verificar o diretório '{dir_path}': {e}")
            # Dependendo da política do seu aplicativo, você pode querer encerrar aqui:
            # raise RuntimeError(f"Falha ao criar estrutura de diretorios: {e}") from e
    # Info no arquivo de log; nao imprimir no console
    logger.info("Estrutura de pastas verificada.")

# Se este script for executado diretamente, chama a função de setup
# (Útil para testar o script de setup isoladamente)
if __name__ == "__main__":
    # Execução direta: ainda imprime algo amigável
    print("Verificando/criando estrutura de pastas...")
    setup_dirs()
    print("Estrutura de pastas verificada.")
