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

# Default mapping used if display_mappings.json is missing/invalid
DEFAULT_DISPLAY_MAPPINGS: Dict[str, str] = {
    "numero_ssa": "Nº SSA",
    "situacao": "Situação",
    "derivada_de": "Derivada de",
    "localizacao_codigo": "Loc.",
    "descricao_localizacao": "Desc. Loc.",
    "equipamento": "Equip.",
    "semana_cadastro": "Sem.\nCadastro",
    "data_cadastro": "Emitida Em",
    "descricao_ssa": "Descrição da SSA",
    "setor_emissor": "Emissor",
    "setor_executor": "Executor",
    "solicitante": "Solicitante",
    "servico_origem": "Serv. Origem",
    "grau_prioridade_emissao": "Prior. Emissão",
    "grau_prioridade_planejamento": "Prior. Planej.",
    "execucao_simples": "Exec. Simples",
    "responsavel_programacao": "Resp. Prog.",
    "semana_programada": "Sem. Prog.",
    "responsavel_execucao": "Resp. Exec.",
    "descricao_execucao": "Descrição da Execução",
    "anomalia": "Anomalia",
    "sistema_origem": "Sis. Origem",
    "prazo_limite": "Prazo Limite",
    "status_execucao_prazo": "Situação do Prazo",
    "tempo_disponivel": "Tempo Disp.",
    "data_limite": "Data Limite",
    "tempo_excedido": "Tempo Excedido",
    "desde": "Desde",
    "tempo_total": "Tempo Total",
    "desde_1": "Desde (1)",
    "total_tempo_tpe_planejado": "Tempo TPE Plan.",
    "total_tempo_tex_planejado": "Tempo TEX Plan.",
    "total_tempo_tpo_planejado": "Tempo TPO Plan.",
    "total_horas_programadas": "Horas Prog.",
    "semana_executada": "Sem. Exec.",
    "num_reprogramacoes": "Nº Reprog.",
    "execucao_parcial": "Exec. Parcial",
    "atividade_especial": "Atividade Especial",
    "equipamento_retirado": "Equipamento Retirado",
    "sn_retirado": "SN Retirado",
    "destino": "Destino",
    "equipamento_instalado": "Equipamento Instalado",
    "sn_instalado": "SN Instalado",
    "sn_extra": "SN Extra",
    "origem": "Origem",
    "desativacao_da_localizacao": "Desativação da Localização",
    "instalacao_estimada": "Instalação Estimada",
    "executado": "Executado",
    "concluido": "Concluído",
    "total_tempo_tpo_executada": "Tempo TPO Exec.",
    "data_inicio_programada": "Data Início Prog.",
    "data_programacao": "Data Programação",
    "data_inicio_reprogramada": "Data Início Reprog.",
    "data_reprogramacao": "Data Reprog.",
    "situacao_reprogramacao": "Situação Reprog.",
    "total_de_reprogramacoes": "Total Reprog.",
    "situacao_de_desvio": "Situação Desvio",
    "ate_1": "Até (1)",
    "ate_2": "Até (2)",
    "desde_2": "Desde (2)",
    "numero_ssa_relacionada_1": "Nº SSA Rel. 1",
    "numero_ssa_relacionada_2": "Nº SSA Rel. 2",
    "numero_ssa_relacionada_3": "Nº SSA Rel. 3",
    "setor_emissor_relacionado_1": "Setor Emissor Rel. 1",
    "setor_emissor_relacionado_2": "Setor Emissor Rel. 2",
    "setor_executor_relacionado_1": "Setor Executor Rel. 1",
    "setor_executor_relacionado_2": "Setor Executor Rel. 2",
    "situacao_relacionada_1": "Situação Rel. 1",
    "situacao_relacionada_2": "Situação Rel. 2",
    "relacao": "Relação"
}

