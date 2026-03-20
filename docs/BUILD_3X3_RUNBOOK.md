# Build 3x3 Runbook (Windows Linux macOS x PyInstaller Nuitka PyOxidizer)

## Objetivo

Padrao reproduzivel para gerar e validar build nas 3 plataformas e 3 backends, com comandos canonicos via `uv` e saida padronizada.

## Regras fixas

1. Usar sempre `uv run --python 3.13` para execucao Python.
2. Nao commitar artefatos de build (`builds/`, `launchers/dist/`, `dist_packages/`).
3. Rodar smoke fora do repo (`C:\Windows\Temp` ou `/tmp`).
4. Garantir runtime dirs visiveis: `config`, `data`, `docs_entrada`, `docs_saida`, `exportacao`.

## Pre requisitos por host

### Windows 11

1. `uv` instalado e funcional.
2. Python 3.13 mais recente disponivel no uv:

```powershell
uv python install 3.13
uv run --python 3.13 python -V
```

3. Inno Setup para empacotador (`iscc`) quando for gerar instalador.

### Debian 13 via WSL

1. `uv` instalado e funcional.
2. Python 3.13 mais recente disponivel no uv.
3. Dependencias de build:

```bash
sudo apt-get update
sudo apt-get install -y patchelf build-essential
```

### macOS

1. `uv` instalado e funcional.
2. Python 3.13 mais recente disponivel no uv.
3. Ferramentas de assinatura/notarizacao (quando aplicavel no ciclo de release).

## Isolamento de ambientes

```bash
# Windows
set UV_PROJECT_ENVIRONMENT=.venv-win

# Linux/WSL
export UV_PROJECT_ENVIRONMENT=.venv-linux
```

## Build por backend

### Windows

```powershell
dev_env/build/build_pyinstaller.bat --silent
dev_env/build/build_nuitka.bat --silent
dev_env/build/build_pyoxidizer.bat --silent
```

### Debian 13 via WSL

```bash
bash dev_env/build/build_pyinstaller_debian.sh --silent
bash dev_env/build/build_nuitka_debian.sh --silent
bash dev_env/build/build_pyoxidizer_debian.sh --silent
```

### macOS

```bash
uv run --python 3.13 launchers/build_multiplatform.py --platform macos_arm64 --apps gui
```

## Saida esperada

- PyInstaller:
  - `launchers/dist/<platform>/`
  - `builds/pyinstaller/<platform>/`
- Nuitka:
  - `builds/nuitka/<platform>/`
- PyOxidizer:
  - `builds/pyoxidizer/<platform>/`
- Pacotes:
  - `dist_packages/`

## Smoke minimo

### Windows (PowerShell)

```powershell
# Ajustar nome do exe conforme versao atual
& "C:\Users\mauri\git\SSA_Consulta_Rapida\launchers\dist\windows_amd64\SSA_CLI_v4.33_windows_amd64.exe" --help
```

### Linux/WSL

```bash
/tmp/SSA_CLI_v4.33_debian_amd64 --help
```

### macOS

Abrir app empacotada e validar:
1. startup sem crash
2. titulo com versao
3. menu Sobre

## Instalador Windows (Inno)

1. Gerar distribuicao via script de distribuicao do projeto.
2. Validar que `iscc` esta no host.
3. Rodar instalacao e confirmar runtime dirs visiveis na pasta final.

## Limpeza

### Limpeza segura (temporarios)

```bash
uv run --python 3.13 scripts/cleanup_build_artifacts.py --scope temp
```

### Limpeza completa (com confirmacao)

```bash
uv run --python 3.13 scripts/cleanup_build_artifacts.py --scope full
```

## Diagnostico rapido de falhas conhecidas

1. `Failed to load Python DLL ... python313.dll` (Windows/PyInstaller): revisar `strip` desativado.
2. `No module named core` (PyOxidizer): revisar install manifest no `pyoxidizer.bzl`.
3. `patchelf not found` (Nuitka Debian): instalar prerequisito no host.
4. `main.py nao encontrado` em runtime: fluxo legado bloqueante removido, validar versao atual do binario.
5. titulo duplicado em Windows/Linux: validar binario com patch de `ApplicationDisplayName` por plataforma.

## Fechamento da rodada

1. `git status --short`
2. validar que nao houve inclusao de artefatos pesados
3. commit atomico por slice
4. push para `dev`
5. atualizar:
   - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/RECOVERY_BACKLOG.md`

## Nota operacional desta conversa

1. `iscc` confirmado no host atual (`C:\\Users\\mauri\\scoop\\shims\\iscc.exe`).
2. Instalador `pyinstaller` compilado com sucesso via `scripts/create_distribution.py`.
3. `patchelf` instalado no WSL Debian 13 com `apt-get`.
4. Script `build_nuitka_debian.sh` ajustado:
   - GUI com plugin PyQt6
   - CLI sem plugin PyQt6
   - handler de erro com identificacao de step + tail de log em modo silencioso
5. Build `nuitka` Debian segue pesado no host e requer rodada dedicada para fechamento final de tempo/retorno.
