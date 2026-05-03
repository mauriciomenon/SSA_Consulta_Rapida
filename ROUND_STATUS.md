# ROUND_STATUS

## CURRENT TRUTH 2026-05-01 20h56

- Branch alvo: `dev`.
- HEAD validado: `55e2c4e2685099d672e05897f4631ca1af6b0175 2026-05-01 20:55:47 -0300 STABILITY_PATCH: deduplicate Debian target normalization`.
- PR #56: merged.
- `dev` contem correcoes de release v4.37 que ainda precisam chegar ao `main` antes do rebuild final.
- Artefatos v4.37 anteriores a este HEAD estao stale e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
- Orquestradores ativos:
  - Windows AMD64: `dev_env/build/release_windows.ps1`.
  - Debian AMD64: `dev_env/build/release_debian.sh`.
- Dry-run validado neste HEAD:
  - Windows: `release_windows.ps1 -Backend all -DryRun -Yes -SkipBuild -SkipPackage -SkipInstaller`.
  - Debian WSL: `release_debian.sh --backend all --package all --dry-run -y`.
- Protecao de codigo:
  - Nuitka e o backend preferencial para release protegido.
  - PyInstaller tem protecao parcial.
  - PyOxidizer so e aceitavel como protegido quando o pacote nao expuser `.py`/`.pyc` do app.
- Proximo passo operacional: sincronizar `main`, rebuildar Windows AMD64 e Debian AMD64 a partir deste HEAD, validar artefatos e so entao atualizar release v4.37.

## 2026-04-30T14:51:45-03:00 PR56 stability slice

- Scope: PR #56 actionable review fixes and follow-up validation.
- Kluster MCP: `kluster_code_review_auto` timed out after 120s on the modified files.
- Kluster CLI deep: `kluster review file ... --mode deep` returned backend HTTP 500 after the first follow-up run.
- Kluster CLI instant: first run completed and reported remaining search/filter/refactor items plus one script comment issue; the script comment issue was fixed.
- Kluster CLI instant retry: one retry returned backend HTTP 500.
- Kluster CLI instant successful run after status update: review `69f39d18295e5d0b624eac55`.
- Kluster final remaining items: structural import orchestrator refactor, filter/search performance and parser documentation, duplicated emoji definitions, local lazy imports in rescan worker, and filter-search cache performance.
- Status: classic validation passed; Kluster backend was unstable and final remaining items are deferred as non-blocking or performance-slice items.

## 2026-05-03T00:45:00-03:00 security workflow slice

- Scope: GitHub Actions hardening, vulnerable requirements scan cleanup, and secret scan workflow tightening.
- Kluster CLI deep on `docs/RECOVERY_BACKLOG.md`: timed out after 60s (`kluster review file docs/RECOVERY_BACKLOG.md --mode deep`).
- Fallback planned: rerun Kluster in instant mode for documentation/status files and keep deep mode for code/workflow files when it completes inside the local 60s window.
- Codex security preflight: timed out after 60s while running broad `gitleaks` (`C:\Users\mauri\.codex\scripts\security-preflight.ps1 -RepoPath C:\Users\mauri\git\SSA_Consulta_Rapida -Mode manual`).

## 2026-05-03T02:30:00-03:00 Nuitka runtime source-path slice

- Scope: corrigir entrypoints Nuitka para nao usar caminho do repo de build como fallback de runtime.
- Evidencia: smoke isolado do executavel Nuitka CLI carregou 70.954 SSAs mesmo com `APPDATA`, `LOCALAPPDATA` e `SSA_*` limpos; o entrypoint `launchers/cli_entry.py` so tratava `sys.frozen`, mas Nuitka expõe `__compiled__`.
- Kluster MCP/tool discovery: `tool_search` nao expôs ferramenta Kluster callable nesta sessao.
- Kluster CLI fallback: `pnpm.CMD dlx kluster-verify --help` falhou com `ERR_PNPM_FETCH_404` para `https://registry.npmjs.org/kluster-verify`.
- Validacao classica focada: `py_compile`, `ruff`, `ty` e `pytest` focado passaram antes do commit.
- Observacao operacional: hooks locais de commit ainda executam Kluster quando disponiveis no fluxo de commit.

## 2026-05-03T03:12:00-03:00 Nuitka parent-data isolation slice

- Scope: impedir que entrypoints Nuitka copiem `data/ssas.db` de diretorio pai do `.dist`.
- Evidencia: smoke isolado do Windows Nuitka CLI criou runtime temporario e copiou `builds/nuitka/windows_amd64/data/ssas.db` com 70.954 SSAs para `APPDATA` temporario.
- Causa: `_find_bundled_dir` e `_find_bundled_data_dir` aceitavam `exe_path.parent.parent / "data"`, que no layout local aponta para `builds/nuitka/windows_amd64/data`.
- Kluster MCP/tool discovery: `tool_search` nao expos ferramenta Kluster callable nesta sessao.
- Kluster CLI fallback: `C:\Users\mauri\.pnpm\bin\pnpm.CMD dlx kluster-verify --help` falhou com `ERR_PNPM_FETCH_404` para `https://registry.npmjs.org/kluster-verify`.
- Validacao classica focada antes do commit: `py_compile`, `ruff`, `ty` e `pytest` focado passaram.

## 2026-05-03T03:50:00-03:00 Windows release smoke isolation slice

- Scope: impedir que o smoke do orquestrador Windows use `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, cwd ou `SSA_*` do usuario.
- Evidencia: `builds/reports/release_report_windows_amd64.json` gerado para `da964144a82b7e93a3f46ccf239949fc23318547` registrou `DADOS CARREGADOS: 70,954 SSAs` no smoke, enquanto o smoke manual isolado do mesmo executavel retornou sem dados carregados.
- Causa: `Invoke-Smoke` em `dev_env/build/release_windows.ps1` usava `Start-Process` sem ambiente isolado.
- Kluster CLI fallback: `C:\Users\mauri\.pnpm\bin\pnpm.CMD dlx kluster-verify --help` falhou com `ERR_PNPM_FETCH_404` para `https://registry.npmjs.org/kluster-verify`.