# Default mapping used if column_mappings.json is missing/invalid
DEFAULT_COLUMN_MAPPINGS: Dict[str, list] = {
    "numero_ssa": [
        "Nº SSA",
        "Nº SSA*",
        "Nº SSA Original",
        "Numero SSA",
        "Nº da SSA"
    ],
    "situacao": [
        "Situação",
        "Situacao",
        "Status"
    ],
    "derivada_de": [
        "Derivada de",
        "Derivada De"
    ],
    "localizacao_codigo": [
        "Loc.",
        "Localização",
        "Cod. Localização",
        "Codigo Localizacao"
    ],
    "descricao_localizacao": [
        "Desc. Loc.",
        "Descrição da Localização",
        "Descricao Localizacao"
    ],
    "equipamento": [
        "Equip.",
        "Equipamento"
    ],
    "semana_cadastro": [
        "Sem.\nCadastro",
        "Sem. Cadastro",
        "Semana Cadastro"
    ],
    "data_cadastro": [
        "Emitida Em",
        "Data de Emissão",
        "Data Cadastro",
        "Data/Hora de Cadastro"
    ],
    "descricao_ssa": [
        "Descrição da SSA",
        "Descricao da SSA",
        "Descricao"
    ],
    "setor_emissor": [
        "Emissor",
        "Setor Emissor"
    ],
    "setor_executor": [
        "Executor",
        "Setor Executor"
    ],
    "solicitante": [
        "Solicitante"
    ],
    "servico_origem": [
        "Serv. Origem",
        "Serviço de Origem"
    ],
    "grau_prioridade_emissao": [
        "Prior. Emissão",
        "Prioridade Emissão",
        "Grau Prioridade Emissão"
    ],
    "grau_prioridade_planejamento": [
        "Prior. Planej.",
        "Prioridade Planejamento",
        "Grau Prioridade Planejamento"
    ],
    "execucao_simples": [
        "Exec. Simples",
        "Execução Simples"
    ],
    "responsavel_programacao": [
        "Resp. Prog.",
        "Responsável Programação"
    ],
    "semana_programada": [
        "Sem. Prog.",
        "Semana Programada"
    ],
    "responsavel_execucao": [
        "Resp. Exec.",
        "Responsável Execução"
    ],
    "descricao_execucao": [
        "Descrição da Execução",
        "Descricao da Execucao"
    ],
    "prazo_limite": [
        "Prazo Limite"
    ],
    "tempo_disponivel": [
        "Tempo Disp.",
        "Tempo Disponível"
    ],
    "data_limite": [
        "Data Limite"
    ],
    "tempo_excedido": [
        "Tempo Excedido"
    ],
    "desde": [
        "Desde"
    ],
    "tempo_total": [
        "Tempo Total"
    ],
    "desde_1": [
        "Desde (1)"
    ],
    "total_tempo_tpe_planejado": [
        "Tempo TPE Plan.",
        "Total Tempo TPE Planejado"
    ],
    "total_tempo_tex_planejado": [
        "Tempo TEX Plan.",
        "Total Tempo TEX Planejado"
    ],
    "total_tempo_tpo_planejado": [
        "Tempo TPO Plan.",
        "Total Tempo TPO Planejado"
    ],
    "total_horas_programadas": [
        "Horas Prog.",
        "Total Horas Programadas"
    ],
    "total_tempo_tpe_executada": [
        "Total Tempo TPE Executada"
    ],
    "semana_executada": [
        "Sem. Exec.",
        "Semana Executada"
    ],
    "num_reprogramacoes": [
        "Nº Reprog.",
        "Número de Reprogramações",
        "Reprogramações"
    ],
    "execucao_parcial": [
        "Exec. Parcial",
        "Execução Parcial"
    ],
    "anomalia": [
        "Anomalia"
    ],
    "sistema_origem": [
        "Sis. Origem",
        "Sistema de Origem"
    ],
    "numero_desvios": [
        "Número de Desvios",
        "Nº de Desvios",
        "Desvio"
    ],
    "justificativa": [
        "Justificativa",
        "Justificativa sem APR"
    ],
    "atividade_especial": [
        "Actividad Especial"
    ],
    "equipamento_retirado": [
        "Equipamento Retirado"
    ],
    "destino": [
        "Destino"
    ],
    "equipamento_instalado": [
        "Equipamento Instalado"
    ],
    "origem": [
        "Origem"
    ],
    "desativacao_da_localizacao": [
        "Desativação da localização"
    ],
    "instalacao_estimada": [
        "Instalação Estimada"
    ],
    "executado": [
        "Executado"
    ],
    "concluido": [
        "Concluído"
    ],
    "total_tempo_tpo_executada": [
        "Total Tempo TPO Executada"
    ],
    "data_inicio_programada": [
        "Data início Programada"
    ],
    "data_programacao": [
        "Data de programação"
    ],
    "data_inicio_reprogramada": [
        "Data início Reprogramada"
    ],
    "data_reprogramacao": [
        "Data de reprogramação"
    ],
    "situacao_reprogramacao": [
        "Situação de Reprogramação"
    ],
    "total_de_reprogramacoes": [
        "Total de Reprogramações"
    ],
    "situacao_de_desvio": [
        "Situação de Desvio"
    ],
    "relacao": [
        "Relação"
    ],
    "sn": [
        "SN"
    ],
    "ate_1": [
        "Até (1)"
    ],
    "ate_2": [
        "Até (2)"
    ],
    "desde_2": [
        "Desde (2)"
    ],
    "numero_ssa_relacionada_1": [
        "Número da SSA Relacionada"
    ],
    "numero_ssa_relacionada_2": [
        "Número da SSA Relacionada (2)"
    ],
    "setor_emissor_relacionado_1": [
        "Setor Emissor Relacionado"
    ],
    "setor_emissor_relacionado_2": [
        "Setor Emissor Relacionado (2)"
    ],
    "setor_executor_relacionado_1": [
        "Setor Executor Relacionado"
    ],
    "setor_executor_relacionado_2": [
        "Setor Executor Relacionado (2)"
    ],
    "situacao_relacionada_1": [
        "Situação Relacionada"
    ],
    "situacao_relacionada_2": [
        "Situação Relacionada (2)"
    ],
    "status_execucao_prazo": [
        "Situação do Prazo",
        "Status Prazo"
    ]
}

