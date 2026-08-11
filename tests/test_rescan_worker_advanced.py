"""
Testes para RescanWorker

Este modulo contem testes de unidade e integracao para o RescanWorker,
responsavel por reescanear dados de forma assincrona.
"""

import json
import logging
import os
import shutil
import sqlite3
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytest.importorskip(
    "PyQt6", reason="Dependência PyQt6 indisponível no ambiente de teste"
)
from PyQt6.QtWidgets import QApplication

from utils.path_safety import reserve_unique_path  # noqa: E402
from core import import_staging
from core.import_errors import ExtractionError
from core.import_staging import stage_external_import_files

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.workers.rescan_worker import RescanOutcome  # noqa: E402
from gui.workers.rescan_worker import RescanWorker, _LogHandler  # noqa: E402
from utils import path_safety  # noqa: E402

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Fixture para garantir QApplication disponível."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def rescan_worker():
    """Cria instância de RescanWorker para testes."""
    worker = RescanWorker(
        main_py_path="/fake/path/main.py", project_root="/fake/project"
    )
    yield worker
    # Cleanup
    if worker._logger_attached:
        worker._detach_logger()


def test_rescan_worker_accepts_explicit_external_source_file(
    tmp_path,
    monkeypatch,
):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    source = outside_root / "entrada.xlsx"
    source.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    worker = RescanWorker(
        main_py_path=str(runtime_root / "main.py"),
        project_root=str(runtime_root),
        source_files=(str(source),),
    )

    assert worker._resolve_source_files() == (str(source.resolve()),)


def test_rescan_worker_defers_source_validation_to_staging(
    tmp_path,
    monkeypatch,
):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    sources = (outside_root / "one.xlsx", outside_root / "two.xlsx")
    for source in sources:
        source.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [runtime_root])

    calls = 0

    def counting_normalize(extra_allowed_files):
        nonlocal calls
        calls += 1
        return {Path(path).resolve(strict=False) for path in extra_allowed_files}

    monkeypatch.setattr(
        import_staging,
        "_normalize_explicit_allowed_files",
        counting_normalize,
    )

    worker = RescanWorker(
        main_py_path=str(runtime_root / "main.py"),
        project_root=str(runtime_root),
        source_files=tuple(str(source) for source in sources),
    )

    assert worker._resolve_source_files() == tuple(str(source) for source in sources)
    assert calls == 0


@pytest.fixture
def signal_collector():
    """Helper para coletar signals emitidos."""

    class SignalCollector:
        def __init__(self):
            self.output_lines = []
            self.error_lines = []
            self.progress = []
            self.finished_success = False
            self.finished_error = None

        def on_output(self, msg):
            self.output_lines.append(msg)

        def on_error(self, msg):
            self.error_lines.append(msg)

        def on_progress(self, pct, msg):
            self.progress.append((pct, msg))

        def on_finished_success(self):
            self.finished_success = True

        def on_finished_error(self, msg):
            self.finished_error = msg

    return SignalCollector()


# =============================================================================
# Testes Unitários - RescanWorker
# =============================================================================


