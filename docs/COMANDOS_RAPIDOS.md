# Comandos Rapidos - SSA Consulta Rapida v4.42

## Sync desta folha (2026-03-26 07:35 -0300)

1. Este runbook continua valido para baseline `v4.42`.
2. Fluxo de importacao recomendado:
   - incremental: `--force-rescan`
   - full rescan: `--reset-db`
3. Operacoes de DB auxiliares continuam disponiveis via menu GUI `Database`.

## Runtime padrao

- Comando padrao: `uv run --python <runtime> ...`
- Ordem recomendada de runtime: `3.13 -> 3.12 -> 3.11 -> 3.10`

## Inicializacao rapida (uv-first)

```powershell
git clone https://github.com/mauriciomenon/SSA_Consulta_Rapida.git
cd SSA_Consulta_Rapida

uv venv
uv sync

$PY_RUNTIME = "3.13"
uv run --python $PY_RUNTIME main.py --version
uv run --python $PY_RUNTIME main.py
```

## Execucao principal

```powershell
$PY_RUNTIME = "3.13"

# Help
uv run --python $PY_RUNTIME main.py --help

# CLI
uv run --python $PY_RUNTIME main.py

# GUI
uv run --python $PY_RUNTIME main.py --gui

# Streamlit
uv run --python $PY_RUNTIME main.py --streamlit
```

## Importacao e banco

```powershell
$PY_RUNTIME = "3.13"

# Atualizar dados (incremental)
uv run --python $PY_RUNTIME main.py --force-rescan

# Recriar DB e reimportar tudo
uv run --python $PY_RUNTIME main.py --reset-db

# Limpeza de dados legados
uv run --python $PY_RUNTIME main.py --clean-data
```

## Validacao tecnica minima

```powershell
$PY_RUNTIME = "3.13"

uv run --python $PY_RUNTIME python -m py_compile main.py
uv run --python $PY_RUNTIME ruff check main.py
uv run --python $PY_RUNTIME ty check main.py
uv run --python $PY_RUNTIME pytest -q tests/test_docs_and_priority.py
```

## Recuperacao rapida (safe mode)

```powershell
# Criar checkpoint (stash + pacote de recuperacao)
pwsh -File scripts_manutencao/quick_recovery.ps1 -Action checkpoint -Message "WIP rapida"

# Restaurar checkpoint
pwsh -File scripts_manutencao/quick_recovery.ps1 -Action restore
git stash pop
```

## Fallback manual sem uv

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Build silencioso (Windows e Debian)

```powershell
# Windows
dev_env\build\build_pyinstaller.bat --silent
dev_env\build\build_nuitka_clean.bat --silent
dev_env\build\build_pyoxidizer.bat --silent

# Debian via WSL
$REPO_ROOT = "/mnt/c/caminho/para/SSA_Consulta_Rapida"
wsl -e bash -lc "cd $REPO_ROOT && bash dev_env/build/build_pyinstaller_debian.sh --silent"
wsl -e bash -lc "cd $REPO_ROOT && bash dev_env/build/build_nuitka_debian.sh --silent"
wsl -e bash -lc "cd $REPO_ROOT && bash dev_env/build/build_pyoxidizer_debian.sh --silent"
```

## Notas

1. Para fluxo operacional e handoff, usar o PR/conversa atual.
2. Para troubleshooting geral, usar `docs/TROUBLESHOOTING.md`.
3. Para troubleshooting de importacao, usar `docs/TROUBLESHOOTING_IMPORTACAO.md`.
4. Antes dos comandos WSL acima, ajuste `$REPO_ROOT` para o caminho montado do repo no seu ambiente.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
