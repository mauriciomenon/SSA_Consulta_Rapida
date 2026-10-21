# ruff: noqa: E402
# tests/test_extracao.py
import hashlib
import json
import os
import sys
from zipfile import ZIP_STORED, ZipFile

import pandas as pd
import pytest
from openpyxl import Workbook

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from extracao.extractor import (
    ExtractionError,
    _normalize_datatypes,
    _normalize_tempo_excedido_value,
    extract_data_from_excel,
    open_validated_excel_source,
    validate_excel_import_limits,
)

# --- Testes ---


def test_validate_excel_import_limits_keeps_original_error_of_untellable_stream():
    class _NoTellStream:
        name = "stream.xlsx"

        def tell(self):
            raise OSError("stream sem tell")

        def seek(self, *_args):
            raise AssertionError("seek nao deveria ser chamado sem posicao original")

    with pytest.raises(OSError, match="stream sem tell"):
        validate_excel_import_limits((_NoTellStream(),))


def test_normalize_tempo_excedido_minutes_with_m_suffix():
    assert _normalize_tempo_excedido_value("1h 30m") == "PT1H30M"
    assert _normalize_tempo_excedido_value("15mi") == "PT15M"


def test_normalize_tempo_excedido_months_with_mo_suffix():
    assert _normalize_tempo_excedido_value("2mo 5d") == "P2M5D"


def test_normalize_tempo_excedido_does_not_match_partial_words():
    assert _normalize_tempo_excedido_value("15minutes") == "15minutes"
    assert _normalize_tempo_excedido_value("1h30m") == "PT1H30M"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1a, 9m, 22d 5h : 47mi", "P1Y9M22DT5H47M"),
        ("3m, 2d 14h : 42mi", "P3M2DT14H42M"),
        ("1a, 2m, 3d", "P1Y2M3D"),
        ("2a, 5h : 10mi", "P2YT5H10M"),
        ("1m, 2mi", "P1MT2M"),
        ("12d 3h : 4mi", "P12DT3H4M"),
        ("45mi", "PT45M"),
        ("1H 30M", "PT1H30M"),
    ],
)
def test_normalize_tempo_excedido_keeps_years_and_months(raw, expected):
    assert _normalize_tempo_excedido_value(raw) == expected


@pytest.mark.parametrize("raw", ["1h 15minutes", "-1h", "1.5h", "cerca de 2h", "2 anos"])
def test_normalize_tempo_excedido_keeps_text_when_not_fully_recognized(raw):
    assert _normalize_tempo_excedido_value(raw) == raw


def test_extract_data_from_excel_fails_when_required_columns_missing(tmp_path):
    # Header exists, but required canonical columns are not present.
    df = pd.DataFrame(
        {
            "Nº SSA": [202500101],
            "Local": ["Sala A"],
            "Descricao sem mapeamento": ["x"],
        }
    )
    file_path = tmp_path / "missing_required.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    with pytest.raises(ExtractionError) as excinfo:
        extract_data_from_excel(str(file_path))

    assert "Missing required columns" in str(excinfo.value)


def test_extract_data_from_excel_accepts_english_api_headers(tmp_path):
    df = pd.DataFrame(
        {
            "ssa_number": [202600233],
            "description": ["API report row"],
            "issue_datetime": ["2026-01-07 13:56:00"],
            "executor_sector": ["IEE3"],
            "emitter_sector": ["MEL4"],
            "localization": ["M075A006"],
            "year_week": [202602],
        }
    )
    file_path = tmp_path / "api_headers.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    result = extract_data_from_excel(str(file_path))

    assert str(result.loc[0, "numero_ssa"]) == "202600233"
    assert result.loc[0, "descricao_ssa"] == "API report row"
    assert result.loc[0, "setor_executor"] == "IEE3"
    assert result.loc[0, "setor_emissor"] == "MEL4"
    assert "data_cadastro" in result.columns


def test_extract_data_from_excel_empty_mapping_keeps_original_columns_and_fails_required(
    tmp_path, monkeypatch
):
    # Empty mapping should keep original names and fail required canonical check.
    df = pd.DataFrame(
        {
            "Nº SSA": [202500101],
            "Emitida Em": ["01/07/2025"],
            "Descricao da SSA": ["teste"],
        }
    )
    file_path = tmp_path / "empty_mapping.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )
    with pytest.raises(ExtractionError) as excinfo:
        extract_data_from_excel(str(file_path))

    assert "Missing required columns" in str(excinfo.value)


def test_extract_data_from_excel_header_without_rows_returns_empty_dataframe(tmp_path):
    # Contract: never returns None. Header-only input returns empty DataFrame.
    df = pd.DataFrame(columns=["Nº SSA", "Descrição da SSA", "Emitida Em"])
    file_path = tmp_path / "header_only.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    extracted = extract_data_from_excel(str(file_path))
    assert isinstance(extracted, pd.DataFrame)
    assert extracted.empty


