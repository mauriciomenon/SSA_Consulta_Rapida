# gui/mixins/__init__.py
# Mixin classes for SSAMainWindow
#
# Padrao de nomenclatura: funcao_pai_mixin.py
# Exemplos: filter_gui_ssa_mixin.py, display_gui_ssa_mixin.py

from gui.mixins.filter_gui_ssa_mixin import FilterGUISSAMixin

# TODO: Implementar outros mixins
# from gui.mixins.display_gui_ssa_mixin import DisplayGUISSAMixin
# from gui.mixins.event_gui_ssa_mixin import EventGUISSAMixin
# from gui.mixins.theme_gui_ssa_mixin import ThemeGUISSAMixin

__all__ = [
    "FilterGUISSAMixin",
    # 'DisplayGUISSAMixin',
    # 'EventGUISSAMixin',
    # 'ThemeGUISSAMixin'
]
