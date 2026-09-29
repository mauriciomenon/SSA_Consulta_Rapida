"""A reanalise interativa deve usar o mesmo banco selecionado pela CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest

from interface import cli
from launchers import cli_entry


@pytest.mark.parametrize("runtime_override", [False, True])
def test_rescan_passes_selected_database_table_and_runtime(
    tmp_path: Path, runtime_override: bool
) -> None:
    selected = tmp_path / "custom" / "selecionado.db"
    runtime_root = str(tmp_path / "runtime") if runtime_override else cli.project_root
    environment = {"SSA_RUNTIME_ROOT": runtime_root} if runtime_override else {}
    with (
        patch.dict(cli.os.environ, environment, clear=True),
        patch.object(cli, "_is_cli_non_interactive", return_value=False),
        patch.object(cli, "run_importer_logic", return_value=False) as importer,
        patch.object(cli.import_outcome, "get_last_import_outcome", return_value=None),
    ):
        cli._handle_rescan(str(selected), "custom_table", [], {}, {}, {})

    arguments = importer.call_args.kwargs
    assert arguments["data_dir"] == str(selected.parent)
    assert arguments["db_name"] == selected.name
    assert arguments["table_name"] == "custom_table"
    assert arguments["docs_dir"] == str(Path(runtime_root) / "docs_entrada")
    assert arguments["force_import"] is True
    assert arguments["extra_allowed_roots"] == (str(selected.parent), runtime_root)


def test_packaged_cli_rescan_uses_selected_target(tmp_path: Path) -> None:
    from core import app_logic

    selected = tmp_path / "custom" / "selecionado.db"
    runtime_root = str(tmp_path / "runtime")
    paths = cli_entry.CliRuntimePaths(
        runtime_base=runtime_root,
        docs_dir=str(Path(runtime_root) / "docs_entrada"),
        data_dir=str(Path(runtime_root) / "data"),
        db_path=str(selected),
    )
    with (
        patch.dict(cli.os.environ, {"SSA_TABLE_NAME": "custom_table"}),
        patch.object(cli_entry, "_bootstrap_runtime", return_value=runtime_root),
        patch.object(cli_entry, "_smoke_test_exit_code", return_value=None),
        patch.object(cli_entry, "_cli_info_exit_code", return_value=None),
        patch.object(cli_entry, "_prepare_cli_runtime_paths", return_value=paths),
        patch.object(cli_entry, "_should_run_import", return_value=True),
        patch.object(app_logic, "run_importer_logic", return_value=False) as importer,
        patch.object(cli.import_outcome, "get_last_import_outcome", return_value=None),
        pytest.raises(SystemExit) as exit_info,
    ):
        cli_entry.main()

    assert exit_info.value.code == 0
    arguments = importer.call_args.kwargs
    assert arguments["data_dir"] == str(selected.parent)
    assert arguments["db_name"] == selected.name
    assert arguments["table_name"] == "custom_table"
    assert arguments["docs_dir"] == paths.docs_dir
    assert arguments["extra_allowed_roots"] == [runtime_root]