def _get_config_dir() -> str:
    """Allow tests/overrides via SSA_CONFIG_DIR; default to 'config'."""
    return os.environ.get('SSA_CONFIG_DIR') or CONFIG_DIR

def load_display_mappings_integrity() -> Dict[str, str]:
    """Load display_mappings.json; if missing/invalid, recreate with defaults and return it."""
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, 'display_mappings.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            return data
        else:
            logger.warning(f"display_mappings.json inválido em '{path}'. Será restaurado para o padrão.")
    except Exception:
        logger.warning(f"display_mappings.json ausente ou ilegível em '{path}'. Será restaurado para o padrão.")
    # Restore
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_DISPLAY_MAPPINGS, f, indent=2, ensure_ascii=False)
        logger.warning(f"display_mappings.json foi recriado em '{path}' com valores padrão.")
    except Exception as e:
        logger.error(f"Falha ao restaurar display_mappings.json: {e}")
    return DEFAULT_DISPLAY_MAPPINGS.copy()

def load_column_mappings_integrity() -> Dict[str, list]:
    """Load column_mappings.json; if missing/invalid, recreate with defaults and return it.

    Estrutura esperada: { canonical_name: [list_of_aliases, ...], ... }
    """
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, 'column_mappings.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            # Sanidade superficial: todas as chaves devem mapear para listas não vazias
            ok = all(isinstance(v, list) and len(v) > 0 for v in data.values())
            if ok:
                return data
            else:
                logger.warning(f"column_mappings.json inválido em '{path}'. Será restaurado para o padrão.")
        else:
            logger.warning(f"column_mappings.json inválido em '{path}'. Será restaurado para o padrão.")
    except Exception:
        logger.warning(f"column_mappings.json ausente ou ilegível em '{path}'. Será restaurado para o padrão.")
    # Restore
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_COLUMN_MAPPINGS, f, indent=2, ensure_ascii=False)
        logger.warning(f"column_mappings.json foi recriado em '{path}' com valores padrão.")
    except Exception as e:
        logger.error(f"Falha ao restaurar column_mappings.json: {e}")
    return DEFAULT_COLUMN_MAPPINGS.copy()

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
                # Cria um arquivo padrão mínimo quando o exemplo não existir
                try:
                    os.makedirs(CONFIG_DIR, exist_ok=True)
                    if target_file.endswith('default_settings.json'):
                        default_content = {
                            "display_settings": {
                                "column_visibility": {},
                                "column_widths": {
                                    "#": 4,
                                    "Nº SSA": 9,
                                    "Loc.": 10,
                                    "Emi.": 6,
                                    "Exe.": 6
                                },
                                "max_auto_scroll_pages": 3
                            },
                            "user_preferences": {
                                "auto_scroll_to_end": False,
                                "filter_mode_default": "contains"
                            },
                            "default_filters": []
                        }
                        with open(target_file, 'w', encoding='utf-8') as f:
                            json.dump(default_content, f, indent=2, ensure_ascii=False)
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    elif target_file.endswith('display_mappings.json'):
                        with open(target_file, 'w', encoding='utf-8') as f:
                            json.dump(DEFAULT_DISPLAY_MAPPINGS, f, indent=2, ensure_ascii=False)
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    elif target_file.endswith('column_mappings.json'):
                        with open(target_file, 'w', encoding='utf-8') as f:
                            json.dump(DEFAULT_COLUMN_MAPPINGS, f, indent=2, ensure_ascii=False)
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    else:
                        logger.warning(f"Arquivo de exemplo '{example_path}' não encontrado para '{target_file}'.")
                except Exception as e:
                    logger.error(f"Falha ao gerar arquivo padrão '{target_file}': {e}")

