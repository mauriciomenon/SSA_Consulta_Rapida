# Build Execution Audit 2026-03-11

## Historical Snapshot

Este arquivo descreve uma auditoria historica de build daquela rodada.
Nao usar este bloco como `Current Truth` atual.

Fontes ativas atuais:
1. `docs/BUILD_SYSTEM.md`
2. `docs/BUILD_MULTIPLATFORM.md`
3. `docs/GUIA_DISTRIBUICAO.md`

- Sync timestamp: 2026-03-12 00:45 -0300
- Branch alvo: `dev`
- Ultimos commits relevantes:
  - `b63d9133` DOC_SYNC: licoes aprendidas cross-project de build tooling
  - `20b7f1c2` STABILITY_PATCH: cleanup reutilizavel e prompt pos-build
  - `52fd44c6` STABILITY_PATCH: remove bloqueio main.py no rescan e ajusta titulo por plataforma
  - `c996afb7` STABILITY_PATCH: estabiliza runtime pyoxidizer windows/debian
  - `7b812b9f` STABILITY_PATCH: inclui data e docs no template do instalador Inno
  - `cbfa3114` STABILITY_PATCH: corrige runtime frozen CLI e remove strip windows
  - `5a0a6a8e` STABILITY_PATCH: padroniza build uv windows/debian e corrige runtime assets
  - `05bbc2e1` STABILITY_PATCH: fix startup app mac + title/about + rebuild app+dmg

## Escopo deste relatorio

Este documento consolida o processo de build para Windows/Linux/macOS com 3 backends (`pyinstaller`, `nuitka`, `pyoxidizer`), caminhos de saida/limpeza, configuracoes envolvidas, erros encontrados, correcoes aplicadas e status de atendimento dos pedidos desta conversa.

## Comandos canonicos (sempre via uv)

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

Nota: `pyinstaller` e o backend default de release. `nuitka` e `pyoxidizer` seguem como trilha opcional, com validacao por ciclo.

## Estrutura de saida padronizada

### Artefatos finais

- PyInstaller:
  - `launchers/dist/windows_amd64/`
  - `launchers/dist/debian_amd64/`
  - `launchers/dist/macos_arm64/`
  - `builds/pyinstaller/<platform>/`
- Nuitka:
  - `builds/nuitka/windows_amd64/`
  - `builds/nuitka/debian_amd64/`
- PyOxidizer:
  - `builds/pyoxidizer/windows_amd64/`
  - `builds/pyoxidizer/debian_amd64/`
- Pacotes finais:
  - `dist_packages/`

### Staging/temporarios (nao versionar)

- `build/pyoxidizer_stage_windows_amd64/`
- `build/x86_64-pc-windows-msvc/`
- `build/x86_64-unknown-linux-gnu/`
- `launchers/platforms/*/temp/`

## Limpeza reproduzivel

Script canonico:

```bash
uv run --python 3.13 scripts/cleanup_build_artifacts.py --scope temp
```

- `--scope temp`: remove apenas temporarios/staging.
- `--scope full`: remove tambem `builds/*`, `launchers/dist/*`, `dist_packages/*`.
- `--yes`: elimina prompt no `scope full`.

Scripts de build (`.bat`/`.sh`) agora perguntam no final (modo nao silencioso) se deve rodar cleanup `temp`.

## Configuracoes e arquivos envolvidos

### Config de build

- `dev_env/build/build_pyinstaller.bat`
- `dev_env/build/build_nuitka.bat`
- `dev_env/build/build_nuitka_clean.bat`
- `dev_env/build/build_pyoxidizer.bat`
- `dev_env/build/build_pyinstaller_debian.sh`
- `dev_env/build/build_nuitka_debian.sh`
- `dev_env/build/build_pyoxidizer_debian.sh`
- `dev_env/build/pyoxidizer.bzl`
- `launchers/platforms/windows_amd64/build_config.json`
- `launchers/platforms/debian_amd64/build_config.json`
- `launchers/platforms/macos_arm64/build_config.json`

### Runtime/config da aplicacao

- `config/default_settings.json`
- `config/version.json`
- `main.py`
- `launchers/gui_entry.py`
- `launchers/cli_entry.py`
- `core/config_manager.py`
- `utils/setup_project_structure.py`
- `scripts/create_distribution.py` (inclui Inno script e estrutura de distribuicao)

### Pastas runtime que devem ficar visiveis

- `config/`
- `data/`
- `docs_entrada/`
- `docs_saida/`
- `exportacao/`

## Erros encontrados e tratamento aplicado

### PyInstaller (Windows)

- Erro: `Failed to load Python DLL ... python313.dll (LoadLibrary: invalid access)`.
- Causa: build com `strip` no Windows pode quebrar runtime.
- Acao: desativacao de `strip` no config Windows.
- Status: corrigido e validado em smoke.

### PyInstaller (Debian/WSL)

