from __future__ import annotations

from tests.release_script_assertions import PROJECT_ROOT, read_repo_text


GUIA_DISTRIBUICAO = PROJECT_ROOT / "docs" / "GUIA_DISTRIBUICAO.md"
SOLUCOES_AMBIENTE = PROJECT_ROOT / "docs" / "SOLUCOES_AMBIENTE_BUILD.md"


def test_distribuicao_doc_does_not_hardcode_personal_wsl_path() -> None:
    text = read_repo_text("docs", "GUIA_DISTRIBUICAO.md")

    assert "/mnt/c/Users/mauri/" not in text
    assert "C:\\Users\\mauri" not in text
    assert "<WSL-repo-path>" in text


def test_solucoes_ambiente_doc_marks_legacy_body_historical() -> None:
    text = read_repo_text("docs", "SOLUCOES_AMBIENTE_BUILD.md")

    assert text.count("## CURRENT TRUTH") == 1
    assert "- Branch fonte: `dev`." in text
    assert "- Branch destino do PR: `main`." in text
    assert "- Branch alvo: `dev`." not in text
    assert "## HISTORICAL SNAPSHOT 2025-11-14" in text
    assert "**Data**: 2025-11-14" not in text


def test_solucoes_ambiente_doc_uses_generic_user_paths() -> None:
    text = read_repo_text("docs", "SOLUCOES_AMBIENTE_BUILD.md")

    assert "C:\\Users\\menon" not in text
    assert "C:\\Users\\<usuario>" in text
