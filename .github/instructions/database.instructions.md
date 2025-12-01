---
applyTo: '**/armazenamento/**,**/*database*.py,**/*db*.py,**/schema*.sql'
description: Instrucoes para operacoes com banco de dados SQLite
---

# Database SQLite

## Estrutura do Projeto

```
armazenamento/
├── database.py              # Conexao e operacoes basicas
├── database_optimized.py    # Queries otimizadas
├── database_validation.py   # Validacao de dados
├── database_integrity.py    # Integridade referencial
├── database_upsert_logic.py # Logica de upsert
├── schema_manager.py        # Gerenciamento de schema
└── identifier_utils.py      # Utilitarios de ID

config/
├── schema.sql               # Schema atual
└── schema_unified.sql       # Schema unificado

data/
└── ssas.db                  # Banco de dados
```

## Padroes de Seguranca (CRITICO)

### SEMPRE usar parametros
```python
# CORRETO
cursor.execute(
    "SELECT * FROM ssas WHERE numero = ? AND status = ?",
    (numero, status)
)

# ERRADO - SQL Injection
cursor.execute(f"SELECT * FROM ssas WHERE numero = '{numero}'")
```

### Context manager para conexoes
```python
from contextlib import contextmanager
import sqlite3

@contextmanager
def get_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

## Operacoes Comuns

### Insert com validacao
```python
def inserir_ssa(conn: Connection, ssa: dict) -> int:
    """Insere SSA validando dados."""
    validar_ssa(ssa)  # Levanta excecao se invalido

    cursor = conn.execute(
        """
        INSERT INTO ssas (numero, descricao, status, data_criacao)
        VALUES (?, ?, ?, ?)
        """,
        (ssa["numero"], ssa["descricao"], ssa["status"], datetime.now())
    )
    return cursor.lastrowid
```

### Upsert pattern
```python
def upsert_ssa(conn: Connection, ssa: dict) -> None:
    """Insere ou atualiza SSA."""
    conn.execute(
        """
        INSERT INTO ssas (numero, descricao, status)
        VALUES (?, ?, ?)
        ON CONFLICT(numero) DO UPDATE SET
            descricao = excluded.descricao,
            status = excluded.status,
            data_atualizacao = CURRENT_TIMESTAMP
        """,
        (ssa["numero"], ssa["descricao"], ssa["status"])
    )
```

## Ferramentas MCP Relevantes

### Codacy (Obrigatorio)
Apos editar arquivos de DB:
- Verificar SQL injection
- Verificar resource leaks (conexoes nao fechadas)

### Snyk
Para verificar vulnerabilidades em queries

## Migrations

### Adicionar coluna
```python
def migrate_add_column(conn: Connection) -> None:
    """Adiciona coluna nova_coluna se nao existir."""
    cursor = conn.execute("PRAGMA table_info(ssas)")
    colunas = [row[1] for row in cursor.fetchall()]

    if "nova_coluna" not in colunas:
        conn.execute("ALTER TABLE ssas ADD COLUMN nova_coluna TEXT")
```

## Backup

### Antes de operacoes criticas
```python
import shutil
from datetime import datetime

def backup_db(db_path: str) -> str:
    """Cria backup timestamped do banco."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path
```

## Indices para Performance

```sql
-- Indices recomendados para este projeto
CREATE INDEX IF NOT EXISTS idx_ssas_numero ON ssas(numero);
CREATE INDEX IF NOT EXISTS idx_ssas_status ON ssas(status);
CREATE INDEX IF NOT EXISTS idx_ssas_data ON ssas(data_criacao);
```
