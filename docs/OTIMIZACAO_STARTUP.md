# Otimizacao de Tempo de Inicializacao

## Problema

Tempo de startup inicial: **~6 segundos**

Gargalos identificados:
- pandas: 4200ms (68% do tempo total)
- openpyxl: 1022ms (17%)
- PyQt6: 586ms (10%)
- sqlite3: 79ms (1%)
- Outros: 267ms (4%)

## Solucoes Praticas

### 1. Bytecode Cache (Ja Ativo)

Python automaticamente compila modulos para bytecode (.pyc) em `__pycache__/`.

**Ganho:** 10-15% reducao no startup (500-900ms)

**Status:** Automatico, nenhuma acao necessaria

### 2. PyOxidizer - Executavel Nativo (Implementado)

Compila Python e codigo para executavel nativo.

**Ganho:** Reducao significativa, de 6s para 2-3s

**Vantagens:**
- Codigo compilado para C nativo (alta seguranca)
- Pastas editaveis mantidas separadas (config/, themes/, data/)
- Nao requer Python instalado
- Startup rapido

**Build:**
```bash
pip install pyoxidizer
pyoxidizer build --release
```

Resultado em: `build/x86_64-pc-windows-msvc/release/install/`

Veja: [BUILD_PYOXIDIZER.md](BUILD_PYOXIDIZER.md)

### 3. Lazy Imports (Nao Implementado)

Postergar imports ate serem necessarios.

**Exemplo:**
```python
# Em vez de:
import pandas as pd
import PyQt6.QtWidgets

# Fazer:
def launch_gui():
    import PyQt6.QtWidgets  # Import apenas quando GUI lancada
    # ...
```

**Ganho:** Reducao significativa para CLI (inicia em <100ms)

**Status:** Nao implementado (requer refatoracao grande)

## Recomendacao

### Para Distribuicao: **PyOxidizer**

Melhor opcao para build final.

**Build:**
```bash
pyoxidizer build --release
```

**Resultado:**
- Startup: 2-3s
- Codigo fonte protegido (C nativo)
- Pastas editaveis separadas
- Tamanho: ~150-200MB

Veja: [BUILD_PYOXIDIZER.md](BUILD_PYOXIDIZER.md)

### Para Desenvolvimento: Python Direto

Durante desenvolvimento:
```bash
python main.py --gui
```

Startup: 6s (aceitavel para dev)

## Medicao de Performance

Script para medir tempos de import:

```bash
python scripts_manutencao/measure_startup_time.py
```

Resultado atual:
```
--- Standard Library ---
   11.90ms  argparse
   52.70ms  logging
   79.11ms  sqlite3
   21.43ms  json

--- Scientific Libraries ---
 4204.33ms  pandas
 1022.28ms  openpyxl

--- GUI Libraries (PyQt6) ---
  585.97ms  PyQt6.QtWidgets

--- Project Core Modules ---
   67.21ms  core.app_logic
  105.88ms  gui.gui_ssa

Total: 6154.86ms (6.15s)
```

## Notas

- Primeira execucao sempre sera lenta (imports iniciais)
- Bytecode cache (.pyc) ja ajuda automaticamente
- PyInstaller pode ser usado como alternativa de compatibilidade
- Executavel gerado: ~100-150MB

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

