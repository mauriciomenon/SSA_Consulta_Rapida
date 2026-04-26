# tests/test_caching.py
# ruff: noqa: E402
import json
import os
import sys

import pytest

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import utils.caching as caching  # noqa: E402
from utils.caching import get_all_xlsx_files  # noqa: E402
from utils.caching import _calculate_hash, get_files_to_process

# --- Fixture: Preparando o Ambiente de Teste ---


@pytest.fixture
def temp_docs_dir(tmp_path):
    """
    Fixture que cria um diretório 'docs_entrada' temporário e alguns arquivos de teste.
    """
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()

    # Cria dois arquivos de teste com conteúdo
    (docs_dir / "relatorio_a.xlsx").write_text("dados do relatorio a")
    (docs_dir / "relatorio_b.xlsx").write_text("dados do relatorio b")

    return str(docs_dir)


# --- Testes ---


def test_get_files_to_process_all_new(temp_docs_dir):
    """
    Testa o cenário onde não há cache e todos os arquivos devem ser processados.
    """
    # 1. Preparação: O cache está vazio.
    empty_cache = {}

    # 2. Ação
    files_to_process = get_files_to_process(temp_docs_dir, empty_cache)

    # 3. Verificação: Esperamos que os dois arquivos sejam identificados.
    assert len(files_to_process) == 2
    # Verificamos pelos nomes dos arquivos, não pelo caminho completo, para ser mais robusto
    filenames = [os.path.basename(f) for f in files_to_process]
    assert "relatorio_a.xlsx" in filenames
    assert "relatorio_b.xlsx" in filenames


def test_get_files_to_process_one_modified(temp_docs_dir):
    """
    Testa o cenário onde um arquivo foi modificado e deve ser reprocessado.
    """
    # 1. Preparação: Criamos um cache inicial
    file_a_path = os.path.join(temp_docs_dir, "relatorio_a.xlsx")
    file_b_path = os.path.join(temp_docs_dir, "relatorio_b.xlsx")

    initial_cache = {
        "relatorio_a.xlsx": _calculate_hash(file_a_path),
        "relatorio_b.xlsx": _calculate_hash(file_b_path),
    }

    # Modificamos o conteúdo do arquivo A
    with open(file_a_path, "w") as f:
        f.write("dados modificados do relatorio a")

    # 2. Ação
    files_to_process = get_files_to_process(temp_docs_dir, initial_cache)

    # 3. Verificação: Apenas o arquivo A deve ser processado.
    assert len(files_to_process) == 1
    assert os.path.basename(files_to_process[0]) == "relatorio_a.xlsx"


def test_get_files_to_process_no_changes(temp_docs_dir):
    """
    Testa o cenário onde não há nenhuma alteração nos arquivos.
    """
    # 1. Preparação: Criamos um cache que corresponde exatamente aos arquivos existentes.
    file_a_path = os.path.join(temp_docs_dir, "relatorio_a.xlsx")
    file_b_path = os.path.join(temp_docs_dir, "relatorio_b.xlsx")

    current_cache = {
        "relatorio_a.xlsx": _calculate_hash(file_a_path),
        "relatorio_b.xlsx": _calculate_hash(file_b_path),
    }

    # 2. Ação
    files_to_process = get_files_to_process(temp_docs_dir, current_cache)

    # 3. Verificação: Nenhum arquivo deve ser processado.
    assert len(files_to_process) == 0
    assert not files_to_process  # Outra forma de verificar se a lista está vazia