def test_extract_data_from_excel_classifies_invalid_identity_rows(
    tmp_path,
    monkeypatch,
    caplog,
):
    rows = [
        [
            "Numero da SSA",
            "Descricao da SSA",
            "Emitida Em",
            "Responsavel na Execucao",
            "Observacao",
        ],
        [202500101, "SSA valida", "01/07/2025", "TEC 1", None],
        [None, None, "02/07/2025", "TEC 2", None],
        [None, None, None, None, "   "],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "invalid_identity_rows.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Responsavel na Execucao": "responsavel_execucao",
        },
    )

    caplog.set_level("INFO")
    extracted = extract_data_from_excel(str(file_path))

    assert len(extracted) == 1
    summary = extracted.attrs["invalid_row_summary"]
    assert summary["total_removed"] == 2
    assert summary["empty_removed"] == 1
    assert summary["payload_removed"] == 1
    assert "data_cadastro" in summary["payload_columns_sample"]
    assert "responsavel_execucao" in summary["payload_columns_sample"]
    assert extracted.attrs["row_count_before_invalid_filter"] == 3
    assert (
        "Extracao - invalid_identity_rows.xlsx: removidos 2 registros invalidos sem identidade"
        in caplog.text
    )
    assert (
        "Extracao concluida para 'invalid_identity_rows.xlsx': 1 linhas validas, 2 invalidos sem identidade"
        in caplog.text
    )


@pytest.mark.parametrize(
    ("marker_column", "labels"),
    [
        ("numero_desvios", ["Desvio #1", "Desvio #2", "Desvio #3"]),
        (
            "num_reprogramacoes",
            ["Reprogramacao #1", "Reprogramacao #2", "Reprogramacao final"],
        ),
        ("parciais", ["Parcial #1", "Parcial #2", "Parcial #3"]),
    ],
)
def test_extract_data_from_excel_captures_hierarchical_continuations(
    tmp_path,
    monkeypatch,
    marker_column,
    labels,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600101, None, None, 202600102],
            "descricao_ssa": ["SSA pai", None, None, "SSA isolada"],
            "data_cadastro": ["2026-01-01 10:00:00", None, None, None],
            marker_column: [*labels, labels[0]],
            "payload_evento": ["primeiro", "segundo", "terceiro", "isolado"],
            "campo_apenas_pai": [None, None, None, "nao propagar"],
        }
    )
    file_path = tmp_path / f"hierarchical_{marker_column}_11-08-2026_0200AM.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    assert len(extracted) == 2
    summary = extracted.attrs["invalid_row_summary"]
    assert summary["total_removed"] == 0
    assert summary["payload_removed"] == 0
    assert summary["hierarchical_rows_captured"] == 2
    assert summary["hierarchical_rows_by_type"] == {marker_column: 2}
    records = extracted.attrs["ssa_event_records"]
    assert [record["record_label"] for record in records] == [*labels, labels[0]]
    assert [record["record_order"] for record in records] == [1, 2, 3, 1]
    assert [record["source_row"] for record in records] == [2, 3, 4, 5]
    assert {record["numero_ssa"] for record in records} == {
        "202600101",
        "202600102",
    }
    assert {record["arquivo_origem"] for record in records} == {file_path.name}
    assert {record["data_planilha"] for record in records} == {
        "2026-08-11T02:00:00"
    }
    assert {record["data_arquivo_origem"] for record in records} == {
        "2026-08-11 02:00:00"
    }
    assert json.loads(records[1]["payload_json"])["payload_evento"] == "segundo"
    assert all(
        "campo_apenas_pai" not in json.loads(record["payload_json"])
        for record in records
    )
    isolated_parent = extracted.loc[extracted["numero_ssa"].eq(202600102)].iloc[0]
    assert isolated_parent["campo_apenas_pai"] == "nao propagar"


@pytest.mark.parametrize(
    ("marker_column", "labels"),
    [
        (
            "Deviation Records",
            ["Deviation #1", "Deviation #2", "Deviation #3"],
        ),
        (
            "Registros de Desviacion",
            ["Desviacion #1", "Desviacion #2", "Desviacion #3"],
        ),
    ],
)
def test_extract_data_from_excel_captures_structural_hierarchy_without_alias(
    tmp_path,
    monkeypatch,
    marker_column,
    labels,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600104, None, None],
            "descricao_ssa": ["SSA pai", None, None],
            "data_cadastro": ["2026-01-01 10:00:00", None, None],
            marker_column: labels,
            "payload_evento": ["primeiro", "segundo", "terceiro"],
        }
    )
    file_path = tmp_path / f"structural_{marker_column.replace(' ', '_')}.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    assert len(extracted) == 1
    summary = extracted.attrs["invalid_row_summary"]
    assert summary["total_removed"] == 0
    assert summary["hierarchical_rows_captured"] == 2
    assert summary["hierarchical_rows_by_type"] == {marker_column: 2}
    records = extracted.attrs["ssa_event_records"]
    assert [record["record_type"] for record in records] == [marker_column] * 3
    assert [record["record_label"] for record in records] == labels
    assert [record["record_order"] for record in records] == [1, 2, 3]


