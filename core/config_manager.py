# core/config_manager.py 20250725 163000 (v2.1 - Melhorias de Erro, Logging)
"""
Gerenciador de configurações da aplicação.

Responsável por carregar, salvar e garantir a existência do arquivo settings.json.
"""

import json
import os
import shutil
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Caminhos padrão
CONFIG_DIR = 'config'
DEFAULT_SETTINGS_FILE = os.path.join(CONFIG_DIR, 'default_settings.json')
USER_SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'display_mappings.json')
COLUMN_MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'column_mappings.json')

def load_settings() -> Dict[str, Any]:
    """
    Carrega as configurações do usuário. Se não existir, carrega as padrões.
    
    Returns:
        Dict[str, Any]: Um dicionário com as configurações.
    """
    settings_path = USER_SETTINGS_FILE
    if not os.path.exists(settings_path):
        logger.info(f"Arquivo de configuração do usuário '{settings_path}' não encontrado. Carregando padrões.")
        settings_path = DEFAULT_SETTINGS_FILE

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        logger.debug(f"Configurações carregadas de '{settings_path}'.")
        return settings
    except FileNotFoundError:
        logger.critical(f"Arquivo de configuração '{settings_path}' não encontrado.")
        # Retorna um dicionário vazio ou padrão mínimo como último recurso?
        # Ou lança uma exceção? Vamos lançar para que o chamador decida.
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON em '{settings_path}': {e}")
        raise

def save_settings(settings: Dict[str, Any]):
    """
    Salva as configurações do usuário.
    
    Args:
        settings (Dict[str, Any]): O dicionário de configurações a ser salvo.
    """
    try:
        os.makedirs(os.path.dirname(USER_SETTINGS_FILE), exist_ok=True)
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logger.info(f"Configurações salvas em '{USER_SETTINGS_FILE}'.")
    except IOError as e:
        logger.error(f"Erro ao salvar configurações em '{USER_SETTINGS_FILE}': {e}")
        raise

def ensure_default_settings():
    """
    Garante que os arquivos de configuração padrão existam.
    Se não existirem, os copia dos arquivos de exemplo ou os cria.
    """
    required_files = {
        DEFAULT_SETTINGS_FILE: 'default_settings.json.example',
        DISPLAY_MAPPINGS_FILE: 'display_mappings.json.example',
        COLUMN_MAPPINGS_FILE: 'column_mappings.json.example',
        # Adicione outros arquivos de configuração aqui se necessário
    }

    for target_file, example_file in required_files.items():
        if not os.path.exists(target_file):
            example_path = os.path.join(CONFIG_DIR, example_file)
            if os.path.exists(example_path):
                try:
                    shutil.copyfile(example_path, target_file)
                    logger.info(f"Arquivo de configuração padrão criado: {target_file}")
                except IOError as e:
                    logger.error(f"Falha ao copiar '{example_path}' para '{target_file}': {e}")
            else:
                # Se o arquivo exemplo também não existir, cria um padrão mínimo ou loga um aviso
                logger.warning(f"Arquivo de exemplo '{example_path}' não encontrado para '{target_file}'.")
                # Aqui você poderia criar um arquivo padrão mínimo, se desejado.
                # Por enquanto, apenas avisa.

# --- Placeholder para handler de configuração via CLI ---
# Este handler pode ser expandido para um menu interativo ou edição direta.
def handle_config_command():
    """Handler para o comando '-c' ou 'config' na CLI."""
    print("\n--- Menu de Configurações ---")
    print("Funcionalidade de configuração ainda não implementada.")
    print("Edite o arquivo 'config/settings.json' manualmente para alterar as configurações.")
    print("Reinicie o programa para que as mudanças tenham efeito.")
    # Futura implementação poderia:
    # 1. Carregar settings atuais
    # 2. Mostrar opções (ex: auto_scroll, visibilidade de colunas)
    # 3. Permitir edição
    # 4. Salvar settings atualizadas
    # 5. Notificar que as mudanças terão efeito na próxima execução ou recarregar
