"""
Configuration Manager - Sistema Centralizado de Configurações
Elimina chaves duplicadas entre arquivos de configuração.
"""

import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import os
from datetime import datetime


class ConfigurationManager:
    """
    Gerenciador centralizado de configurações.
    Elimina duplicações e inconsistências entre arquivos de config.
    """

    def __init__(self, config_dir: Union[str, Path]):
        """
        Inicializa gerenciador de configurações.

        Args:
            config_dir: Diretório com arquivos de configuração
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}
        self._merged_config: Dict[str, Any] = {}

        # Mapeamento de prioridades entre arquivos
        self._file_priority = {
            'settings.json': 100,           # Maior prioridade
            'default_settings.json': 90,
            'gui_poc_preferences.json': 80,
            'column_mappings.json': 70,
            'display_mappings.json': 60,
            'column_priority.json': 50,
            'version.json': 40             # Menor prioridade
        }

        # Configurações padrão integradas
        self._default_config = {
            # GUI Settings
            'gui': {
                'window_width': 1200,
                'window_height': 800,
                'table_max_width': 1000,
                'font_size': 10,
                'show_summary': True,
                'enable_cache': True,
                'cache_max_entries': 50,
                'auto_resize_columns': True,
                'expandable_columns': ['TITULO', 'DESCRICAO', 'OBSERVACOES']
            },

            # CLI Settings
            'cli': {
                'output_format': 'table',
                'max_width': 120,
                'show_stats': True,
                'color_output': True,
                'pagination': True,
                'page_size': 50
            },

            # Column Configuration
            'columns': {
                'priorities': {
                    'SSA': 1,
                    'TITULO': 2,
                    'STATUS': 3,
                    'PLANEJADOR': 4,
                    'PRIORIDADE': 5
                },
                'mappings': {
                    'SSA': 'SSA',
                    'TITULO': 'Título',
                    'STATUS': 'Status',
                    'PLANEJADOR': 'Planejador'
                },
                'display_formats': {
                    'SSA': {'width': 15, 'align': 'center'},
                    'TITULO': {'width': 50, 'align': 'left'},
                    'STATUS': {'width': 20, 'align': 'center'}
                },
                'min_widths': {
                    'SSA': 8,
                    'TITULO': 20,
                    'STATUS': 10,
                    'DEFAULT': 8
                }
            },

            # Export Settings
            'export': {
                'default_format': 'xlsx',
                'include_summary': True,
                'date_format': '%d/%m/%Y',
                'decimal_separator': ',',
                'encoding': 'utf-8'
            },

            # Performance Settings
            'performance': {
                'chunk_size': 1000,
                'parallel_processing': True,
                'max_memory_mb': 512,
                'cache_enabled': True,
                'preload_data': True
            },

            # Validation Settings
            'validation': {
                'required_columns': ['SSA', 'TITULO', 'STATUS'],
                'max_rows': 10000,
                'strict_mode': False,
                'auto_fix_data': True
            }
        }

        self._load_all_configs()
        self._merge_configurations()

    def _load_all_configs(self) -> None:
        """Carrega todos os arquivos de configuração."""
        if not self.config_dir.exists():
            return

        for config_file in self.config_dir.glob('*.json'):
            self._load_config_file(config_file)

    def _load_config_file(self, file_path: Path) -> None:
        """
        Carrega arquivo de configuração específico.

        Args:
            file_path: Caminho do arquivo de configuração
        """
        try:
            # Verifica se arquivo foi modificado
            current_mtime = file_path.stat().st_mtime
            file_key = file_path.name

            if (file_key in self._file_timestamps and
                self._file_timestamps[file_key] >= current_mtime):
                return  # Arquivo não foi modificado

            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self._configs[file_key] = config_data
                self._file_timestamps[file_key] = current_mtime

        except Exception as e:
            print(f"Erro ao carregar {file_path}: {e}")

    def _merge_configurations(self) -> None:
        """
        Mescla todas as configurações por prioridade.
        Elimina duplicações e conflitos.
        """
        # Inicia com configuração padrão
        merged = self._default_config.copy()

        # Ordena arquivos por prioridade (menor prioridade primeiro)
        sorted_files = sorted(
            self._configs.keys(),
            key=lambda f: self._file_priority.get(f, 0)
        )

        # Mescla configurações por prioridade
        for file_name in sorted_files:
            file_config = self._configs[file_name]
            merged = self._deep_merge(merged, file_config)

        self._merged_config = merged
        self._resolve_conflicts()

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Mescla dicionários recursivamente.

        Args:
            base: Dicionário base
            override: Dicionário para sobrescrever

        Returns:
            Dicionário mesclado
        """
        result = base.copy()

        for key, value in override.items():
            if (key in result and
                isinstance(result[key], dict) and
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _resolve_conflicts(self) -> None:
        """
        Resolve conflitos conhecidos nas configurações.
        Elimina chaves duplicadas identificadas pelo detector.
        """
        # Conflitos conhecidos do detector_frankenstein.py:
        # - max_width vs table_max_width
        # - font_size duplicado
        # - show_summary duplicado

        config = self._merged_config

        # Unifica configurações de largura
        if 'max_width' in config and 'gui' in config:
            if 'table_max_width' not in config['gui']:
                config['gui']['table_max_width'] = config.get('max_width', 1000)
            # Remove duplicata
            config.pop('max_width', None)

        # Unifica configurações de fonte
        gui_font = config.get('gui', {}).get('font_size')
        root_font = config.get('font_size')

        if gui_font and root_font and gui_font != root_font:
            # GUI tem prioridade
            config.pop('font_size', None)
        elif root_font and not gui_font:
            config.setdefault('gui', {})['font_size'] = root_font
            config.pop('font_size', None)

        # Unifica configurações de summary
        gui_summary = config.get('gui', {}).get('show_summary')
        cli_summary = config.get('cli', {}).get('show_stats')
        root_summary = config.get('show_summary')

        if root_summary is not None:
            config.setdefault('gui', {}).setdefault('show_summary', root_summary)
            config.setdefault('cli', {}).setdefault('show_stats', root_summary)
            config.pop('show_summary', None)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Recupera configuração por chave.
        Suporta notação com pontos (ex: 'gui.window_width').

        Args:
            key: Chave da configuração
            default: Valor padrão se não encontrado

        Returns:
            Valor da configuração
        """
        if '.' in key:
            return self._get_nested(key, default)

        return self._merged_config.get(key, default)

    def _get_nested(self, key: str, default: Any = None) -> Any:
        """
        Recupera configuração aninhada por notação com pontos.

        Args:
            key: Chave aninhada (ex: 'gui.window_width')
            default: Valor padrão

        Returns:
            Valor da configuração
        """
        keys = key.split('.')
        current = self._merged_config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        """
        Define configuração.

        Args:
            key: Chave da configuração
            value: Valor a definir
            persist: Se deve salvar no arquivo settings.json
        """
        if '.' in key:
            self._set_nested(key, value)
        else:
            self._merged_config[key] = value

        if persist:
            self._save_settings()

    def _set_nested(self, key: str, value: Any) -> None:
        """
        Define configuração aninhada por notação com pontos.

        Args:
            key: Chave aninhada
            value: Valor a definir
        """
        keys = key.split('.')
        current = self._merged_config

        # Navega até o penúltimo nível
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Define valor final
        current[keys[-1]] = value

    def get_gui_config(self) -> Dict[str, Any]:
        """Retorna configurações específicas da GUI."""
        return self.get('gui', {})

    def get_cli_config(self) -> Dict[str, Any]:
        """Retorna configurações específicas do CLI."""
        return self.get('cli', {})

    def get_column_config(self) -> Dict[str, Any]:
        """Retorna configurações de colunas."""
        return self.get('columns', {})

    def get_column_priorities(self) -> Dict[str, int]:
        """Retorna prioridades das colunas."""
        return self.get('columns.priorities', {})

    def get_column_mappings(self) -> Dict[str, str]:
        """Retorna mapeamentos de colunas."""
        return self.get('columns.mappings', {})

    def get_display_formats(self) -> Dict[str, Dict[str, Any]]:
        """Retorna formatos de exibição das colunas."""
        return self.get('columns.display_formats', {})

    def get_min_widths(self) -> Dict[str, int]:
        """Retorna larguras mínimas das colunas."""
        return self.get('columns.min_widths', {})

    def get_export_config(self) -> Dict[str, Any]:
        """Retorna configurações de exportação."""
        return self.get('export', {})

    def get_performance_config(self) -> Dict[str, Any]:
        """Retorna configurações de performance."""
        return self.get('performance', {})

    def get_validation_config(self) -> Dict[str, Any]:
        """Retorna configurações de validação."""
        return self.get('validation', {})

    def reload(self) -> None:
        """Recarrega todas as configurações."""
        self._configs.clear()
        self._file_timestamps.clear()
        self._load_all_configs()
        self._merge_configurations()

    def _save_settings(self) -> None:
        """Salva configurações no arquivo settings.json."""
        settings_file = self.config_dir / 'settings.json'

        try:
            # Salva apenas configurações modificáveis (não as padrão)
            save_data = {}

            for section in ['gui', 'cli', 'columns', 'export', 'performance']:
                if section in self._merged_config:
                    save_data[section] = self._merged_config[section]

            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def export_merged_config(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Exporta configuração mesclada para debugging.

        Args:
            output_path: Caminho para salvar (opcional)

        Returns:
            Configuração mesclada completa
        """
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'loaded_files': list(self._configs.keys()),
            'file_priorities': self._file_priority,
            'merged_config': self._merged_config
        }

        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Erro ao exportar configuração: {e}")

        return export_data

    def validate_config(self) -> List[str]:
        """
        Valida configuração mesclada.

        Returns:
            Lista de erros/warnings de validação
        """
        issues = []
        config = self._merged_config

        # Valida configurações da GUI
        gui_config = config.get('gui', {})
        if gui_config.get('window_width', 0) < 800:
            issues.append("GUI window_width muito pequena (mínimo 800)")

        # Valida configurações de colunas
        column_config = config.get('columns', {})
        required_cols = config.get('validation', {}).get('required_columns', [])
        priorities = column_config.get('priorities', {})

        for col in required_cols:
            if col not in priorities:
                issues.append(f"Coluna obrigatória '{col}' sem prioridade definida")

        # Valida configurações de performance
        perf_config = config.get('performance', {})
        max_memory = perf_config.get('max_memory_mb', 0)
        if max_memory > 0 and max_memory < 128:
            issues.append("max_memory_mb muito baixo (mínimo 128MB)")

        return issues

    def get_conflicts_report(self) -> Dict[str, Any]:
        """
        Gera relatório de conflitos resolvidos.

        Returns:
            Relatório detalhado de conflitos
        """
        report = {
            'duplicate_keys_found': [],
            'conflicts_resolved': [],
            'file_priority_used': self._file_priority,
            'loaded_files': list(self._configs.keys())
        }

        # Detecta chaves duplicadas entre arquivos
        all_keys = set()
        duplicate_keys = set()

        for file_name, config in self._configs.items():
            file_keys = self._get_all_keys(config)
            duplicates = all_keys.intersection(file_keys)
            duplicate_keys.update(duplicates)
            all_keys.update(file_keys)

        report['duplicate_keys_found'] = list(duplicate_keys)

        # Lista conflitos conhecidos que foram resolvidos
        report['conflicts_resolved'] = [
            'max_width vs table_max_width - GUI priority',
            'font_size duplication - GUI priority',
            'show_summary vs show_stats - Unified to both sections'
        ]

        return report

    def _get_all_keys(self, config: Dict[str, Any], prefix: str = '') -> List[str]:
        """
        Recupera todas as chaves de um dicionário aninhado.

        Args:
            config: Dicionário de configuração
            prefix: Prefixo para chaves aninhadas

        Returns:
            Lista de todas as chaves
        """
        keys = []
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)

            if isinstance(value, dict):
                keys.extend(self._get_all_keys(value, full_key))

        return keys