def test_get_files_to_process_skips_hash_when_metadata_unchanged(
    temp_docs_dir, monkeypatch
):
    file_a_path = os.path.join(temp_docs_dir, "relatorio_a.xlsx")
    file_b_path = os.path.join(temp_docs_dir, "relatorio_b.xlsx")

    st_a = os.stat(file_a_path)
    st_b = os.stat(file_b_path)

    cache = {
        "relatorio_a.xlsx": {
            "sha256": _calculate_hash(file_a_path),
            "size": st_a.st_size,
            "mtime_ns": st_a.st_mtime_ns,
        },
        "relatorio_b.xlsx": {
            "sha256": _calculate_hash(file_b_path),
            "size": st_b.st_size,
            "mtime_ns": st_b.st_mtime_ns,
        },
    }

    def boom(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("unexpected hash computation")

    monkeypatch.setattr(caching, "_calculate_hash", boom)

    files_to_process = get_files_to_process(temp_docs_dir, cache)
    assert files_to_process == []


def test_get_files_to_process_upgrades_legacy_cache_file(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()

    file_a = docs_dir / "relatorio_a.xlsx"
    file_b = docs_dir / "relatorio_b.xlsx"
    file_a.write_text("dados do relatorio a", encoding="utf-8")
    file_b.write_text("dados do relatorio b", encoding="utf-8")

    st_a = os.stat(str(file_a))
    st_b = os.stat(str(file_b))

    legacy_cache = {
        "relatorio_a.xlsx": caching._calculate_hash(str(file_a)),
        "relatorio_b.xlsx": caching._calculate_hash(str(file_b)),
    }
    cache_file = tmp_path / "file_cache.json"
    cache_file.write_text(json.dumps(legacy_cache, indent=4), encoding="utf-8")

    files_to_process = caching.get_files_to_process(str(docs_dir), str(cache_file))
    assert files_to_process == []

    upgraded = json.loads(cache_file.read_text(encoding="utf-8"))
    assert upgraded["relatorio_a.xlsx"]["sha256"] == legacy_cache["relatorio_a.xlsx"]
    assert upgraded["relatorio_a.xlsx"]["size"] == st_a.st_size
    assert upgraded["relatorio_a.xlsx"]["mtime_ns"] == st_a.st_mtime_ns
    assert upgraded["relatorio_b.xlsx"]["sha256"] == legacy_cache["relatorio_b.xlsx"]
    assert upgraded["relatorio_b.xlsx"]["size"] == st_b.st_size
    assert upgraded["relatorio_b.xlsx"]["mtime_ns"] == st_b.st_mtime_ns

    # Second run should not hash again when metadata matches.
    def boom(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("unexpected hash computation")

    monkeypatch.setattr(caching, "_calculate_hash", boom)

    files_to_process = caching.get_files_to_process(str(docs_dir), str(cache_file))
    assert files_to_process == []


def test_get_files_to_process_requeues_when_stat_unavailable(
    temp_docs_dir, monkeypatch
):
    def _no_stat(_path):  # noqa: ARG001
        return None

    monkeypatch.setattr(caching, "_safe_file_stat", _no_stat)
    files_to_process = get_files_to_process(temp_docs_dir, {})

    assert len(files_to_process) == 2
    filenames = {os.path.basename(path) for path in files_to_process}
    assert filenames == {"relatorio_a.xlsx", "relatorio_b.xlsx"}


def test_get_ignored_legacy_excel_files_lists_only_xls(tmp_path):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "legado_a.xls").write_text("a", encoding="utf-8")
    (docs_dir / "legado_b.xls").write_text("b", encoding="utf-8")
    (docs_dir / "legado_c.XLS").write_text("c", encoding="utf-8")
    (docs_dir / "atual.xlsx").write_text("c", encoding="utf-8")

    ignored = caching.get_ignored_legacy_excel_files(str(docs_dir))

    assert [os.path.basename(path) for path in ignored] == [
        "legado_a.xls",
        "legado_b.xls",
        "legado_c.XLS",
    ]


def test_get_all_xlsx_files_includes_processadas_and_ignores_nosurvivor(tmp_path):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    processadas = docs_dir / "processadas"
    processadas.mkdir()
    nosurvivor = processadas / "nosurvivor"
    nosurvivor.mkdir()
    other = processadas / "lote_a"
    other.mkdir()

    (docs_dir / "raiz.xlsx").write_text("a", encoding="utf-8")
    (docs_dir / "raiz_upper.XLSX").write_text("au", encoding="utf-8")
    (processadas / "proc_root.xlsx").write_text("b", encoding="utf-8")
    (processadas / "proc_root_upper.XLSX").write_text("bu", encoding="utf-8")
    (other / "proc_child.xlsx").write_text("c", encoding="utf-8")
    (nosurvivor / "ignorar.xlsx").write_text("d", encoding="utf-8")

    root_only = get_all_xlsx_files(str(docs_dir))
    assert [os.path.basename(path) for path in root_only] == [
        "raiz.xlsx",
        "raiz_upper.XLSX",
    ]

    with_processadas = get_all_xlsx_files(
        str(docs_dir),
        include_processadas=True,
        ignore_subdirs=["nosurvivor"],
    )
    names = sorted(os.path.basename(path) for path in with_processadas)
    assert names == [
        "proc_child.xlsx",
        "proc_root.xlsx",
        "proc_root_upper.XLSX",
        "raiz.xlsx",
        "raiz_upper.XLSX",
    ]


def test_update_cache_for_files_uses_relative_keys_when_docs_dir_provided(tmp_path):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    processadas = docs_dir / "processadas"
    processadas.mkdir()
    root_file = docs_dir / "dup.xlsx"
    proc_file = processadas / "dup.xlsx"
    root_file.write_text("root", encoding="utf-8")
    proc_file.write_text("proc", encoding="utf-8")

    cache_file = tmp_path / "file_cache.json"
    caching.update_cache_for_files(
        [str(root_file), str(proc_file)],
        str(cache_file),
        docs_dir=str(docs_dir),
    )
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "dup.xlsx" in data
    assert "processadas/dup.xlsx" in data
    assert data["dup.xlsx"]["sha256"] != data["processadas/dup.xlsx"]["sha256"]


def test_get_files_to_process_accepts_relative_cache_keys_for_processadas(tmp_path):
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    processadas = docs_dir / "processadas"
    processadas.mkdir()
    root_file = docs_dir / "dup.xlsx"
    proc_file = processadas / "dup.xlsx"
    root_file.write_text("root", encoding="utf-8")
    proc_file.write_text("proc", encoding="utf-8")

    cache_data = {
        "dup.xlsx": {
            "sha256": caching._calculate_hash(str(root_file)),
            "size": os.stat(root_file).st_size,
            "mtime_ns": os.stat(root_file).st_mtime_ns,
        },
        "processadas/dup.xlsx": {
            "sha256": caching._calculate_hash(str(proc_file)),
            "size": os.stat(proc_file).st_size,
            "mtime_ns": os.stat(proc_file).st_mtime_ns,
        },
    }
    files = caching.get_files_to_process(
        str(docs_dir),
        cache_data,
        include_processadas=True,
        ignore_subdirs=["nosurvivor"],
    )
    assert files == []
