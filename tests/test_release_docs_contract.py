from __future__ import annotations

import re

from tests.release_script_assertions import PROJECT_ROOT, read_repo_text


GUIA_DISTRIBUICAO = PROJECT_ROOT / "docs" / "GUIA_DISTRIBUICAO.md"
SOLUCOES_AMBIENTE = PROJECT_ROOT / "docs" / "SOLUCOES_AMBIENTE_BUILD.md"
# REPO-15: a ultima release publicada (fato: tag e assets no GitHub), nao a versao em VERSION.
PUBLISHED_TAG = "v4.51"
PUBLISHED_LINE = f"Ultima release publicada: `{PUBLISHED_TAG}` (tag -> `e2481cf4`"


def test_distribuicao_doc_enforces_native_host_isolation() -> None:
    text = read_repo_text("docs", "GUIA_DISTRIBUICAO.md")
    current_truth = text.split("## HISTORICAL SNAPSHOT", 1)[0]

    assert re.search(r"/mnt/c/Users/[^/<$]+/", text) is None
    assert re.search(r"C:\\Users\\(?!<usuario>)", text) is None
    assert "/mnt/" not in current_truth
    assert "-Target all" not in current_truth
    assert "clone Linux proprio" in current_truth
    assert "Validacao Linux exige clone Linux proprio" in current_truth


def test_solucoes_ambiente_doc_marks_legacy_body_historical() -> None:
    text = read_repo_text("docs", "SOLUCOES_AMBIENTE_BUILD.md")

    assert text.count("## CURRENT TRUTH") == 1
    assert "Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`" in text
    assert PUBLISHED_LINE in text
    assert "candidata local em validacao" not in text
    assert "Build e testes exigem ferramentas nativas e clone do proprio host" in text
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

    assert PUBLISHED_LINE in source_truth
    assert "candidata local em validacao" not in source_truth
    assert "Validacao Linux exige clone Linux proprio" in source_truth
    assert "PR #57: aberto em draft" not in source_truth
    assert "PR #56: merged" not in source_truth
    assert "df0345caea9ac3050c87d2172eb75817b8fc3689" not in source_truth
    # BL-38 achado 5: 4705c2e5 nao e alcancavel pela historia atual; saiu do bloco vigente.
    assert "4705c2e5" not in source_truth
    notes = read_repo_text(f"RELEASE_NOTES_{PUBLISHED_TAG}.md")
    assert notes.startswith(f"# Release {PUBLISHED_TAG}\n")
    assert f"A tag `{PUBLISHED_TAG}` aponta para `e2481cf4`" in notes

    for doc_name, release_line in [
        ("SOLUCOES_AMBIENTE_BUILD.md", PUBLISHED_LINE),
        ("BUILD_3X3_RUNBOOK.md", PUBLISHED_LINE),
        ("BUILD_TOOLING_LESSONS_LEARNED.md", f"Release ativa: `{PUBLISHED_TAG}`"),
    ]:
        current_truth = read_repo_text("docs", doc_name).split(
            "## HISTORICAL SNAPSHOT", 1
        )[0]
        assert (
            "Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`" in current_truth
        )
        assert release_line in current_truth
        assert "Build e testes exigem ferramentas nativas e clone do proprio host" in current_truth
        assert "PR atual: #57" not in current_truth
        assert "df0345caea9ac3050c87d2172eb75817b8fc3689" not in current_truth
