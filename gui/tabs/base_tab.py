# gui/tabs/base_tab.py
# Base class for all tab widgets

from PyQt6.QtWidgets import QWidget, QVBoxLayout


class BaseTab(QWidget):
    """
    Base class for tab widgets in the SSA application.

    All tab implementations should inherit from this class to ensure
    consistent structure and interface.

    Usage:
        class MyTab(BaseTab):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setup_ui()

            def setup_ui(self):
                # Implement tab-specific UI here
                pass
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

    def setup_ui(self):
        """
        Setup the tab's UI components.

        This method should be overridden by subclasses to create
        the tab-specific interface.
        """
        raise NotImplementedError("Subclasses must implement setup_ui()")

    def get_layout(self):
        """
        Get the tab's main layout.

        Returns:
            QVBoxLayout: The tab's layout
        """
        return self._layout

    def on_tab_activated(self):
        """
        Called when the tab becomes active.

        Override this method to perform actions when the tab is shown
        (e.g., refresh data, update UI).
        """
        pass

    def on_tab_deactivated(self):
        """
        Called when the tab becomes inactive.

        Override this method to perform cleanup or save state
        when the tab is hidden.
        """
        pass
