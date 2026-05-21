# core/config_manager.py 20250725 163000 (v2.1 - Melhorias de Erro, Logging)
"""
Gerenciador de configuracoes da aplicacao.

Responsavel por carregar, salvar e garantir a existencia do arquivo settings.json.
"""

import json
import os
import shutil
import tempfile
from typing import Any, Dict

from utils.path_safety import PathSafetyError, ensure_path_is_allowed
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "core")


def _atomic_write_json_file(
    path: str, data: Any, *, indent: int, ensure_ascii: bool
) -> None:
    """Write JSON atomically to prevent truncated/corrupted config files on crash."""
    target_dir = os.path.dirname(path) or "."
    base_name = os.path.basename(path) or "config.json"
    os.makedirs(target_dir, exist_ok=True)
    try:
        target_mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        target_mode = 0o600

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=f".{base_name}.tmp.", dir=target_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None  # ownership transferred to file object
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError as exc:
                logger.debug(
                    "fsync failed for config temp file (%s): %s", tmp_path, exc
                )
        os.chmod(tmp_path, target_mode)
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                logger.warning(
                    "Falha ao fechar file descriptor temporario de config '%s': %s",
                    path,
                    exc,
                )
        if tmp_path:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario de config '%s': %s",
                    tmp_path,
                    exc,
                )