# --- Placeholder para handler de configuração via CLI ---
# Este handler pode ser expandido para um menu interativo ou edição direta.
def handle_config_command():
    """Handler para o comando '-c' ou 'config' na CLI.

    Implementa um menu simples para configurar:
      - user_preferences.filter_mode_default
      - default_filters (substituir lista inteira, opcional)
    """
    try:
        settings = load_settings()
    except Exception as e:
        print(f"Erro ao carregar configurações: {e}")
        return

    user_prefs = settings.get('user_preferences') or {}
    current_mode = user_prefs.get('filter_mode_default', 'contains')
    allowed = ['contains', 'prefix', 'suffix', 'exact', 'regex']

    print("\n--- Configurações ---")
    print("1) Modo de filtro padrão (aplicado a termos SEM marcador):")
    print("   - Valores permitidos:", ", ".join(allowed))
    print(f"   - Atual: {current_mode}")
    new_mode = input("   > Novo valor (Enter para manter): ").strip().lower()
    if new_mode:
        if new_mode not in allowed:
            print("Valor inválido. Nenhuma alteração aplicada ao modo padrão.")
        else:
            user_prefs['filter_mode_default'] = new_mode
            settings['user_preferences'] = user_prefs
            print(f"Modo padrão atualizado para: {new_mode}")

    print("\n2) Substituir filtros padrão (opcional):")
    print("   - Digite termos separados por vírgula para substituir a lista inteira;")
    print("   - Deixe em branco para manter a lista atual.")
    print(f"   - Atual: {settings.get('default_filters', [])}")
    new_filters_raw = input("   > Nova lista (ex.: adm, ^mel, !$2025) [Enter p/ manter]: ").strip()
    if new_filters_raw:
        new_filters = [t.strip() for t in new_filters_raw.split(',') if t.strip()]
        settings['default_filters'] = new_filters
        print(f"Filtros padrão atualizados: {new_filters}")

    try:
        save_settings(settings)
        print("Configurações salvas. Elas serão aplicadas imediatamente na CLI e no próximo filtro da GUI.")
    except Exception as e:
        print(f"Falha ao salvar configurações: {e}")
