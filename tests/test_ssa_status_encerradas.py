"""RD-01a: uma definicao de encerrada (DEC-01/DEC-02) para todos os consumidores."""

import sqlite3
from contextlib import closing

import pandas as pd

from gui.ssa.filter_domain_rules import (
    EXCLUDED_TERMINAL_STATUSES,
    MACRO_BAIXAR_STATUS_EXCLUSIONS,
    exclude_terminal_status_rows,
)
from gui.workers.data_loader_processing import (
    DEFAULT_UI_SORT_SPEC,
    build_initial_sorted_dataframe,
)
from gui.workers.data_loader_query import build_default_ui_order_clause
from shared.ssa_status import (
    SSA_ENCERRADAS,
    SSA_STATUS_CODES,
    SSA_STATUS_DESCRIPTIONS,
    format_status_display,
    is_encerrada,
    status_code_series,
)

SITUACOES = ["STE", "ses", "SCA - Servico Cancelado", " SCC ", "SAD", "APV", None, "SEE"]


def test_encerradas_are_ste_ses_sca_scc_only() -> None:
    assert SSA_ENCERRADAS == {"STE", "SES", "SCA", "SCC"}
    assert EXCLUDED_TERMINAL_STATUSES == SSA_ENCERRADAS
    assert set(MACRO_BAIXAR_STATUS_EXCLUSIONS) == SSA_ENCERRADAS
    assert [is_encerrada(v) for v in SITUACOES] == [
        True, True, True, True, False, False, False, False,
    ]


def test_catalog_follows_manual_g05() -> None:
    assert "AIP" not in SSA_STATUS_CODES and "ASI" not in SSA_STATUS_CODES
    assert SSA_STATUS_DESCRIPTIONS["ALE"] == "Aguardando Liberacao do Equipamento"
    assert SSA_STATUS_DESCRIPTIONS["ASL"] == "Aguardando Servicos de Laboratorio"
    assert format_status_display("SCC") == "SCC - Cancelada no Cadastramento"


def test_hide_closed_uses_status_code() -> None:
    df = pd.DataFrame({"numero_ssa": range(len(SITUACOES)), "situacao": SITUACOES})
    kept = exclude_terminal_status_rows(df)
    # SAD, APV, vazio e SEE ficam; as 4 encerradas (com e sem descricao) saem.
    assert kept["numero_ssa"].tolist() == [4, 5, 6, 7]


def test_validation_missing_date_exception_uses_status_code() -> None:
    """RD-04: 'SCC - CANCELADA' sem data_cadastro segue a excecao de SCC."""
    from armazenamento.database_validation import validate_dataframe_before_insert

    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "situacao": ["SCC - CANCELADA", "APV"],
            "data_cadastro": ["", ""],
        }
    )
    report = validate_dataframe_before_insert(df)

    # So a APV (indice 1) fica sem data invalida; a SCC tem a excecao de negocio.
    assert list(report["invalid_by_column"]["data_cadastro"]) == [1]


def test_default_order_sql_matches_pandas(tmp_path) -> None:
    numeros = [str(202600000 + i) for i in range(len(SITUACOES))]
    df = pd.DataFrame({"numero_ssa": numeros, "situacao": SITUACOES})
    db = tmp_path / "ordem.db"
    with closing(sqlite3.connect(db)) as conn:
        df.to_sql("ssa_table", conn, index=False)
        clause = build_default_ui_order_clause(DEFAULT_UI_SORT_SPEC)
        sql_order = [
            row[0]
            for row in conn.execute(f"SELECT numero_ssa FROM ssa_table ORDER BY {clause}")
        ]
    pandas_order = build_initial_sorted_dataframe(df)["numero_ssa"].tolist()

    assert sql_order == pandas_order
    closed_flags = status_code_series(
        df.set_index("numero_ssa").loc[sql_order, "situacao"]
    ).isin(SSA_ENCERRADAS).tolist()
    # Abertas primeiro (numero desc), encerradas no fim.
    assert closed_flags == [False] * 4 + [True] * 4