def test_extract_data_from_excel_does_not_capture_unrelated_structural_footer(
    tmp_path,
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600107, None, None],
            "descricao_ssa": ["SSA pai", None, None],
            "data_cadastro": ["2026-01-01 10:00:00", None, None],
            "Deviation Records": ["Deviation #1", "Deviation #2", "TOTAL"],
            "payload_evento": ["primeiro", "segundo", "rodape"],
        }
    )
    file_path = tmp_path / "structural_footer.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    summary = extracted.attrs["invalid_row_summary"]
    assert summary["hierarchical_rows_captured"] == 1
    assert summary["payload_removed"] == 1
    assert [
        record["record_label"] for record in extracted.attrs["ssa_event_records"]
    ] == ["Deviation #1", "Deviation #2"]


def test_extract_data_from_excel_fails_on_ambiguous_structural_markers(
    tmp_path,
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600108, None],
            "descricao_ssa": ["SSA pai", None],
            "data_cadastro": ["2026-01-01 10:00:00", None],
            "Deviation Records": ["Deviation #1", "Deviation #2"],
            "Stage": ["Stage #1", "Stage #2"],
        }
    )
    file_path = tmp_path / "ambiguous_structural_markers.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    with pytest.raises(ExtractionError) as exc_info:
        extract_data_from_excel(str(file_path))

    assert exc_info.value.error_code == "AMBIGUOUS_HIERARCHICAL_MARKERS"


def test_extract_data_from_excel_fails_on_ambiguous_structural_tail(
    tmp_path,
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600109, None, None],
            "descricao_ssa": ["SSA pai", None, None],
            "data_cadastro": ["2026-01-01 10:00:00", None, None],
            "Deviation Records": [
                "Deviation #1",
                "Deviation #2",
                "Deviation final",
            ],
        }
    )
    file_path = tmp_path / "ambiguous_structural_tail.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    with pytest.raises(ExtractionError) as exc_info:
        extract_data_from_excel(str(file_path))

    assert exc_info.value.error_code == "AMBIGUOUS_HIERARCHICAL_TAIL"


def test_extract_data_from_excel_captures_canonical_first_event_without_children(
    tmp_path,
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600105],
            "descricao_ssa": ["SSA pai"],
            "data_cadastro": ["2026-01-01 10:00:00"],
            "numero_desvios": ["Desvio #1"],
            "payload_evento": ["permanece na linha pai"],
        }
    )
    file_path = tmp_path / "canonical_first_event.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    summary = extracted.attrs["invalid_row_summary"]
    assert summary["hierarchical_rows_captured"] == 0
    assert summary["hierarchical_records_captured"] == 1
    records = extracted.attrs["ssa_event_records"]
    assert [record["record_label"] for record in records] == ["Desvio #1"]
    assert json.loads(records[0]["payload_json"]) == {
        "numero_desvios": "Desvio #1"
    }
    assert extracted.iloc[0]["payload_evento"] == "permanece na linha pai"


@pytest.mark.parametrize(
    ("marker_column", "labels"),
    [
        ("numero_desvios", [1, 2]),
        ("Unknown Marker", ["Deviation #1", None]),
        ("Unknown Marker", ["Deviation #1", "Partial #2"]),
        ("Unknown Marker", ["Deviation #1", "Deviation #3"]),
    ],
)
def test_extract_data_from_excel_rejects_unproved_hierarchy(
    tmp_path,
    monkeypatch,
    marker_column,
    labels,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600106, None],
            "descricao_ssa": ["SSA pai", None],
            "data_cadastro": ["2026-01-01 10:00:00", None],
            marker_column: labels,
        }
    )
    file_path = tmp_path / "unproved_hierarchy.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    assert extracted.attrs["ssa_event_records"] == []


def test_extract_data_from_excel_uses_explicit_mapping_file(tmp_path):
    frame = pd.DataFrame(
        {
            "  ticket  ": [202600110],
            "Summary": ["SSA com mapping customizado"],
            "Created": ["2026-01-01 10:00:00"],
        }
    )
    file_path = tmp_path / "custom_mapping.xlsx"
    mapping_path = tmp_path / "mapping.json"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    mapping_path.write_text(
        json.dumps(
            {
                "numero_ssa": ["T\u00edcket"],
                "descricao_ssa": ["Summary"],
                "data_cadastro": ["Created"],
            }
        ),
        encoding="utf-8",
    )

    extracted = extract_data_from_excel(
        str(file_path),
        mappings_path=str(mapping_path),
    )

    assert extracted.loc[0, "numero_ssa"] == 202600110
    assert extracted.loc[0, "descricao_ssa"] == "SSA com mapping customizado"