def atomic_write_json_file(
    path: str,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Public helper to write JSON atomically."""
    _atomic_write_json_file(path, data, indent=indent, ensure_ascii=ensure_ascii)


def _atomic_copy_file(src: str, dst: str) -> None:
    """Copy a file atomically to avoid partial writes when creating defaults."""
    target_dir = os.path.dirname(dst) or "."
    base_name = os.path.basename(dst) or "file"
    os.makedirs(target_dir, exist_ok=True)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{base_name}.tmp.", dir=target_dir, delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
        shutil.copyfile(src, tmp_path)
        shutil.copymode(src, tmp_path)
        try:
            with open(tmp_path, "rb") as f:
                os.fsync(f.fileno())
        except OSError as exc:
            logger.debug("fsync failed for config temp file (%s): %s", tmp_path, exc)
        os.replace(tmp_path, dst)
        tmp_path = None
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario de copia '%s': %s",
                    tmp_path,
                    exc,
                )


# Caminhos padrao
CONFIG_DIR = "config"
DEFAULT_SETTINGS_FILE = os.path.join(CONFIG_DIR, "default_settings.json")
USER_SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
DISPLAY_MAPPINGS_FILE = os.path.join(CONFIG_DIR, "display_mappings.json")
COLUMN_MAPPINGS_FILE = os.path.join(CONFIG_DIR, "column_mappings.json")

# Default mapping used if display_mappings.json is missing/invalid
DEFAULT_DISPLAY_MAPPINGS: Dict[str, str] = {
    "id": "id",
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
    "total_tempo_tpe_executada": "Tempo Total TPE Executada",
    "total_tempo_tex_planejado": "Tempo TEX Plan.",
    "total_tempo_tpo_planejado": "Tempo TPO Plan.",
    "total_horas_programadas": "Horas Prog.",
    "semana_executada": "Sem. Exec.",
    "num_reprogramacoes": "Nº Reprog.",
    "execucao_parcial": "Exec. Parcial",
    "situacao_da_parcial": "Situacao da Parcial",
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
    "total_tempo_tex_executada": "Tempo Total TEX Executada",
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
    "relacao": "Relação",
}

# Column affinity score (higher means closer to left in "show all by affinity").
# Keep this as a plain map so UI flows can reuse it without layout coupling.
COLUMN_AFFINITY_SCORES: Dict[str, int] = {
    # Core identifiers
    "numero_ssa": 1000,
    "situacao": 980,
    "derivada_de": 960,
    "localizacao_codigo": 940,
    "descricao_localizacao": 930,
    "equipamento": 920,
    "descricao_ssa": 900,
    # Emissao
    "data_cadastro": 860,
    "semana_cadastro": 850,
    "solicitante": 840,
    "setor_emissor": 830,
    "grau_prioridade_emissao": 820,
    # Planejamento
    "grau_prioridade_planejamento": 780,
    "semana_programada": 770,
    "responsavel_programacao": 760,
    # Programacao
    "data_inicio_programada": 730,
    "data_programacao": 720,
    # Reprogramacao
    "num_reprogramacoes": 680,
    "total_de_reprogramacoes": 670,
    "data_inicio_reprogramada": 660,
    "data_reprogramacao": 650,
    "situacao_reprogramacao": 640,
    # Execucao
    "descricao_execucao": 600,
    "responsavel_execucao": 590,
    "semana_executada": 580,
    "execucao_simples": 570,
    "execucao_parcial": 560,
    "concluido": 550,
    "executado": 540,
}

# Default mapping used if column_mappings.json is missing/invalid
DEFAULT_COLUMN_MAPPINGS: Dict[str, list] = {
    "numero_ssa": ["Nº SSA", "Nº SSA*", "Nº SSA Original", "Numero SSA", "Nº da SSA"],
    "situacao": ["Situação", "Situacao", "Status"],
    "derivada_de": ["Derivada de", "Derivada De"],
    "localizacao_codigo": [
        "Loc.",
        "Localização",
        "Cod. Localização",
        "Codigo Localizacao",
    ],
    "descricao_localizacao": [
        "Desc. Loc.",
        "Descrição da Localização",
        "Descricao Localizacao",
    ],
    "equipamento": ["Equip.", "Equipamento"],
    "semana_cadastro": ["Sem.\nCadastro", "Sem. Cadastro", "Semana Cadastro"],
    "data_cadastro": [
        "Emitida Em",
        "Data de Emissão",
        "Data Cadastro",
        "Data/Hora de Cadastro",
    ],
    "descricao_ssa": ["Descrição da SSA", "Descricao da SSA", "Descricao"],
    "setor_emissor": ["Emissor", "Setor Emissor"],
    "setor_executor": ["Executor", "Setor Executor"],
    "solicitante": ["Solicitante"],
    "servico_origem": ["Serv. Origem", "Serviço de Origem"],
    "grau_prioridade_emissao": [
        "Prior. Emissão",
        "Prioridade Emissão",
        "Grau Prioridade Emissão",
    ],
    "grau_prioridade_planejamento": [
        "Prior. Planej.",
        "Prioridade Planejamento",
        "Grau Prioridade Planejamento",
    ],
    "execucao_simples": ["Exec. Simples", "Execução Simples"],
    "responsavel_programacao": ["Resp. Prog.", "Responsável Programação"],
    "semana_programada": ["Sem. Prog.", "Semana Programada"],
    "responsavel_execucao": ["Resp. Exec.", "Responsável Execução"],
    "descricao_execucao": ["Descrição da Execução", "Descricao da Execucao"],
    "prazo_limite": ["Prazo Limite"],
    "tempo_disponivel": ["Tempo Disp.", "Tempo Disponível"],
    "data_limite": ["Data Limite"],
    "tempo_excedido": ["Tempo Excedido"],
    "desde": ["Desde"],
    "tempo_total": ["Tempo Total"],
    "desde_1": ["Desde (1)"],
    "total_tempo_tpe_planejado": ["Tempo TPE Plan.", "Total Tempo TPE Planejado"],
    "total_tempo_tex_planejado": ["Tempo TEX Plan.", "Total Tempo TEX Planejado"],
    "total_tempo_tpo_planejado": ["Tempo TPO Plan.", "Total Tempo TPO Planejado"],
    "total_horas_programadas": ["Horas Prog.", "Total Horas Programadas"],
    "total_tempo_tpe_executada": ["Total Tempo TPE Executada"],
    "semana_executada": ["Sem. Exec.", "Semana Executada"],
    "num_reprogramacoes": ["Nº Reprog.", "Número de Reprogramações", "Reprogramações"],
    "execucao_parcial": ["Exec. Parcial", "Execução Parcial"],
    "anomalia": ["Anomalia"],
    "sistema_origem": ["Sis. Origem", "Sistema de Origem"],
    "numero_desvios": ["Número de Desvios", "Nº de Desvios", "Desvio"],
    "justificativa": ["Justificativa", "Justificativa sem APR"],
    "atividade_especial": ["Atividade Especial", "Actividad Especial"],
    "equipamento_retirado": ["Equipamento Retirado"],
    "destino": ["Destino"],
    "equipamento_instalado": ["Equipamento Instalado"],
    "origem": ["Origem"],
    "desativacao_da_localizacao": ["Desativação da localização"],
    "instalacao_estimada": ["Instalação Estimada"],
    "executado": ["Executado"],
    "concluido": ["Concluído"],
    "total_tempo_tpo_executada": ["Total Tempo TPO Executada"],
    "data_inicio_programada": ["Data início Programada"],
    "data_programacao": ["Data de programação"],
    "data_inicio_reprogramada": ["Data início Reprogramada"],
    "data_reprogramacao": ["Data de reprogramação"],
    "situacao_reprogramacao": ["Situação de Reprogramação"],
    "total_de_reprogramacoes": ["Total de Reprogramações"],
    "situacao_de_desvio": ["Situação de Desvio"],
    "relacao": ["Relação"],
    "sn": ["SN"],
    "ate_1": ["Até (1)"],
    "ate_2": ["Até (2)"],
    "desde_2": ["Desde (2)"],
    "numero_ssa_relacionada_1": ["Número da SSA Relacionada"],
    "numero_ssa_relacionada_2": ["Número da SSA Relacionada (2)"],
    "setor_emissor_relacionado_1": ["Setor Emissor Relacionado"],
    "setor_emissor_relacionado_2": ["Setor Emissor Relacionado (2)"],
    "setor_executor_relacionado_1": ["Setor Executor Relacionado"],
    "setor_executor_relacionado_2": ["Setor Executor Relacionado (2)"],
    "situacao_relacionada_1": ["Situação Relacionada"],
    "situacao_relacionada_2": ["Situação Relacionada (2)"],
    "status_execucao_prazo": ["Situação do Prazo", "Status Prazo"],
}


def _get_config_dir() -> str:
    """Allow tests/overrides via SSA_CONFIG_DIR; default to 'config'."""
    raw_cfg_dir = os.environ.get("SSA_CONFIG_DIR")
    if not raw_cfg_dir:
        return CONFIG_DIR
    try:
        return str(
            ensure_path_is_allowed(
                raw_cfg_dir,
                purpose="SSA_CONFIG_DIR",
                expect_directory=True,
            )
        )
    except PathSafetyError as exc:
        logger.warning("SSA_CONFIG_DIR invalido (%s). Usando '%s'.", exc, CONFIG_DIR)
        return CONFIG_DIR


def _resolve_config_path(default_path: str) -> str:
    """Resolve a config path honoring SSA_CONFIG_DIR while keeping default constants."""
    cfg_dir = _get_config_dir()
    if cfg_dir == CONFIG_DIR:
        return default_path
    return os.path.join(cfg_dir, os.path.basename(default_path))


def load_display_mappings_integrity() -> Dict[str, str]:
    """Load display_mappings.json; if missing/invalid, recreate with defaults and return it."""
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, "display_mappings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            return data
        else:
            logger.warning(
                f"display_mappings.json invalido em '{path}'. Sera restaurado para o padrao."
            )
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            f"display_mappings.json ausente ou ilegivel em '{path}'. Sera restaurado para o padrao."
        )
    # Restore
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        _atomic_write_json_file(
            path, DEFAULT_DISPLAY_MAPPINGS, indent=2, ensure_ascii=False
        )
        logger.warning(
            f"display_mappings.json foi recriado em '{path}' com valores padrao."
        )
    except Exception as e:
        logger.error(f"Falha ao restaurar display_mappings.json: {e}")
        logger.error("Usando defaults em memoria; arquivo nao foi atualizado.")
        return DEFAULT_DISPLAY_MAPPINGS.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            restored_data = json.load(f)
        if isinstance(restored_data, dict) and restored_data:
            return restored_data
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Falha ao reler display_mappings restaurado em '{path}': {e}")
    return DEFAULT_DISPLAY_MAPPINGS.copy()


def load_column_mappings_integrity() -> Dict[str, list]:
    """Load column_mappings.json; if missing/invalid, recreate with defaults and return it.

    Estrutura esperada: { canonical_name: [list_of_aliases, ...], ... }
    """
    cfg_dir = _get_config_dir()
    path = os.path.join(cfg_dir, "column_mappings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            # Sanidade superficial: todas as chaves devem mapear para listas não vazias
            ok = all(isinstance(v, list) and len(v) > 0 for v in data.values())
            if ok:
                return data
            else:
                logger.warning(
                    f"column_mappings.json inválido em '{path}'. Será restaurado para o padrão."
                )
        else:
            logger.warning(
                f"column_mappings.json inválido em '{path}'. Será restaurado para o padrão."
            )
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            f"column_mappings.json ausente ou ilegível em '{path}'. Será restaurado para o padrão."
        )
    # Restore
    try:
        os.makedirs(cfg_dir, exist_ok=True)
        _atomic_write_json_file(
            path, DEFAULT_COLUMN_MAPPINGS, indent=2, ensure_ascii=False
        )
        logger.warning(
            f"column_mappings.json foi recriado em '{path}' com valores padrão."
        )
    except Exception as e:
        logger.error(f"Falha ao restaurar column_mappings.json: {e}")
        logger.error("Usando defaults em memoria; arquivo nao foi atualizado.")
        return DEFAULT_COLUMN_MAPPINGS.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            restored_data = json.load(f)
        if isinstance(restored_data, dict) and restored_data:
            ok = all(isinstance(v, list) and len(v) > 0 for v in restored_data.values())
            if ok:
                return restored_data
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Falha ao reler column_mappings restaurado em '{path}': {e}")
    return DEFAULT_COLUMN_MAPPINGS.copy()


def load_settings() -> Dict[str, Any]:
    """
    Carrega as configurações do usuário. Se não existir, carrega as padrões.

    Returns:
        Dict[str, Any]: Um dicionário com as configurações.
    """
    user_settings_file = _resolve_config_path(USER_SETTINGS_FILE)
    default_settings_file = _resolve_config_path(DEFAULT_SETTINGS_FILE)
    settings_path = user_settings_file
    if not os.path.exists(settings_path):
        logger.info(
            f"Arquivo de configuração do usuário '{settings_path}' não encontrado. Carregando padrões."
        )
        if not os.path.exists(default_settings_file):
            message = (
                "Arquivos de configuracao ausentes: "
                f"user='{user_settings_file}', default='{default_settings_file}'. "
                "Execute ensure_default_settings antes de carregar configuracoes."
            )
            logger.critical(message)
            raise FileNotFoundError(message)
        settings_path = default_settings_file

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
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
    user_settings_file = _resolve_config_path(USER_SETTINGS_FILE)
    try:
        os.makedirs(os.path.dirname(user_settings_file), exist_ok=True)
        _atomic_write_json_file(
            user_settings_file, settings, indent=4, ensure_ascii=False
        )
        logger.info(f"Configuracoes salvas em '{user_settings_file}'.")
    except IOError as e:
        logger.error(f"Erro ao salvar configuracoes em '{user_settings_file}': {e}")
        raise


def ensure_default_settings(*, fail_fast: bool = True) -> list[str]:
    """
    Garante que os arquivos de configuração padrão existam.
    Se não existirem, os copia dos arquivos de exemplo ou os cria.

    Args:
        fail_fast (bool): Se True, levanta RuntimeError quando houver falhas.

    Returns:
        list[str]: Lista de erros de provisionamento. Lista vazia indica sucesso.

    Raises:
        RuntimeError: Quando `fail_fast=True` e existir falha de provisionamento.
    """
    errors: list[str] = []
    required_files = {
        _resolve_config_path(DEFAULT_SETTINGS_FILE): "default_settings.json.example",
        _resolve_config_path(DISPLAY_MAPPINGS_FILE): "display_mappings.json.example",
        _resolve_config_path(COLUMN_MAPPINGS_FILE): "column_mappings.json.example",
        # Adicione outros arquivos de configuração aqui se necessário
    }

    for target_file, example_file in required_files.items():
        if not os.path.exists(target_file):
            cfg_dir = _get_config_dir()
            example_path = os.path.join(cfg_dir, example_file)
            if not os.path.exists(example_path):
                example_path = os.path.join(CONFIG_DIR, example_file)
            if os.path.exists(example_path):
                try:
                    _atomic_copy_file(example_path, target_file)
                    logger.info(f"Arquivo de configuração padrão criado: {target_file}")
                except IOError as e:
                    logger.error(
                        f"Falha ao copiar '{example_path}' para '{target_file}': {e}"
                    )
                    errors.append(f"copy_failed:{target_file}")
            else:
                # Cria um arquivo padrão mínimo quando o exemplo não existir
                try:
                    os.makedirs(os.path.dirname(target_file) or cfg_dir, exist_ok=True)
                    if target_file.endswith("default_settings.json"):
                        default_content = {
                            "version": "1.0.0",
                            "description": "Default settings for SSA Consulta Rapida",
                            "display_settings": {
                                "column_visibility": {},
                                "column_widths": {
                                    "#": 4,
                                    "Nº SSA": 9,
                                    "Loc.": 10,
                                    "Emi.": 6,
                                    "Exe.": 6,
                                },
                                "max_auto_scroll_pages": 3,
                            },
                            "user_preferences": {
                                "auto_scroll_to_end": False,
                                "filter_mode_default": "contains",
                            },
                            "default_filters": [],
                            "import_settings": {
                                "include_processadas_in_full_rescan": True,
                                "processadas_subdir": "processadas",
                                "ignore_nosurvivor_in_full_rescan": True,
                                "nosurvivor_subdir": "nosurvivor",
                                "move_processed_after_import": False,
                                "route_zero_survivor_to_nosurvivor": True,
                                "upsert_short_circuit_policy": "consulta_only",
                            },
                        }
                        _atomic_write_json_file(
                            target_file, default_content, indent=2, ensure_ascii=False
                        )
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    elif target_file.endswith("display_mappings.json"):
                        _atomic_write_json_file(
                            target_file,
                            DEFAULT_DISPLAY_MAPPINGS,
                            indent=2,
                            ensure_ascii=False,
                        )
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    elif target_file.endswith("column_mappings.json"):
                        _atomic_write_json_file(
                            target_file,
                            DEFAULT_COLUMN_MAPPINGS,
                            indent=2,
                            ensure_ascii=False,
                        )
                        logger.info(f"Arquivo padrão gerado: {target_file}")
                    else:
                        logger.warning(
                            f"Arquivo de exemplo '{example_path}' não encontrado para '{target_file}'."
                        )
                except Exception as e:
                    logger.error(f"Falha ao gerar arquivo padrão '{target_file}': {e}")
                    errors.append(f"generate_failed:{target_file}")
    if errors:
        logger.critical(
            "ensure_default_settings completed with errors: %s", "; ".join(errors)
        )
        if fail_fast:
            raise RuntimeError("ensure_default_settings failed: " + "; ".join(errors))
    return errors


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

    user_prefs = settings.get("user_preferences") or {}
    current_mode = user_prefs.get("filter_mode_default", "contains")
    allowed = ["contains", "prefix", "suffix", "exact", "regex"]

    print("\n--- Configurações ---")
    print("1) Modo de filtro padrão (aplicado a termos SEM marcador):")
    print("   - Valores permitidos:", ", ".join(allowed))
    print(f"   - Atual: {current_mode}")
    new_mode = input("   > Novo valor (Enter para manter): ").strip().lower()
    changed_filter_mode = False
    changed_default_filters = False
    if new_mode:
        if new_mode not in allowed:
            print("Valor invalido. Nenhuma alteracao aplicada ao modo padrao.")
        else:
            user_prefs["filter_mode_default"] = new_mode
            settings["user_preferences"] = user_prefs
            changed_filter_mode = True
            print(f"Modo padrao atualizado para: {new_mode}")

    print("\n2) Substituir filtros padrao (opcional):")
    print("   - Digite termos separados por virgula para substituir a lista inteira;")
    print("   - Deixe em branco para manter a lista atual.")
    print(f"   - Atual: {settings.get('default_filters', [])}")
    new_filters_raw = input(
        "   > Nova lista (ex.: adm, ^mel, !$2025) [Enter p/ manter]: "
    ).strip()
    if new_filters_raw:
        new_filters = [t.strip() for t in new_filters_raw.split(",") if t.strip()]
        settings["default_filters"] = new_filters
        changed_default_filters = True
        print(f"Filtros padrao atualizados: {new_filters}")

    try:
        if not changed_filter_mode and not changed_default_filters:
            print("Nenhuma alteracao de configuracao para salvar.")
            return
        latest_settings = load_settings()
        if changed_filter_mode:
            latest_user_prefs = latest_settings.get("user_preferences") or {}
            latest_user_prefs["filter_mode_default"] = user_prefs[
                "filter_mode_default"
            ]
            latest_settings["user_preferences"] = latest_user_prefs
        if changed_default_filters:
            latest_settings["default_filters"] = settings["default_filters"]
        settings = latest_settings
        save_settings(settings)
        print(
            "Configuracoes salvas. Reinicie fluxos ja abertos para garantir que usem os novos valores."
        )
    except Exception as e:
        print(f"Falha ao salvar configuracoes: {e}")
