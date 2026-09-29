from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest

from core import import_outcome
from dev_env import streamlit_app as app
from utils import path_safety


def test_import_api_uses_only_explicit_roots(tmp_path, monkeypatch):
    from core import app_logic

    docs = tmp_path / "planilhas"
    docs.mkdir()
    database = tmp_path / "novo.db"
    calls = []
    monkeypatch.setattr(path_safety, "get_allowed_roots", lambda: [])
    monkeypatch.setattr(
        app_logic, "run_importer_logic", lambda **kwargs: calls.append(kwargs) or True
    )
    assert app_logic.import_files_to_database(str(docs), str(database)) is False
    assert not calls
    roots = (str(tmp_path),)
    assert app_logic.import_files_to_database(
        str(docs), str(database), extra_allowed_roots=roots
    ) is True
    assert calls[0]["extra_allowed_roots"] == roots
    assert calls[0]["docs_dir"] == str(docs)
    assert not database.exists()


def test_read_api_does_not_reuse_other_session_roots(tmp_path, monkeypatch):
    from core import app_logic

    database = tmp_path / "externo.db"
    expected = pd.DataFrame({"numero_ssa": ["202600001"]})
    query = Mock(return_value=expected)
    monkeypatch.setattr(path_safety, "get_allowed_roots", lambda: [])
    monkeypatch.setattr(app_logic.database, "query_db", query)
    assert app_logic.get_filtered_data(
        str(database), extra_allowed_roots=(str(tmp_path),)
    ).equals(expected)
    query.reset_mock()
    assert app_logic.get_filtered_data(str(database)).empty
    query.assert_not_called()


@pytest.fixture
def source_ui(monkeypatch):
    ui = MagicMock()
    ui.session_state = {}
    ui.columns.return_value = [ui, ui, ui]
    ui.button.return_value = False
    ui.text_input.side_effect = lambda _label, *, value, key: value
    monkeypatch.setattr(app, "st", ui)
    return ui


def test_new_database_selection_authorizes_only_current_call(tmp_path, monkeypatch):
    database = tmp_path / "new.db"
    baseline = str(tmp_path / "unrelated")
    monkeypatch.setenv("SSA_EXTRA_ALLOWED_PATHS", baseline)
    monkeypatch.setattr(path_safety, "get_allowed_roots", lambda: [Path(baseline)])

    resolved = app._resolve_user_source_path(
        str(database), purpose="Banco", expect_directory=False
    )

    assert resolved == str(database.resolve())
    assert not database.exists()
    assert os.environ["SSA_EXTRA_ALLOWED_PATHS"] == baseline
    with pytest.raises(path_safety.PathSafetyError, match="fora das bases"):
        path_safety.ensure_path_is_allowed(database)


def test_source_directory_must_exist(tmp_path):
    missing = tmp_path / "missing-docs"

    with pytest.raises(path_safety.PathSafetyError, match="nao existe"):
        app._resolve_user_source_path(
            str(missing), purpose="Planilhas", expect_directory=True
        )

    assert not missing.exists()


def test_source_directory_existing_file_is_not_reported_as_missing(tmp_path):
    """Um caminho que existe como arquivo nao pode ser reportado como
    'nao existe': a mensagem precisa distinguir os dois casos."""
    file_path = tmp_path / "planilhas.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(path_safety.PathSafetyError, match="nao e um diretorio"):
        app._resolve_user_source_path(
            str(file_path), purpose="Planilhas", expect_directory=True
        )


