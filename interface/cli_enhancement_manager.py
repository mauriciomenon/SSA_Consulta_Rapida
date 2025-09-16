"""
CLI Enhancement Integration - Integra melhorias na CLI existente
Permite ativar/desativar enhanced table printer facilmente.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

class CLIEnhancementManager:
    """
    Gerencia a integração das melhorias na CLI.
    """

    def __init__(self):
        """Inicializa o gerenciador de melhorias."""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.settings_file = os.path.join(self.project_root, 'config', 'cli_enhancements.json')
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Carrega configurações das melhorias CLI."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar configurações CLI: {e}")

        # Configurações padrão
        return {
            "enhanced_table_printer": True,
            "unified_column_config": True,
            "improved_ssa_normalization": True,
            "word_wrap_in_cli": True,
            "debug_output": False,
            "version": "1.0"
        }

    def _save_settings(self):
        """Salva configurações das melhorias."""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar configurações CLI: {e}")

    def is_enhanced_printer_enabled(self) -> bool:
        """Verifica se enhanced table printer está habilitado."""
        return self.settings.get("enhanced_table_printer", True)

    def is_unified_config_enabled(self) -> bool:
        """Verifica se configuração unificada está habilitada."""
        return self.settings.get("unified_column_config", True)

    def is_debug_enabled(self) -> bool:
        """Verifica se debug está habilitado."""
        return self.settings.get("debug_output", False)

    def enable_enhanced_printer(self):
        """Habilita enhanced table printer."""
        self.settings["enhanced_table_printer"] = True
        self._save_settings()

    def disable_enhanced_printer(self):
        """Desabilita enhanced table printer."""
        self.settings["enhanced_table_printer"] = False
        self._save_settings()

    def toggle_debug(self):
        """Alterna modo debug."""
        self.settings["debug_output"] = not self.settings.get("debug_output", False)
        self._save_settings()
        return self.settings["debug_output"]

    def get_status_report(self) -> str:
        """Retorna relatório do status das melhorias."""
        status = []
        status.append("📊 STATUS DAS MELHORIAS CLI")
        status.append("=" * 40)

        enhanced = "✅ ATIVO" if self.is_enhanced_printer_enabled() else "❌ INATIVO"
        status.append(f"Enhanced Table Printer: {enhanced}")

        unified = "✅ ATIVO" if self.is_unified_config_enabled() else "❌ INATIVO"
        status.append(f"Configuração Unificada: {unified}")

        debug = "✅ ATIVO" if self.is_debug_enabled() else "❌ INATIVO"
        status.append(f"Debug Output: {debug}")

        status.append("")
        status.append("🔧 MELHORIAS IMPLEMENTADAS:")
        status.append("• Larguras fixas determinísticas (como GUI)")
        status.append("• Sistema de crescimento proporcional 50/50")
        status.append("• Normalização correta de números SSA")
        status.append("• Configuração unificada GUI/CLI")
        status.append("• Word wrap inteligente para descrições")
        status.append("• Seleção otimizada de colunas")

        version = self.settings.get("version", "1.0")
        status.append(f"")
        status.append(f"Versão das melhorias: {version}")

        return "\n".join(status)

# Instância global
enhancement_manager = CLIEnhancementManager()

def print_cli_enhancements_status():
    """Função de conveniência para imprimir status."""
    print(enhancement_manager.get_status_report())

def toggle_cli_debug():
    """Função de conveniência para alternar debug."""
    new_state = enhancement_manager.toggle_debug()
    state_str = "ATIVADO" if new_state else "DESATIVADO"
    print(f"Debug CLI {state_str}")
    return new_state