def test_extract_data_from_excel_preserves_unmapped_header_without_explicit_mapping(
    tmp_path,
    monkeypatch,
):
    file_path = tmp_path / "unmapped_header.xlsx"
    pd.DataFrame(
        {
            "numero_ssa": [202600113],
            "descricao_ssa": ["SSA"],
            "data_cadastro": ["2026-01-01 10:00:00"],
            "Unmapped Payload": ["MUST_SURVIVE"],
        }
    ).to_excel(file_path, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "numero_ssa": "numero_ssa",
            "descricao_ssa": "descricao_ssa",
            "data_cadastro": "data_cadastro",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert extracted.loc[0, "Unmapped Payload"] == "MUST_SURVIVE"


def test_extract_data_from_excel_rejects_invalid_explicit_mapping(tmp_path):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600111],
            "descricao_ssa": ["SSA"],
            "data_cadastro": ["2026-01-01 10:00:00"],
        }
    )
    file_path = tmp_path / "invalid_mapping.xlsx"
    mapping_path = tmp_path / "mapping.json"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    mapping_path.write_text('{"numero_ssa": "Ticket"}', encoding="utf-8")

    with pytest.raises(ExtractionError) as exc_info:
        extract_data_from_excel(
            str(file_path),
            mappings_path=str(mapping_path),
        )

    assert exc_info.value.error_code == "INVALID_COLUMN_MAPPINGS"


@pytest.mark.parametrize(
    "invalid_mapping",
    [
        {
            "numero_ssa": ["Ticket"],
            "descricao_ssa": ["Summary"],
            "data_cadastro": ["Created"],
            "__ssa_source_sheet": ["Payload"],
        },
        {
            "numero_ssa": ["Ticket"],
            "descricao_ssa": ["Summary"],
            "data_cadastro": ["Created"],
            "campo_a": ["Shared"],
            "campo_b": [" shared "],
        },
        {
            "numero_ssa": ["Ticket"],
            "descricao_ssa": ["Summary"],
            "data_cadastro": ["Created"],
            " __SSA_SOURCE_ROW ": ["Payload"],
        },
        {
            "numero_ssa": ["Ticket"],
            "descricao_ssa": ["Summary"],
            "data_cadastro": ["Created"],
            "payload": [" __SSA_SOURCE_SHEET "],
        },
    ],
)
def test_extract_data_from_excel_rejects_unsafe_explicit_mapping(
    tmp_path,
    invalid_mapping,
):
    file_path = tmp_path / "unsafe_mapping.xlsx"
    mapping_path = tmp_path / "mapping.json"
    pd.DataFrame(
        {
            "Ticket": [202600112],
            "Summary": ["SSA"],
            "Created": ["2026-01-01 10:00:00"],
            "Payload": ["MUST_SURVIVE"],
        }
    ).to_excel(file_path, index=False)
    mapping_path.write_text(json.dumps(invalid_mapping), encoding="utf-8")

    with pytest.raises(ExtractionError) as exc_info:
        extract_data_from_excel(str(file_path), mappings_path=str(mapping_path))

    assert exc_info.value.error_code == "INVALID_COLUMN_MAPPINGS"


def test_extract_data_from_excel_does_not_link_continuation_across_sheets(
    tmp_path,
    monkeypatch,
):
    parent = pd.DataFrame(
        {
            "numero_ssa": [202600102],
            "descricao_ssa": ["SSA pai"],
            "data_cadastro": ["2026-01-01 10:00:00"],
            "numero_desvios": ["Desvio #1"],
            "payload_evento": ["primeiro"],
        }
    )
    orphan = pd.DataFrame(
        {
            "numero_ssa": [None],
            "descricao_ssa": [None],
            "data_cadastro": [None],
            "numero_desvios": ["Desvio #2"],
            "payload_evento": ["orfao"],
        }
    )
    file_path = tmp_path / "hierarchical_cross_sheet.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        parent.to_excel(writer, sheet_name="parent", index=False)
        orphan.to_excel(writer, sheet_name="orphan", index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    assert len(extracted) == 1
    summary = extracted.attrs["invalid_row_summary"]
    assert summary["payload_removed"] == 1
    assert summary["hierarchical_rows_captured"] == 0
    records = extracted.attrs["ssa_event_records"]
    assert [record["record_label"] for record in records] == ["Desvio #1"]


def test_extract_data_from_excel_does_not_link_past_description_only_parent(
    tmp_path,
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "numero_ssa": [202600103, None, None, None],
            "descricao_ssa": ["SSA numerada", None, "SSA sem numero", None],
            "data_cadastro": ["2026-01-01 10:00:00", None, None, None],
            "numero_desvios": [
                "Desvio #1",
                "Desvio #2",
                "Desvio #1",
                "Desvio #2",
            ],
            "payload_evento": ["primeiro", "segundo", "novo pai", "orfao"],
        }
    )
    file_path = tmp_path / "hierarchical_description_boundary.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {},
    )

    extracted = extract_data_from_excel(str(file_path))

    assert len(extracted) == 2
    summary = extracted.attrs["invalid_row_summary"]
    assert summary["payload_removed"] == 1
    assert summary["hierarchical_rows_captured"] == 1
    records = extracted.attrs["ssa_event_records"]
    assert [record["record_label"] for record in records] == [
        "Desvio #1",
        "Desvio #2",
    ]
    assert {record["numero_ssa"] for record in records} == {"202600103"}


