from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from gui.ssa import gui_workers


def test_revision_fallback_invalidates_uuid_and_details_cache():
    window = SimpleNamespace(
        df_completo=pd.DataFrame({"numero_ssa": ["202600001"]}),
        _data_revision=42,
        _data_uuid="old-uuid",
        _data_revision_request_id=1,
        _details_ssa_index_sources={"old": 1},
        _details_ssa_series_index={"old": 1},
        _details_render_payload_cache={"old": 1},
    )

    def fail_after_revision(_reason):
        window._data_revision = 43
        raise RuntimeError("widget disposed")

    window._bump_data_revision = fail_after_revision

    gui_workers._sync_data_revision_after_load(window, 2)

    assert window._data_revision == 43
    assert window._data_uuid != "old-uuid"
    assert window._data_revision_request_id == 2
    assert window._data_revision_df_ids == id(window.df_completo)
    assert window._details_ssa_index_sources is None
    assert window._details_ssa_series_index is None
    assert window._details_render_payload_cache == {}


def test_partial_load_error_invalidates_new_dataframe_identity():
    class Label:
        def __init__(self):
            self.value = ""

        def setText(self, value):
            self.value = value

    window = SimpleNamespace(
        df_completo=pd.DataFrame({"numero_ssa": ["202600002"]}),
        _active_data_load_request_id=7,
        _data_load_busy=True,
        _data_revision=6,
        _data_uuid="old-uuid",
        _data_revision_request_id=6,
        status_label=Label(),
        load_button=None,
        search_button=None,
        api_button=None,
        progress_bar=None,
    )

    with patch.object(gui_workers, "refresh_database_actions"):
        gui_workers.on_load_error(window, "render failed", request_id=7, data_applied=True)

    assert window._data_revision == 7
    assert window._data_uuid != "old-uuid"
    assert window._data_revision_request_id == 7
    assert "exibicao pode estar incompleta" in window.status_label.value
