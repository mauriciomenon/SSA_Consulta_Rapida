# interface/command_handlers.py 20250723 163500 (v1.0 - Funcoes de Tratamento de Comandos)
import json
import os

# Importacoes relativas necessarias para as funcoes
# Supondo que 'config' esta no root do projeto para os settings
# Isso sera ajustado via sys.path em cli.py/main.py se necessario
from core.config_manager import _resolve_config_path  # noqa: SLF001
from core.config_manager import (
    load_display_mappings_integrity,
    load_settings,
    save_settings,
)
from utils.robust_logging import get_robust_logger


def _get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


logger = get_robust_logger().get_logger(__name__, "cli")


class _MappingsCacheManager:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def get(self, file_name: str) -> dict | None:
        value = self._cache.get(file_name)
        if value is None:
            return None
        return value.copy()

    def set(self, file_name: str, value: dict) -> None:
        self._cache[file_name] = value.copy()

    def clear(self) -> None:
        self._cache.clear()


_MAPPINGS_CACHE_MANAGER = _MappingsCacheManager()


def _resolve_settings_path_for_message() -> str:
    return _resolve_config_path(os.path.join("config", "settings.json"))


def _resolve_mapping_path(file_name: str) -> str | None:
    if not isinstance(file_name, str):
        logger.warning("Nome de mapping invalido (tipo=%s).", type(file_name).__name__)
        return None
    normalized = file_name.strip()
    if not normalized:
        logger.warning("Nome de mapping vazio.")
        return None
    if normalized != os.path.basename(normalized):
        logger.warning("Mapping fora do escopo permitido: '%s'.", normalized)
        return None
    if not normalized.lower().endswith(".json"):
        logger.warning("Mapping com extensao invalida: '%s'.", normalized)
        return None
    return _resolve_config_path(os.path.join("config", normalized))


def _load_mappings_handler(file_name: str) -> dict:
    """Carrega mapeamentos de configuracao de arquivos JSON."""
    cached = _MAPPINGS_CACHE_MANAGER.get(file_name)
    if cached is not None:
        return cached
    if file_name == "display_mappings.json":
        try:
            data = load_display_mappings_integrity()
        except Exception as exc:
            logger.warning(
                "Falha ao carregar display mappings por integridade: %s", exc
            )
            return {}
        if isinstance(data, dict):
            _MAPPINGS_CACHE_MANAGER.set(file_name, data)
            return data.copy()
        return {}
    path = _resolve_mapping_path(file_name)
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Falha ao carregar mapping '%s': %s", path, exc)
        return {}
    if isinstance(data, dict):
        _MAPPINGS_CACHE_MANAGER.set(file_name, data)
        return data.copy()
    logger.warning("Mapping '%s' em formato invalido; usando fallback vazio.", path)
    return {}


def _save_settings_handler(settings: dict):
    """Salva as configuracoes atualizadas de volta ao settings.json."""
    settings_path = _resolve_settings_path_for_message()
    try:
        # Delegate to core.config_manager for atomic writes and consistent formatting.
        save_settings(settings)
        _MAPPINGS_CACHE_MANAGER.clear()
        print(f"Configuracoes salvas com sucesso em: {settings_path}")
    except (OSError, ValueError, TypeError, RuntimeError) as e:
        logger.exception("Falha ao salvar configuracoes da CLI")
        print(
            f"ERRO: Nao foi possivel salvar as configuracoes em: {settings_path}. "
            f"Erro: {e}"
        )
        raise


def _attempt_save_settings(settings: dict) -> bool:
    try:
        _save_settings_handler(settings)
        return True
    except (OSError, ValueError, TypeError, RuntimeError):
        # _save_settings_handler ja registra erro e feedback ao usuario.
        return False
    except Exception as exc:
        logger.exception("Falha inesperada ao salvar configuracoes da CLI: %s", exc)
        print("ERRO: Falha inesperada ao salvar configuracoes.")
        return False


def print_help():
    """Exibe a mensagem de ajuda para os comandos da CLI."""
    print("\n" + "=" * 50 + "\nAJUDA DE COMANDOS\n" + "=" * 50)
    print("O uso principal é digitar termos para filtrar os dados.\n")
    print("Comandos especiais:")
    print("  -d <N>            : Mostra os DETALHES completos da SSA na linha N.")
    print(
        "  -e <nome_arquivo> : EXPORTA os resultados atuais para um arquivo CSV, XLSX e JSON."
    )
    print(
        "  -rescan           : Força uma nova verificação e importação de todos os relatórios."
    )
    print(
        "  -v, voltar        : Desfaz o último filtro aplicado, voltando ao estado anterior."
    )
    print(
        "  -r, resetar       : Zera todos os filtros e recarrega a exibição com todos os dados do banco (ou com filtros padrão)."
    )
    print(
        "  -c, config        : Abre o menu de configurações interativo para personalizar a exibição e preferências."
    )
    print(
        "  -h, ajuda         : Exibe esta mensagem de ajuda com todos os comandos disponíveis."
    )
    print("  -q, sair          : Encerra o programa e sai da aplicação.")
    print("=" * 50)


