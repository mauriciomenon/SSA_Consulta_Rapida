---
applyTo: '**/tests/**,**/*test*.py,**/pytest.ini,**/conftest.py'
description: Instrucoes para escrita e execucao de testes
---

# Testes com Pytest

## Estrutura de Testes

```
tests/
├── conftest.py          # Fixtures compartilhadas
├── test_core/           # Testes de core/
├── test_armazenamento/  # Testes de armazenamento/
├── test_extracao/       # Testes de extracao/
└── test_gui/            # Testes de gui/
```

## Convencoes

### Nomenclatura
```python
# Arquivo: test_<modulo>.py
# Funcao: test_<funcao>_<cenario>_<resultado_esperado>

def test_validar_ssa_numero_valido_retorna_true():
    ...

def test_validar_ssa_numero_invalido_levanta_excecao():
    ...
```

### Estrutura AAA (Arrange, Act, Assert)
```python
def test_exemplo():
    # Arrange - preparar dados
    entrada = {"numero": "12345"}

    # Act - executar acao
    resultado = funcao_testada(entrada)

    # Assert - verificar resultado
    assert resultado == esperado
```

## Fixtures Comuns

```python
# conftest.py

import pytest
from pathlib import Path

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Cria banco temporario para testes."""
    db_path = tmp_path / "test.db"
    # setup...
    yield db_path
    # cleanup...

@pytest.fixture
def sample_ssa() -> dict:
    """SSA de exemplo para testes."""
    return {
        "numero": "12345",
        "descricao": "Teste",
        "status": "Ativo"
    }
```

## Ferramentas MCP para Testes

### Playwright (Testes E2E de GUI)
```
- browser_navigate: Abrir aplicacao
- browser_click: Interagir com elementos
- browser_snapshot: Verificar estado
```

### Apos escrever testes
```
1. Executar: pytest tests/test_<modulo>.py -v
2. Codacy: codacy_cli_analyze no arquivo de teste
3. Coverage: pytest --cov=<modulo>
```

## Mocks e Patches

```python
from unittest.mock import Mock, patch

def test_com_mock():
    with patch('modulo.funcao_externa') as mock:
        mock.return_value = "valor_mockado"
        resultado = funcao_testada()
        assert resultado == esperado
        mock.assert_called_once()
```

## Testes Parametrizados

```python
import pytest

@pytest.mark.parametrize("entrada,esperado", [
    ("12345", True),
    ("", False),
    ("abc", False),
    ("123456789", True),
])
def test_validar_numero_ssa(entrada: str, esperado: bool):
    assert validar_numero(entrada) == esperado
```

## Markers

```python
# pytest.ini
[pytest]
markers =
    slow: testes lentos
    integration: testes de integracao
    gui: testes de interface

# Uso:
@pytest.mark.slow
def test_operacao_lenta():
    ...

# Executar apenas rapidos:
# pytest -m "not slow"
```
