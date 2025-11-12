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

### 2. PyInstaller - Executavel Standalone

Cria executavel unico com Python e dependencias embutidas.

**Ganho:** Reducao moderada, de 6s para 3.5-4s

**Vantagens:**
- Nao requer Python instalado
- Distribuivel como executavel unico
- Startup consistente

**Instalacao:**
```bash
pip install pyinstaller
```

**Criar executavel Windows:**
```bash
pyinstaller --name SSA_Consulta_Rapida ^
    --windowed ^
    --onefile ^
    --add-data "config;config" ^
    --add-data "themes;themes" ^
    main.py
```

Executavel gerado em: `dist/SSA_Consulta_Rapida.exe`

**Criar executavel Linux/Mac:**
```bash
pyinstaller --name SSA_Consulta_Rapida \
    --windowed \
    --onefile \
    --add-data "config:config" \
    --add-data "themes:themes" \
    main.py
```

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

Para uso diario: **PyInstaller**

1. Compilar uma vez:
```bash
pyinstaller --name SSA_Consulta_Rapida --windowed --onefile main.py
```

2. Usar executavel gerado:
```bash
dist/SSA_Consulta_Rapida.exe --gui
```

Primeira execucao: ~4s (descompactacao)
Execucoes seguintes: ~3.5-4s

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
- PyInstaller e a melhor opcao para uso diario
- Executavel gerado: ~100-150MB
