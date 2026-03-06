# ruff: noqa: E402
# tests/test_extracao.py
import pytest
import pandas as pd
import os
import sys

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from extracao.extractor import (
    ExtractionError,
    _normalize_datatypes,
    _normalize_tempo_excedido_value,
    extract_data_from_excel,
    read_report,
)

# --- Fixtures: Preparando o Ambiente de Teste ---

@pytest.fixture
def temp_excel_file(tmp_path):
    """
    Fixture que cria um arquivo Excel temporário para os testes.
    'tmp_path' é uma fixture mágica do pytest que nos dá uma pasta temporária.
    """
    # Dados de exemplo que vamos colocar no Excel
    data = {
        'Nº SSA': [202500101, 202500102],
        'Local': ['Sala A', 'Sala B'],
        'Descrição da SSA': ['Problema no servidor', 'Falha na rede'],
        'Emitida Em': ['01/07/2025', '15/07/2025'],
        'Coluna Inutil': [None, None] # Coluna que deve ser ignorada
    }
    df = pd.DataFrame(data)

    # Escreve cabecalho na primeira linha para o fluxo robust-only de read_report.
    file_path = tmp_path / "relatorio_teste.xlsx"
    writer = pd.ExcelWriter(file_path, engine='openpyxl')
    df.to_excel(writer, index=False)
    writer.close()

    return str(file_path)

@pytest.fixture
def setup_test_config(monkeypatch):
    """
    Fixture que simula o nosso arquivo de configuração, garantindo que o teste
    não dependa do arquivo real.
    'monkeypatch' é uma fixture do pytest que nos permite modificar o comportamento
    de funções, variáveis ou módulos durante os testes.
    """
    # Mapeamento de colunas de exemplo
    test_mappings = {
      "numero_ssa": ["Nº SSA"],
      "localizacao": ["Local"],
      "descricao_ssa": ["Descrição da SSA"],
      "data_cadastro": ["Emitida Em"]
    }

    # Função interna que irá substituir a _load_column_mappings original
    def mock_load_mappings():
        return {alias: canonical for canonical, aliases in test_mappings.items() for alias in aliases}

    # Diz ao pytest para usar a nossa função 'mock_load_mappings' sempre que
    # a função '_load_column_mappings' for chamada no módulo 'extractor'.
    monkeypatch.setattr('extracao.extractor._load_column_mappings', mock_load_mappings)


# --- Testes ---

def test_read_report_success(temp_excel_file, setup_test_config):
    """
    Testa o caminho feliz: ler um relatório, renomear colunas e normalizar tipos.
    Note que passamos as fixtures como argumentos para o teste.
    """
    # 1. Ação: Executa a função a ser testada com os arquivos temporários criados pelas fixtures.
    df, _ = read_report(temp_excel_file)

    # 2. Verificação
    assert df is not None
    assert not df.empty

    # Verifica colunas esperadas no fluxo robust-only.
    expected_columns = ['numero_ssa', 'local', 'descricao_ssa', 'data_cadastro']
    assert all(col in df.columns for col in expected_columns)

    # Verifica se os dados foram lidos corretamente
    assert str(df['numero_ssa'].iloc[0]) == "202500101"
    assert df['local'].iloc[1] == 'Sala B'


def test_read_report_returns_error_metadata_on_missing_file(tmp_path):
    missing_file = tmp_path / "arquivo_inexistente_12345.xlsx"
    df, metadata = read_report(str(missing_file))
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert metadata["stats_dict"]["status"] == "error"
    assert "error" in metadata["stats_dict"]


def test_normalize_tempo_excedido_minutes_with_m_suffix():
    assert _normalize_tempo_excedido_value("1h 30m") == "PT1H30M"
    assert _normalize_tempo_excedido_value("15mi") == "PT15M"


def test_normalize_tempo_excedido_months_with_mo_suffix():
    assert _normalize_tempo_excedido_value("2mo 5d") == "P2M5D"


def test_normalize_tempo_excedido_does_not_match_partial_words():
    assert _normalize_tempo_excedido_value("15minutes") == "15minutes"
    assert _normalize_tempo_excedido_value("1h30m") == "PT1H30M"


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

    monkeypatch.setattr("extracao.extractor._load_column_mappings", lambda: {})
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
        lambda: {
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
        lambda: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
            "Desde": "desde",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert str(extracted["numero_ssa"].iloc[0]) == "202500101"
    assert "data_cadastro" in extracted.columns


def test_extract_data_from_excel_drops_nan_header_columns_safely(
    tmp_path, monkeypatch
):
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
        lambda: {
            "Numero da SSA": "numero_ssa",
            "Descricao da SSA": "descricao_ssa",
            "Emitida Em": "data_cadastro",
        },
    )

    extracted = extract_data_from_excel(str(file_path))

    assert str(extracted["numero_ssa"].iloc[0]) == "202500102"
    assert "data_cadastro" in extracted.columns
    assert not any(str(col).startswith("nan") for col in extracted.columns)


def test_extract_data_from_excel_respects_cancel_callback_before_io(tmp_path):
    fake_file = tmp_path / "arquivo_que_nao_precisa_existir.xlsx"
    with pytest.raises(ExtractionError, match="operation cancelled"):
        extract_data_from_excel(
            str(fake_file),
            should_cancel=lambda: True,
        )


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
