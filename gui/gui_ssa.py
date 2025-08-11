"""
DEPRECATED: Este protótipo de GUI está obsoleto. Use gui/app_gui.py.

Este arquivo permanece no repositório apenas como referência histórica. Para
interface gráfica, utilize AppGuiWindow em gui/app_gui.py, que usa a lógica
centralizada de core.app_logic.
"""

import warnings
warnings.warn(
    "gui.gui_ssa está DEPRECIADO. Use gui.app_gui.AppGuiWindow.",
    DeprecationWarning,
    stacklevel=2,
)

# Impede uso acidental em produção
raise ImportError("Modulo depreciado: gui.gui_ssa. Use gui.app_gui.AppGuiWindow")