def handle_config_command():
    """Gerencia o menu de configuracoes interativo."""
    while True:
        current_settings = load_settings()
        print("\n" + "=" * 50 + "\nMENU DE CONFIGURAÇÕES\n" + "=" * 50)
        print("1. Configuracoes de Exibicao")
        print("2. Preferencias do Usuario")
        print("0. Voltar ao menu principal")
        print("=" * 50)

        choice = input("Escolha uma opcao: ").strip()

        if choice == "1":
            _handle_display_settings(current_settings)
        elif choice == "2":
            _handle_user_preferences(current_settings)
        elif choice == "0":
            break
        else:
            print("Opcao invalida. Tente novamente.")


def _handle_display_settings(settings: dict):
    """Gerencia as configuracoes de exibicao."""
    while True:
        print("\n" + "=" * 50 + "\nCONFIGURAÇÕES DE EXIBIÇÃO\n" + "=" * 50)
        print("1. Visibilidade de Colunas")
        print("2. Largura de Colunas")
        print("0. Voltar")
        print("=" * 50)

        choice = input("Escolha uma opcao: ").strip()

        if choice == "1":
            _handle_column_visibility(settings)
        elif choice == "2":
            _handle_column_widths(settings)
        elif choice == "0":
            break
        else:
            print("Opcao invalida. Tente novamente.")


def _handle_column_visibility(settings: dict):
    """Permite ao usuario alternar a visibilidade das colunas."""
    display_settings = settings.get("display_settings", {})
    column_visibility = display_settings.get("column_visibility", {})
    display_map = _load_mappings_handler(
        "display_mappings.json"
    )  # Usar a propria funcao de load

    while True:
        print("\n" + "=" * 50 + "\nVISIBILIDADE DE COLUNAS\n" + "=" * 50)

        column_names = list(display_map.keys())
        for i, col_internal in enumerate(column_names):
            display_name = display_map.get(col_internal, col_internal)
            status = (
                "VISÍVEL" if column_visibility.get(col_internal, True) else "OCULTA"
            )
            print(f"{i + 1}. {display_name:<25} [{status}]")

        print("0. Voltar")
        print("=" * 50)

        col_choice = input(
            "Digite o numero da coluna para alternar (ou 0 para voltar): "
        ).strip()

        if col_choice == "0":
            break

        if col_choice.isdigit():
            idx = int(col_choice) - 1
            if 0 <= idx < len(column_names):
                selected_col = column_names[idx]
                current_state = column_visibility.get(selected_col, True)
                new_state = not current_state
                column_visibility[selected_col] = new_state
                if not _attempt_save_settings(settings):
                    column_visibility[selected_col] = current_state
                    print("Falha ao salvar. Alteracao de visibilidade foi desfeita.")
            else:
                print("Numero de coluna invalido.")
        else:
            print("Entrada invalida. Por favor, digite um numero.")


def _handle_column_widths(settings: dict):
    """Permite ao usuario editar a largura das colunas."""
    display_settings = settings.get("display_settings", {})
    column_widths = display_settings.get("column_widths", {})
    display_map = _load_mappings_handler(
        "display_mappings.json"
    )  # Usar a propria funcao de load

    while True:
        print("\n" + "=" * 50 + "\nLARGURA DE COLUNAS\n" + "=" * 50)

        display_names = [
            display_map.get(col_internal, col_internal)
            for col_internal in display_map.keys()
        ]

        for i, display_name in enumerate(display_names):
            current_width = column_widths.get(display_name, "Auto")
            print(f"{i + 1}. {display_name:<25} [Largura: {current_width}]")

        print("0. Voltar")
        print("=" * 50)

        col_choice = input(
            "Digite o numero da coluna para editar a largura (ou 0 para voltar): "
        ).strip()

        if col_choice == "0":
            break

        if col_choice.isdigit():
            idx = int(col_choice) - 1
            if 0 <= idx < len(display_names):
                selected_display_name = display_names[idx]
                new_width_input = input(
                    f"Digite a nova largura para '{selected_display_name}' (numero ou 'Auto' para automatico): "
                ).strip()
                had_existing_width = selected_display_name in column_widths
                previous_width = column_widths.get(selected_display_name)
                changed = False

                if new_width_input.lower() == "auto":
                    if selected_display_name in column_widths:
                        del column_widths[selected_display_name]
                        changed = True
                    if changed:
                        print(
                            f"Largura de '{selected_display_name}' definida como automatica."
                        )
                elif new_width_input.isdigit():
                    new_width = int(new_width_input)
                    if new_width > 0:
                        if (not had_existing_width) or previous_width != new_width:
                            column_widths[selected_display_name] = new_width
                            changed = True
                        if changed:
                            print(
                                f"Largura de '{selected_display_name}' definida como {new_width}."
                            )
                    else:
                        print("Largura deve ser um numero positivo.")
                else:
                    print("Entrada invalida. Por favor, digite um numero ou 'Auto'.")

                if changed and not _attempt_save_settings(settings):
                    if had_existing_width:
                        column_widths[selected_display_name] = previous_width
                    else:
                        column_widths.pop(selected_display_name, None)
                    print("Falha ao salvar. Alteracao de largura foi desfeita.")
            else:
                print("Numero de coluna invalido.")
        else:
            print("Entrada invalida. Por favor, digite um numero.")


