# tests/test_caching.py
import pytest
import os
import sys
import hashlib

# Adiciona a raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from utils.caching import get_files_to_process, _calculate_hash

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
        "relatorio_b.xlsx": _calculate_hash(file_b_path)
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
        "relatorio_b.xlsx": _calculate_hash(file_b_path)
    }

    # 2. Ação
    files_to_process = get_files_to_process(temp_docs_dir, current_cache)

    # 3. Verificação: Nenhum arquivo deve ser processado.
    assert len(files_to_process) == 0
    assert not files_to_process # Outra forma de verificar se a lista está vazia


