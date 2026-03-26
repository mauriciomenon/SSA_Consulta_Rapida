# interface/display.py 20250725 174500 (v10.12 - Tratamento de Erros Aprimorado)
import logging
from typing import Any, Dict

import pandas as pd

from utils.formatting import format_cell

logger = logging.getLogger(__name__)

# Importa a funcao de impressao de tabela do novo modulo
# (Assumindo que table_printer.py esteja em interface/table_printer.py)
# from interface.table_printer import pretty_print_df


def pretty_print_details(series: Any, display_map: Dict[str, str]):
    """
    Imprime os detalhes de uma unica linha (SSA) de forma legivel.

    Args:
        series (Any): Uma linha do DataFrame (pd.Series) ou um dicionário.
        display_map (Dict[str, str]): Mapeamento de nomes internos para nomes de exibição.
    """
    # --- Tratamento de Erros ---
    if not isinstance(display_map, dict):
        # Print first (tests capture stdout) then log.
        print("Erro: Configuração de exibição inválida.")
        logger.error(
            "Erro em pretty_print_details: display_map deve ser um dicionário."
        )
        return

    # Tenta converter para Series se for um dicionário
    if isinstance(series, dict):
        try:
            series = pd.Series(series)
        except Exception as e:
            logger.error(f"Erro ao converter dict para Series: {e}")
            print("Erro: Dados da SSA inválidos.")
            return
    elif not isinstance(series, pd.Series):
        print("Erro: Formato de dados da SSA inválido.")
        logger.error(
            f"Erro em pretty_print_details: 'series' deve ser pd.Series ou dict, recebido {type(series)}."
        )
        return

    # --- Impressão ---
    try:
        print("\n" + "=" * 50)
        ssa_number = series.get("numero_ssa", "N/A")
        print(f" DETALHES DA SSA: {ssa_number}")
        print("=" * 50)

        # Itera sobre os itens da Series
        for k, value in series.items():
            key: str = str(k)
            header = display_map.get(key, key)
            # Usa format_cell para padronizar datas, numeros, SSA e ocultar nulls
            formatted = format_cell(value, key)
            display_value = (
                formatted if (formatted is not None and formatted != "") else "-"
            )
            print(f"{header + ':':<25} {display_value}")

        print("=" * 50)
    except Exception as e:
        logger.error(f"Erro inesperado em pretty_print_details: {e}")
        print("Erro: Falha ao exibir os detalhes da SSA.")
