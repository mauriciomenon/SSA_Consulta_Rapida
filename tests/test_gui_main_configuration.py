"""
Testes para o sistema de configuracao isolado da GUI Principal (main.py --gui)
Valida carregamento, estrutura e isolamento das configuracoes.
"""

import importlib
import json
import os
import sys
from unittest.mock import mock_open, patch

import pytest

# Adiciona o projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestGUIMainConfiguration:
    """Testes para o sistema de configuracao da GUI Principal."""

    def test_gui_main_preferences_contract_available_without_file(self):
        """Contrato de configuracao deve existir mesmo sem arquivo local versionado."""
        from gui.gui_config import load_gui_main_preferences

        with patch("gui.gui_config.os.path.exists", return_value=False):
            config = load_gui_main_preferences()

        assert "display_columns" in config
        assert "column_display_names" in config
        assert "display_mappings" in config
        assert "column_widths" in config

    def test_load_gui_main_preferences_structure(self):
        """Testa se a funcao de carregamento funciona e estrutura e valida."""
        from gui.gui_config import load_gui_main_preferences

        config = load_gui_main_preferences()

        assert "display_columns" in config
        assert "column_display_names" in config
        assert "display_mappings" in config
        assert "column_widths" in config
        assert "gui_settings" in config
        assert isinstance(config["display_columns"], list)
        assert isinstance(config["column_display_names"], dict)
        assert isinstance(config["display_mappings"], dict)
        assert isinstance(config["column_widths"], dict)
        assert isinstance(config["gui_settings"], dict)

    def test_load_gui_main_preferences_fallback(self):
        """Testa fallback quando arquivo nao existe."""
        from gui.gui_config import load_gui_main_preferences

        with patch("gui.gui_config.os.path.exists", return_value=False):
            config = load_gui_main_preferences()
            assert "display_columns" in config
            assert len(config["display_columns"]) > 0
            assert "numero_ssa" in config["display_columns"]
            assert "derivada_de" in config["display_columns"]
            assert config["version"] == "1.0.0"

    def test_load_gui_main_preferences_honors_ssa_config_dir(
        self, tmp_path, monkeypatch
    ):
        """GUI config deve respeitar SSA_CONFIG_DIR ao resolver gui_main_preferences.json."""
        from gui.gui_config import load_gui_main_preferences

        cfg_dir = tmp_path / "cfg_gui"
        cfg_dir.mkdir()
        cfg_file = cfg_dir / "gui_main_preferences.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "display_columns": ["numero_ssa", "situacao"],
                    "column_display_names": {"numero_ssa": "No SSA"},
                    "column_widths": {"numero_ssa": 99},
                    "gui_settings": {"page_size": 77},
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

        config = load_gui_main_preferences()

        assert config["gui_settings"]["page_size"] == 77
        assert config["column_widths"]["numero_ssa"] == 99
        assert config["column_display_names"]["numero_ssa"] == "No SSA"

    def test_load_gui_main_preferences_with_missing_ssa_config_dir_uses_defaults(
        self, tmp_path, monkeypatch
    ):
        """Quando SSA_CONFIG_DIR aponta para pasta ausente, contrato default deve permanecer estavel."""
        from gui.gui_config import load_gui_main_preferences

        missing_dir = tmp_path / "cfg_missing"
        monkeypatch.setenv("SSA_CONFIG_DIR", str(missing_dir))

        config = load_gui_main_preferences()

        assert "display_columns" in config
        assert "numero_ssa" in config["display_columns"]
        assert "column_display_names" in config
        assert "numero_ssa" in config["column_display_names"]

    def test_get_gui_main_preferences_path_reflects_runtime_env_change(
        self, tmp_path, monkeypatch
    ):
        from gui import gui_config

        cfg_dir = tmp_path / "cfg_runtime"
        cfg_dir.mkdir()
        monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))

        resolved = gui_config.get_gui_main_preferences_path()

        assert resolved.endswith("gui_main_preferences.json")
        assert str(cfg_dir) in resolved

    def test_load_gui_main_preferences_explicit_path_has_precedence_over_env(
        self, tmp_path, monkeypatch
    ):
        from gui.gui_config import load_gui_main_preferences

        cfg_dir_env = tmp_path / "cfg_env"
        cfg_dir_env.mkdir()
        monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir_env))

        explicit_path = tmp_path / "explicit_gui_main_preferences.json"
        explicit_path.write_text(
            json.dumps(
                {
                    "display_columns": ["numero_ssa", "situacao"],
                    "column_display_names": {"numero_ssa": "Numero Expl"},
                    "column_widths": {"numero_ssa": 88},
                    "gui_settings": {"page_size": 33},
                }
            ),
            encoding="utf-8",
        )

        config = load_gui_main_preferences(config_path=str(explicit_path))

        assert config["column_display_names"]["numero_ssa"] == "Numero Expl"
        assert config["column_widths"]["numero_ssa"] == 88
        assert config["gui_settings"]["page_size"] == 33

    def test_load_gui_main_preferences_invalid_json(self):
        """Testa comportamento com JSON invalido."""
        from gui.gui_config import load_gui_main_preferences

        with patch("gui.gui_config.open", mock_open(read_data="invalid json")):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()
                assert "display_columns" in config
                assert config["version"] == "1.0.0"

    def test_load_gui_main_preferences_invalid_structure_uses_platform_defaults(self):
        from gui.gui_config import load_gui_main_preferences

        with patch("gui.gui_config.open", mock_open(read_data='["bad"]')):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                with patch("gui.gui_config.sys.platform", "darwin"):
                    config = load_gui_main_preferences()

        assert config["column_widths"]["descricao_ssa"] == 420
        assert config["column_widths"]["semana_cadastro"] == 74

    def test_load_gui_main_preferences_invalid_integrity_uses_platform_defaults(self):
        invalid_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {},
            "column_widths": {},
            "column_widths_by_platform": [],
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(invalid_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                with patch("gui.gui_config.sys.platform", "darwin"):
                    config = load_gui_main_preferences()

        assert config["column_widths"]["descricao_ssa"] == 420
        assert config["column_widths"]["semana_cadastro"] == 74

    def test_partial_config_is_merged_with_contract(self):
        """JSON parcial deve preservar contrato minimo de colunas e mapeamentos."""
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {"numero_ssa": "No SSA"},
            "column_widths": {"numero_ssa": 10},
            "gui_settings": {"page_size": 25},
        }

        from gui.gui_config import REQUIRED_DISPLAY_COLUMNS, load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        for required in REQUIRED_DISPLAY_COLUMNS:
            assert required in config["display_columns"]
            assert required in config["column_display_names"]
            assert required in config["display_mappings"]

        assert config["column_display_names"]["numero_ssa"] == "No SSA"
        assert config["gui_settings"]["page_size"] == 25
        assert config["column_widths"]["numero_ssa"] == 10

    def test_load_gui_main_preferences_migrates_managed_legacy_widths(self):
        from gui.gui_config import (
            DEFAULT_COLUMN_WIDTHS_BY_PLATFORM,
            get_default_column_widths,
            load_gui_main_preferences,
        )

        legacy_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {"numero_ssa": "No SSA"},
            "column_widths": {
                "data_cadastro": 95,
                "grau_prioridade_emissao": DEFAULT_COLUMN_WIDTHS_BY_PLATFORM["linux"][
                    "grau_prioridade_emissao"
                ],
                "grau_prioridade_planejamento": DEFAULT_COLUMN_WIDTHS_BY_PLATFORM[
                    "linux"
                ]["grau_prioridade_planejamento"],
                "total_de_reprogramacoes": DEFAULT_COLUMN_WIDTHS_BY_PLATFORM[
                    "linux"
                ]["total_de_reprogramacoes"],
                "execucao_parcial": DEFAULT_COLUMN_WIDTHS_BY_PLATFORM["linux"][
                    "execucao_parcial"
                ],
                "semana_executada": DEFAULT_COLUMN_WIDTHS_BY_PLATFORM["linux"][
                    "semana_executada"
                ],
                "responsavel_execucao": 150,
            },
            "gui_settings": {"page_size": 25},
        }

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(legacy_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                with patch("gui.gui_config.sys.platform", "darwin"):
                    config = load_gui_main_preferences()
                    runtime_widths = get_default_column_widths(platform_name="darwin")

        assert config["column_widths"]["data_cadastro"] == 95
        assert (
            config["column_widths"]["grau_prioridade_emissao"]
            == runtime_widths["grau_prioridade_emissao"]
        )
        assert (
            config["column_widths"]["grau_prioridade_planejamento"]
            == runtime_widths["grau_prioridade_planejamento"]
        )
        assert (
            config["column_widths"]["total_de_reprogramacoes"]
            == runtime_widths["total_de_reprogramacoes"]
        )
        assert (
            config["column_widths"]["execucao_parcial"]
            == runtime_widths["execucao_parcial"]
        )
        assert (
            config["column_widths"]["semana_executada"]
            == runtime_widths["semana_executada"]
        )
        assert (
            config["column_widths"]["responsavel_execucao"]
            == runtime_widths["responsavel_execucao"]
        )

    def test_load_gui_main_preferences_preserves_explicit_hidden_required_columns(self):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "hidden_columns": [
                "grau_prioridade_emissao",
                "execucao_parcial",
                "responsavel_execucao",
            ],
            "column_display_names": {},
            "column_widths": {},
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        assert "grau_prioridade_emissao" not in config["display_columns"]
        assert "execucao_parcial" not in config["display_columns"]
        assert "responsavel_execucao" not in config["display_columns"]
        assert "grau_prioridade_emissao" in config["hidden_columns"]
        assert "execucao_parcial" in config["hidden_columns"]
        assert "responsavel_execucao" in config["hidden_columns"]

    def test_load_gui_main_preferences_prioritizes_display_columns_over_hidden_overlap(
        self,
    ):
        partial_config = {
            "display_columns": ["situacao", "numero_ssa", "descricao_ssa"],
            "hidden_columns": ["numero_ssa", "descricao_ssa", "equipamento"],
            "column_display_names": {},
            "column_widths": {},
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        assert config["display_columns"][:3] == [
            "situacao",
            "numero_ssa",
            "descricao_ssa",
        ]
        assert "numero_ssa" not in config["hidden_columns"]
        assert "descricao_ssa" not in config["hidden_columns"]
        assert "equipamento" in config["hidden_columns"]

    def test_load_gui_main_preferences_preserves_explicit_data_arquivo_width(self):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao", "data_arquivo_origem"],
            "column_display_names": {},
            "column_widths": {"data_arquivo_origem": 100},
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        assert config["column_widths"]["data_arquivo_origem"] == 100

    @staticmethod
    def test_migrate_managed_legacy_widths_skips_missing_target_width():
        from gui.gui_config import (
            HARD_DEFAULT_GUI_MAIN_PREFERENCES,
            _migrate_managed_legacy_widths,
        )

        legacy_width = HARD_DEFAULT_GUI_MAIN_PREFERENCES["column_widths"][
            "descricao_ssa"
        ]

        migrated = _migrate_managed_legacy_widths(
            {"descricao_ssa": legacy_width},
            {},
        )

        assert migrated["descricao_ssa"] == legacy_width

    def test_load_gui_main_preferences_uses_platform_specific_widths(self):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {},
            "column_widths": {"descricao_ssa": 999},
            "column_widths_by_platform": {
                "darwin": {"descricao_ssa": 340},
                "win32": {"descricao_ssa": 340},
                "linux": {"descricao_ssa": 298},
            },
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                with patch("gui.gui_config.sys.platform", "darwin"):
                    darwin_config = load_gui_main_preferences()
                with patch("gui.gui_config.sys.platform", "win32"):
                    win_config = load_gui_main_preferences()
                with patch("gui.gui_config.sys.platform", "linux"):
                    linux_config = load_gui_main_preferences()

        assert darwin_config["column_widths"]["descricao_ssa"] == 340
        assert win_config["column_widths"]["descricao_ssa"] == 340
        assert linux_config["column_widths"]["descricao_ssa"] == 298

    def test_load_gui_main_preferences_falls_back_to_generic_widths_without_platform_map(
        self,
    ):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {},
            "column_widths": {"descricao_ssa": 333},
            "gui_settings": {},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                with patch("gui.gui_config.sys.platform", "darwin"):
                    config = load_gui_main_preferences()

        assert config["column_widths"]["descricao_ssa"] == 333

    def test_load_gui_main_preferences_preserves_valid_table_cell_alignment(self):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {},
            "column_widths": {},
            "gui_settings": {"table_cell_alignment": "right"},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        assert config["gui_settings"]["table_cell_alignment"] == "right"

    def test_load_gui_main_preferences_invalid_table_cell_alignment_falls_back_to_right(
        self,
    ):
        partial_config = {
            "display_columns": ["numero_ssa", "situacao"],
            "column_display_names": {},
            "column_widths": {},
            "gui_settings": {"table_cell_alignment": "diagonal"},
        }

        from gui.gui_config import load_gui_main_preferences

        with patch(
            "gui.gui_config.open", mock_open(read_data=json.dumps(partial_config))
        ):
            with patch("gui.gui_config.os.path.exists", return_value=True):
                config = load_gui_main_preferences()

        assert config["gui_settings"]["table_cell_alignment"] == "right"

    def test_load_gui_main_preferences_auto_create_uses_code_defaults(
        self, tmp_path, monkeypatch
    ):
        from gui import gui_config
        from gui.gui_config import DEFAULT_GUI_MAIN_PREFERENCES

        cfg_dir = tmp_path / "cfg_runtime"
        cfg_dir.mkdir()
        template_path = tmp_path / "gui_main_preferences.json.example"
        template_path.write_text(
            json.dumps(
                {
                    "display_columns": ["numero_ssa", "situacao", "setor_executor"],
                    "hidden_columns": ["descricao_localizacao"],
                    "column_display_names": {
                        "numero_ssa": "Numero SSA",
                        "situacao": "Sit.",
                        "setor_executor": "Exec.",
                    },
                    "display_mappings": {
                        "numero_ssa": "Numero SSA",
                        "situacao": "Sit.",
                        "setor_executor": "Exec.",
                    },
                    "column_widths": {"numero_ssa": 111, "situacao": 55},
                    "gui_settings": {"page_size": 99},
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("SSA_CONFIG_DIR", str(cfg_dir))
        monkeypatch.setattr(
            gui_config,
            "get_gui_main_preferences_template_path",
            lambda: str(template_path),
        )

        config = gui_config.load_gui_main_preferences(auto_create=True)
        created_path = cfg_dir / "gui_main_preferences.json"
        created = json.loads(created_path.read_text(encoding="utf-8"))

        assert created_path.exists()
        assert (
            created["column_widths"]["numero_ssa"]
            == DEFAULT_GUI_MAIN_PREFERENCES["column_widths"]["numero_ssa"]
        )
        assert (
            created["gui_settings"]["page_size"]
            == DEFAULT_GUI_MAIN_PREFERENCES["gui_settings"]["page_size"]
        )
        assert (
            config["column_widths"]["numero_ssa"]
            == DEFAULT_GUI_MAIN_PREFERENCES["column_widths"]["numero_ssa"]
        )
        assert (
            config["gui_settings"]["page_size"]
            == DEFAULT_GUI_MAIN_PREFERENCES["gui_settings"]["page_size"]
        )

    def test_load_gui_main_preferences_auto_create_writes_platform_widths(
        self, tmp_path
    ):
        from gui import gui_config

        config_path = tmp_path / "gui_main_preferences.json"

        with patch("gui.gui_config.sys.platform", "darwin"):
            config = gui_config.load_gui_main_preferences(
                config_path=str(config_path), auto_create=True
            )

        created = json.loads(config_path.read_text(encoding="utf-8"))

        assert created["column_widths"]["descricao_ssa"] == 420
        assert created["column_widths"]["semana_cadastro"] == 74
        assert created["column_widths"]["semana_executada"] == 60
        assert config["column_widths"]["descricao_ssa"] == 420

    def test_gui_main_preferences_reference_file_matches_code_defaults(self):
        from gui.gui_config import (
            DEFAULT_GUI_MAIN_PREFERENCES,
            get_gui_main_preferences_template_path,
        )

        with open(
            get_gui_main_preferences_template_path(), "r", encoding="utf-8"
        ) as fh:
            reference_payload = json.load(fh)

        assert reference_payload == DEFAULT_GUI_MAIN_PREFERENCES

    def test_gui_main_preferences_isolation_from_cli(self):
        """Verifica que as configuracoes sao independentes do CLI."""
        from core.config_manager import load_settings
        from gui.gui_config import GUI_MAIN_PREFERENCES

        try:
            cli_settings = load_settings()
        except Exception:
            cli_settings = {}

        assert GUI_MAIN_PREFERENCES != cli_settings
        assert "display_columns" in GUI_MAIN_PREFERENCES
        assert "created_for" in GUI_MAIN_PREFERENCES
        assert GUI_MAIN_PREFERENCES["created_for"] == "GUI Main (main.py --gui)"

    def test_column_display_names_mapping(self):
        """Testa mapeamento de nomes de colunas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        names = GUI_MAIN_PREFERENCES.get("column_display_names", {})
        assert isinstance(names, dict)
        assert "numero_ssa" in names
        assert isinstance(names["numero_ssa"], str)
        assert names["numero_ssa"].strip()

    def test_column_widths_configuration(self):
        """Testa configuracao de larguras de colunas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        widths = GUI_MAIN_PREFERENCES.get("column_widths", {})
        assert isinstance(widths, dict)
        assert "numero_ssa" in widths
        assert isinstance(widths["numero_ssa"], int)
        assert widths["numero_ssa"] > 0

    def test_gui_settings_validation(self):
        """Testa configuracoes especificas da GUI."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        settings = GUI_MAIN_PREFERENCES.get("gui_settings", {})
        assert isinstance(settings, dict)
        assert "page_size" in settings
        assert "debounce_delay" in settings
        assert "default_filter_mode" in settings
        assert "table_cell_alignment" in settings
        assert isinstance(settings["page_size"], int)
        assert settings["page_size"] > 0
        assert settings["table_cell_alignment"] == "right"

    def test_display_columns_validation(self):
        """Testa lista de colunas de exibicao."""
        from gui.gui_config import GUI_MAIN_PREFERENCES, REQUIRED_DISPLAY_COLUMNS

        columns = GUI_MAIN_PREFERENCES.get("display_columns", [])
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert "numero_ssa" in columns
        assert len(columns) == len(set(columns))
        for required in REQUIRED_DISPLAY_COLUMNS:
            assert required in columns

    def test_hidden_columns_validation(self):
        """Testa lista de colunas ocultas."""
        from gui.gui_config import GUI_MAIN_PREFERENCES

        hidden = GUI_MAIN_PREFERENCES.get("hidden_columns", [])
        display = GUI_MAIN_PREFERENCES.get("display_columns", [])

        assert isinstance(hidden, list)
        for col in hidden:
            assert col not in display

    def test_gui_main_import_independence(self):
        """Testa que GUI Main pode ser importada sem dependencias do CLI."""
        modules_to_restore = {}
        for module_name in list(sys.modules):
            if (
                module_name == "gui"
                or module_name.startswith("gui.gui_config")
                or module_name.startswith("core.config_manager")
            ):
                modules_to_restore[module_name] = sys.modules[module_name]
                del sys.modules[module_name]

        try:
            importlib.invalidate_caches()
            gui_config = importlib.import_module("gui.gui_config")
            GUI_MAIN_PREFERENCES = gui_config.GUI_MAIN_PREFERENCES
            load_gui_main_preferences = gui_config.load_gui_main_preferences

            assert isinstance(GUI_MAIN_PREFERENCES, dict)
            assert callable(load_gui_main_preferences)
        except ImportError as e:
            pytest.fail(f"GUI Main nao deveria depender de modulos do CLI: {e}")
        finally:
            for module_name in sorted(
                modules_to_restore.keys(), key=lambda item: item.count(".")
            ):
                module_obj = modules_to_restore[module_name]
                sys.modules[module_name] = module_obj


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
