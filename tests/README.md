# Suite de Testes - SSA Consulta Rápida

## Visão Geral

Esta pasta contém a suite completa de testes do projeto SSA Consulta Rápida, com **669 testes** cobrindo:
- Workers assíncronos
- Cache e performance
- GUI e interface
- Importação de dados
- Banco de dados SQLite
- Lógica de filtragem
- Exportação de dados

## Estrutura de Testes

```
tests/
├── README.md                          # Este arquivo
├── conftest.py                        # Fixtures e configuração pytest
├── test_*.py                          # Testes unitários e de integração
│
├── test_workers_*.py                  # Workers assíncronos
│   ├── test_data_loader_worker.py     # DataLoaderWorker (9 testes)
│   ├── test_filter_worker.py          # FilterWorker (8 testes)
│   ├── test_workers_advanced.py       # Testes avançados (35 testes)
│   └── test_rescan_worker.py          # RescanWorker (novo)
│
├── test_gui_*.py                      # Testes da interface gráfica
│   ├── test_gui_workers_*.py          # Workers da GUI
│   ├── test_gui_filter_*.py           # Filtros da GUI
│   └── test_gui_table_*.py            # Renderização de tabela
│
├── test_import_*.py                   # Importação de dados
│   ├── test_import_cache_integrity.py
│   ├── test_import_detailed.py
│   └── test_import_dtypes.py
│
├── test_database_*.py                 # Banco de dados
│   ├── test_database.py
│   ├── test_database_optimized_*.py
│   └── test_derivadas_*.py
│
├── test_filter_*.py                   # Lógica de filtragem
│   ├── test_filter.py
│   ├── test_filter_cache_locking.py
│   └── test_filter_modes.py
│
├── test_cli_*.py                      # Interface de linha de comando
│   ├── test_cli_column_selection.py
│   └── test_cli_config_preserve_session.py
│
├── test_cache_*.py                    # Cache e performance
│   └── test_caching_atomic_save.py
│
└── _helpers/                          # Helpers e utilitários
    ├── db_utils.py
    └── dtypes_matrix.py
```

## Executando Testes

### Usando o venv do projeto

```bash
# Ativar ambiente
source .venv/bin/activate

# Executar todos os testes
python -m pytest tests/ -v

# Executar com cobertura
python -m pytest tests/ --cov=. --cov-report=html

# Executar testes específicos
python -m pytest tests/test_workers_advanced.py -v
python -m pytest tests/test_data_loader_worker.py -v
python -m pytest tests/test_filter_worker.py -v
```

### Usando uv

```bash
# Executar todos os testes
uv run pytest tests/ -v

# Executar categoria específica
uv run pytest tests/test_workers_*.py -v
uv run pytest tests/test_gui_*.py -v
uv run pytest tests/test_import_*.py -v
uv run pytest tests/test_database_*.py -v
```

## Categorias de Testes

### 1. Workers (52 testes)

Testes para workers assíncronos PyQt6:

- **DataLoaderWorker**: Carregamento de dados SQLite
- **FilterWorker**: Filtragem com cache LRU
- **RescanWorker**: Reescaneamento de dados

```bash
# Executar todos os testes de workers
python -m pytest tests/test_*worker*.py -v
```

### 2. GUI (45+ testes)

Testes para interface gráfica PyQt6:

- Renderização de tabela
- Filtros avançados
- Paginação
- Workers da GUI
- Configurações

```bash
# Executar testes de GUI
python -m pytest tests/test_gui_*.py -v
```

### 3. Importação (30+ testes)

Testes para importação de dados Excel:

- Detecção de formato
- Cache de integridade
- Tipos de dados
- Triggers de derivadas

```bash
# Executar testes de importação
python -m pytest tests/test_import_*.py -v
```

### 4. Banco de Dados (25+ testes)

Testes para SQLite e operações DB:

- Operações CRUD
- Upsert e merge
- Schema e migrations
- Derivadas

```bash
# Executar testes de banco de dados
python -m pytest tests/test_database*.py tests/test_derivadas*.py -v
```

### 5. Filtros (15+ testes)

Testes para lógica de filtragem:

- Modos de filtro
- Regex e fallback
- Cache de filtros
- Locking thread-safe

```bash
# Executar testes de filtros
python -m pytest tests/test_filter*.py -v
```

### 6. CLI (20+ testes)

Testes para interface de linha de comando:

