# GUI Dev Variant Plan and Notes

File: `gui/novo_gui_ssa_dev.py`

- Creates a small, isolated window for API experiments without touching the main GUI.
- QThread + QObject worker with cooperative cancel and progress.
- Renders a simple table preview and raw JSON tab for diagnostics.

Next steps (optional):
- Wire this into the main GUI via a menu entry (in a separate dev branch).
- Add filters and CSV export from the dev window.