class TestRescanWorkerUnit:
    """Testes unitários para RescanWorker."""

    def test_init_creates_worker(self):
        """Testa que construtor cria worker corretamente."""
        worker = RescanWorker(main_py_path="/path/main.py", project_root="/project")

        assert worker.main_py_path == "/path/main.py"
        assert worker.project_root == "/project"
        assert worker._should_stop is False
        assert worker._logger_attached is False
        assert isinstance(worker.log_handler, _LogHandler)

    def test_stop_sets_flag(self, rescan_worker):
        """Testa que stop() seta flag de cancelamento."""
        assert rescan_worker._should_stop is False
        rescan_worker.stop()
        assert rescan_worker._should_stop is True

    def test_count_database_rows_returns_unavailable_on_database_error(
        self, rescan_worker, tmp_path
    ):
        db_path = tmp_path / "broken.db"
        db_path.touch()
        rescan_worker.db_path = str(db_path)

        with (
            patch.object(rescan_worker.logger, "warning") as warning,
            patch(
                "gui.workers.rescan_worker.count_table_rows",
                side_effect=sqlite3.OperationalError("broken"),
            ),
        ):
            assert rescan_worker._count_database_rows() is None
        warning.assert_called_once()
        assert "broken" in str(warning.call_args)

    def test_attach_logger_adds_handler(self, rescan_worker):
        """Testa que _attach_logger adiciona handler ao logger."""
        logger = rescan_worker.logger
        initial_handlers = len(logger.handlers)

        rescan_worker._attach_logger()

        assert rescan_worker._logger_attached is True
        assert len(logger.handlers) == initial_handlers + 1
        assert rescan_worker.log_handler in logger.handlers

        # Cleanup
        rescan_worker._detach_logger()

    def test_attach_logger_increments_refcount(self):
        """Testa que _attach_logger incrementa refcount global."""
        worker = RescanWorker("/fake/main.py", "/fake/project")
        logger = worker.logger
        initial_handlers = len(logger.handlers)
        try:
            worker._attach_logger()
            assert len(logger.handlers) == initial_handlers + 1
            assert worker.log_handler in logger.handlers
            assert worker._logger_attached is True
        finally:
            if worker._logger_attached:
                worker._detach_logger()
        assert len(logger.handlers) == initial_handlers

    def test_detach_logger_removes_handler(self, rescan_worker):
        """Testa que _detach_logger remove handler do logger."""
        logger = rescan_worker.logger

        rescan_worker._attach_logger()
        assert rescan_worker.log_handler in logger.handlers

        rescan_worker._detach_logger()
        assert rescan_worker.log_handler not in logger.handlers
        assert rescan_worker._logger_attached is False

    def test_detach_logger_decrements_refcount(self):
        """Testa que _detach_logger decrementa refcount global."""
        # Nota: Teste simplificado devido a estado global compartilhado
        worker = RescanWorker("/fake/main.py", "/fake/project")
        logger = worker.logger

        worker._attach_logger()
        assert worker.log_handler in logger.handlers

        try:
            worker._detach_logger()
            # Verificar que handler foi removido (comportamento principal)
            assert worker.log_handler not in logger.handlers
            assert worker._logger_attached is False
        finally:
            # Cleanup extra se necessário
            if worker._logger_attached:
                worker._detach_logger()

    def test_multiple_attach_detach_refcount(self):
        """Testa refcount com múltiplos attach/detach."""
        # Nota: Teste simplificado devido a estado global compartilhado
        worker = RescanWorker("/fake/main.py", "/fake/project")
        logger = worker.logger
        initial_handlers = len(logger.handlers)

        try:
            # Attach 3 vezes - handler deve ser adicionado apenas uma vez
            for _ in range(3):
                worker._attach_logger()
                # Handler deve estar presente
                assert worker.log_handler in logger.handlers
            assert len(logger.handlers) == initial_handlers + 1

            # Detach 3 vezes
            for _ in range(3):
                worker._detach_logger()

            # Handler deve ser removido
            assert worker.log_handler not in logger.handlers
            assert len(logger.handlers) == initial_handlers
            assert worker._logger_attached is False
        finally:
            # Cleanup extra se necessário
            while worker._logger_attached:
                worker._detach_logger()

    def test_progress_callback_start(self, rescan_worker, signal_collector):
        """Testa callback de progresso - evento start."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.progress.connect(signal_collector.on_progress)

        rescan_worker._progress_callback("start", {"total": 10})

        assert len(signal_collector.output_lines) == 1
        assert "10 arquivos" in signal_collector.output_lines[0]
        assert len(signal_collector.progress) == 1
        assert signal_collector.progress[0][0] == 10
        assert signal_collector.progress[0][1].endswith(
            "Iniciando processamento..."
        )

    def test_progress_callback_file_start(self, rescan_worker, signal_collector):
        """Testa callback de progresso - evento file_start."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.progress.connect(signal_collector.on_progress)

        rescan_worker._progress_callback(
            "file_start", {"filename": "test.xlsx", "current": 5, "total": 10}
        )

        assert len(signal_collector.output_lines) == 1
        assert "test.xlsx" in signal_collector.output_lines[0]
        assert len(signal_collector.progress) == 1
        # 10 + (5/10 * 70) = 45%
        assert signal_collector.progress[0][0] == 45

    def test_progress_callback_file_success(self, rescan_worker, signal_collector):
        """Testa callback de progresso - evento file_success."""
        rescan_worker.output_line.connect(signal_collector.on_output)

        rescan_worker._progress_callback(
            "file_success", {"filename": "test.xlsx", "records": 100}
        )

        assert len(signal_collector.output_lines) == 1
        assert "[OK]" in signal_collector.output_lines[0]
        assert "test.xlsx" in signal_collector.output_lines[0]
        assert "100 registros" in signal_collector.output_lines[0]

    def test_progress_callback_appends_updated_ssas_only_when_nonzero(
        self, rescan_worker, signal_collector
    ):
        rescan_worker.output_line.connect(signal_collector.on_output)

        rescan_worker._progress_callback(
            "file_success",
            {
                "filename": "updated.xlsx",
                "records": 100,
                "ssa_inserted": 4,
                "ssa_updated": 7,
            },
        )
        rescan_worker._progress_callback(
            "file_success",
            {
                "filename": "unchanged.xlsx",
                "records": 100,
                "ssa_inserted": 0,
                "ssa_updated": 0,
            },
        )

        assert signal_collector.output_lines[0].endswith(
            "100 registros | 7 SSAs atualizadas"
        )
        assert "SSAs atualizadas" not in signal_collector.output_lines[1]

    def test_progress_callback_file_error(self, rescan_worker, signal_collector):
        """Testa callback de progresso - evento file_error."""
        rescan_worker.error_line.connect(signal_collector.on_error)

        rescan_worker._progress_callback(
            "file_error", {"filename": "test.xlsx", "error": "Arquivo corrompido"}
        )

        assert len(signal_collector.error_lines) == 1
        assert "[ERRO]" in signal_collector.error_lines[0]
        assert "test.xlsx" in signal_collector.error_lines[0]
        assert "Arquivo corrompido" in signal_collector.error_lines[0]

    def test_progress_callback_explicit_single_batch_emits_batch_summary(
        self, rescan_worker, signal_collector
    ):
        rescan_worker.explicit_files = ("test.xlsx",)
        rescan_worker.output_line.connect(signal_collector.on_output)

        rescan_worker._progress_callback(
            "finish", {"total": 1, "processed": 1, "errors": []}
        )

        assert any(
            "Bloco 1/1 concluido: 1/1 arquivos | 0 SSAs atualizadas | 0 SSAs novas"
            in line
            for line in signal_collector.output_lines
        )

    @pytest.mark.parametrize(
        "error_code", ["MISSING_REQUIRED_COLUMNS", "ALL_ROWS_REJECTED"]
    )
    def test_progress_callback_deterministic_rejection_is_warning_only(
        self, rescan_worker, signal_collector, error_code
    ):
        rescan_worker.error_line.connect(signal_collector.on_error)

        rescan_worker._progress_callback(
            "file_error",
            {
                "filename": "fora_do_padrao.xlsx",
                "error": "colunas obrigatorias ausentes",
                "error_code": error_code,
            },
        )

        assert rescan_worker._has_runtime_errors is False
        assert signal_collector.error_lines == [
            "[AVISO] fora_do_padrao.xlsx: colunas obrigatorias ausentes"
        ]

    def test_progress_callback_finish(self, rescan_worker, signal_collector):
        """Testa callback de progresso - evento finish."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.progress.connect(signal_collector.on_progress)

        rescan_worker._progress_callback(
            "finish",
            {"total": 10, "processed": 8, "errors": ["file1.xlsx", "file2.xlsx"]},
        )

        assert (
            len(signal_collector.output_lines) == 3
        )  # linha em branco + mensagem + erros
        assert "8/10" in signal_collector.output_lines[1]
        assert "2 arquivos falharam" in signal_collector.output_lines[2]
        assert signal_collector.progress[0] == (90, "Finalizando...")

    def test_progress_callback_stopped(self, rescan_worker, signal_collector):
        """Testa que callback não processa quando stopped."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker._should_stop = True

        rescan_worker._progress_callback("start", {"total": 10})

        assert len(signal_collector.output_lines) == 0