def test_extract_data_from_excel_preserves_empty_required_alias_until_normalization(
    tmp_path, monkeypatch
):
    df = pd.DataFrame(
        {
            "Nº SSA": [202500101],
            "Descrição da SSA": ["SSA sem data no lote"],
            "Emitida Em": [None],
            "Local": ["Sala A"],
            "Coluna Inutil": [None],
        }
    )
    file_path = tmp_path / "empty_required_alias.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Nº SSA": "numero_ssa",
            "Descrição da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Local": "localizacao",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert str(extracted["numero_ssa"].iloc[0]) == "202500101"
    assert "data_cadastro" in extracted.columns
    assert pd.isna(extracted["data_cadastro"].iloc[0])


def test_extract_data_from_excel_handles_duplicate_header_labels_without_ambiguity(
    tmp_path, monkeypatch
):
    rows = [
        [None, "Cabecalho visual", None, None, None],
        ["Numero da SSA", "Descricao da SSA", "Emitida Em", "Desde", "Desde"],
        [202500101, "SSA duplicada", None, "01/02/2025", "02/02/2025"],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "duplicate_headers.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Desde": "desde",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert str(extracted["numero_ssa"].iloc[0]) == "202500101"
    assert "data_cadastro" in extracted.columns


def test_extract_data_from_excel_drops_nan_header_columns_safely(tmp_path, monkeypatch):
    rows = [
        [None, "Cabecalho visual", None, None, None],
        ["Numero da SSA", "Descricao da SSA", "Emitida Em", float("nan"), float("nan")],
        [202500102, "SSA com nan", None, None, None],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "nan_headers.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert str(extracted["numero_ssa"].iloc[0]) == "202500102"
    assert "data_cadastro" in extracted.columns
    assert not any(str(col).startswith("nan") for col in extracted.columns)


def test_extract_data_from_excel_aligns_distinct_aliases_across_sheets(
    tmp_path, monkeypatch
):
    sheet_a = pd.DataFrame(
        {
            "Numero da SSA": [202600201],
            "Descricao da SSA": ["Aba A"],
            "Data Cadastro": ["01/02/2026"],
        }
    )
    sheet_b = pd.DataFrame(
        {
            "Numero da SSA": [202600202],
            "Descricao da SSA": ["Aba B"],
            "Emitida Em": ["03/02/2026"],
        }
    )
    file_path = tmp_path / "aliases_por_aba.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        sheet_a.to_excel(writer, sheet_name="A", index=False)
        sheet_b.to_excel(writer, sheet_name="B", index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Data Cadastro": "data_cadastro",
            "Emitida Em": "data_cadastro",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert sorted(extracted["numero_ssa"].astype(int)) == [202600201, 202600202]
    assert extracted["data_cadastro"].notna().all()
    assert not any(str(col).startswith("data_cadastro_") for col in extracted.columns)


def test_extract_data_from_excel_skips_title_row_in_column_a(tmp_path):
    rows = [
        ["Relatorio de SSAs - exportado em 01/02/2026", None, None],
        [None, None, None],
        ["Número da SSA", "Descrição da SSA", "Emitida Em"],
        [202600601, "SSA com titulo", "01/02/2026 10:00:00"],
    ]
    file_path = tmp_path / "com_titulo.xlsx"
    pd.DataFrame(rows).to_excel(file_path, index=False, header=False)

    extracted = extract_data_from_excel(str(file_path))

    assert int(extracted["numero_ssa"].iloc[0]) == 202600601
    assert extracted["descricao_ssa"].iloc[0] == "SSA com titulo"


def test_extract_data_from_excel_production_mapping_ignores_case_accents_spaces(
    tmp_path,
):
    frame = pd.DataFrame(
        [[202600501, "SSA", "01/02/2026 10:00:00"]],
        columns=["NÚMERO DA SSA", "descricao da ssa", "  Emitida   Em "],
    )
    file_path = tmp_path / "cabecalho_variante.xlsx"
    frame.to_excel(file_path, index=False)

    extracted = extract_data_from_excel(str(file_path))

    assert int(extracted["numero_ssa"].iloc[0]) == 202600501
    assert extracted["descricao_ssa"].iloc[0] == "SSA"
    assert extracted["data_cadastro"].iloc[0] == pd.Timestamp("2026-02-01 10:00:00")


def test_extract_data_from_excel_keeps_position_of_empty_repeated_column(
    tmp_path, monkeypatch
):
    frame = pd.DataFrame(
        [
            [
                202600401,
                "SSA",
                "01/02/2026",
                "01/02/2026 10:00:00",
                None,
                "03/02/2026 09:00:00",
                "05/02/2026 08:00:00",
            ]
        ],
        columns=["Numero da SSA", "Descricao da SSA", "Emitida Em", "Desde", "Ate", "Desde", "Ate"],
    )
    file_path = tmp_path / "desde_vazio.xlsx"
    frame.to_excel(file_path, index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Desde": "desde",
            "Ate": "ate",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    row = extracted.iloc[0]
    assert str(row["desde"]).startswith("01/02/2026")
    assert pd.isna(row["ate"])
    assert str(row["desde_1"]).startswith("03/02/2026")
    assert str(row["ate_1"]).startswith("05/02/2026")


def test_extract_data_from_excel_concats_repeated_names_with_distinct_layouts(
    tmp_path, monkeypatch
):
    sheet_a = pd.DataFrame(
        [[202600301, "Aba A", "01/02/2026", "02/02/2026"]],
        columns=["Numero da SSA", "Descricao da SSA", "Data Cadastro", "Emitida Em"],
    )
    sheet_b = pd.DataFrame(
        [["03/02/2026", 202600302, "Aba B"]],
        columns=["Data Cadastro", "Numero da SSA", "Descricao da SSA"],
    )
    file_path = tmp_path / "nomes_repetidos.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        sheet_a.to_excel(writer, sheet_name="A", index=False)
        sheet_b.to_excel(writer, sheet_name="B", index=False)
    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Data Cadastro": "data_cadastro",
            "Emitida Em": "data_cadastro",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    by_ssa = extracted.set_index(extracted["numero_ssa"].astype(int))
    assert by_ssa.loc[202600301, "data_cadastro"] == pd.Timestamp("2026-02-01")
    assert by_ssa.loc[202600302, "data_cadastro"] == pd.Timestamp("2026-02-03")
    assert by_ssa.loc[202600301, "data_cadastro_1"] == "02/02/2026"


def test_extract_data_from_excel_remaps_executadas_trailing_nan_columns_to_tempo_totals(
    tmp_path, monkeypatch
):
    debug_phases: dict[str, list[str]] = {}
    rows = [
        [None, "Cabecalho visual", None, None, None, None, None],
        [
            "Numero da SSA",
            "Descricao da SSA",
            "Emitida Em",
            "Anomalia",
            float("nan"),
            float("nan"),
            float("nan"),
        ],
        [202500103, "SSA executada", "01/07/2025", "Sem anomalia", 1.5, 2.5, 3.5],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "SSAs Executadas_22-07-2025_0309PM.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Anomalia": "anomalia",
        },
    )

    extracted = extract_data_from_excel(str(file_path), _debug_phases=debug_phases)

    assert str(extracted["numero_ssa"].iloc[0]) == "202500103"
    assert debug_phases["header_raw"][-4:] == ["Anomalia", "nan", "nan", "nan"]
    assert debug_phases["after_empty_column_prune"][-4:] == [
        "Anomalia",
        "nan",
        "nan",
        "nan",
    ]
    assert debug_phases["after_rename"][-4:] == ["anomalia", "nan", "nan", "nan"]
    assert debug_phases["after_structural_repair"][-4:] == [
        "anomalia",
        "total_tempo_tpe_executada",
        "total_tempo_tex_executada",
        "total_tempo_tpo_executada",
    ]
    assert debug_phases["after_deduplicate"][-4:] == [
        "anomalia",
        "total_tempo_tpe_executada",
        "total_tempo_tex_executada",
        "total_tempo_tpo_executada",
    ]
    assert extracted["total_tempo_tpe_executada"].iloc[0] == pytest.approx(1.5)
    assert extracted["total_tempo_tex_executada"].iloc[0] == pytest.approx(2.5)
    assert extracted["total_tempo_tpo_executada"].iloc[0] == pytest.approx(3.5)
    assert not any(str(col).startswith("nan") for col in extracted.columns)


def test_extract_data_from_excel_remaps_single_numeric_tex_column_after_anomalia(
    tmp_path, monkeypatch
):
    debug_phases: dict[str, list[str]] = {}
    rows = [
        [None, "Cabecalho visual", None, None, None, None],
        [
            "Numero da SSA",
            "Descricao da SSA",
            "Emitida Em",
            "Anomalia",
            float("nan"),
            float("nan"),
        ],
        [202500104, "SSA executada tex", "01/07/2025", "Sem anomalia", None, 2.5],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "SSAs Executadas_22-07-2025_0304PM.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Anomalia": "anomalia",
        },
    )

    extracted = extract_data_from_excel(str(file_path), _debug_phases=debug_phases)

    assert str(extracted["numero_ssa"].iloc[0]) == "202500104"
    assert debug_phases["header_raw"][-3:] == ["Anomalia", "nan", "nan"]
    assert debug_phases["after_empty_column_prune"][-2:] == ["Anomalia", "nan"]
    assert debug_phases["after_rename"][-2:] == ["anomalia", "nan"]
    assert debug_phases["after_structural_repair"][-2:] == [
        "anomalia",
        "total_tempo_tex_executada",
    ]
    assert debug_phases["after_deduplicate"][-2:] == [
        "anomalia",
        "total_tempo_tex_executada",
    ]
    assert extracted["total_tempo_tex_executada"].iloc[0] == pytest.approx(2.5)
    assert "nan" not in extracted.columns


def test_extract_data_from_excel_does_not_remap_textual_unnamed_column_to_tex(
    tmp_path, monkeypatch
):
    debug_phases: dict[str, list[str]] = {}
    rows = [
        [None, "Cabecalho visual", None, None, None, None],
        [
            "Numero da SSA",
            "Descricao da SSA",
            "Emitida Em",
            "Anomalia",
            float("nan"),
            float("nan"),
        ],
        [
            202500105,
            "SSA executada texto",
            "01/07/2025",
            "Sem anomalia",
            None,
            "texto livre",
        ],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "SSAs Executadas_textual_nan.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Anomalia": "anomalia",
        },
    )

    extracted = extract_data_from_excel(str(file_path), _debug_phases=debug_phases)

    assert str(extracted["numero_ssa"].iloc[0]) == "202500105"
    assert debug_phases["after_rename"][-2:] == ["anomalia", "nan"]
    assert debug_phases["after_structural_repair"][-2:] == ["anomalia", "nan"]
    assert debug_phases["after_deduplicate"][-2:] == ["anomalia", "nan"]
    assert "total_tempo_tex_executada" not in extracted.columns
    assert "nan" in extracted.columns


def test_extract_data_from_excel_remaps_single_numeric_tex_column_when_anomalia_was_dropped(
    tmp_path, monkeypatch
):
    debug_phases: dict[str, list[str]] = {}
    rows = [
        [None, "Cabecalho visual", None, None, None, None, None, None, None, None],
        [
            "Numero da SSA",
            "Descricao da SSA",
            "Emitida Em",
            "Execucao Parcial",
            "Responsavel na Execucao",
            "Descricao Execucao",
            "Prazo Limite",
            "Sistema de Origem",
            "Anomalia",
            float("nan"),
        ],
        [
            202500106,
            "SSA tex degradada",
            "01/07/2025",
            1,
            "Tecnico",
            "Servico",
            "Dentro do Prazo",
            None,
            None,
            4.25,
        ],
    ]
    df = pd.DataFrame(rows)
    file_path = tmp_path / "SSAs Executadas_22-07-2025_0303PM (2).xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False)

    monkeypatch.setattr(
        "extracao.extractor._load_column_mappings",
        lambda _mappings_path=None: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Execucao Parcial": "execucao_parcial",
            "Responsavel na Execucao": "responsavel_execucao",
            "Descricao Execucao": "descricao_execucao",
            "Prazo Limite": "prazo_limite",
            "Sistema de Origem": "sistema_origem",
            "Anomalia": "anomalia",
        },
    )

    extracted = extract_data_from_excel(str(file_path), _debug_phases=debug_phases)

    assert str(extracted["numero_ssa"].iloc[0]) == "202500106"
    assert "Sistema de Origem" in debug_phases["header_raw"]
    assert "Anomalia" in debug_phases["header_raw"]
    assert "Sistema de Origem" not in debug_phases["after_empty_column_prune"]
    assert "Anomalia" not in debug_phases["after_empty_column_prune"]
    assert debug_phases["after_rename"][-2:] == ["prazo_limite", "nan"]
    assert debug_phases["after_structural_repair"][-2:] == [
        "prazo_limite",
        "total_tempo_tex_executada",
    ]
    assert debug_phases["after_deduplicate"][-2:] == [
        "prazo_limite",
        "total_tempo_tex_executada",
    ]
    assert extracted["total_tempo_tex_executada"].iloc[0] == pytest.approx(4.25)
    assert "nan" not in extracted.columns


