"""Contrato da ajuda de busca (RD-02): os exemplos precisam fazer o que a ajuda promete.

`!termo` exclui linhas que CONTEM o termo em qualquer coluna; para excluir a situacao STE o
exemplo correto e `!=ste`. `OU`/`OR` e espacos sao literais (nao sao operadores).
"""

import pandas as pd

from core.search_filter import filter_dataframe
from interface.cli import _build_cli_plain_help_text

FRAME = pd.DataFrame(
    {
        "numero_ssa": ["202600001", "202600002", "202600003"],
        "situacao": ["STE", "SPG", "APV"],
        "descricao_ssa": ["troca de rele", "ajuste do painel", "svp mel4"],
    }
)


def _ssas(terms: list[str]) -> list[str]:
    return filter_dataframe(FRAME, terms)["numero_ssa"].tolist()


def test_negative_exact_excludes_only_status_ste() -> None:
    assert _ssas(["!=ste"]) == ["202600002", "202600003"]


def test_negative_contains_also_drops_rows_with_ste_inside_words() -> None:
    assert _ssas(["!ste"]) == ["202600003"]  # "ajuste" contem "ste"


def test_or_keyword_and_spaces_are_literal() -> None:
    assert _ssas(["svp OU ajuste"]) == []
    assert _ssas(["mel4 svp"]) == []
    assert _ssas(["svp mel4"]) == ["202600003"]


def test_help_examples_use_exact_negative_for_status() -> None:
    for detailed in (False, True):
        text = _build_cli_plain_help_text(detailed=detailed)
        assert "!=ste" in text
        assert "svp, !ste," not in text
