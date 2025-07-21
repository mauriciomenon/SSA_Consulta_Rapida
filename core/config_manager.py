# core/config_manager.py 20250721 120510 (v2.0 - Inteligente)
import json
import os

SETTINGS_PATH = os.path.join('config', 'settings.json')
DISPLAY_MAPPINGS_PATH = os.path.join('config', 'display_mappings.json')

def _get_all_display_columns() -> dict:
    """Lê o display_mappings para obter todas as colunas possíveis e define sua visibilidade padrão."""
    try:
        with open(DISPLAY_MAPPINGS_PATH, 'r', encoding='utf-8') as f:
            display_map = json.load(f)
        
        # Por padrão, todas as colunas são visíveis, exceto 'semana_cadastro'
        visibility = {key: True for key in display_map.keys()}
        if 'semana_cadastro' in visibility:
            visibility['semana_cadastro'] = False
        return visibility
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _get_default_settings() -> dict:
    """Cria a estrutura de configurações padrão completa."""
    return {
        "display_settings": {
            "column_widths": {
                "#": 4, "Nº SSA": 9, "Loc.": 10, "Emissor": 8, "Executor": 8,
                "Sem.\nCadastro": 8, "Data\nCadastro": 10
            },
            "column_visibility": _get_all_display_columns()
        },
        "user_preferences": {
            "auto_scroll_to_end": False
        }
    }

def _merge_settings(user_settings: dict, default_settings: dict) -> tuple[dict, bool]:
    """Garante que as configurações do usuário contenham todas as chaves padrão."""
    settings_changed = False
    # Garante que a seção column_visibility exista
    if 'column_visibility' not in user_settings.get('display_settings', {}):
        user_settings.setdefault('display_settings', {})['column_visibility'] = {}
        settings_changed = True

    # Verifica se falta alguma coluna na configuração do usuário e a adiciona
    default_visibility = default_settings['display_settings']['column_visibility']
    user_visibility = user_settings['display_settings']['column_visibility']
    
    for key, value in default_visibility.items():
        if key not in user_visibility:
            user_visibility[key] = value
            settings_changed = True
            
    return user_settings, settings_changed

def load_settings() -> dict:
    """
    Carrega as configurações do settings.json, criando ou atualizando o arquivo
    conforme necessário para ser amigável ao usuário.
    """
    default_settings = _get_default_settings()
    
    if not os.path.exists(SETTINGS_PATH):
        print(f"AVISO: Arquivo de configurações não encontrado. Criando '{SETTINGS_PATH}' com valores padrão.")
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=4)
            return default_settings
        except IOError:
            return default_settings

    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            user_settings = json.load(f)
        
        # Mescla para garantir que novas colunas sejam adicionadas
        final_settings, changed = _merge_settings(user_settings, default_settings)
        
        if changed:
            print(f"AVISO: O arquivo de configurações foi atualizado com novas opções. Salvando alterações em '{SETTINGS_PATH}'.")
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(final_settings, f, indent=4)

        return final_settings
    except (json.JSONDecodeError, IOError):
        print(f"ERRO: Não foi possível ler o arquivo de configurações. Usando padrões.")
        return default_settings