def test_extract_data_from_excel_respects_cancel_callback_before_io(tmp_path):
    fake_file = tmp_path / "arquivo_que_nao_precisa_existir.xlsx"
    with pytest.raises(ExtractionError, match="operation cancelled"):
        extract_data_from_excel(
            str(fake_file),
            should_cancel=lambda: True,
        )


def test_extract_data_from_excel_cancels_during_sheet_parse(tmp_path, monkeypatch):
    file_path = tmp_path / "large.xlsx"
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet()
    sheet.append(["Nº SSA", "Descricao da SSA"])
    for row_number in range(10_000):
        sheet.append([202600000 + row_number, "Texto de teste"])
    workbook.save(file_path)
    original_digest = hashlib.sha256(file_path.read_bytes()).digest()

    parse_active = False
    parse_completed = False
    checks_during_parse = 0
    original_parse = pd.ExcelFile.parse

    def tracked_parse(self, *args, **kwargs):
        nonlocal parse_active, parse_completed
        parse_active = True
        try:
            result = original_parse(self, *args, **kwargs)
            parse_completed = True
            return result
        finally:
            parse_active = False

    def should_cancel():
        nonlocal checks_during_parse
        if parse_active:
            checks_during_parse += 1
            return True
        return False

    monkeypatch.setattr(pd.ExcelFile, "parse", tracked_parse)

    with pytest.raises(ExtractionError) as exc_info:
        extract_data_from_excel(str(file_path), should_cancel=should_cancel)

    assert exc_info.value.error_code == "OPERATION_CANCELLED"
    assert checks_during_parse >= 1
    assert parse_completed is False
    assert hashlib.sha256(file_path.read_bytes()).digest() == original_digest


