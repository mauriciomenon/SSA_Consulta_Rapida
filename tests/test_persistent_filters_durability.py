"""G-30: filtros salvos chegam ao disco (fsync) antes de substituir o arquivo."""

import json

from gui.ssa import persistent_filters


def test_save_persistent_filters_fsyncs_before_replace(tmp_path, monkeypatch):
    events = []
    real_fsync = persistent_filters.os.fsync
    real_replace = persistent_filters._replace_private_json_file

    def spy_fsync(fd):
        events.append("fsync")
        real_fsync(fd)

    def spy_replace(source, target):
        events.append("replace")
        real_replace(source, target)

    monkeypatch.setattr(persistent_filters.os, "fsync", spy_fsync)
    monkeypatch.setattr(persistent_filters, "_replace_private_json_file", spy_replace)
    path = tmp_path / "gui_saved_filters.json"

    assert persistent_filters.save_persistent_filters_file(
        str(path), [{"name": "abertas", "terms": "!=ste"}]
    )

    assert events[:2] == ["fsync", "replace"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["filters"] == [{"name": "abertas", "terms": "!=ste"}]