- Seleção de colunas
- Configurações
- Paginação
- Queries seguras

```bash
# Executar testes de CLI
python -m pytest tests/test_cli_*.py -v
```

## Fixtures Disponíveis

O arquivo `conftest.py` disponibiliza fixtures reutilizáveis:

### Fixtures Principais

```python
# Fixture de QApplication para testes PyQt6
@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Garante QApplication disponível."""
    app = QApplication.instance() or QApplication([])
    yield app

# Fixture de banco de dados temporário
@pytest.fixture
def temp_db(tmp_path):
    """Cria DB SQLite temporário com dados de teste."""
    # ...

# Fixture de DataFrame de exemplo
@pytest.fixture
def sample_dataframe():
    """DataFrame de exemplo para testes."""
    # ...
```

## Boas Práticas

### 1. Nomenclatura

```python
# Nomear testes de forma descritiva
def test_normalize_order_by_rejects_sql_injection():
    """Testa proteção contra SQL injection."""
    pass

def test_worker_emits_error_on_db_failure():
    """Testa emissão de erro em falha de DB."""
    pass
```

### 2. Organização

```python
class TestDataLoaderWorkerUnit:
    """Testes unitários isolados."""
    
    def test_sanitize_identifier_valid(self):
        pass

class TestDataLoaderWorkerIntegration:
    """Testes de integração com signals."""
    
    def test_worker_emits_data_loaded(self):
        pass
```

### 3. Mocking

```python
from unittest.mock import patch, MagicMock

# Mockar chamadas externas
with patch("gui.workers.data_loader_worker.query_db") as mock_query:
    mock_query.return_value = pd.DataFrame()
    worker.run()
```

### 4. Skip Condicional

```python
# Pular testes se dependência não disponível
pytest.importorskip("PyQt6", reason="PyQt6 indisponível")
```

## Adicionando Novos Testes

### Template para Workers

```python
# tests/test_novo_worker.py
import pytest
from unittest.mock import patch
from gui.workers.novo_worker import NovoWorker

pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app

class TestNovoWorkerUnit:
    """Testes unitários."""
    
    def test_metodo_publico(self):
        worker = NovoWorker()
        resultado = worker.metodo()
        assert resultado == esperado

class TestNovoWorkerIntegration:
    """Testes de integração."""
    
    def test_worker_emite_signal(self):
        worker = NovoWorker()
        emitted = []
        worker.signal.connect(lambda x: emitted.append(x))
        worker.run()
        assert len(emitted) == 1
```

## Métricas de Qualidade

### Cobertura Atual

- **Total de testes**: 669
- **Workers**: 52 testes (100% métodos cobertos)
- **GUI**: 45+ testes
- **Importação**: 30+ testes
- **Database**: 25+ testes

### Verificar Cobertura

```bash
# Instalar plugin de cobertura
pip install pytest-cov

# Gerar relatório
python -m pytest tests/ --cov=gui --cov=core --cov=armazenamento --cov-report=html

# Abrir relatório
open htmlcov/index.html
```

## Troubleshooting

### Problema: PyQt6 não encontrado

```bash
# Instalar PyQt6 no venv
source .venv/bin/activate
pip install PyQt6
```

### Problema: Testes falhando por timeout

```bash
# Aumentar timeout
python -m pytest tests/ --timeout=120
```

### Problema: Testes de GUI travando

```bash
# Executar em modo headless
export QT_QPA_PLATFORM=offscreen
python -m pytest tests/test_gui_*.py -v
```

## CI/CD

### Comando para CI

```bash
# Executar todos os testes com report
python -m pytest tests/ \
    --verbose \
    --tb=short \
    --junitxml=report.xml \
    --cov=. \
    --cov-report=xml
```

### Pré-commit

```bash
# Verificar testes antes de commit
python -m pytest tests/ -x --tb=line
```

## Recursos Adicionais

- [Documentação dos Workers](../docs/WORKERS_API_DOCUMENTATION.md)
- [Diagramas de Arquitetura](../docs/WORKERS_ARCHITECTURE_DIAGRAMS.md)
- [Pytest Documentation](https://docs.pytest.org/)
- [PyQt6 Testing Guide](https://www.riverbankcomputing.com/static/Docs/PyQt6/)

---

**Mantenedor**: Equipe SSA Consulta Rápida  
**Última atualização**: 2025-02-23  
**Branch**: codex/dev-filtros-stability