def test_validate_excel_import_limits_accepts_legitimate_xlsx(tmp_path):
    file_path = tmp_path / "legitimate.xlsx"
    pd.DataFrame({"numero_ssa": [202600001]}).to_excel(file_path, index=False)

    total_bytes = validate_excel_import_limits((file_path,))

    assert total_bytes == file_path.stat().st_size


def test_validate_excel_import_limits_rejects_file_size(tmp_path, monkeypatch):
    file_path = tmp_path / "large.xlsx"
    file_path.write_bytes(b"12345")
    monkeypatch.setattr("extracao.extractor.MAX_XLSX_FILE_BYTES", 4)

    with pytest.raises(ExtractionError) as exc_info:
        validate_excel_import_limits((file_path,))

    assert exc_info.value.error_code == "FILE_TOO_LARGE"


def test_validate_excel_import_limits_rejects_batch_count(tmp_path, monkeypatch):
    file_paths = (tmp_path / "one.xlsx", tmp_path / "two.xlsx")
    for file_path in file_paths:
        file_path.write_bytes(b"x")
    monkeypatch.setattr("extracao.extractor.MAX_IMPORT_BATCH_FILES", 1)

    with pytest.raises(ExtractionError) as exc_info:
        validate_excel_import_limits(file_paths, inspect_archives=False)

    assert exc_info.value.error_code == "BATCH_FILE_LIMIT_EXCEEDED"