@pytest.mark.parametrize("valid_docs", [False, True])
def test_source_selection_updates_state_only_after_both_paths_validate(
    tmp_path, monkeypatch, source_ui, valid_docs
):
    baseline = str(tmp_path / "allowed-before")
    monkeypatch.setenv("SSA_EXTRA_ALLOWED_PATHS", baseline)
    previous = {"db_path": "previous.db", "docs_dir": "previous-docs"}
    source_ui.session_state["streamlit_source_state"] = previous
    database = tmp_path / "new.db"
    documents = tmp_path / "documents"
    if valid_docs:
        documents.mkdir()
    source_ui.text_input.side_effect = [str(database), str(documents)]
    source_ui.button.side_effect = lambda _label, *, key: key == "apply_source_paths"

    app._render_source_ops_panel("previous.db", "previous-docs")

    assert not database.exists()
    assert os.environ["SSA_EXTRA_ALLOWED_PATHS"] == baseline
    if valid_docs:
        assert source_ui.session_state["streamlit_source_state"] == {
            "db_path": str(database.resolve()),
            "docs_dir": str(documents.resolve()),
            "extra_allowed_roots": (str(tmp_path.resolve()), str(documents.resolve())),
        }
        source_ui.success.assert_called_once()
        source_ui.error.assert_not_called()
    else:
        assert source_ui.session_state["streamlit_source_state"] is previous
        source_ui.success.assert_not_called()
        source_ui.error.assert_called_once()


def test_load_dataframe_forwards_session_roots(tmp_path, monkeypatch):
    database = tmp_path / "selected.db"
    database.touch()
    roots = (str(tmp_path),)
    expected = pd.DataFrame({"numero_ssa": ["202500001"]})
    read_data = Mock(return_value=expected)
    monkeypatch.setattr(app, "get_filtered_data", read_data)
    load = getattr(app.load_dataframe, "__wrapped__", app.load_dataframe)

    result = load(str(database), roots)

    pd.testing.assert_frame_equal(result, expected)
    read_data.assert_called_once_with(str(database), extra_allowed_roots=roots)


@pytest.mark.parametrize("action", ["load_data_ops", "reimport_data_ops"])
@pytest.mark.parametrize("blocked", [False, True])
def test_source_import_passes_roots_and_refreshes_state(
    tmp_path, monkeypatch, source_ui, action, blocked
):
    selected_db = str(tmp_path / "selected.db")
    selected_docs = str(tmp_path / "documents")
    roots = (str(tmp_path), selected_docs)
    source_ui.session_state = {
        "streamlit_source_state": {
            "db_path": selected_db,
            "docs_dir": selected_docs,
            "extra_allowed_roots": roots,
        },
        "recent_api_df": pd.DataFrame({"numero_ssa": ["old"]}),
    }
    source_ui.button.side_effect = lambda _label, *, key: key == action
    outcome = import_outcome.build_import_outcome(
        raw_status="candidate_invalid" if blocked else "updated",
        legacy_result=True,
        run_id="test-source-import",
        reason="validacao",
        primary_db_path=selected_db,
        working_db_path=selected_db,
    )
    monkeypatch.setattr(
        import_outcome, "get_last_import_outcome", Mock(side_effect=[None, outcome])
    )
    importer = Mock(return_value=True)
    cached_loader = Mock()
    cached_filters = Mock()
    monkeypatch.setattr(app, "import_files_to_database", importer)
    monkeypatch.setattr(app, "load_dataframe", cached_loader)
    monkeypatch.setattr(app, "filter_cache", cached_filters)

    app._render_source_ops_panel("unselected.db", "unselected-docs")

    importer.assert_called_once_with(
        docs_dir=selected_docs,
        db_path=selected_db,
        force_import=action == "reimport_data_ops",
        raise_on_error=True,
        extra_allowed_roots=roots,
    )
    cached_loader.clear.assert_called_once_with()
    cached_filters.clear.assert_called_once_with()
    assert source_ui.session_state["recent_api_df"] is None
    source_ui.rerun.assert_called_once_with()
    if blocked:
        source_ui.success.assert_not_called()
        assert "status bloqueante (candidate_invalid)" in source_ui.error.call_args.args[0]
    else:
        source_ui.error.assert_not_called()
        source_ui.success.assert_called_once_with("Importacao concluida.")