# =============================================================================
# Testes de Integração - RescanWorker
# =============================================================================


class TestRescanWorkerIntegration:
    """Testes de integração para RescanWorker com signals."""

    def test_run_emits_output_signals(self, rescan_worker, signal_collector):
        """Testa que run() emite signals de output."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.progress.connect(signal_collector.on_progress)
        rescan_worker.finished_success.connect(signal_collector.on_finished_success)

        # Mock run_importer_logic para retornar sucesso
        with patch("gui.workers.rescan_worker.run_importer_logic", return_value=True):
            rescan_worker.run()

        assert len(signal_collector.output_lines) > 0
        assert "Iniciando Reescaneamento" in signal_collector.output_lines[0]
        assert signal_collector.finished_success is True
        assert rescan_worker.last_outcome == "no_changes"

    def test_run_success_without_processed_files_marks_no_changes_when_context_exists(
        self, signal_collector
    ):
        worker = RescanWorker("main.py", ".", force_import=False)
        worker.finished_success.connect(signal_collector.on_finished_success)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 1})
            callback("finish", {"total": 1, "processed": 0, "errors": []})
            return True

        try:
            with patch(
                "gui.workers.rescan_worker.run_importer_logic",
                side_effect=_mock_importer,
            ):
                worker.run()
            assert signal_collector.finished_success is True
            assert worker.last_outcome == RescanOutcome.NO_CHANGES
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    def test_run_full_without_updates_without_context_emits_success(
        self, rescan_worker, signal_collector
    ):
        """Full sem contexto de arquivos permanece como no-op valido."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.finished_success.connect(signal_collector.on_finished_success)
        rescan_worker.finished_error.connect(signal_collector.on_finished_error)

        # Mock run_importer_logic para retornar falha
        with patch("gui.workers.rescan_worker.run_importer_logic", return_value=False):
            rescan_worker.run()

        assert signal_collector.finished_success is True
        assert signal_collector.finished_error is None
        assert rescan_worker.last_outcome == "no_changes"
        assert any(
            "Reescaneamento Completo Concluido (sem alteracoes)" in line
            for line in signal_collector.output_lines
        )

    def test_run_full_without_updates_with_processed_context_emits_no_changes_success(
        self, rescan_worker, signal_collector
    ):
        """Full sem erros e sem atualizacao deve terminar como no_changes."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.finished_success.connect(signal_collector.on_finished_success)
        rescan_worker.finished_error.connect(signal_collector.on_finished_error)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 2})
            callback("finish", {"total": 2, "processed": 0, "errors": []})
            return False

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=_mock_importer
        ):
            rescan_worker.run()

        assert signal_collector.finished_success is True
        assert signal_collector.finished_error is None
        assert rescan_worker.last_outcome == "no_changes"
        assert any(
            "Reescaneamento Completo Concluido" in line
            for line in signal_collector.output_lines
        )

    def test_run_diff_with_only_deterministic_rejections_emits_success_message(
        self, signal_collector
    ):
        worker = RescanWorker("main.py", ".", force_import=False)
        worker.output_line.connect(signal_collector.on_output)
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 1})
            callback("file_start", {"filename": "bad.xlsx", "current": 1, "total": 1})
            callback(
                "file_error",
                {
                    "filename": "bad.xlsx",
                    "error": "bad cols",
                    "error_code": "MISSING_REQUIRED_COLUMNS",
                    "deterministic": True,
                },
            )
            callback(
                "finish",
                {
                    "total": 1,
                    "processed": 0,
                    "errors": [("extraction", "bad.xlsx", "bad cols")],
                    "deterministic_failure_count": 1,
                    "rejection_only": True,
                },
            )
            return False

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=_mock_importer
        ):
            worker.run()

        assert signal_collector.finished_success is True
        assert signal_collector.finished_error is None
        assert worker.last_outcome == "rejections_only"
        assert any(
            "Rejeicoes Deterministicas" in line
            for line in signal_collector.output_lines
        )
        assert not any(
            "Nenhum arquivo novo ou alterado foi encontrado." in line
            for line in signal_collector.output_lines
        )

    def test_run_diff_with_runtime_errors_emits_error(self, signal_collector):
        worker = RescanWorker("main.py", ".", force_import=False)
        worker.output_line.connect(signal_collector.on_output)
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 1})
            callback("file_error", {"filename": "bad.xlsx", "error": "bad cols"})
            callback(
                "finish",
                {
                    "total": 1,
                    "processed": 0,
                    "errors": [("extraction", "bad.xlsx", "bad cols")],
                    "deterministic_failure_count": 0,
                    "rejection_only": False,
                },
            )
            return False

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=_mock_importer
        ):
            worker.run()

        assert signal_collector.finished_success is False
        assert signal_collector.finished_error is not None
        assert worker.last_outcome == "error"
        assert "diferencial falhou com erros" in signal_collector.finished_error.lower()
        assert "bad.xlsx" in signal_collector.finished_error
        assert "bad cols" in signal_collector.finished_error
        assert any(
            "Reescaneamento Diferencial Falhou" in line
            for line in signal_collector.output_lines
        )

    def test_run_full_with_only_deterministic_rejections_emits_success_message(
        self, signal_collector
    ):
        worker = RescanWorker("main.py", ".", force_import=True)
        worker.output_line.connect(signal_collector.on_output)
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 1})
            callback("file_start", {"filename": "bad.xlsx", "current": 1, "total": 1})
            callback(
                "file_error",
                {
                    "filename": "bad.xlsx",
                    "error": "bad cols",
                    "error_code": "MISSING_REQUIRED_COLUMNS",
                    "deterministic": True,
                },
            )
            callback(
                "finish",
                {
                    "total": 1,
                    "processed": 0,
                    "errors": [("extraction", "bad.xlsx", "bad cols")],
                    "deterministic_failure_count": 1,
                    "rejection_only": True,
                },
            )
            return False

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=_mock_importer
        ):
            worker.run()

        assert signal_collector.finished_success is True
        assert signal_collector.finished_error is None
        assert worker.last_outcome == "rejections_only"
        assert any(
            "Rejeicoes Deterministicas" in line
            for line in signal_collector.output_lines
        )
        assert not any(
            "Reescaneamento Completo Falhou" in line
            for line in signal_collector.output_lines
        )

    def test_run_full_without_updates_emits_no_changes_success(
        self, signal_collector
    ):
        worker = RescanWorker("main.py", ".", force_import=True)
        worker.output_line.connect(signal_collector.on_output)
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)

        def _mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 1})
            callback(
                "finish",
                {
                    "total": 1,
                    "processed": 0,
                    "errors": [],
                },
            )
            return False

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=_mock_importer
        ):
            worker.run()

        assert signal_collector.finished_success is True
        assert signal_collector.finished_error is None
        assert worker.last_outcome == "no_changes"
        assert any(
            "Reescaneamento Completo Concluido" in line
            for line in signal_collector.output_lines
        )

    def test_run_emits_error_on_unsafe_identity_payload(
        self, rescan_worker, signal_collector
    ):
        """Unsafe identity payload must end as GUI error."""
        rescan_worker.error_line.connect(signal_collector.on_error)
        rescan_worker.finished_error.connect(signal_collector.on_finished_error)

        with patch(
            "gui.workers.rescan_worker.run_importer_logic",
            side_effect=ExtractionError(
                "1 linha sem identidade ainda possui payload",
                error_code="UNSAFE_INVALID_IDENTITY_PAYLOAD",
            ),
        ):
            rescan_worker.run()

        assert signal_collector.finished_error is not None
        assert rescan_worker.last_outcome == "error"
        assert "sem identidade ainda possui payload" in signal_collector.finished_error
        assert len(signal_collector.error_lines) > 0

    def test_run_emits_cancelled_when_stopped(self, rescan_worker, signal_collector):
        """Testa que run() emite cancelled quando stopped."""
        rescan_worker.finished_error.connect(signal_collector.on_finished_error)

        # Parar worker antes de executar
        rescan_worker.stop()

        with patch("gui.workers.rescan_worker.run_importer_logic", return_value=True):
            rescan_worker.run()

        assert signal_collector.finished_error is not None
        assert rescan_worker.last_outcome == "cancelled"
        assert "cancelado" in signal_collector.finished_error.lower()

    def test_run_calls_importer_with_correct_params(self, rescan_worker):
        """Testa que run() chama importer com parâmetros corretos."""
        with patch("gui.workers.rescan_worker.run_importer_logic") as mock_importer:
            mock_importer.return_value = True
            rescan_worker.run()

            mock_importer.assert_called_once()
            call_kwargs = mock_importer.call_args[1]
            expected_root = str(Path("/fake/project").resolve())

            assert call_kwargs["docs_dir"] == str(Path(expected_root) / "docs_entrada")
            assert call_kwargs["data_dir"] == str(Path(expected_root) / "data")
            assert call_kwargs["db_name"] == "ssas.db"
            assert call_kwargs["extra_allowed_roots"] == (expected_root,)
            assert call_kwargs["table_name"] == "ssa_table"
            assert call_kwargs["force_import"] is True
            assert callable(call_kwargs["should_cancel"])
            assert callable(call_kwargs["progress_callback"])

    @staticmethod
    def test_run_calls_importer_with_active_db_path(tmp_path):
        active_db = tmp_path / "alternate_db" / "custom.sqlite"
        active_db.parent.mkdir()
        active_db.write_bytes(b"")
        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            db_path=str(active_db),
        )
        try:
            with patch("gui.workers.rescan_worker.run_importer_logic") as mock_importer:
                mock_importer.return_value = True
                worker.run()

                mock_importer.assert_called_once()
                call_kwargs = mock_importer.call_args[1]

                assert call_kwargs["data_dir"] == str(active_db.parent)
                assert call_kwargs["db_name"] == active_db.name
                assert call_kwargs["docs_dir"] == str(tmp_path / "docs_entrada")
                assert call_kwargs["extra_allowed_roots"] == (
                    str(tmp_path.resolve()),
                    str(active_db.parent),
                )
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    @staticmethod
    def test_run_passes_external_active_db_parent_as_allowed_root(tmp_path):
        project_root = tmp_path / "project"
        project_root.mkdir()
        active_db = tmp_path / "selected_db" / "custom.sqlite"
        active_db.parent.mkdir()
        active_db.write_bytes(b"")
        worker = RescanWorker(
            main_py_path=str(project_root / "main.py"),
            project_root=str(project_root),
            db_path=str(active_db),
        )
        try:
            with patch("gui.workers.rescan_worker.run_importer_logic") as mock_importer:
                mock_importer.return_value = True
                worker.run()

                call_kwargs = mock_importer.call_args[1]

                assert call_kwargs["data_dir"] == str(active_db.parent)
                assert call_kwargs["db_name"] == active_db.name
                assert call_kwargs["docs_dir"] == str(project_root / "docs_entrada")
                assert call_kwargs["extra_allowed_roots"] == (
                    str(project_root.resolve()),
                    str(active_db.parent),
                )
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    def test_run_calls_importer_with_explicit_files(self, tmp_path):
        """Testa que run() encaminha explicit_files no modo de importacao explicita."""
        docs_dir = tmp_path / "docs_entrada"
        docs_dir.mkdir()
        file_a = docs_dir / "a.xlsx"
        file_b = docs_dir / "b.xlsx"
        file_a.write_text("a", encoding="utf-8")
        file_b.write_text("b", encoding="utf-8")
        worker = RescanWorker(
            main_py_path="/path/main.py",
            project_root=str(tmp_path),
            force_import=False,
            explicit_files=(str(file_a), str(file_b)),
            operation_label="Importacao externa",
        )
        try:
            with patch("gui.workers.rescan_worker.run_importer_logic") as mock_importer:
                mock_importer.return_value = True
                worker.run()

                mock_importer.assert_called_once()
                call_kwargs = mock_importer.call_args[1]

                assert call_kwargs["force_import"] is False
                assert call_kwargs["docs_dir"] == str(docs_dir)
                assert call_kwargs["explicit_files"] == (
                    str(file_a.resolve()),
                    str(file_b.resolve()),
                )
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    def test_run_stages_source_files_before_importer(self, tmp_path):
        docs_dir = tmp_path / "docs_entrada"
        docs_dir.mkdir()
        source_dir = tmp_path / "fontes"
        source_dir.mkdir()
        source = source_dir / "entrada.xlsx"
        source.write_text("payload", encoding="utf-8")
        source_legacy = source_dir / "entrada_legacy.xls"
        source_legacy.write_text("payload-legacy", encoding="utf-8")

        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=False,
            source_files=(str(source), str(source_legacy)),
            operation_label="Importacao externa",
        )
        try:
            with patch("gui.workers.rescan_worker.run_importer_logic") as mock_importer:
                def _mock_importer(**kwargs):
                    callback = kwargs["progress_callback"]
                    callback("start", {"total": 1})
                    callback("finish", {"total": 1, "processed": 1, "errors": []})
                    return True

                mock_importer.side_effect = _mock_importer
                worker.run()

                staged_file = docs_dir / "entrada.xlsx"
                staged_legacy = docs_dir / "entrada_legacy.xls"
                assert staged_file.exists()
                assert not staged_legacy.exists()
                assert worker.last_outcome == RescanOutcome.UPDATED
                call_kwargs = mock_importer.call_args[1]
                assert call_kwargs["docs_dir"] == str(docs_dir)
                assert call_kwargs["explicit_files"] == (str(staged_file),)
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    def test_run_splits_143_external_files_into_three_batches(self, tmp_path):
        docs_dir = tmp_path / "docs_entrada"
        docs_dir.mkdir()
        source_dir = tmp_path / "fontes"
        source_dir.mkdir()
        sources = []
        for index in range(143):
            source = source_dir / f"entrada_{index:03d}.xlsx"
            source.write_bytes(b"xlsx")
            sources.append(str(source))
        db_path = tmp_path / "data" / "ssas.db"
        db_path.parent.mkdir()
        db_path.touch()

        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=False,
            source_files=tuple(sources),
            db_path=str(db_path),
            operation_label="Importacao",
        )
        assert hasattr(worker, "batch_completed")
        outputs: list[str] = []
        completed_batches: list[tuple[int, int]] = []
        worker.output_line.connect(outputs.append)
        worker.batch_completed.connect(
            lambda current, total: completed_batches.append((current, total))
        )
        batch_sizes: list[int] = []
        inserted_by_batch = (20, 10, 5)
        updated_by_batch = (3, 0, 2)

        def _mock_importer(**kwargs):
            batch_index = len(batch_sizes)
            explicit_files = tuple(kwargs["explicit_files"] or ())
            batch_sizes.append(len(explicit_files))
            callback = kwargs["progress_callback"]
            callback("start", {"total": len(explicit_files)})
            callback(
                "file_success",
                {
                    "filename": Path(explicit_files[0]).name,
                    "records": 1,
                    "ssa_inserted": inserted_by_batch[batch_index],
                    "ssa_updated": updated_by_batch[batch_index],
                },
            )
            callback(
                "finish",
                {
                    "total": len(explicit_files),
                    "processed": len(explicit_files),
                    "errors": [],
                },
            )
            return True

        try:
            with (
                patch(
                    "gui.workers.rescan_worker.run_importer_logic",
                    side_effect=_mock_importer,
                ),
                patch(
                    "gui.workers.rescan_worker.count_table_rows",
                    create=True,
                    # Deliberate mismatch: inserted metrics must not be derived
                    # from a net row delta that can include independent removals.
                    side_effect=(100, 119, 130, 134),
                ),
            ):
                worker.run()
        finally:
            if worker._logger_attached:
                worker._detach_logger()

        assert batch_sizes == [64, 64, 15]
        assert completed_batches == [(1, 3), (2, 3), (3, 3)]
        assert outputs[0].endswith("=== Iniciando Importacao ===")
        assert any(
            "143 arquivos selecionados; serao processados em 3 ciclos de ate 64 arquivos"
            in line
            for line in outputs
        )
        assert any("Etapa: preparando ciclo 2/3 (65-128/143)" in line for line in outputs)
        assert any("[STAGE 65/143]" in line for line in outputs)
        assert any(
            "Bloco 1/3 concluido: 64/64 arquivos | 3 SSAs atualizadas | 20 SSAs novas"
            in line
            for line in outputs
        )
        assert any(
            "Bloco 2/3 concluido: 64/64 arquivos | 0 SSAs atualizadas | 10 SSAs novas"
            in line
            for line in outputs
        )
        assert sum(
            line.startswith("Bloco ") and "SSAs atualizadas" in line
            for line in outputs
        ) == 3
        assert (
            "Banco de dados: 100 -> 134 SSAs no total; "
            "5 SSAs atualizadas; 35 SSAs novas."
        ) in outputs

    def test_force_import_only_recreates_database_for_first_explicit_batch(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SSA_RUNTIME_ROOT", str(tmp_path / "runtime"))
        source_dir = tmp_path / "fontes"
        source_dir.mkdir()
        sources = []
        for index in range(65):
            source = source_dir / f"entrada_{index:03d}.xlsx"
            pd.DataFrame(
                [
                    {
                        "Numero SSA": f"2026{index + 1:05d}",
                        "Situacao": "ABERTA",
                        "Setor Executor": "TEST",
                        "Emitida Em": "01/01/2026",
                        "Descricao": f"Lote {index + 1}",
                    }
                ]
            ).to_excel(source, index=False)
            sources.append(str(source))

        db_path = tmp_path / "data" / "ssas.db"
        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=True,
            source_files=tuple(sources),
            db_path=str(db_path),
            operation_label="Importacao externa",
        )
        try:
            worker.run()
        finally:
            if worker._logger_attached:
                worker._detach_logger()

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT numero_ssa FROM ssa_table "
                "WHERE numero_ssa IN (?, ?) ORDER BY numero_ssa",
                ("202600001", "202600065"),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]

        assert worker.last_outcome == RescanOutcome.UPDATED
        assert total == 65
        assert rows == [("202600001",), ("202600065",)]
        assert worker.force_import is True

    def test_run_reports_error_when_later_explicit_batch_fails(
        self, tmp_path, signal_collector
    ):
        source_dir = tmp_path / "fontes"
        source_dir.mkdir()
        sources = []
        for index in range(65):
            source = source_dir / f"entrada_{index:03d}.xlsx"
            source.write_bytes(b"xlsx")
            sources.append(str(source))
        db_path = tmp_path / "data" / "ssas.db"
        db_path.parent.mkdir()
        db_path.touch()

        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=False,
            source_files=tuple(sources),
            db_path=str(db_path),
            operation_label="Importacao externa",
        )
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)
        calls = {"count": 0}

        def _mock_importer(**kwargs):
            calls["count"] += 1
            callback = kwargs["progress_callback"]
            explicit_files = tuple(kwargs["explicit_files"] or ())
            callback("start", {"total": len(explicit_files)})
            if calls["count"] == 1:
                callback(
                    "file_success",
                    {
                        "filename": Path(explicit_files[0]).name,
                        "records": 1,
                        "ssa_inserted": 1,
                        "ssa_updated": 0,
                    },
                )
                callback(
                    "finish",
                    {
                        "total": len(explicit_files),
                        "processed": len(explicit_files),
                        "errors": [],
                    },
                )
                return True
            callback(
                "file_error",
                {"filename": Path(explicit_files[0]).name, "error": "falha"},
            )
            callback(
                "finish",
                {
                    "total": len(explicit_files),
                    "processed": 0,
                    "errors": [("import", explicit_files[0], "falha")],
                },
            )
            return False

        try:
            with (
                patch(
                    "gui.workers.rescan_worker.run_importer_logic",
                    side_effect=_mock_importer,
                ),
                patch(
                    "gui.workers.rescan_worker.count_table_rows",
                    side_effect=(10, 11, 11),
                ),
            ):
                worker.run()
        finally:
            if worker._logger_attached:
                worker._detach_logger()

        assert calls["count"] == 2
        assert worker.last_outcome == RescanOutcome.ERROR
        assert signal_collector.finished_success is False
        assert "falhou com erros" in signal_collector.finished_error

    def test_run_explicit_batch_emits_cancelled_when_stop_arrives_during_import(
        self, tmp_path, signal_collector
    ):
        docs_dir = tmp_path / "docs_entrada"
        docs_dir.mkdir()
        source = tmp_path / "entrada.xlsx"
        source.write_bytes(b"xlsx")
        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=False,
            source_files=(str(source),),
            operation_label="Importacao externa",
        )
        worker.finished_error.connect(signal_collector.on_finished_error)
        outputs: list[str] = []
        worker.output_line.connect(outputs.append)

        def _cancel_during_import(**kwargs):
            kwargs["progress_callback"](
                "file_success",
                {
                    "filename": "entrada.xlsx",
                    "records": 1,
                    "ssa_inserted": 1,
                    "ssa_updated": 0,
                },
            )
            worker.stop()
            return True

        try:
            with (
                patch(
                    "gui.workers.rescan_worker.run_importer_logic",
                    side_effect=_cancel_during_import,
                ),
                patch(
                    "gui.workers.rescan_worker.count_table_rows",
                    return_value=0,
                ),
            ):
                worker.run()
        finally:
            if worker._logger_attached:
                worker._detach_logger()

        assert worker.last_outcome == RescanOutcome.CANCELLED
        assert signal_collector.finished_error == "Processo cancelado pelo usuario"
        assert not any(line.startswith("Banco de dados:") for line in outputs)

    def test_stage_source_files_stops_after_copy_when_cancel_requested(self, tmp_path):
        docs_dir = tmp_path / "docs_entrada"
        docs_dir.mkdir()
        source_dir = tmp_path / "fontes"
        source_dir.mkdir()
        source = source_dir / "cancel.xlsx"
        source.write_text("payload", encoding="utf-8")

        cancel_state = {"should_stop": False}
        def _copy_and_cancel(source, destination):
            cancel_state["should_stop"] = True
            return shutil.copyfile(source, destination)

        with patch(
            "core.import_staging.copy_source_without_execute_bit",
            side_effect=_copy_and_cancel,
        ):
            staged_files, summary = stage_external_import_files(
                project_root=str(tmp_path),
                source_files=(str(source),),
                should_cancel=lambda: cancel_state["should_stop"],
            )
        assert staged_files == []
        assert summary["copied"] == 0
        assert summary["failed"] == 0
        assert not (docs_dir / "cancel.xlsx").exists()

    def test_unique_destination_path_uses_reserved_set_for_collisions(self, tmp_path):
        target = tmp_path / "entrada.xlsx"
        target.write_text("old", encoding="utf-8")
        reserved = {str(target.resolve())}

        candidate = reserve_unique_path(target, reserved_paths=reserved)

        assert candidate.endswith("entrada__1.xlsx")
        assert os.path.abspath(candidate) in reserved

    def test_run_consolidation_operation_moves_files(self, tmp_path, signal_collector):
        docs_dir = tmp_path / "docs_entrada"
        logs_dir = tmp_path / "logs"
        docs_dir.mkdir()
        logs_dir.mkdir()
        (docs_dir / "ok.xlsx").write_text("ok", encoding="utf-8")

        payload = {
            "paths": {"docs_dir": str(docs_dir)},
            "file_reports": [
                {"file": "ok.xlsx", "counts": {"rows_inserted": 1}},
            ],
        }
        (logs_dir / "import_run_20260327_000001_000001.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        worker = RescanWorker(
            main_py_path=str(tmp_path / "main.py"),
            project_root=str(tmp_path),
            force_import=False,
            operation_label="Consolidacao de arquivos",
            operation_kind="consolidate",
        )
        worker.finished_success.connect(signal_collector.on_finished_success)
        worker.finished_error.connect(signal_collector.on_finished_error)
        worker.output_line.connect(signal_collector.on_output)

        try:
            worker.run()
            assert worker.last_outcome == RescanOutcome.UPDATED
            assert signal_collector.finished_success is True
            assert signal_collector.finished_error is None
            assert (docs_dir / "processadas" / "ok.xlsx").exists()
        finally:
            if worker._logger_attached:
                worker._detach_logger()

    def test_progress_sequence(self, rescan_worker, signal_collector):
        """Testa sequência completa de progresso."""
        rescan_worker.output_line.connect(signal_collector.on_output)
        rescan_worker.progress.connect(signal_collector.on_progress)
        rescan_worker.finished_success.connect(signal_collector.on_finished_success)

        def mock_importer(**kwargs):
            callback = kwargs["progress_callback"]
            callback("start", {"total": 3})
            callback("file_start", {"filename": "file1.xlsx", "current": 1, "total": 3})
            callback("file_success", {"filename": "file1.xlsx", "records": 10})
            callback("file_start", {"filename": "file2.xlsx", "current": 2, "total": 3})
            callback("file_success", {"filename": "file2.xlsx", "records": 20})
            callback("finish", {"total": 3, "processed": 2, "errors": []})
            return True

        with patch(
            "gui.workers.rescan_worker.run_importer_logic", side_effect=mock_importer
        ):
            rescan_worker.run()

        # Verificar sequência de progresso
        assert len(signal_collector.progress) >= 4
        assert signal_collector.progress[0][0] == 5  # Configurando
        assert signal_collector.progress[1][0] == 10  # Start
        assert signal_collector.progress[-2][0] == 90  # Finish
        assert signal_collector.progress[-1][0] == 100  # Concluído

        assert signal_collector.finished_success is True


# =============================================================================
# Testes para _LogHandler
# =============================================================================


class TestLogHandler:
    """Testes para o handler de logs customizado."""

    def test_emit_output_signal(self):
        """Testa emissão de log para output_signal."""
        output_signal = MagicMock()
        error_signal = MagicMock()

        handler = _LogHandler(output_signal, error_signal)
        handler.setLevel(logging.INFO)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Mensagem de info",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        output_signal.emit.assert_called_once()
        error_signal.emit.assert_not_called()

    def test_emit_error_signal(self):
        """Testa emissão de log para error_signal."""
        output_signal = MagicMock()
        error_signal = MagicMock()

        handler = _LogHandler(output_signal, error_signal)
        handler.setLevel(logging.INFO)

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Mensagem de erro",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        output_signal.emit.assert_not_called()
        error_signal.emit.assert_called_once()

    def test_emit_handles_exception(self):
        """Testa que emit não quebra em exceção."""
        output_signal = MagicMock()
        output_signal.emit.side_effect = Exception("Signal error")
        error_signal = MagicMock()

        handler = _LogHandler(output_signal, error_signal)
        handler.setLevel(logging.INFO)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Teste",
            args=(),
            exc_info=None,
        )

        # Não deve levantar exceção
        handler.emit(record)


# =============================================================================
# Testes de Thread Safety
# =============================================================================


class TestRescanWorkerThreadSafety:
    """Testes de thread safety para RescanWorker."""

    def test_logger_lock_prevents_race_condition(self):
        """Testa que lock previne condições de corrida no logger."""
        shared_logger = logging.getLogger("ssa")
        initial_handlers = len(shared_logger.handlers)
        workers = []
        errors = []

        def create_and_attach():
            try:
                worker = RescanWorker("/fake/main.py", "/fake/project")
                worker._attach_logger()
                workers.append(worker)
            except Exception as e:
                errors.append(str(e))

        # Criar múltiplas threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=create_and_attach)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Cleanup
        for worker in workers:
            if worker._logger_attached:
                worker._detach_logger()

        # Verificar que não houve erros
        assert len(errors) == 0
        # Verificar que todos os workers foram criados
        assert len(workers) == 5
        assert len(shared_logger.handlers) == initial_handlers

    def test_stop_is_thread_safe(self, rescan_worker):
        """Testa que stop() é thread-safe."""
        rescan_worker._should_stop = False

        def stop_worker():
            rescan_worker.stop()

        threads = []
        for _ in range(10):
            t = threading.Thread(target=stop_worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert rescan_worker._should_stop is True


# =============================================================================
# Testes de Regressão
# =============================================================================


class TestRescanWorkerRegression:
    """Testes de regressão para bugs identificados."""

    def test_detach_logger_idempotent(self, rescan_worker):
        """Testa que detach_logger é idempotente (não quebra se chamado múltiplas vezes)."""
        rescan_worker._attach_logger()
        rescan_worker._detach_logger()

        # Segunda chamada não deve quebrar
        rescan_worker._detach_logger()
        rescan_worker._detach_logger()

        assert rescan_worker._logger_attached is False

    def test_progress_callback_with_missing_keys(self, rescan_worker, signal_collector):
        """Testa que callback lida com dados incompletos."""
        rescan_worker.output_line.connect(signal_collector.on_output)

        # Chamar com dados incompletos - não deve quebrar
        # file_start com defaults: current=0, total=1
        rescan_worker._progress_callback("file_start", {})  # Sem current/total
        rescan_worker._progress_callback("file_success", {})  # Sem filename (usa '')

        # Não deve quebrar - file_error emite em error_line
        rescan_worker.error_line.connect(signal_collector.on_error)
        rescan_worker._progress_callback("file_error", {})  # Sem error

        # Verificar que emitiu (pode ser menos que 3 se algum não emitir)
        assert len(signal_collector.output_lines) >= 1
        assert len(signal_collector.error_lines) >= 1

    def test_run_cleanup_on_exception(self, rescan_worker, signal_collector):
        """Testa que cleanup é executado mesmo em exceção."""
        rescan_worker._attach_logger()
        assert rescan_worker._logger_attached is True

        rescan_worker.finished_error.connect(signal_collector.on_finished_error)

        with patch(
            "gui.workers.rescan_worker.run_importer_logic",
            side_effect=Exception("Erro forçado"),
        ):
            rescan_worker.run()

        # Logger deve ser detached mesmo com exceção
        assert rescan_worker._logger_attached is False
        assert signal_collector.finished_error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
