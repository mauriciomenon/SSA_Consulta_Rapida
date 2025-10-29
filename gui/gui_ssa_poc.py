"""
# ==============================================================================
# COMPATIBILITY SHIM - DEPRECATION CANDIDATE
# ==============================================================================
# Status: Compatibility layer for legacy code
# Created: Unknown (shim for legacy.gui_ssa_poc)
# Last modified: 2025-10-29T12:10:00 (documented deprecation)
# Purpose: Different purpose from main GUI (quick queries/PoC)
# Recommendation: Keep if still used, document deprecation path
#
# Compat layer para GUI PoC legada.
#
# O módulo original muito extenso foi movido para ``legacy.gui_ssa_poc`` para
# reduzir ruído de lint e permitir evolução independente.
#
# ATENÇÃO: Atualize seus imports para usar diretamente:
#     from legacy.gui_ssa_poc import <Simbolo>
#
# Este arquivo será removido em uma versão futura.
"""
from __future__ import annotations

from legacy.gui_ssa_poc import *  # type: ignore  # noqa: F401,F403

# Exporta símbolos não internos (lista dinâmica removida para evitar warning do analisador).
# Se for necessário limitar, importe explicitamente no projeto consumidor.
__all__ = []  # shim não declara explicitamente; re-export wildcard.

# Nenhuma lógica adicional aqui – use legacy.gui_ssa_poc diretamente.
