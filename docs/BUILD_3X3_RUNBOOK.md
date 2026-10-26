# Build 3x3 Runbook (Windows Linux macOS x PyInstaller Nuitka)

## CURRENT TRUTH (2026-10-25, release v4.51 publicada; estabilizacao no branch rev)

- Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`, bloco `CURRENT TRUTH`.
- Ultima release publicada: `v4.51` (tag -> `e2481cf4`, merge do PR #135 em 2026-09-29; release no GitHub em 2026-09-30; assets e SHA-256 em `RELEASE_NOTES_v4.51.md`).
- Em andamento: estabilizacao no branch `rev`, sem tag. O build do REL-01 e de teste de processo: sai do `rev` e o `build_info.json` registra branch e commit. O build oficial sai do `main`, depois do PR.
- Este runbook detalha execucao 3x3; nao deve duplicar a matriz completa de release.
- Build e testes exigem ferramentas nativas e clone do proprio host; nao compartilhar checkout ou venv entre sistemas.
- Publicacao neste checkout: `origin` envia ao GitHub principal e ao GitLab; o push URL do espelho `schottge-menon` esta comentado em `.git/config` (conta suspensa). Conferir a configuracao antes de usar em outro clone.
- Os builds locais da candidata v4.51 (2026-09-24, a partir de `a2954a48`) nao sao os assets publicados: a release traz um pacote por alvo, inclusive Debian amd64 e arm64.

## Objetivo

Padrao reproduzivel para gerar e validar build nas 3 plataformas e 2 backends (PyInstaller e Nuitka), com comandos canonicos via `uv` e saida padronizada.
O PyOxidizer foi removido na v4.52: o pyoxidizer 0.24.0 esta sem manutencao desde 2022-12-30 e so embute CPython 3.10, que o projeto nao suporta mais.

## Regras fixas

1. Usar sempre `uv run --no-sync` para execucao Python.
2. Nao commitar artefatos de build (`builds/`, `launchers/dist/`, `dist_packages/`).
3. Rodar smoke fora do repo (`C:\Windows\Temp` ou `/tmp`).
4. Garantir runtime dirs visiveis: `config`, `data`, `docs_entrada`, `docs_saida`.
5. Nao misturar shells:
   - Windows: PowerShell chama `.bat` com `.\` e caminhos `\`.
   - Debian/Linux: shell POSIX chama `.sh` com `/` em clone Linux nativo.
   - macOS: shell POSIX chama `.sh` ou `uv` com `/`.
6. Nao chamar `bash dev_env/...` no PowerShell e nao chamar `.\dev_env\...bat` no Linux/macOS.
7. Nao usar checkout em `/mnt/*`, executavel Windows ou venv Windows para build/teste Linux.

## Pre requisitos por host

### Windows 11

1. `uv` instalado e funcional.
2. Python 3.13 mais recente disponivel no uv:

```powershell
uv python install 3.13
uv run --no-sync python -V
```

3. Inno Setup para empacotador (`iscc`) quando for gerar instalador.
`rcedit` e um editor de recursos PE do Windows. Ele altera icone, `FileVersion`,
`ProductVersion` e strings de versao em executaveis `.exe`.

Regra de uso no projeto:
1. PyInstaller Windows recebe metadata no momento do build via `--version-file`.
2. Nao aplicar `rcedit` manualmente sobre PyInstaller onefile pronto; isso pode quebrar o arquivo PKG embutido.
3. Nuitka Windows deve continuar usando recursos/versionamento no proprio fluxo de build.

### Debian 13 em host/VM Linux nativo

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

# Linux
export UV_PROJECT_ENVIRONMENT=.venv-linux
```

## Build por backend

### Windows deterministico

Use este fluxo para release local Windows. Ele executa preflight, seleciona
backends, chama somente wrappers `.bat`, valida `build_info.json`, valida
metadata dos EXEs, gera ZIPs por backend, roda smoke minimo e escreve relatorio.

```powershell
.\dev_env\build\release_windows.ps1
```

Modo nao interativo:

```powershell
.\dev_env\build\release_windows.ps1 -Backend pyinstaller,nuitka -Yes
```

Sem instalador Inno:

```powershell
.\dev_env\build\release_windows.ps1 -Backend pyinstaller -Yes -SkipInstaller
```

Saida de auditoria:

```text
builds\reports\release_report_windows_amd64.json
```

Regra de integridade:
1. workspace sujo bloqueia o release
2. `build_info.git_commit` precisa bater com `git rev-parse HEAD`
3. ZIP precisa conter EXE, `config/build_info.json` e `GUIA_MIGRACAO_NOVA_INSTALACAO.md`
4. PowerShell nao chama shell POSIX neste fluxo

### Windows

```powershell
.\dev_env\build\build_pyinstaller.bat --silent
.\dev_env\build\build_nuitka.bat --silent
```

### Debian 13 deterministico local ou via SSH

Use este fluxo para release Debian AMD64. Ele roda somente em shell POSIX,
chama somente wrappers `.sh`, valida workspace limpo, `build_info.json`,
guia de migracao, conteudo do `.deb` e escreve relatorio com hashes.

Local no clone Debian nativo:

```bash
bash dev_env/build/release_debian.sh --backend pyinstaller,nuitka --package deb -y
```

Via SSH para host Debian:

```bash
bash dev_env/build/release_debian.sh --ssh-host user@debian-host --ssh-repo /home/user/SSA_Consulta_Rapida --backend pyinstaller,nuitka --package deb -y
```

AppImage e opcional e existe somente para `pyinstaller` e `nuitka`:

```bash
bash dev_env/build/release_debian.sh --backend pyinstaller,nuitka --package appimage -y
```

Saida de auditoria:

```text
builds/reports/release_report_debian_amd64.json
```

Regras Debian:
1. workspace sujo bloqueia o release
2. `.deb` aceita `pyinstaller` e `nuitka`
3. AppImage aceita apenas `pyinstaller` e `nuitka`
4. `--with-local-data` nao e suportado via SSH; execute localmente no host Debian se precisar desse modo
5. PowerShell nao entra neste fluxo
6. backends rodam em serie por desenho; Nuitka pressiona CPU/RAM/IO e paralelizar build completo so deve ser feito em slice proprio com medicao de recursos

### Debian 13 via WSL

```bash
bash dev_env/build/build_pyinstaller_debian.sh --silent
bash dev_env/build/build_nuitka_debian.sh --silent
```

### macOS

```bash
uv run --no-sync launchers/build_multiplatform.py --platform macos_arm64 --apps gui
```

## Saida esperada

- PyInstaller:
  - `launchers/dist/<platform>/`
  - `builds/pyinstaller/<platform>/`
- Nuitka:
  - `builds/nuitka/<platform>/`
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

Executar somente depois de gerar os binarios da versao local.

```powershell
$APP_VERSION = (Get-Content -Raw .\config\version.json | ConvertFrom-Json).version_short
$EXES = @(
  ".\launchers\dist\windows_amd64\SSA_CLI_v${APP_VERSION}_windows_amd64\SSA_CLI_v${APP_VERSION}_windows_amd64.exe",
  ".\launchers\dist\windows_amd64\SSA_GUI_v${APP_VERSION}_windows_amd64\SSA_GUI_v${APP_VERSION}_windows_amd64.exe",
  ".\builds\nuitka\windows_amd64\cli_entry.dist\SSA_CLI_v${APP_VERSION}_windows_amd64.exe",
  ".\builds\nuitka\windows_amd64\gui_entry.dist\SSA_GUI_v${APP_VERSION}_windows_amd64.exe"
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
# -type f: o onedir do PyInstaller tem o mesmo nome e o binario fica dentro.
CLI_BIN="$(find /tmp -maxdepth 2 -type f -name 'SSA_CLI_v*_debian_amd64' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)"
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
uv run --no-sync scripts/cleanup_build_artifacts.py --scope temp
```

### Limpeza completa (com confirmacao)

```bash
uv run --no-sync scripts/cleanup_build_artifacts.py --scope full
```

## Diagnostico rapido de falhas conhecidas

1. `Failed to load Python DLL ... python313.dll` (Windows/PyInstaller): revisar `strip` desativado.
2. `patchelf not found` (Nuitka Debian): instalar prerequisito no host.
3. `main.py nao encontrado` em runtime: fluxo legado bloqueante removido, validar versao atual do binario.
4. titulo duplicado em Windows/Linux: validar binario com patch de `ApplicationDisplayName` por plataforma.

## Fechamento da rodada

1. `git status --short`
2. validar que nao houve inclusao de artefatos pesados
3. commit atomico por slice
4. push para `dev`
5. atualizar:
   - `README.md`
   - `docs/README.md`

## Nota operacional do baseline atual

1. Confirmar prerequisitos de empacotamento no host antes de iniciar o ciclo.
2. Validar instalador `pyinstaller` e artefatos em `dist_packages/` no proprio host de release.
3. No host/VM Debian nativo, garantir `patchelf` presente antes do preflight do Nuitka.
4. Tratar performance do build Nuitka Debian como rodada dedicada quando o host estiver sob carga.
5. Nao versionar caminhos locais de host neste runbook.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