- Erro observado em rodada anterior: falta de `config/default_settings.json` no runtime.
- Causa: seed/runtime path inconsistente no pacote anterior.
- Acao: ajustes de runtime bootstrap e seed de dirs/config no fluxo frozen.
- Status: corrigido no fluxo atual; manter smoke por release.

### Nuitka (Windows)

- Status atual: build e smoke de CLI/GUI executados no ciclo de estabilizacao.
- Risco residual: validar novamente apos qualquer mudanca grande em bootstrap/runtime dirs.

### Nuitka (Debian/WSL)

- Erro historico: dependencia `patchelf` ausente.
- Causa: requisito de toolchain do ambiente.
- Acao:
  - `patchelf` instalado no WSL.
  - script `dev_env/build/build_nuitka_debian.sh` ajustado para diagnostico melhor:
    - separa comando GUI (com plugin PyQt6) de CLI (sem plugin PyQt6).
    - adiciona `trap` com identificacao de `LAST_STEP` e tail de log no modo silencioso.
- Status: avancou; ainda requer fechamento final de tempo/retorno no host para rodada de release.

### PyOxidizer (Windows)

- Erro: `No module named core/interface/utils`.
- Causa: pacotes internos nao incluidos no install manifest.
- Acao: incluir explicitamente pacotes e entrypoint no `pyoxidizer.bzl`.
- Status: corrigido.

- Erro: numpy/pandas em modo limitado por libs nativas faltantes.
- Causa: diretorios `.libs` nao copiados.
- Acao: `scripts/sync_pyoxidizer_runtime_libs.py` integrado nos scripts.
- Status: corrigido.

### PyOxidizer (Debian/WSL)

- Erro: falha em glob com `..` no `pyoxidizer.bzl` (rodada anterior).
- Causa: padrao de caminho nao portavel.
- Acao: ajustar padrao de path/glob para install manifest.
- Status: corrigido no pipeline atual.

### GUI/runtime cross-platform

- Erro: popup `Arquivo main.py nao encontrado em AppData/...`.
- Causa: hard-check legado em fluxo de rescan modular.
- Acao: remover bloqueio por arquivo e manter warning de compat.
- Status: corrigido (`52fd44c6`).

- Erro: titulo duplicado em Windows/Debian.
- Causa: `ApplicationDisplayName` + `WindowTitle` no mesmo ambiente visual.
- Acao: manter `ApplicationDisplayName` apenas no macOS.
- Status: corrigido (`52fd44c6`).

## Inno Setup (Windows installer)

- Estrutura de distribuicao e template do instalador seguem em `scripts/create_distribution.py`.
- Ajuste aplicado no ciclo: inclusao de `data` e pastas de docs no template.
- Evidencia desta rodada:
  - `Get-Command iscc` -> `C:\Users\mauri\scoop\shims\iscc.exe`
  - `uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller` -> instalador compilado com sucesso.
- Status: atendido para trilha `pyinstaller` no host atual.

## Reprodutibilidade cross-project (checklist)

1. Fixar tudo em `uv run --python 3.13`.
2. Separar env por OS quando necessario:
   - Windows: `UV_PROJECT_ENVIRONMENT=.venv-win`
   - Linux/WSL: `UV_PROJECT_ENVIRONMENT=.venv-linux`
3. Garantir que runtime nao dependa de `CWD`.
4. Garantir seed de `config/default_settings.json` no runtime user dir.
5. Garantir criacao de `config`, `data`, `docs_entrada`, `docs_saida`, `exportacao` no bootstrap.
6. Rodar smoke fora do repo (`C:\Windows\Temp` ou `/tmp`).
7. Registrar licao aprendida com: sintoma, causa, fix, comando de validacao.
8. Manter limpeza separada entre `temp` e `full`.

## Matriz de pedidos da conversa (desde o inicio)

Legenda de status:
- `ATENDIDO`: concluido com evidencia em commit/doc.
- `PARCIAL`: avancou, mas ainda existe validacao pendente.
- `NAO ATENDIDO`: nao concluido nesta rodada.