def test_validate_excel_import_limits_allows_trusted_full_rescan_count(
    tmp_path, monkeypatch
):
    file_paths = (tmp_path / "one.xlsx", tmp_path / "two.xlsx")
    for file_path in file_paths:
        file_path.write_bytes(b"x")
    monkeypatch.setattr("extracao.extractor.MAX_IMPORT_BATCH_FILES", 1)

    total_bytes = validate_excel_import_limits(
        file_paths,
        inspect_archives=False,
        enforce_batch_file_limit=False,
    )

    assert total_bytes == 2


def test_validate_excel_import_limits_rejects_batch_size(tmp_path, monkeypatch):
    file_paths = (tmp_path / "one.xlsx", tmp_path / "two.xlsx")
    for file_path in file_paths:
        file_path.write_bytes(b"123")
    monkeypatch.setattr("extracao.extractor.MAX_IMPORT_BATCH_BYTES", 5)

    with pytest.raises(ExtractionError) as exc_info:
        validate_excel_import_limits(file_paths, inspect_archives=False)

    assert exc_info.value.error_code == "BATCH_SIZE_LIMIT_EXCEEDED"


def test_validate_excel_import_limits_rejects_expanded_zip(tmp_path, monkeypatch):
    file_path = tmp_path / "expanded.xlsx"
    with ZipFile(file_path, "w", compression=ZIP_STORED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"x" * 6)
        archive.writestr("xl/worksheets/sheet2.xml", b"x" * 6)
    monkeypatch.setattr("extracao.extractor.MAX_XLSX_EXPANDED_BYTES", 10)

    with pytest.raises(ExtractionError) as exc_info:
        validate_excel_import_limits((file_path,))

    assert exc_info.value.error_code == "XLSX_EXPANDED_TOO_LARGE"


def test_open_validated_excel_source_keeps_validated_inode(tmp_path):
    source = tmp_path / "source.xlsx"
    replacement = tmp_path / "replacement.xlsx"
    with ZipFile(source, "w") as archive:
        archive.writestr("old.xml", b"old")
    with ZipFile(replacement, "w") as archive:
        archive.writestr("new.xml", b"new")

    with open_validated_excel_source(source) as source_stream:
        try:
            os.replace(replacement, source)
        except PermissionError:
            assert os.name == "nt"
        with ZipFile(source_stream) as archive:
            names = archive.namelist()

    assert names == ["old.xml"]


def test_normalize_datatypes_num_reprogramacoes_uses_total_when_text_legacy():
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["Teste"],
            "data_cadastro": ["01/01/2025"],
            "num_reprogramacoes": ["Reprogramacao #1"],
            "total_de_reprogramacoes": ["3"],
        }
    )

    out = _normalize_datatypes(df)

    assert str(out["num_reprogramacoes"].dtype) == "Int64"
    assert out["num_reprogramacoes"].iloc[0] == 3
    assert out["total_de_reprogramacoes"].iloc[0] == 3


def test_normalize_datatypes_num_reprogramacoes_keeps_numeric_value():
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500002"],
            "descricao_ssa": ["Teste"],
            "data_cadastro": ["02/01/2025"],
            "num_reprogramacoes": ["2"],
            "total_de_reprogramacoes": ["5"],
        }
    )

    out = _normalize_datatypes(df)

    assert str(out["num_reprogramacoes"].dtype) == "Int64"
    assert out["num_reprogramacoes"].iloc[0] == 2
    assert out["total_de_reprogramacoes"].iloc[0] == 5


def test_normalize_datatypes_num_reprogramacoes_text_without_total_becomes_null():
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500003"],
            "descricao_ssa": ["Teste"],
            "data_cadastro": ["03/01/2025"],
            "num_reprogramacoes": ["Reprogramacao #7"],
        }
    )

    out = _normalize_datatypes(df)

    assert str(out["num_reprogramacoes"].dtype) == "Int64"
    assert pd.isna(out["num_reprogramacoes"].iloc[0])
