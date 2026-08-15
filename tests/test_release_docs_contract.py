from __future__ import annotations

import re

from tests.release_script_assertions import PROJECT_ROOT, read_repo_text


GUIA_DISTRIBUICAO = PROJECT_ROOT / "docs" / "GUIA_DISTRIBUICAO.md"
SOLUCOES_AMBIENTE = PROJECT_ROOT / "docs" / "SOLUCOES_AMBIENTE_BUILD.md"


def test_distribuicao_doc_does_not_hardcode_personal_wsl_path() -> None:
    text = read_repo_text("docs", "GUIA_DISTRIBUICAO.md")

    assert re.search(r"/mnt/c/Users/[^/<$]+/", text) is None
    assert re.search(r"C:\\Users\\(?!<usuario>)", text) is None
    assert "<WSL-repo-path>" in text


def test_solucoes_ambiente_doc_marks_legacy_body_historical() -> None:
    text = read_repo_text("docs", "SOLUCOES_AMBIENTE_BUILD.md")

    assert text.count("## CURRENT TRUTH") == 1
    assert "Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`" in text
    assert "PR #58 e PR #59: merged" in text
    assert "PR atual: #57" not in text
    assert "- Branch alvo: `dev`." not in text
    assert "## HISTORICAL SNAPSHOT 2025-11-14" in text
    assert "**Data**: 2025-11-14" not in text


def test_solucoes_ambiente_doc_uses_generic_user_paths() -> None:
    text = read_repo_text("docs", "SOLUCOES_AMBIENTE_BUILD.md")

    assert re.search(r"C:\\Users\\(?!<usuario>)", text) is None
    assert "C:\\Users\\<usuario>" in text


def test_release_docs_sync_contract() -> None:
    source_text = read_repo_text("docs", "GUIA_DISTRIBUICAO.md")
    source_truth = source_text.split("## HISTORICAL SNAPSHOT", 1)[0]

    assert "PR #58 e PR #59: merged" in source_truth
    assert "PR #57: aberto em draft" not in source_truth
    assert "PR #56: merged" not in source_truth
    assert "df0345caea9ac3050c87d2172eb75817b8fc3689" not in source_truth
    assert "4705c2e5722c4f3a5266ac02a5d15a1928d5a223" in source_truth  # pragma: allowlist secret

    for doc_name in [
        "SOLUCOES_AMBIENTE_BUILD.md",
        "BUILD_3X3_RUNBOOK.md",
        "BUILD_TOOLING_LESSONS_LEARNED.md",
    ]:
        current_truth = read_repo_text("docs", doc_name).split("## HISTORICAL SNAPSHOT", 1)[0]
        assert "Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`" in current_truth
        assert "PR #58 e PR #59: merged" in current_truth
        assert "PR atual: #57" not in current_truth
        assert "df0345caea9ac3050c87d2172eb75817b8fc3689" not in current_truth