1. Sincronizar branches `main`, `dev`, `codex/...` localmente: `ATENDIDO` (rodada inicial de sync, foco consolidado em `dev`).
2. Corrigir comportamento irritante de abrir varias janelas de terminal/credencial: `ATENDIDO` (padronizacao para execucao no terminal atual e ajuste de git credential helper).
3. Validar toolchain `uv`, `pnpm`, `bun`: `ATENDIDO` (checks de ambiente executados).
4. Garantir Python 3.13 default para `uv` e `uv run`: `ATENDIDO` (3.13.12 ativo no host).
5. Validar pacote de ferramentas `uv run --python 3.13` (pyqt6/pandas/matplotlib/pyoxidizer/nuitka/...): `ATENDIDO` (checks e installs no ciclo).
6. Garantir `python` sempre via `uv` inclusive venv: `ATENDIDO` (docs/comandos canonicos atualizados).
7. Build `windows_amd64` silencioso nas 3 frentes: `PARCIAL` (PyInstaller/Nuitka/PyOxidizer com progresso real; manter smoke final por release).
8. Build `debian_amd64` silencioso nas 3 frentes: `PARCIAL` (PyInstaller ok; `patchelf` instalado; script Nuitka melhorado para diagnostico, mas execucao completa ainda e longa no host e precisa fechamento final para release).
9. Corrigir erro de runtime `main.py nao encontrado`: `ATENDIDO` (`52fd44c6`).
10. Corrigir duplicacao de titulo em Windows/Debian: `ATENDIDO` (`52fd44c6`).
11. Garantir visibilidade de `config/data/docs_entrada/docs_saida/exportacao`: `ATENDIDO` (bootstrap + docs de processo consolidados).
12. Expor mais o source code (hardening): `PARCIAL` (registrado caminho com Nuitka/PyOxidizer/Cython; nao houve rollout Cython neste slice).
13. Padronizar estrutura de pastas de output entre ferramentas: `ATENDIDO` (documentado e aplicado no pipeline atual).
14. Criar script de limpeza reutilizavel e pergunta ao final do build: `ATENDIDO` (`20b7f1c2`).
15. Atualizar docs/processos para usar uv (sem pip/python direto): `ATENDIDO` (docs de build e comandos canonicos atualizados).
16. Refinar Inno Setup (icone/pastas): `ATENDIDO` (template atualizado + instalador `pyinstaller` compilado nesta rodada com `iscc` presente no host).
17. Nao subir artefatos pesados de build no git: `ATENDIDO` (politica mantida em docs e pratica de commits).
18. Documentar onde ficam exe/binarios por backend: `ATENDIDO` (secao de saida padronizada).
19. Salvar licoes aprendidas reproduziveis para outros projetos: `ATENDIDO` (`docs/BUILD_TOOLING_LESSONS_LEARNED.md` + este audit).
20. Atualizar migracao de conversa/backlog/verdade atual: `ATENDIDO` (docs de controle sincronizados neste slice).

## Pendencias abertas (objetivas)

1. Fechar validacao final de tempo/retorno do `build_nuitka_debian.sh --silent` em rodada dedicada de release.
2. Rodar bateria final de smoke cross-platform no pacote atual antes de release.
3. Decidir se entra ciclo dedicado de Cython para hardening adicional de source.

## Evidencia adicional desta rodada (2026-03-12 00:05)

1. `patchelf` instalado no WSL:
   - comando: `wsl -u root -e bash -lc "apt-get update && apt-get install -y patchelf"`
   - resultado: pacote `patchelf 0.18.0-1.4` instalado.
2. Runtime dirs visiveis confirmadas em artefatos:
   - `launchers/dist/windows_amd64`: `config`, `data`, `docs_entrada`, `docs_saida`
   - `launchers/dist/debian_amd64`: `config`, `data`, `docs_entrada`, `docs_saida`
3. Build Nuitka Debian:
   - comando: `bash dev_env/build/build_nuitka_debian.sh --silent`
   - resultado observado: artefatos `gui_entry.dist` e `cli_entry.dist` presentes; execucao completa ainda sensivel a tempo de compilacao no host.
4. Hardening do script Nuitka Debian:
   - `STABILITY_PATCH` em `dev_env/build/build_nuitka_debian.sh`:
     - CLI sem plugin `pyqt6`.
     - handler de erro com `LAST_STEP` + tail de log no modo silencioso.

## Plano de fechamento das pendencias (comandos)

1. Inno Setup final:
   - validar `iscc`:
     - `where iscc`
   - gerar distribuicao e compilacao do instalador:
     - `uv run --python 3.13 scripts/create_distribution.py --platform windows_amd64 --build-system pyinstaller`
   - smoke do instalador:
     - instalar e validar existencia de `config`, `data`, `docs_entrada`, `docs_saida`, `exportacao`.
2. Nuitka Debian com prerequisito:
   - `sudo apt-get update && sudo apt-get install -y patchelf`
   - `bash dev_env/build/build_nuitka_debian.sh --silent`
3. Smoke cross-platform final:
   - Windows: CLI + GUI a partir de `C:\Windows\Temp`
   - Debian: CLI + GUI a partir de `/tmp` (ou host com display)
   - macOS: abrir `.app` e validar startup + titulo + menu Sobre
4. Hardening adicional de source:
   - opcao A: manter somente `nuitka`/`pyoxidizer` no release
   - opcao B: adicionar ciclo dedicado de Cython para modulos criticos

## Referencias cruzadas

- `docs/BUILD_MULTIPLATFORM.md`
- `docs/BUILD_TOOLING_LESSONS_LEARNED.md`
- `docs/BUILD_3X3_RUNBOOK.md`
- internal continuity docs removed from the public repository

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
