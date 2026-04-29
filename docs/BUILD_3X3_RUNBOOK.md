# Build 3x3 Runbook (Windows Linux macOS x PyInstaller Nuitka PyOxidizer)

## Objetivo

Padrao reproduzivel para gerar e validar build nas 3 plataformas e 3 backends, com comandos canonicos via `uv` e saida padronizada.

## Regras fixas

1. Usar sempre `uv run --python 3.13` para execucao Python.
2. Nao commitar artefatos de build (`builds/`, `launchers/dist/`, `dist_packages/`).
3. Rodar smoke fora do repo (`C:\Windows\Temp` ou `/tmp`).
4. Garantir runtime dirs visiveis: `config`, `data`, `docs_entrada`, `docs_saida`, `exportacao`.
5. Nao misturar shells:
   - Windows: PowerShell chama `.bat` com `.\` e caminhos `\`.
   - Debian/WSL/Linux: shell POSIX chama `.sh` com `/`.
   - macOS: shell POSIX chama `.sh` ou `uv` com `/`.
6. Nao chamar `bash dev_env/...` no PowerShell e nao chamar `.\dev_env\...bat` no WSL/Linux/macOS.

## Pre requisitos por host

### Windows 11

1. `uv` instalado e funcional.
2. Python 3.13 mais recente disponivel no uv:

```powershell
uv python install 3.13
uv run --python 3.13 python -V
```

3. Inno Setup para empacotador (`iscc`) quando for gerar instalador.
4. `rcedit` no `PATH` para build PyOxidizer Windows com icone e metadata:

```powershell
scoop install rcedit
rcedit.exe --help
```

`rcedit` e um editor de recursos PE do Windows. Ele altera icone, `FileVersion`,
`ProductVersion` e strings de versao em executaveis `.exe`.

Regra de uso no projeto:
1. PyInstaller Windows recebe metadata no momento do build via `--version-file`.
2. Nao aplicar `rcedit` manualmente sobre PyInstaller onefile pronto; isso pode quebrar o arquivo PKG embutido.
3. PyOxidizer Windows usa `rcedit` no script de build para aplicar icone e metadata.
4. Nuitka Windows deve continuar usando recursos/versionamento no proprio fluxo de build.

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
.\dev_env\build\build_pyinstaller.bat --silent
.\dev_env\build\build_nuitka.bat --silent
.\dev_env\build\build_pyoxidizer.bat --silent
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
# Copiar o binario para fora do repo antes do smoke
$DIST_ROOT = "C:\Windows\Temp"
$CLI_BIN = Get-ChildItem "$DIST_ROOT\SSA_CLI_v*_windows_amd64.exe" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
if (-not $CLI_BIN) {
  throw "Nenhum binario SSA_CLI_v*_windows_amd64.exe encontrado em $DIST_ROOT"
}
& $CLI_BIN --help
```

### Windows metadata (PowerShell)

```powershell
$EXES = @(
  ".\launchers\dist\windows_amd64\SSA_CLI_v4.37_windows_amd64\SSA_CLI_v4.37_windows_amd64.exe",
  ".\launchers\dist\windows_amd64\SSA_GUI_v4.37_windows_amd64\SSA_GUI_v4.37_windows_amd64.exe",
  ".\builds\nuitka\windows_amd64\cli_entry.dist\SSA_CLI_v4.37_windows_amd64.exe",
  ".\builds\nuitka\windows_amd64\gui_entry.dist\SSA_GUI_v4.37_windows_amd64.exe",
  ".\builds\pyoxidizer\windows_amd64\SSA_Consulta_Rapida.exe"
)
$ROWS = @()
foreach ($EXE in $EXES) {
  $INFO = [System.Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path $EXE).Path)
  $ROWS += [pscustomobject]@{
    Path = $EXE
    FileVersion = $INFO.FileVersion
    ProductVersion = $INFO.ProductVersion
    ProductName = $INFO.ProductName
  }
}
$ROWS | Format-Table -AutoSize
```

### Linux/WSL

```bash
CLI_BIN="$(ls -t /tmp/SSA_CLI_v*_debian_amd64 2>/dev/null | head -n 1)"
if [ -z "$CLI_BIN" ]; then
  echo "[erro] nenhum binario SSA_CLI_v*_debian_amd64 encontrado em /tmp" >&2
  exit 1
fi
"$CLI_BIN" --help
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

## Nota operacional do baseline atual

1. Confirmar prerequisitos de empacotamento no host antes de iniciar o ciclo.
2. Validar instalador `pyinstaller` e artefatos em `dist_packages/` no proprio host de release.
3. No Debian/WSL, garantir `patchelf` presente antes do preflight do Nuitka.
4. Tratar performance do build Nuitka Debian como rodada dedicada quando o host estiver sob carga.
5. Nao versionar caminhos locais de host neste runbook.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