def _handle_user_preferences(settings: dict):
    """Gerencia as preferencias do usuario, incluindo filtros padrao."""
    user_preferences = settings.get("user_preferences", {})
    default_filters = settings.get("default_filters", [])

    while True:
        print("\n" + "=" * 50 + "\nPREFERÊNCIAS DO USUÁRIO\n" + "=" * 50)
        auto_scroll_status = (
            "ATIVADO"
            if user_preferences.get("auto_scroll_to_end", False)
            else "DESATIVADO"
        )
        print(f"1. Rolagem Automatica ao Final (Paginacao): [{auto_scroll_status}]")
        print(
            f"2. Filtros Padrao: [{', '.join(default_filters) if default_filters else 'Nenhum'}]"
        )
        print("0. Voltar")
        print("=" * 50)

        choice = input("Escolha uma opcao: ").strip()

        if choice == "1":
            current_state = user_preferences.get("auto_scroll_to_end", False)
            new_state = not current_state
            user_preferences["auto_scroll_to_end"] = new_state
            if _attempt_save_settings(settings):
                print(
                    f"Rolagem automatica agora esta {'ATIVADA' if new_state else 'DESATIVADA'}."
                )
            else:
                user_preferences["auto_scroll_to_end"] = current_state
                print("Falha ao salvar. Alteracao de rolagem automatica foi desfeita.")
        elif choice == "2":
            _handle_default_filters(settings)
        elif choice == "0":
            break
        else:
            print("Opcao invalida. Tente novamente.")


def _handle_default_filters(settings: dict):
    """Permite ao usuario adicionar/remover filtros padrao."""
    default_filters = settings.get("default_filters", [])

    while True:
        print("\n" + "=" * 50 + "\nGERENCIAR FILTROS PADRÃO\n" + "=" * 50)
        print(
            f"Filtros Atuais: [{', '.join(default_filters) if default_filters else 'Nenhum'}]"
        )
        print("1. Adicionar filtro")
        print("2. Remover filtro")
        print("0. Voltar")
        print("=" * 50)

        choice = input("Escolha uma opcao: ").strip()

        if choice == "1":
            new_filter = input("Digite o novo termo de filtro para adicionar: ").strip()
            if new_filter and new_filter not in default_filters:
                default_filters.append(new_filter)
                if _attempt_save_settings(settings):
                    print(f"'{new_filter}' adicionado aos filtros padrao.")
                else:
                    default_filters.pop()
                    print("Falha ao salvar. Inclusao de filtro foi desfeita.")
            else:
                print("Termo invalido ou ja existente.")
        elif choice == "2":
            if not default_filters:
                print("Nao ha filtros padrao para remover.")
                continue

            for i, f in enumerate(default_filters):
                print(f"{i + 1}. {f}")

            try:
                filter_index = (
                    int(input("Digite o numero do filtro para remover: ").strip()) - 1
                )
                if 0 <= filter_index < len(default_filters):
                    removed_filter = default_filters.pop(filter_index)
                    if _attempt_save_settings(settings):
                        print(f"'{removed_filter}' removido dos filtros padrao.")
                    else:
                        default_filters.insert(filter_index, removed_filter)
                        print("Falha ao salvar. Remocao de filtro foi desfeita.")
                else:
                    print("Numero de filtro invalido.")
            except ValueError:
                print("Entrada invalida. Digite um numero.")
        elif choice == "0":
            break
        else:
            print("Opcao invalida. Tente novamente.")
