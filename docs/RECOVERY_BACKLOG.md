# Recovery Backlog

Este arquivo registra hardening e limpeza pos-merge da branch de recovery.
O escopo fica dividido por prioridade para manter a entrega segura e incremental.

## Update 2026-03-10 12:45 - PR45 pendencias (hook staged-size + DMG cli-only + docs current truth)

Session timestamp:
1. start: `2026-03-10 12:38:31 -0300`
2. end: `2026-03-10 12:45:00 -0300`

Objetivo do slice:
1. fechar pendencias reais do PR em build/distribuicao sem tocar GUI/layout.
2. corrigir false-pass de limite de arquivo em hook pre-commit.
3. alinhar docs de migracao/handoff com politica de um unico bloco `CURRENT TRUTH`.

Mudancas aplicadas:
1. `scripts/git_hooks/pre-commit`:
   - validacao de tamanho passou para blob staged (`git cat-file -s :path`), evitando bypass por diferenca entre working tree e index.
2. `launchers/build_multiplatform.py`:
   - `post_process(..., apps=...)` agora recebe o escopo de apps.
   - em `macos_arm64` + `package=dmg`, build `cli-only` pula etapa DMG com sucesso (sem exigir `.app`).
3. `tests/test_build_multiplatform_manifest.py`:
   - novo teste cobrindo skip de DMG quando `apps=["cli"]`.
4. docs de controle:
   - `docs/NEXT_CHAT_MIGRATION.md` e `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` normalizados para manter apenas o primeiro bloco como `CURRENT TRUTH`; blocos seguintes viraram `HISTORICAL SNAPSHOT`.

Validacao tecnica desta rodada:
1. `uv run --python 3.13 python -m py_compile launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
2. `uv run --python 3.13 ruff check launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
3. `uv run --python 3.13 ty check launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_build_multiplatform_manifest.py tests/test_create_distribution.py` -> `22 passed`
5. `bash -n scripts/git_hooks/pre-commit` -> pass

Deferido (nao bloqueante neste slice):
1. debts antigos em `launchers/build_multiplatform.py` (naming de metodo "online", concentracao de responsabilidades e custo de manifest em arvores profundas).
2. alerta kluster `pip_exe used before assignment` classificado como falso positivo; variavel e inicializada antes dos ramos condicionais em `setup_virtual_environment`.

## Update 2026-03-10 12:13 - icone oficial cross-OS (blue SSA, sem raio)

Session timestamp:
1. start: `2026-03-10 12:06:08 -0300`
2. end: `2026-03-10 12:13:00 -0300`

Objetivo do slice:
1. fechar um icone oficial simples com tema SSA visivel (versao azul sem raio).
2. gerar artefatos oficiais compativeis com Windows/macOS/Linux.

Mudancas aplicadas:
1. `resources/app_icon.svg` atualizado para layout azul com `SSA` central.
2. geracao oficial:
   - `resources/app_icon.png` (1024x1024)
   - `resources/app_icon.ico` (multi-size: 16/24/32/48/64/128/256)
   - `resources/app_icon.icns` (iconset completo via `iconutil`)
3. fallback operacional adotado para esta rodada:
   - `cairosvg` do venv falhou por bind nativo de `cairo`.
   - geracao feita por `rsvg-convert` + `Pillow` + `iconutil` (sem alterar runtime do app).

Validacao tecnica desta rodada:
1. `file resources/app_icon.svg resources/app_icon.png resources/app_icon.ico resources/app_icon.icns` -> formatos validos confirmados.
2. `uv run --python 3.13 python -m py_compile launchers/convert_icon.py launchers/build_multiplatform.py` -> pass
3. `uv run --python 3.13 ruff check launchers/convert_icon.py launchers/build_multiplatform.py` -> pass
4. `uv run --python 3.13 ty check launchers/convert_icon.py launchers/build_multiplatform.py` -> pass
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_build_multiplatform_manifest.py` -> `4 passed`

Deferido (nao bloqueante neste slice):
1. ajuste no `launchers/convert_icon.py` para fallback nativo automatico sem dependencia de `cairosvg` fica para slice de tooling.
2. variacoes de icone em `resources/icon_variants/*` mantidas como opcao de design (nao usadas no build oficial).

## Update 2026-03-10 12:02 - pipeline macOS com .dmg nativo no build_multiplatform

Session timestamp:
1. start: `2026-03-10 11:55:14 -0300`
2. end: `2026-03-10 12:02:40 -0300`

Objetivo do slice:
1. remover limitacao do pipeline macOS para gerar tambem instalador `.dmg` no mesmo fluxo de build.
2. manter executavel direto (`.app`/onedir) e evitar refatoracao ampla.

Mudancas aplicadas:
1. `launchers/build_multiplatform.py`:
   - `post_process(...)` agora aciona empacotamento DMG quando `post_build.package == "dmg"` em `macos_arm64`.
   - novo `_find_macos_gui_app(...)` para localizar bundle `.app` alvo.
   - novo `_create_macos_dmg(...)` com `hdiutil create ...` (sem shell).
   - novo `_get_macos_dmg_name(...)` para naming canonico unico.
   - `build_platform(...)` agora propaga falha de `post_process` (nao mascara erro de pacote).
2. `launchers/platforms/macos_arm64/build_config.json`:
   - `post_build.package` alterado de `"zip"` para `"dmg"`.
3. `tests/test_build_multiplatform_manifest.py`:
   - novo teste de geracao DMG no `post_process`.
   - novo teste de falha controlada quando `.app` nao existe.

Validacao tecnica desta rodada:
1. `uv run --python 3.13 python -m py_compile launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
2. `uv run --python 3.13 ruff check launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
3. `uv run --python 3.13 ty check launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_build_multiplatform_manifest.py` -> `4 passed`
5. build real:
   - `timeout 1800s uv run --python 3.13 python launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui --skip-venv` -> pass
   - artefato validado: `launchers/dist/macos_arm64/SSA_Consulta_Rapida_v4.32_macos_arm64.dmg` (gerado)
   - `.app` e onedir continuam sendo gerados no mesmo run.

Deferido (nao bloqueante neste slice):
1. pyoxidizer/nuitka continuam trilha experimental; pipeline operacional de release segue PyInstaller.
2. codesign/notarizacao macOS segue fora deste slice (requer ambiente e credenciais de release).

## Update 2026-03-10 11:51 - remove B110/B112 remanescentes no GUI/worker

Session timestamp:
1. start: `2026-03-10 11:47:39 -0300`
2. end: `2026-03-10 11:51:10 -0300`

Objetivo do slice:
1. remover `try/except` proibido (`pass` e `continue`) reportado em `gui/gui_ssa.py` e `gui/workers/data_loader_worker.py`.
2. manter patch minimo sem alterar layout GUI nem fluxo de importacao.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - remove `except Exception: pass` no `finally` do combo rapido de setor executor.
   - remove `except ... continue` na leitura de `import_run_*.json`; troca por:
     - captura especifica (`OSError`, `UnicodeDecodeError`, `json.JSONDecodeError`) com log debug.
     - `continue` fora do bloco `except`.
2. `gui/workers/data_loader_worker.py`:
   - remove `except ... continue` na verificacao de colunas nao nulas.
   - mantem fallback com log debug por coluna, sem suppress silencioso.

Validacao tecnica desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/workers/data_loader_worker.py tests/test_gui_filter_logic.py tests/test_data_loader_worker.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/workers/data_loader_worker.py tests/test_gui_filter_logic.py tests/test_data_loader_worker.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/workers/data_loader_worker.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_data_loader_worker.py tests/test_gui_filter_logic.py -k "quick_setor_executor_combo_applies_filter_and_syncs_or_group_only or DataLoaderWorker or non_null"` -> `2 passed, 157 deselected`
5. `timeout 60s uv run --python 3.13 bandit -q -r gui/gui_ssa.py gui/workers/data_loader_worker.py` -> sem `B110/B112`; sobraram apenas alertas antigos de `subprocess` e SQL dinamico com sanitizacao.

Deferido (nao bloqueante neste slice):
1. debt antigo de arquitetura/performance em `gui/gui_ssa.py` (God class, resize perf, sort perf).
2. alerta kluster sobre chamada `query_db(self.db_path, '', query, raise_on_error=True)` classificado como falso positivo:
   - assinatura real aceita `(db_path, table_name, query, params, raise_on_error)` em `armazenamento/database.py`.

## Update 2026-03-10 11:26 - hotfix build macos util + quick setor executor sync + hooks tamanho

Session timestamp:
1. start: `2026-03-10 10:55:39 -0300`
2. end: `2026-03-10 11:26:00 -0300`
3. commit evidencia: `338614c6`

Objetivo do slice:
1. remover falha de runtime nos binarios macOS (`No module named 'concurrent'` e derivados).
2. endurecer bloqueio de arquivos grandes no fluxo git (pre-commit e pre-push).
3. corrigir UX/sync do quick filter `setor_executor` com filtros avancados, sem persistencia.

Mudancas aplicadas:
1. build/pacote:
   - `launchers/platforms/macos_arm64/build_config.json`
   - `launchers/platforms/windows_amd64/build_config.json`
   - `launchers/platforms/debian_amd64/build_config.json`
   - exclusoes agressivas de stdlib removidas; lista reduzida para `tkinter/test/unittest`.
2. `launchers/build_multiplatform.py`:
   - `--add-data` agora usa separador correto por plataforma (`;` no Windows, `:` no Unix).
   - manifesto agora lista artefatos reais de root (arquivos + diretorios), ignora hidden (`.DS_Store`, `build_manifest.json`) e calcula tamanho de diretorio com guarda de `OSError`.
   - help de `--all` alinhado para comportamento real (apps da plataforma atual, sem cross-compilation).
3. hooks:
   - `scripts/git_hooks/pre-commit`: bloqueio de arquivo staged >= 95MB.
   - `scripts/git_hooks/pre-push` (novo): bloqueio de blob >= 95MB no push.
   - `scripts/install_hooks.sh`: instalacao deterministica (`pre-commit`, `pre-push`) e `core.hooksPath=.git/hooks`.
   - `README.md`: secao de hooks atualizada para o fluxo real.
4. GUI quick filter:
   - `gui/gui_ssa.py`
   - `gui/ssa/gui_filters_advanced_ui.py`
   - `tests/test_gui_filter_logic.py`
   - `setor_executor` no combo rapido agora exibe prefixo explicito no item (`Setor Executor: ...`).
   - sincronismo do quick filter com UI de `Executor` nos filtros avancados (inclui troca de aba e refresh), sem gravar `_advanced_filters`.
5. testes novos:
   - `tests/test_build_multiplatform_manifest.py` (cobre manifesto com diretorios e hidden skip).
6. ajustes adicionais de robustez:
   - `gui/gui_ssa.py`: `import_external_excel_files` simplificado para uso direto de `_build_unique_destination_path` da instancia.
   - `launchers/build_multiplatform.py`: `_compute_directory_size_bytes` ignora symlink para evitar loop acidental em arvore ciclica.

Validacao tecnica desta rodada:
1. `uv run --python 3.13 python -m py_compile launchers/build_multiplatform.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filter_logic.py tests/test_build_multiplatform_manifest.py` -> pass
2. `uv run --python 3.13 ruff check launchers/build_multiplatform.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filter_logic.py tests/test_build_multiplatform_manifest.py` -> pass
3. `uv run --python 3.13 ty check launchers/build_multiplatform.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filter_logic.py tests/test_build_multiplatform_manifest.py` -> pass
4. `uv run --python 3.13 pytest -q tests/test_build_multiplatform_manifest.py tests/test_gui_filter_logic.py -k "quick_setor_executor_combo_applies_filter_and_syncs_or_group_only or setor_executor_order_prioritizes_smin_then_mel_then_alpha"` -> `2 passed`
5. build real:
   - `uv run --python 3.13 python launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui --skip-venv` -> build OK
   - smoke runtime:
     - CLI/GUI nao exibem mais erro de modulo ausente por exclusao de stdlib.

Deferido (nao bloqueante neste slice):
1. debts estruturais antigos do kluster em `launchers/build_multiplatform.py` e `gui/gui_ssa.py` (SRP/performance/global workers).
2. revisar em ciclo proprio se `cleanup_online_unnecessary_files` deve ser separado em utilitario dedicado de manutencao git.

## Update 2026-03-10 10:38 - pente fino completo build/distribuicao (pyinstaller/pyoxidizer/nuitka/pytoexe)

Session timestamp:
1. start: `2026-03-10 10:22:33 -0300`
2. end: `2026-03-10 10:38:24 -0300`

Objetivo do slice:
1. revisar scripts e docs de build/distribuicao para pyinstaller, pyoxidizer, nuitka e pytoexe.
2. validar ferramentas instaladas no host.
3. executar dry-run operacional/tentativa real de pacote e corrigir bloqueadores reais.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_detect_primary_executable_name(...)` agora cobre bundle `.app` e executavel embutido em pasta.
   - `_resolve_inno_source(...)` usa `exe_path` de forma consistente para pyoxidizer/nuitka.
   - `create_inno_setup_script(...)` simplificado com helpers:
     - `_normalize_windows_path(...)`
     - `_build_inno_excludes_str(...)`
     - `_build_inno_iss_content(...)`
   - texto do README gerado alinhado com estrutura pre-criada no pacote.
2. `tests/test_create_distribution.py`:
   - novo `test_detect_primary_executable_name_accepts_app_bundle_directory`.
   - novo `test_resolve_inno_source_pyoxidizer_uses_exe_path_from_build_info`.
   - asserts do ISS atualizados para `SourceDir` macro e mode `absolute`.
3. docs operacionais:
   - `docs/GUIA_DISTRIBUICAO.md`
   - `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
   - `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
   - `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
   - alinhados com status real, trilha historica e suporte `pytoexe/py2exe` (nao suportado).

Verificacao de ferramentas no host:
1. `pyinstaller --version` -> `6.19.0`
2. `nuitka --version` -> `4.0.1`
3. `pyoxidizer --version` -> `0.24.0`
4. `iscc` -> `NOT_FOUND`
5. `pytoexe`/`py2exe` -> `NOT_FOUND`

Dry-run/tentativa real de pacote:
1. `pyinstaller --skip-installer` -> OK (ZIP gerado)
2. `pyinstaller` -> ZIP OK, installer FAIL (origem Windows/Inno nao resolvida neste host)
3. `nuitka --skip-installer` -> FAIL (`builds/nuitka` ausente)
4. `pyoxidizer --skip-installer` -> FAIL (`builds/pyoxidizer` ausente)
5. `pytoexe` -> FAIL esperado (choice invalida)
6. evidencia consolidada: `/tmp/ssa_pack_audit_20260310_1030/summary.log`

Validacao tecnica desta rodada:
1. kluster clean em:
   - `scripts/create_distribution.py`
   - `tests/test_create_distribution.py`
   - `docs/GUIA_DISTRIBUICAO.md`
   - `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
   - `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
   - `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
2. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `17 passed`

Deferido (nao bloqueante neste slice):
1. validar fluxo de installer em host Windows com ISCC e build `windows_amd64` disponivel.
2. debt de qualidade em `_has_primary_executable` (funcao ainda concentrada).

## Update 2026-03-10 10:15 - fechamento dos 3 itens em loop no ISS/resolve/zip

Session timestamp:
1. start: `2026-03-10 10:07:22 -0300`
2. end: `2026-03-10 10:15:45 -0300`

Objetivo do slice:
1. eliminar risco semantico do path `Source` no `.iss`.
2. alinhar definitivamente `resolve` vs `failure_reason`.
3. reduzir concentracao em `create_zip_package` para remover apontamento recorrente.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_resolve_inno_source(...)` agora usa `exe_path` do `BUILD_SYSTEMS` de forma consistente (incluindo pyoxidizer).
   - `create_inno_setup_script(...)` foi simplificado com helpers:
     - `_normalize_windows_path(...)`
     - `_build_inno_excludes_str(...)`
     - `_build_inno_iss_content(...)`
   - template ISS passou a usar `SourceDir` macro explicita e mode fixo `absolute`.
   - `create_zip_package(...)` segue com staging modular e sem voltar ao bloco monolitico.
2. `tests/test_create_distribution.py`:
   - ajustes de asserts para `SourceDir` macro e mode `absolute`.
   - novo teste `test_resolve_inno_source_pyoxidizer_uses_exe_path_from_build_info`.
   - mantidos os testes de regressao para `resolve` vs `failure_reason`.

Validacao desta rodada:
1. `kluster review file scripts/create_distribution.py` -> clean
2. `kluster review file tests/test_create_distribution.py` -> clean
3. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
6. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `16 passed`

Deferido (nao bloqueante neste slice):
1. validacao final em maquina Windows com ISCC real continua recomendada, mesmo com kluster e testes locais verdes.

## Update 2026-03-10 10:08 - cobertura de regressao para resolve vs failure_reason (pyinstaller)

Session timestamp:
1. start: `2026-03-10 10:07:22 -0300`
2. end: `2026-03-10 10:08:49 -0300`

Objetivo do slice:
1. comprovar por teste que `_resolve_build_directory_failure_reason` nao mascara caso `legacy sem executavel` como `diretorio ausente`.
2. travar por regressao os casos `canonical sem exe` e `legacy sem exe`.

Mudancas aplicadas:
1. `tests/test_create_distribution.py`:
   - novo `test_failure_reason_pyinstaller_reports_canonical_missing_primary_executable`
   - novo `test_failure_reason_pyinstaller_reports_legacy_missing_primary_executable`
2. runtime nao alterado neste micro-slice.

Validacao desta rodada:
1. `kluster review file tests/test_create_distribution.py` -> clean
2. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `15 passed`

Deferido (nao bloqueante neste slice):
1. validacao em Windows/ISCC real para risco semantico de path `Source` no `.iss`.
2. debt de concentracao residual em `create_zip_package` e `create_inno_setup_script`.

## Update 2026-03-10 10:05 - modularizacao minima em create_zip_package + define SourcePath

Session timestamp:
1. start: `2026-03-10 10:01:24 -0300`
2. end: `2026-03-10 10:05:18 -0300`

Objetivo do slice:
1. reduzir concentracao em `create_zip_package` com extracao minima de blocos.
2. corrigir tipagem de `build_name` em `VERSION.txt`.
3. eliminar risco de macro indefinida no `.iss` com define explicito de `SourcePath`.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - novos helpers de ZIP:
     - `_copy_runtime_bundle(...)`
     - `_write_package_version_file(...)`
     - `_create_package_zip(...)`
   - `create_zip_package(...)` ficou como orquestrador dos helpers.
   - `build_name` normalizado para `str` antes de escrever metadata.
   - `create_inno_setup_script(...)` agora define `#define SourcePath "{dist_output_resolvido}"`.
2. `tests/test_create_distribution.py`:
   - asserts novos para validar `#define SourcePath "..."` nos cenarios relative/absolute.

Validacao desta rodada:
1. `kluster review file scripts/create_distribution.py` -> 3 issues:
   - 1 HIGH semantic (path Source absoluto/relativo no .iss, sem repro local)
   - 2 MEDIUM antigos (fallback reason e funcao longa)
2. `kluster review file tests/test_create_distribution.py` -> clean
3. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
6. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. validar em runner Windows com ISCC real o cenario de `Source` absoluto no `.iss`.
2. debt antigo de sincronia entre `_resolve_build_directory` e `_resolve_build_directory_failure_reason`.
3. debt de concentracao residual em `create_zip_package` (melhorado, nao zerado).

## Update 2026-03-10 09:59 - extracao minima de responsabilidades em compile_installer

Session timestamp:
1. start: `2026-03-10 09:57:26 -0300`
2. end: `2026-03-10 09:59:27 -0300`

Objetivo do slice:
1. reduzir concentracao de responsabilidade em `compile_installer` com patch minimo.
2. manter comportamento/retornos identicos (`success|missing|failed`).

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - adicionado `_get_iscc_path()` para descoberta/validacao do compilador.
   - adicionado `_run_iscc_compile(...)` para execucao e tratamento de retorno.
   - `compile_installer(...)` agora orquestra os dois blocos, sem alterar contrato externo.

Validacao desta rodada:
1. `timeout 120s kluster review file scripts/create_distribution.py` -> 1 issue (debt antigo de `create_zip_package`, fora de escopo)
2. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. debt antigo de qualidade em `create_zip_package` (funcao longa).

## Update 2026-03-10 09:55 - marcador explicito de modo SourcePath no Inno

Session timestamp:
1. start: `2026-03-10 09:51:50 -0300`
2. end: `2026-03-10 09:55:10 -0300`

Objetivo do slice:
1. manter `OutputDir={#SourcePath}` e tornar explicito se a origem de `Source` foi resolvida em modo relativo ou absoluto.
2. reforcar cobertura de teste para evitar regressao de fallback.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `create_inno_setup_script(...)` agora define `source_path_mode` (`relative` por padrao, `absolute` no fallback de `relpath`).
   - template `.iss` ganhou `#define SourcePathMode "..."`
2. `tests/test_create_distribution.py`:
   - teste de caminho relativo agora valida `#define SourcePathMode "relative"`.
   - teste de fallback absoluto agora valida `#define SourcePathMode "absolute"`.

Validacao desta rodada:
1. `timeout 120s kluster review file scripts/create_distribution.py` -> 3 issues (1 semantico intencional + 2 debts fora de escopo)
2. `timeout 120s kluster review file tests/test_create_distribution.py` -> clean
3. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
5. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
6. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. manter `OutputDir={#SourcePath}` como decisao intencional deste ciclo.
2. debt de qualidade em `create_zip_package` e `compile_installer` seguem para ciclo dedicado.

## Update 2026-03-10 09:33 - hardening de trust para INNO_SETUP_COMPILER

Session timestamp:
1. start: `2026-03-10 09:31:56 -0300`
2. end: `2026-03-10 09:33:49 -0300`

Objetivo do slice:
1. endurecer override de compilador Inno via `INNO_SETUP_COMPILER`.
2. aceitar override somente quando cumprir regras minimas de confianca.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `compile_installer(...)` agora valida `INNO_SETUP_COMPILER` com regras:
     - caminho absoluto
     - nome `iscc`/`iscc.exe`
     - arquivo existente
     - parent dentro de allowlist confiavel (Program Files Inno Setup e parent de `shutil.which("iscc")` quando existir).
   - override invalido nao interrompe fluxo; apenas loga motivo e segue para PATH/hardcoded.
2. `tests/test_create_distribution.py`:
   - novo `test_compile_installer_rejects_relative_env_override`.
   - novo `test_compile_installer_accepts_absolute_env_override_in_trusted_parent`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. debt de qualidade: `create_zip_package` segue longa.
2. debt semantico geral de resolucao por build system segue para ciclo dedicado.
3. validacao de path/semantica do Source do Inno em ambiente Windows real segue para rodada dedicada.
4. kluster final desta rodada sinalizou HIGH em `Source` relativo do Inno; sem repro nos testes locais, manter para confirmacao em runner Windows com ISCC real.

## Update 2026-03-10 09:28 - Source do Inno com relpath real + fallback absoluto

Session timestamp:
1. start: `2026-03-10 09:26:49 -0300`
2. end: `2026-03-10 09:28:34 -0300`

Objetivo do slice:
1. remover prefixo fixo `..\\..\\` na origem do Inno Setup.
2. usar caminho relativo real entre `DIST_OUTPUT` e `source_dir`, com fallback absoluto seguro.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `create_inno_setup_script` agora calcula `source_dir_spec` via `os.path.relpath(source_dir, DIST_OUTPUT)`.
   - se `relpath` falhar, cai para `str(source_dir.resolve())`.
   - normalizacao unica para formato Windows: `replace("/", "\\")` + remocao de aspas.
2. `tests/test_create_distribution.py`:
   - `test_create_inno_setup_script_uses_sourcepath_outputdir` agora tambem valida `Source` relativo esperado.
   - novo `test_create_inno_setup_script_uses_absolute_source_when_relpath_fails`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `11 passed`

Deferido (nao bloqueante neste slice):
1. debt de qualidade: `create_zip_package` continua longa.
2. debt semantico geral de resolucao por build system continua para ciclo dedicado.
3. deduplicacao de setup dos testes continua para ciclo de manutencao.

## Update 2026-03-10 09:23 - OutputDir do Inno deterministico via SourcePath

Session timestamp:
1. start: `2026-03-10 09:22:09 -0300`
2. end: `2026-03-10 09:23:45 -0300`

Objetivo do slice:
1. remover ambiguidade de saida do instalador Inno em relacao ao cwd.
2. manter patch minimo sem alterar fluxo de compilacao fora do escopo.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `OutputDir=.` substituido por `OutputDir={#SourcePath}` no template `.iss`.
2. `tests/test_create_distribution.py`:
   - novo teste `test_create_inno_setup_script_uses_sourcepath_outputdir`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `10 passed`

Deferido (nao bloqueante neste slice):
1. debt de qualidade: `create_zip_package` segue longa.
2. debt semantico geral de resolucao por build system segue para ciclo dedicado.
3. duplicacao de setup em testes segue para refino futuro.

## Update 2026-03-10 09:18 - fallback explicito canonical->legacy para pyinstaller

Session timestamp:
1. start: `2026-03-10 09:16:57 -0300`
2. end: `2026-03-10 09:18:24 -0300`

Objetivo do slice:
1. deixar explicito no fluxo que pyinstaller tenta canonical e cai para legacy quando canonical nao for valido.
2. cobrir fallback com teste dedicado para reduzir ambiguidade semantica.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_resolve_build_directory` reorganizado para tornar fallback canonical->legacy explicito no corpo da funcao.
   - sem mudanca de comportamento fora do escopo.
2. `tests/test_create_distribution.py`:
   - novo teste `test_resolve_build_directory_pyinstaller_falls_back_to_legacy_when_canonical_invalid`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `9 passed`

Deferido (nao bloqueante neste slice):
1. debt de qualidade em `create_zip_package` (funcao longa) permanece.
2. debt semantico geral de tratamento por build system (resolver unificado vs especifico) permanece para ciclo dedicado.

## Update 2026-03-10 09:11 - erro explicito de resolucao de build (dir vs executavel)

Session timestamp:
1. start: `2026-03-10 09:09:50 -0300`
2. end: `2026-03-10 09:11:25 -0300`

Objetivo do slice:
1. separar no log de empacotamento os casos "diretorio ausente" e "executavel ausente".
2. manter retorno de `_resolve_build_directory` sem refatoracao ampla.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - novo helper `_resolve_build_directory_failure_reason(build_system)` para detalhar causa de falha.
   - `create_zip_package(...)` agora loga erro com motivo especifico de resolucao.
2. `tests/test_create_distribution.py`:
   - ajuste de asserts para mensagens especificas de "executavel ausente" em diretorio legacy/canonico.
   - novo teste `test_create_zip_package_returns_none_when_build_directory_is_missing`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `8 passed`

Deferido (nao bloqueante neste slice):
1. debt de qualidade em `create_zip_package` (funcao longa) permanece.
2. debt semantico em `_resolve_build_directory` (separar resolver dir de validar executavel) permanece para slice dedicado.
3. duplicacao de setup nos testes de distribuicao permanece como debt de manutencao (nao funcional).

## Update 2026-03-10 08:49 - remocao de fallback generico de executavel no pacote

Session timestamp:
1. start: `2026-03-10 08:48:01 -0300`
2. end: `2026-03-10 08:49:45 -0300`

Objetivo do slice:
1. remover fallback literal `executavel_principal` na deteccao do binario do pacote.
2. falhar explicitamente quando nao houver executavel detectavel no staged package.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_detect_primary_executable_name(...)` agora retorna `Optional[str]`.
   - retorno fallback foi removido (`None` quando nao ha executavel).
   - `create_zip_package(...)` agora aborta com erro explicito se a deteccao retornar `None`.
   - `_build_bundle_ignore(...)` passou a inferir tipo real (`arquivo`/`diretorio`) via `_src/name` antes de aplicar `_should_skip_bundle_entry(...)`.
2. `tests/test_create_distribution.py`:
   - novo teste `test_detect_primary_executable_name_returns_none_when_package_has_no_binary`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `7 passed`

Deferido (nao bloqueante neste slice):
1. `create_zip_package` continua com debt de funcao longa (qualidade).
2. alerta semantico amplo do kluster para `_resolve_build_directory` (separacao de responsabilidade entre resolver dir e validar executavel) fica para slice dedicado.
3. rodada agregada do kluster sinalizou risco de trust em `INNO_SETUP_COMPILER`; fluxo atual ja valida nome permitido + existencia de arquivo, e hardening de trust por allowlist de diretorios fica para ciclo de seguranca dedicado.
4. rodada agregada tambem sinalizou path absoluto do Inno e heuristica de executavel pyinstaller; sem repro de regressao nos gates desta rodada, mantido como debt para validacao com ambiente Windows dedicado.

## Update 2026-03-10 08:43 - selecao deterministica + consolidacao de filtro sanitizado

Session timestamp:
1. start: `2026-03-10 08:39:15 -0300`
2. end: `2026-03-10 08:43:39 -0300`

Objetivo do slice:
1. remover dependencia de `mtime` na escolha do build canonico de pyinstaller.
2. tornar selecao deterministica pela ordem declarada em `canonical_dirs`.
3. unificar regra de exclusao de bundle para evitar divergir top-level e nested.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_resolve_build_directory("pyinstaller")` agora retorna o primeiro path valido na ordem de `canonical_dirs`.
   - removida selecao por `max(..., st_mtime)`.
   - novo predicado unico `_should_skip_bundle_entry(...)` usado por `_copy_build_tree_sanitized` e `_build_bundle_ignore`.
2. `tests/test_create_distribution.py`:
   - novo teste `test_resolve_build_directory_pyinstaller_prefers_canonical_order_over_mtime`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `6 passed`
5. `kluster review` final no codigo/docs tocados -> sem blocker funcional; sobrou 1 debt de qualidade (funcao longa).

Deferido (nao bloqueante neste slice):
1. `create_zip_package` continua com debt de funcao longa (qualidade).
2. alerta semantico amplo do kluster sobre caminhos nao-pyinstaller ficou sem alteracao por falta de evidencia de regressao neste slice.
3. alerta de path cross-drive do Inno permanece como debt conhecido, sem impacto no escopo atual.
4. fallback generico de `_detect_primary_executable_name` (`executavel_principal`) segue como debt semantico para tratamento dedicado.

## Update 2026-03-10 08:28 - hardening final do empacotador (status de instalador + copia sanitizada)

Session timestamp:
1. start: `2026-03-10 08:22:45 -0300`
2. end: `2026-03-10 08:31:40 -0300`

Objetivo do slice:
1. remover ambiguidade de status no fluxo de compilacao de instalador.
2. aplicar sanitizacao consistente de copia em todos os caminhos de bundle.
3. fechar ajustes sem alterar conceito de empacotamento canonico.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - `_copy_build_tree` renomeado para `_copy_build_tree_sanitized`.
   - novo `SENSITIVE_LOCAL_EXTENSIONS` e helper `_build_bundle_ignore(...)`.
   - `copytree` de `_internal` e `config` agora aplica `ignore` sanitizado.
   - `compile_installer(...)` agora retorna status explicito: `success|missing|failed`.
   - status `script_failed` adicionado no caller para separar falha de geracao `.iss`.
   - relatorio final diferencia "Inno Setup nao disponivel" de "falha na compilacao".
   - `arcname` do ZIP agora usa base em `package_dir` para maior robustez.
   - validacao de `.app` exige binario executavel em `Contents/MacOS` ou fallback executavel no bundle.
   - referencia de antivirus no readme corrigida para `ANTIVIRUS_EXCLUSOES.md`.
   - copia de `README.md` no bundle mantida como `LEIA-ME.md`.
2. `tests/test_create_distribution.py`:
   - novo teste `test_compile_installer_returns_missing_when_iscc_is_unavailable`.
3. `docs/GUIA_DISTRIBUICAO.md`:
   - troubleshooting separado para "compiler ausente" vs "falha de compilacao".

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `5 passed`
5. `kluster review` no codigo/docs tocados -> sem blocker funcional apos ajustes; sobram debts de qualidade/semantica catalogados abaixo.

Deferido (nao bloqueante neste slice):
1. `scripts/create_distribution.py`: `create_zip_package` continua concentrando responsabilidades (debt de qualidade).
2. `kluster` apontou risco de selecao por mtime em canonical dirs; comportamento atual e intencional por prioridade de build mais recente e ficou sem alteracao neste slice.
3. `kluster` apontou risco cross-drive em source de Inno; fluxo atual ja trata caminho absoluto via fallback de `ValueError`, sem regressao funcional observada nos gates.
4. `kluster` apontou cleanup de temp em early-return; fluxo ja remove `temp_dir` nesses caminhos (classificado como falso positivo na rodada final).

## Update 2026-03-10 08:25 - validacao de executavel primario no empacotamento

Session timestamp:
1. start: `2026-03-10 08:15:30 -0300`
2. end: `2026-03-10 08:25:00 -0300`

Objetivo do slice:
1. evitar pacote ZIP invalido quando diretorio canonico tem conteudo parcial.
2. exigir executavel primario antes de aceitar build dir no empacotamento.
3. manter comportamento default e adicionar configurabilidade minima para canonical dirs em teste/laboratorio.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - novo helper `_get_pyinstaller_canonical_dirs()` para canonical dirs configuraveis via `BUILD_SYSTEMS["pyinstaller"]["canonical_dirs"]` com fallback default.
   - novo helper `_has_primary_executable(build_dir, build_system)` para validar executavel primario.
   - `_resolve_build_directory(...)` agora filtra candidatos por conteudo + executavel valido.
   - `_resolve_inno_source(...)` e `_is_canonical_pyinstaller_directory(...)` passam a usar a mesma origem de canonical dirs.
2. `tests/test_create_distribution.py`:
   - novo teste `test_create_zip_package_returns_none_when_canonical_has_no_primary_executable`.
   - mocks de `BUILD_SYSTEMS` atualizados para declarar `canonical_dirs`.
3. `docs/GUIA_DISTRIBUICAO.md`:
   - troubleshooting atualizado com regra de validacao de executavel primario.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `4 passed`
5. `kluster review file scripts/create_distribution.py tests/test_create_distribution.py` -> clean.

Deferido (nao bloqueante neste slice):
1. hardening mais profundo de matriz por plataforma no empacotador (slice dedicado de distribuicao cross-platform).

## Update 2026-03-10 08:18 - alinhamento Debian para fluxo canonico ZIP

Session timestamp:
1. start: `2026-03-10 08:07:20 -0300`
2. end: `2026-03-10 08:18:00 -0300`

Objetivo do slice:
1. alinhar `debian_amd64` ao comportamento real do pipeline canonico (ZIP).
2. remover riscos de runtime por exclusao agressiva de modulos core no build Debian.
3. documentar claramente que AppImage/.deb ficam fora do fluxo oficial atual.

Mudancas aplicadas:
1. `launchers/platforms/debian_amd64/build_config.json`:
   - `post_build.package`: `appimage` -> `zip`.
   - removeu `json` de `exclude_modules` (risco alto de runtime).
   - removeu `argparse` de `exclude_modules` (risco alto para CLI).
   - removeu exclusoes core de risco (`multiprocessing`, `concurrent`, `asyncio`, `email`, `http`, `urllib`).
2. docs operacionais:
   - `docs/GUIA_DISTRIBUICAO.md`: nota explicita de Debian em ZIP no baseline atual.
   - `docs/BUILD_MULTIPLATFORM.md`: texto de UPX ajustado para "quando disponivel" e bloco de empacotamento Debian.

Validacao desta rodada:
1. `kluster review file launchers/platforms/debian_amd64/build_config.json docs/GUIA_DISTRIBUICAO.md docs/BUILD_MULTIPLATFORM.md` -> clean (0 issues) na rodada final.

Deferido (nao bloqueante neste slice):
1. suporte real a AppImage/.deb como etapa automatica (ciclo dedicado).
2. revisao equivalente de `exclude_modules` para outras plataformas (windows/macos) em slice proprio.

## Update 2026-03-10 08:04 - hardening de build para nao embedar dados locais por padrao

Session timestamp:
1. start: `2026-03-10 07:47:17 -0300`
2. end: `2026-03-10 08:04:00 -0300`

Objetivo do slice:
1. remover inclusao implicita de `data/` no build canonico.
2. reforcar cobertura de empacotamento para exclusao de arquivos locais sensiveis.
3. manter trilha de copia de dados apenas por comando explicito com `--allow-local-data`.

Mudancas aplicadas:
1. `launchers/build_multiplatform.py`:
   - `data/` nao entra mais por padrao no `--add-data`.
   - nova chave de controle em runtime de build: `pyinstaller_args.include_local_data` (default `False`).
   - quando ativada, log explicito de risco operacional.
2. `tests/test_create_distribution.py`:
   - novo teste `test_create_zip_package_excludes_local_data_and_excel_from_canonical_pyinstaller`.
   - cobre exclusao de `.db`, `.xlsx`, `.xls` e ausencia de conteudo sensivel de `data/` e `docs_entrada/`.
3. docs operacionais:
   - `docs/GUIA_DISTRIBUICAO.md`: politica de dados locais no build explicitada.
   - `docs/BUILD_MULTIPLATFORM.md`: regra v4.32+ de nao embedar `data/` por padrao.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile launchers/build_multiplatform.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check launchers/build_multiplatform.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check launchers/build_multiplatform.py tests/test_create_distribution.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `3 passed`
5. `kluster review file launchers/build_multiplatform.py tests/test_create_distribution.py` -> sem blocker novo do slice; ficaram debts antigos estruturais fora de escopo.

Deferido (nao bloqueante neste slice):
1. debt antigo de naming/semantica do `MultiPlatformBuilder` versus limitacao de cross-compile.
2. debt antigo de concentracao de responsabilidades no builder (build + git + cleanup).
3. debt antigo de performance em varreduras recursive + subprocess por arquivo na limpeza de git/cache.

## Update 2026-03-10 07:44 - prune workers deduplicado com cobertura de regressao

Session timestamp:
1. start: `2026-03-10 06:21:27 -0300`
2. end: `2026-03-10 07:44:19 -0300`

Objetivo do slice:
1. reduzir duplicacao entre prunes de workers sem refatoracao ampla.
2. preservar semantica atual de TTL/cap e limpeza de meta.
3. adicionar cobertura focada no fluxo real de prune de rescan.

Mudancas aplicadas:
1. `gui/ssa/gui_workers.py`:
   - novo helper `_classify_and_update_global_workers_locked(...)` para consolidar classificacao global TTL/cap e atualizacao de `global_workers`.
   - `prune_retired_data_loader_workers(...)` passou a reutilizar o helper no bloco global.
   - `prune_retired_rescan_workers(...)` passou a reutilizar o helper com `drop_orphaned_meta=True`.
2. `tests/test_gui_workers_rescan_data.py`:
   - novo teste `test_prune_retired_rescan_workers_expires_oldest_when_above_cap` cobrindo expurgo do worker mais antigo quando estoura `max_global_workers`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> pass
3. `uv run --python 3.13 ty check gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> pass
4. `timeout 600s uv run --python 3.13 pytest -q tests/test_gui_workers_rescan_data.py` -> `10 passed`
5. `kluster review file gui/ssa/gui_workers.py tests/test_gui_workers_rescan_data.py` -> 3 issues medias fora de escopo (arquitetura/performance em `on_data_loaded` e prompt em `rescan_data`), sem novo blocker deste slice.

Deferido (nao bloqueante neste slice):
1. separar `on_data_loaded` (god-function) em ciclo dedicado.
2. desacoplar prompt interativo de `rescan_data` para caller.
3. mover sanitizacao/sort pesado do UI thread para worker em slice de performance dedicado.

## Update 2026-03-10 06:14 - doc sync build/distribuicao v4.32

Session timestamp:
1. start: `2026-03-10 06:14:00 -0300`
2. end: `2026-03-10 06:18:25 -0300`

Objetivo do slice:
1. sincronizar guias de build/distribuicao com o fluxo canonico atual.
2. remover referencias quebradas como caminho principal (`build_*.bat`, `builds/*`, `pyoxidizer.bzl`).
3. manter referencias antigas apenas como historico documentado.

Mudancas aplicadas:
1. `docs/GUIA_DISTRIBUICAO.md`:
   - documento refeito para v4.32.
   - build canonico com `launchers/build_multiplatform.py`.
   - empacotamento com `scripts/create_distribution.py`.
   - instrucoes de instalador e checklist atualizados.
2. `launchers/README.md`:
   - atualizado para plataformas ativas reais (`windows_amd64`, `macos_arm64`, `debian_amd64`).
   - removeu narrativa antiga de targets `x86/x64/intel` fora do estado atual.
3. `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`:
   - bloco `CURRENT TRUTH` + aviso de snapshot historico.
4. `docs/BUILD_NUITKA_GUIA_COMPLETO.md`:
   - bloco `CURRENT TRUTH` declarando trilha experimental.
5. `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`:
   - bloco `CURRENT TRUTH` declarando trilha laboratorio e nao operacional.

Validacao desta rodada:
1. `kluster review file docs/GUIA_DISTRIBUICAO.md launchers/README.md docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md docs/BUILD_NUITKA_GUIA_COMPLETO.md docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md` -> clean (0 issues)

Deferido (nao bloqueante neste slice):
1. referencias legadas dentro de secoes historicas extensas dos guias completos foram mantidas para contexto tecnico.

## Update 2026-03-10 02:39 - alinhamento de distribuicao para caminho canonico

Session timestamp:
1. start: `2026-03-10 02:39:46 -0300`
2. end: `2026-03-10 06:10:31 -0300`

Objetivo do slice:
1. alinhar scripts de distribuicao ao caminho canonico `launchers/dist`.
2. manter fallback legado (`builds/*`) para compatibilidade.
3. endurecer caminho de instalador Inno e reduzir risco de vazamento acidental de dados locais.

Mudancas aplicadas:
1. `scripts/create_distribution.py`:
   - novo resolve de build com prioridade para `launchers/dist/{windows_amd64,macos_arm64,debian_amd64}`.
   - fallback legado mantido para `builds/*`.
   - pacote ZIP em caminho canonico pyinstaller agora copia arvore do build canonico.
   - README de pacote agora usa executavel detectado dinamicamente.
   - Inno Setup agora:
     - resolve exe de origem com suporte a build canonico windows.
     - aceita `INNO_SETUP_COMPILER` e `iscc` no PATH antes de caminhos hardcoded.
     - corrige `OutputDir=.` no `.iss`.
     - corrige `SetupIconFile=..\\assets\\icon.ico`.
     - sincroniza exclusoes com politica de bundle (`EXCLUDED_BUNDLE_ITEMS`).
   - exclusoes de bundle adicionadas para evitar empacotar dados locais (`data`, `docs_entrada`, `.db`, `.xlsx`, etc.) no caminho canonico.
2. `scripts/copy_data_to_builds.py`:
   - resolve alvos pyinstaller no caminho canonico `launchers/dist/<plataforma>`.
   - fallback legado mantido para `builds/*`.
   - inclui bloqueio explicito por seguranca: exige `--allow-local-data` para copiar DB/Excel locais.
3. `tests/test_create_distribution.py`:
   - novo teste cobrindo fallback canonico pyinstaller (`launchers/dist/windows_amd64`).
   - ajuste do teste legado para nova mensagem de erro.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile scripts/create_distribution.py scripts/copy_data_to_builds.py tests/test_create_distribution.py` -> pass
2. `uv run --python 3.13 ruff check scripts/create_distribution.py scripts/copy_data_to_builds.py tests/test_create_distribution.py` -> pass
3. `uv run --python 3.13 ty check scripts/create_distribution.py scripts/copy_data_to_builds.py tests/test_create_distribution.py` -> pass
4. `uv run --python 3.13 pytest -q tests/test_create_distribution.py` -> `2 passed`

Deferido (nao bloqueante neste slice):
1. `scripts/create_distribution.py`: `create_zip_package` ainda concentrando responsabilidade (debt de qualidade, sem refatoracao ampla agora).
2. `scripts/create_distribution.py`: modelagem de atalhos GUI/CLI no Inno pode ser refinada para bins separados em ciclo dedicado.
3. consolidacao de constantes compartilhadas entre scripts de distribuicao em modulo comum (debt de manutencao).

## Update 2026-03-10 01:11 - bugfix real + testes/docs sem mudanca estrutural

Session timestamp:
1. start: `2026-03-10 01:11:31 -0300`
2. end: `2026-03-10 02:36:33 -0300`

Objetivo do slice:
1. corrigir bugs reais de baixo/medio risco sem refatoracao ampla.
2. atacar pendencias principais de testes/docs nao bloqueantes.
3. manter decisoes intencionais sem alteracao.

Mudancas aplicadas:
1. `armazenamento/database.py`:
   - cache de resolucao de tabela agora usa presenca de chave (`cache_key in cache`) em vez de truthy check.
   - hardening de variaveis locais em `initialize_database` para evitar ambiguidade no fallback do schema.
2. `armazenamento/database_validation.py`:
   - coluna obrigatoria ausente deixa de ser skip silencioso; gera violacao estruturada.
   - erro de validacao agora inclui tipo da excecao e log com stacktrace.
3. `extracao/extractor.py`:
   - `_debug_phases` agora preserva fase global e chave por planilha (`<sheet>:<phase>`), sem sobrescrever contexto.
4. `utils/robust_importer.py`:
   - ajuste de resolucao semantica para `sn`.
   - sufixo fora de faixa em duplicadas semanticas deixa de colapsar na ultima opcao fixa.
5. `gui/gui_ssa.py`:
   - fallback de nome unico em importacao externa mantido retrocompativel com stubs de teste.
   - validacao de alvo local bloqueia basename iniciando com `-` (defesa de argumento acidental em fallback externo).
6. `gui/ssa/gui_workers.py`:
   - `_classify_workers_for_ttl` passa a usar `max_global_workers` (expira overflow mais antigo).
   - logs de expiracao incluem identificador do worker.
   - `load_data` registra worker no global logo apos `start()`.
7. `gui/mixins/tab_context_gui_ssa_mixin.py`:
   - unblock de sinais com guarda (`signals_blocked`) para evitar inconsistencias de estado.
8. `gui/ssa/gui_theme.py`:
   - reaplicacao de QSS global considera stylesheet atual do app, nao apenas cache local.
9. `tests/test_gui_workers_rescan_data.py`:
   - teste de classificacao TTL atualizado para contrato com cap ativo.
10. `tests/test_gui_filter_logic.py`:
   - remove `qWait(360)` hardcoded; usa intervalo real do timer + margem.
11. `tests/test_db_reset_and_upsert.py`:
   - assert de reimport reforcado (`filled_count == row_count`).
12. `docs/TROUBLESHOOTING_IMPORTACAO.md`:
   - comandos usam `PY_RUNTIME` em vez de hardcode fixo de versao.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile ...` (arquivos tocados) -> pass
2. `uv run --python 3.13 ruff check ...` (arquivos tocados) -> pass
3. `uv run --python 3.13 ty check ...` (arquivos tocados) -> pass
4. `timeout 600s uv run --python 3.13 pytest -q ... -k "classify_workers_for_ttl or quick_setor_executor_combo_applies_filter_and_syncs_or_group_only or resize_event_coalesces_width_recompute_with_restartable_timer or apply_theme_skips_global_qss_rebuild_when_cached_theme_matches or smart_upsert_reimport_keeps_single_sanitized_column or validate_missing_data_cadastro_exceptions_keep_non_allowed_invalid or import_external_excel_files"` -> `8 passed`
5. `timeout 600s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_import_run_report.py tests/test_gui_workers_signal_connect.py` -> `35 passed`
6. `timeout 600s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "apply_theme_reuses_cached_details_font_when_base_size_unchanged or apply_theme_skips_global_qss_rebuild_when_cached_theme_matches or quick_setor_executor_combo_applies_filter_and_syncs_or_group_only or resize_event_coalesces_width_recompute_with_restartable_timer"` -> `4 passed`

Deferido (nao bloqueante neste slice):
1. debts estruturais amplos apontados por kluster (God class GUI, performance global de resize/sort, rework de robust_importer por I/O).

## Update 2026-03-10 00:55 - hotfix rapido de Setor Executor (sem sync avancado)

Session timestamp:
1. start: `2026-03-10 00:55:26 -0300`
2. end: `2026-03-10 01:00:00 -0300`

Objetivo do slice:
1. remover acoplamento indevido do atalho rapido `Setor Executor` com `_advanced_filters`.
2. manter apenas sync no OR group de filtros por coluna (`setor_executor`/`setor_emissor`).
3. preservar popup rolavel e sem persistencia.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - remove chamada `_sync_quick_setor_executor_into_advanced_filters(selected)` em `_on_quick_setor_executor_changed`.
   - remove helper `_sync_quick_setor_executor_into_advanced_filters`.
   - mantem sync de OR group via `_sync_or_group_values("setor_executor", selected)`.
2. `tests/test_gui_filter_logic.py`:
   - atualiza teste para novo contrato:
     - quick combo sincroniza apenas filtros por coluna/OR group.
     - `_advanced_filters` permanece inalterado.
     - popup continua limitado (`maxVisibleItems=14` + `combobox-popup: 0`).

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "quick_setor_executor_combo_applies_filter_and_syncs_or_group_only or profile_or_filters_executor_or_emissor or sync_or_group_values"` -> `2 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (God class, resize/sort no UI thread, worker retention global, vacuum/analyze).

## Update 2026-03-10 00:42 - sync completo do atalho Setor Executor + popup com rolagem real

Session timestamp:
1. start: `2026-03-10 00:42:00 -0300`
2. end: `2026-03-10 00:46:00 -0300`

Objetivo do slice:
1. sincronizar atalho rapido `Setor Executor` com filtros avancados (executor + emissor).
2. garantir popup com altura limitada e rolagem no combo rapido.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - combo rapido recebeu:
     - `maxVisibleItems=14`
     - estilo `combobox-popup: 0` para evitar popup nativo sem controle de altura
     - scrollbar vertical `AsNeeded` no `view()`
   - novo sync explicito no atalho rapido:
     - `_sync_quick_setor_executor_into_advanced_filters(selected)`
     - atualiza `_advanced_filters` para `setor_executor` e `setor_emissor`
     - limpa `setor_executor_exclude_values` e `setor_emissor_exclude_values`
     - sincroniza UI avancada via `_sync_advanced_filter_ui()`
   - `_on_quick_setor_executor_changed` agora chama o sync avancado antes do refresh final.
2. `tests/test_gui_filter_logic.py`:
   - teste do atalho rapido passou a validar:
     - estilo popup (`combobox-popup: 0`)
     - sync em `_advanced_filters` para executor/emissor
     - excludes limpos no sync rapido.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "quick_setor_executor_combo_applies_filter_and_syncs_panel or quick_setor_executor or num_reprogramacoes"` -> `5 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos em `gui/gui_ssa.py` (God class, performance ampla de resize/sort no UI thread, worker retention global).

## Update 2026-03-10 00:36 - low-stress hardening (cache sort + tooltip + QUrl explicit)

Session timestamp:
1. start: `2026-03-10 00:36:03 -0300`
2. end: `2026-03-10 00:40:00 -0300`

Objetivo do slice:
1. reduzir risco semantico de cache no sort de `num_reprogramacoes`.
2. alinhar tooltip de `Limpar Busca` com o comportamento real de cancelamento da busca em andamento.
3. reforcar uso explicito de `QUrl.fromLocalFile(...)` em abertura local de guia.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - `_sort_num_reprogramacoes_robust`:
     - agora valida alinhamento de `sort_keys` com `df_exibido` antes de ordenar.
     - aplica alinhamento defensivo de indice antes do `.loc`, com log explicito quando houver mismatch.
   - `on_header_clicked`:
     - apos sort de `num_reprogramacoes`, chama `_prime_num_reprogramacoes_sort_cache()` para manter cache coerente com dataframe final exibido.
   - tooltip de `Limpar Busca` atualizado para informar cancelamento da busca em andamento sem limpar filtros de coluna/avancados.
   - `open_installation_guide` usa variavel `safe_doc_url = QUrl.fromLocalFile(...)` antes de `QDesktopServices.openUrl(...)` (contrato explicito).

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "quick_setor_executor or num_reprogramacoes or clear_search_button_label_and_tooltip_are_explicit_on_both_tabs"` -> `6 passed`
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py -k "import_external_excel_files or open_installation_guide"` -> `2 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (God class, update_derivadas sincrono, resize jank).

## Update 2026-03-10 00:22 - atalho Setor Executor sem persistencia + sync completo

Session timestamp:
1. start: `2026-03-10 00:22:40 -0300`
2. end: `2026-03-10 00:30:15 -0300`

Objetivo do slice:
1. remover persistencia do atalho rapido `Setor Executor`.
2. corrigir sincronismo do atalho rapido com filtros de coluna/OR group.
3. melhorar usabilidade do popup de setores (lista longa com rolagem).
4. corrigir ponto critico em importacao externa (`_build_unique_destination_path` fallback call).

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - removeu checkbox `Configuracao persistente` da faixa de opcoes.
   - removeu carga/aplicacao de `quick_setor_executor` salvo no startup.
   - removeu persistencia implicita de `display_columns` via atalho rapido.
   - `quick_setor_executor_combo` agora usa `setMaxVisibleItems(14)`.
   - `_on_quick_setor_executor_changed` agora sincroniza OR group (`_sync_or_group_values`), reconstrui painel (`_build_column_filters_panel`) e so depois aplica refresh.
   - `import_external_excel_files`: fallback de destino unico trocado de descriptor `__get__` para chamada de instancia segura.
2. `tests/test_gui_filter_logic.py`:
   - teste do atalho rapido atualizado para o novo contrato sem persistencia.
   - cobertura de sincronismo: mudanca no combo atualiza `setor_executor` e `setor_emissor`.
   - cobertura de UX: sem `persist_filter_config_checkbox` e popup limitado (`maxVisibleItems=14`).

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "quick_setor_executor or num_reprogramacoes or column_selector_button_shows_visible_count_in_text or setor_executor_order_prioritizes_smin_then_mel_then_alpha"` -> `7 passed`
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py -k "import_external_excel_files"` -> `2 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos de arquitetura/performance em `gui/gui_ssa.py` (God class, resize/jank, fluxo de derivadas sincrono, retencao global de workers).

## Update 2026-03-10 00:17 - cache de sort num_reprogramacoes + estabilizacao de testes

Session timestamp:
1. start: `2026-03-10 00:17:30 -0300`
2. end: `2026-03-10 00:21:00 -0300`

Objetivo do slice:
1. eliminar estado stale imediato no cache de sort de `num_reprogramacoes`.
2. estabilizar testes focados para validar invariantes de cache em vez de identidade de objeto.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - `_sort_num_reprogramacoes_robust` agora atualiza `_num_reprog_sort_cache` para o `sorted_df` retornado.
   - cache passa a refletir `source_id/source_len/index` do dataframe exibido apos a ordenacao.
2. `tests/test_gui_filter_logic.py`:
   - teste de `persist_filter_config_checkbox` nao depende mais de estado persistido anterior.
   - testes de cache de `num_reprogramacoes` passaram a validar alinhamento estrutural (`keys_df`, `index`, `source_len`) em vez de `id(df_exibido)`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "num_reprogramacoes or quick_setor_executor_combo_applies_filter_and_persistence or setor_executor_order_prioritizes_smin_then_mel_then_alpha or column_selector_button_shows_visible_count_in_text"` -> `7 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos de arquitetura/performance apontados pelo kluster em `gui/gui_ssa.py` (God class, resize/best-fit, vacuum sync fallback, closeEvent waits).

## Update 2026-03-09 23:53 - GUI quick setor executor + persistencia opcional

Session timestamp:
1. start: `2026-03-09 23:53:13 -0300`
2. end: `2026-03-10 00:05:00 -0300`

Objetivo do slice:
1. remover seletor de perfil de filtro da UI (nao agrega no fluxo atual).
2. adicionar combo rapido `Setor Executor` no topo, ao lado de `Colunas Visiveis`.
3. mover contador de colunas para o proprio botao (`Colunas Visiveis: N`) e remover box lateral.
4. adicionar opcao `Configuracao persistente` (default desmarcado) para salvar automaticamente a configuracao rapida.

Mudancas aplicadas:
1. `gui/widgets/column_selector.py`:
   - botao passou a exibir `Colunas Visiveis: N`.
   - resumo lateral removido.
2. `gui/gui_ssa.py`:
   - `profile_selector` removido da faixa de opcoes.
   - combo rapido `Setor Executor` adicionado na linha superior (lado direito de `Colunas Visiveis`).
   - ordenacao do combo: `IEE1..IEE4`, depois `MEL1..MEL4`, depois restante em ordem alfabetica.
   - novo checkbox `Configuracao persistente` como primeiro item da faixa de opcoes.
   - persistencia opcional implementada em `gui_settings.persist_quick_filter_config` e `gui_settings.quick_setor_executor`.
   - quando persistencia ativa, mudancas em `setor_executor` rapido e `visible_columns` sao gravadas via `_persist_gui_preferences`.
3. `gui/mixins/tab_context_gui_ssa_mixin.py`:
   - sync de perfil agora ignora ausencia de `profile_selector` sem ruido.
4. `gui/mixins/filter_gui_ssa_mixin.py`:
   - clear global e refresh passam a sincronizar o combo rapido de `Setor Executor`.
5. `tests/test_gui_filter_logic.py`:
   - cobertura para texto do botao de colunas.
   - cobertura para ordenacao de setores priorizada.
   - cobertura para aplicacao do combo rapido + persistencia opcional.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/widgets/column_selector.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/widgets/column_selector.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/widgets/column_selector.py gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "column_selector_button_shows_visible_count_in_text or setor_executor_order_prioritizes_smin_then_mel_then_alpha or quick_setor_executor_combo_applies_filter_and_persistence"` -> `3 passed`
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. debts estruturais/performance recorrentes apontados por kluster em `gui/gui_ssa.py` e mixins (fora do escopo deste patch minimo).

## Update 2026-03-09 23:37 - PR45 path/runtime corrections (targeted)

Session timestamp:
1. start: `2026-03-09 23:37:15 -0300`
2. end: `2026-03-09 23:49:00 -0300`

Objetivo do slice:
1. corrigir refs de docs/path sinalizadas no PR.
2. corrigir retorno inconsistente de `import_external_excel_files`.
3. remover entrega de callback `vacuum/analyze` de dentro de thread de fundo.

Mudancas aplicadas:
1. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`:
   - troca de comando para teste existente: `pytest tests\\test_database.py -q`.
2. `docs/CCR_LLM_PROVIDERS_SETUP.md`:
   - referencia de instrucao ajustada para arquivo que existe no repo atual.
3. `README.md`:
   - link de changelog tecnico alinhado para `docs/CHANGELOG_IMPLEMENTACOES.md`.
4. `gui/gui_ssa.py`:
   - `import_external_excel_files` agora retorna sempre schema com `unsupported`.
   - `run_vacuum_analyze` agora publica resultado em atributo e finaliza no thread da GUI por polling com `QTimer.singleShot`.
5. `tests/test_gui_menu_import_external.py`:
   - novo teste de schema consistente no early return da importacao externa.
   - novo teste do caminho async de `vacuum/analyze` garantindo reset de flags e entrega de resultado.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py` -> `13 passed`

Deferido (nao bloqueante neste slice):
1. kluster `MEDIUM semantic` em `README.md` sobre contradicao textual de normalizacao `numero_ssa` e recomendacao de decompor README (fora do escopo deste patch minimo).

## Update 2026-03-09 23:24 - targeted fix for unique-destination fallback call

Session timestamp:
1. start: `2026-03-09 23:23:06 -0300`
2. end: `2026-03-09 23:24:55 -0300`

Objetivo do slice:
1. corrigir ponto especifico reportado no PR sobre chamada fallback de `_build_unique_destination_path`.
2. manter patch minimo sem alterar comportamento funcional de importacao externa.

Mudanca aplicada:
1. `gui/gui_ssa.py`:
   - fallback de `import_external_excel_files` passou a usar descriptor bound call:
     `SSAMainWindow._build_unique_destination_path.__get__(self, SSAMainWindow)(base_destination)`.
   - objetivo: remover ambiguidade de assinatura em chamada via classe, preservando compatibilidade com janelas stub em testes.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py -k "import_external_excel_files or consolidate_input_files or open_settings_file_with_backup"` -> `5 passed`

Deferido (nao bloqueante neste slice):
1. debts antigos de arquitetura/performance apontados por kluster em `gui/gui_ssa.py` (fora do escopo desta correcao pontual).

## Update 2026-03-09 23:08 - heavy+simple PR follow-up (vacuum async + rescan/menu fixes)

Session timestamp:
1. start: `2026-03-09 22:57:39 -0300`
2. end: `2026-03-09 23:08:07 -0300`

Objetivo do slice:
1. tratar uma pendencia pesada de UX/performance: `VACUUM/ANALYZE` fora da thread principal da GUI.
2. fechar comentarios simples de PR com risco real (prompt mode, dedup worker list, backup timestamp, consolidate nosurvivor).
3. manter patch minimo sem alterar layout/posicao da interface.

Mudancas aplicadas:
1. `gui/gui_ssa.py`:
   - `run_vacuum_analyze` agora executa manutencao de DB em thread de fundo no runtime normal.
   - caminho de teste (`PYTEST_CURRENT_TEST`) mantido sincrono para determinismo.
   - `_build_unique_destination_path` agora tem limite de tentativas e erro explicito.
   - backup de `settings.json` passou a usar timestamp com microssegundos (evita colisao).
   - consolidacao de `nosurvivor` agora considera mutacao real (`rows_inserted`, `rows_updated`, `rows_changed`, `rows_ready_for_insert`) e so incrementa contador apos move bem-sucedido.
2. `gui/ssa/gui_workers.py`:
   - `rescan_mode="prompt"` com `QMessageBox` indisponivel agora cai para incremental seguro.
   - deduplicacao de `expired_all` no prune de data loader workers.
   - limpeza de `_active_rescan_dialog` garantida tambem em `worker.finished`.
3. testes:
   - `tests/test_gui_menu_import_external.py`:
     - monkeypatch headless de `QUrl` + `QDesktopServices` com `raising=False`;
     - backup em duas chamadas seguidas -> dois arquivos distintos;
     - update-only nao vai para `nosurvivor`.
   - `tests/test_gui_workers_rescan_data.py`:
     - `show_non_modal_called` agora e validado;
     - limpeza de `_active_rescan_dialog` no fluxo cancel+finish;
     - modo `prompt` sem dialogo valida `force_import=False`.
4. docs:
   - `docs/CCR_LLM_PROVIDERS_SETUP.md`: nota explicita de snapshot historico para evitar conflito com `instructions` legadas.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> `20 passed`

Deferido (nao bloqueante neste slice):
1. kluster em `gui/gui_ssa.py`:
   - tooltip/UX e debts estruturais antigos (God class, resize/best-fit cost, sort policy) fora deste patch minimo.
2. kluster em `gui/ssa/gui_workers.py`:
   - concentracao residual em `on_data_loaded` e debts de arquitetura/performance (ja mapeados em backlog anterior).

## Update 2026-03-09 22:49 - heavy pending slice (DataLoaderWorker preprocess)

Session timestamp:
1. start: `2026-03-09 22:30:00 -0300`
2. end: `2026-03-09 22:54:17 -0300`

Objetivo do slice:
1. reduzir custo do hot path em `on_data_loaded` movendo preprocessamento pesado para `DataLoaderWorker`.
2. manter fallback legado para chamadas diretas sem quebrar contratos atuais.
3. corrigir aresta de UI stuck quando falha ao instanciar worker de carga.

Mudancas aplicadas:
1. `gui/workers/data_loader_worker.py`:
   - novo preprocessamento para GUI:
     - sanitizacao de `numero_ssa` e `derivada_de`;
     - ordenacao inicial por `situacao`/`numero_ssa`;
     - calculo de colunas nao nulas.
   - metadados enviados via `df.attrs`:
     - `ssa_preprocessed_for_gui`
     - `ssa_sanitized_df`
     - `ssa_non_null_cols`
2. `gui/ssa/gui_workers.py`:
   - `on_data_loaded` consome metadados do worker quando presentes e evita reprocessamento pesado no caminho padrao.
   - fallback legado mantido para chamadas sem attrs.
   - `load_data`: falha de construtor de worker agora restaura UI (`progress_bar`, `load_button`, `search_button`) no bloco de excecao.
   - robustez adicional:
     - `current_filter_profile` agora via `getattr`.
     - `on_load_error` com guards para widgets opcionais.
3. testes:
   - `tests/test_data_loader_worker.py`:
     - cobrindo attrs de preprocessamento e sanitizacao.
   - `tests/test_gui_filter_logic.py`:
     - cobrindo consumo de attrs pre-processados em `on_data_loaded`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/workers/data_loader_worker.py gui/ssa/gui_workers.py tests/test_data_loader_worker.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/workers/data_loader_worker.py gui/ssa/gui_workers.py tests/test_data_loader_worker.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/workers/data_loader_worker.py gui/ssa/gui_workers.py tests/test_data_loader_worker.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_data_loader_worker.py tests/test_gui_workers_signal_connect.py tests/test_load_data_skips_modal_loader_missing_in_pytest.py tests/test_gui_filter_logic.py -k "on_data_loaded or DataLoaderWorker or load_data_handles_loader_constructor_failure_under_pytest"` -> `8 passed`
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_workers_advanced.py -k DataLoaderWorker` -> `14 passed`

Deferido (nao bloqueante neste slice):
1. kluster `HIGH knowledge` em `query_db(self.db_path, '', query, ...)` no worker foi classificado como `FALSO_POSITIVO` nesta rodada:
   - assinatura de `query_db` usa `table_name` somente quando `query` vazio; com query explicita o `''` e contrato historico valido.
2. debts amplos de arquitetura/performance ainda ativos:
   - `on_data_loaded` continua concentrando responsabilidades (debt historico);
   - duplicacao de logica entre caminho fallback e caminho pre-processado.

## Update 2026-03-09 22:30 - ASCII policy guardrails for doc comments

Session timestamp:
1. start: `2026-03-09 22:30:00 -0300`
2. end: `2026-03-09 22:34:14 -0300`

Objetivo do slice:
1. fechar conflito de review ortografico com politica tecnica ASCII do repo.
2. registrar claramente quais debts antigos seguem ativos e priorizados.
3. evitar ambiguidade de decisao no proximo ciclo.

Decisao registrada (oficial):
1. sugestoes ortograficas que introduzem acentos/cedilha em texto tecnico devem ser classificadas como `FALSO_POSITIVO` quando houver conflito com politica ASCII vigente.
2. esta regra vale para docs de controle e comentarios tecnicos de PR neste ciclo.

Debts antigos priorizados para proximo ciclo (top 3):
1. `gui/gui_ssa.py`: `SSAMainWindow` com concentracao alta de responsabilidade (debt arquitetural).
2. `gui/ssa/gui_workers.py`: `on_data_loaded` pesado no UI thread (sanitize/sort + jank em base grande).
3. `gui/ssa/gui_workers.py`: duplicacao de prune/cleanup de workers entre caminhos de carga e rescan.

Validacao desta rodada:
1. kluster auto em docs tocados -> clean.
2. sem alteracao de runtime.

## Update 2026-03-09 22:11 - PR #45 pending comments follow-up (worker/cache/import/integrity)

Session timestamp:
1. start: `2026-03-09 22:11:57 -0300`
2. end: `2026-03-09 22:20:55 -0300`

Objetivo do slice:
1. fechar comentarios pendentes de risco real sem refatoracao ampla.
2. manter patch minimo com foco em concorrencia, consolidacao e consistencia de runtime.
3. preservar layout/fluxo GUI fora do escopo.

Mudancas aplicadas:
1. `gui/ssa/gui_workers.py`:
   - removido corte cego por cap em `_classify_workers_for_ttl` para nao perder worker vivo.
   - inicializacao de `_retired_data_loader_workers` protegida por lock antes de prune.
2. `gui/gui_ssa.py`:
   - `import_external_excel_files` agora copia somente `.xlsx` (case-insensitive) e separa contagem de `nao_suportados`.
   - consolidacao de arquivos passa a rotear `nosurvivor` apenas quando status e contagens indicam sucesso sem sobreviventes.
3. `utils/caching.py`:
   - descoberta de `.xlsx`/`.xls` tornou-se case-insensitive.
4. `armazenamento/database_integrity.py`:
   - `_resolve_report_table_name` prioriza `type='table'` e usa `view` apenas como fallback.
5. testes:
   - `tests/test_gui_workers_rescan_data.py` (novo teste de cap sem perder worker vivo).
   - `tests/test_gui_menu_import_external.py` (import externo `.xlsx` e consolidacao de status de erro).
   - `tests/test_caching.py` (extensoes uppercase).
   - `tests/test_database_verification.py` (preferencia table sobre view).

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_workers.py gui/gui_ssa.py utils/caching.py armazenamento/database_integrity.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_caching.py tests/test_database_verification.py` -> pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_workers.py gui/gui_ssa.py utils/caching.py armazenamento/database_integrity.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_caching.py tests/test_database_verification.py` -> pass
3. `uv run --python 3.13 ty check gui/ssa/gui_workers.py gui/gui_ssa.py utils/caching.py armazenamento/database_integrity.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_caching.py tests/test_database_verification.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_caching.py tests/test_database_verification.py` -> `47 passed`

Deferido (nao bloqueante neste slice):
1. debts de arquitetura/performance geral sinalizados por kluster em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora de escopo de patch minimo).
2. possivel revisao semantica de `database_exists` para arquivo SQLite 0-byte em `database_integrity` (mantido por compatibilidade de contrato atual de testes).

## Update 2026-03-09 21:58 - PR #45 P2 follow-up (worker/menu/doc)

Session timestamp:
1. start: `2026-03-09 21:58:49 -0300`
2. end: `2026-03-09 22:03:00 -0300`

Objetivo do slice:
1. verificar e tratar 3 comentarios P2 (worker registry, dedup helper, doc instructions).
2. manter patch minimo sem alterar layout/fluxo de GUI.
3. deixar debt nao-ascii de testes explicitamente deferido.

Mudancas aplicadas:
1. `gui/ssa/gui_workers.py`:
   - rescan worker passa a ser registrado em `global_workers/global_meta` logo apos `start()`.
2. `tests/test_gui_workers_rescan_data.py`:
   - expectativa ajustada para refletir registro global imediato no caso sem `finished`.
3. `gui/gui_ssa.py`:
   - `import_external_excel_files` reutiliza regra unica de destino com `_build_unique_destination_path` (com fallback seguro para stub de teste).
4. `docs/CCR_LLM_PROVIDERS_SETUP.md`:
   - padrao de sync de instructions corrigido para `*.instructions`.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py` -> `16 passed`

Deferido (nao bloqueante neste slice):
1. debt transversal de nao-ascii em testes legados e novos; requer plano dedicado para normalizacao sem risco de churn amplo.

## Update 2026-03-09 21:43 - PR #45 comments hotfix (blockers)

Session timestamp:
1. start: `2026-03-09 21:43:43 -0300`
2. end: `2026-03-09 21:55:41 -0300`

Objetivo do slice:
1. corrigir bloqueadores reais apontados em comentarios/checks do PR #45.
2. fechar falha de CI (`quality-gates`) sem refatoracao ampla.
3. manter escopo minimo em contrato/log/teste.

Mudancas aplicadas:
1. `tests/test_import_cancellation.py`:
   - contrato alinhado ao fluxo atual de cancelamento (retorno `False` e sem persistencia de cache no cancelamento).
   - fixture de `numero_ssa` ajustada para valor valido.
2. `core/app_logic.py`:
   - bloco de warnings de integridade desindentado para voltar a ser executado no caminho valido.
3. `armazenamento/database_validation.py`:
   - removido campo interno `_invalid_row_seen` tambem no retorno precoce de `df.empty`.
4. `armazenamento/database.py`:
   - `query_db` agora trata `ValueError` no mesmo contrato de `raise_on_error=False`.
   - removido suppress silencioso em whitelist de colunas (agora loga e propaga erro real).
5. `armazenamento/database_integrity.py`:
   - removido warning falso `"Problemas detectados no banco: []"` em caminho de reparo opcional.

Validacao desta rodada:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py armazenamento/database_validation.py armazenamento/database.py armazenamento/database_integrity.py tests/test_import_cancellation.py` -> pass
2. `uv run --python 3.13 ruff check core/app_logic.py armazenamento/database_validation.py armazenamento/database.py armazenamento/database_integrity.py tests/test_import_cancellation.py` -> pass
3. `uv run --python 3.13 ty check core/app_logic.py armazenamento/database_validation.py armazenamento/database.py armazenamento/database_integrity.py tests/test_import_cancellation.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_import_cancellation.py tests/test_database.py tests/test_database_verification.py` -> `30 passed`
5. `timeout 180s uv run --python 3.13 pytest -q tests/test_cli_enhancement_manager_lock_usage.py tests/test_import_cancellation.py tests/test_database_optimized_identifier_guards.py tests/test_gui_filters_advanced_logic.py tests/test_streamlit_filter_cache.py` -> `73 passed`

Deferido (nao bloqueante neste slice):
1. debts estruturais/performance apontados por kluster em `core/app_logic.py`, `armazenamento/database.py` e `armazenamento/database_integrity.py` (fora do escopo do hotfix minimo).

## Update 2026-03-09 19:26 - documentation integrity pass (links and references)

Session timestamp:
1. start: `2026-03-09 19:26:41 -0300`
2. end: `2026-03-09 19:39:20 -0300`

Objetivo do slice:
1. corrigir referencias quebradas em docs ativos.
2. padronizar links de apoio/local para evitar caminhos inexistentes no repo.
3. criar ponteiros de compatibilidade para referencias antigas `docs/ARCH_*`.

Mudancas aplicadas:
1. links corrigidos em:
   - `README.md`
   - `docs/INSTRUCOES_LEITURA.md`
   - `docs/OHMYOPENCODE_MANUAL.md`
   - `docs/OTIMIZACAO_STARTUP.md`
   - `docs/ESTRUTURA_PROJETO.md`
   - `docs/TERMINAL_INTEGRATION.md`
   - `docs/RELEASE_NOTES_v4.11.0.md`
   - `docs/CCR_LLM_PROVIDERS_SETUP.md`
   - `docs/REFACTOR_DEPENDENCY_CYCLES.md`
2. novos ponteiros de compatibilidade:
   - `docs/ARCHITECTURE_OVERVIEW.md`
   - `docs/ARCH_DB_UPSERT.md`
   - `docs/ARCH_GUI_LOAD_AND_FILTER.md`
   - `docs/ARCH_IMPORT_PIPELINE.md`
   - `docs/ARCH_VALIDATION_AND_INTEGRITY.md`
3. arquivo de archive criado:
   - `docs/archive/PLANO_REFATORACAO_SSA_CONSULTA_RAPIDA.md`

Validacao desta rodada:
1. varredura automatica de referencias `.md` em `README.md` + `docs/*.md` com resultado final `missing=0`.
2. kluster executado apos cada alteracao de arquivo.
3. gates tecnicos:
   - `uv run --python 3.13 python -m py_compile main.py` -> pass
   - `uv run --python 3.13 ruff check main.py` -> pass
   - `uv run --python 3.13 ty check main.py` -> pass
   - `uv run --python 3.13 pytest -q tests/test_docs_and_priority.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> `15 passed`
4. commit de evidencia:
   - `dcbbb2f3` (`DOC_SYNC`) - integridade de referencias e ponteiros legacy.

## Update 2026-03-09 19:01 - full documentation refine v4.32

Session timestamp:
1. start: `2026-03-09 19:01:11 -0300`
2. end: `2026-03-09 19:22:01 -0300`

Objetivo do ciclo:
1. atualizar e refinar documentacao ativa do projeto.
2. reduzir ambiguidade entre docs ativos e snapshots historicos.
3. manter baseline unico v4.32 sem tocar runtime.

Slices executados:
1. Slice A:
   - docs index/readme canonicos (`docs/INDEX.md`, `docs/README.md`).
2. Slice B:
   - normalizacao de versao e snapshot em docs de build/historico/importacao.
3. Slice C:
   - alinhamento uv-first no guia de migracao (`docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`).
4. Slice D:
   - guias de troubleshooting migrados para versoes ativas curtas + archive.
5. Slice E:
   - sync de docs de controle e historico de release para fechar o ciclo.

Nao alterado:
1. runtime (`core/gui/armazenamento/extracao/interface/tests`).
2. arquivos frozen (`POLICY_BASELINE_V1_1_FROZEN.md`, `POLICY_BASELINE_V1_FROZEN.md`).

Evidencia de commits desta rodada:
1. `7df32647` (`DOC_SYNC`) - index/readme de docs canonicos.
2. `ea7a987c` (`DOC_SYNC`) - normalizacao de docs ativos + snapshots.
3. `3f1b0945` (`DOC_SYNC`) - guia de migracao alinhado ao padrao uv-first.
4. `731deebf` (`DOC_SYNC`) - troubleshooting ativo simplificado + archive.
5. `b015e5b2` (`DOC_SYNC`) - sync final de controle/historico desta rodada.

## Update 2026-03-09 17:35 - docs governance refine on v4.32

Session timestamp:
1. start: `2026-03-09 17:35:40 -0300`
2. end: `2026-03-09 17:41:28 -0300`

Objetivo do slice:
1. reduzir ambiguidade nos docs de continuidade sem alterar historico profundo.
2. manter baseline `4.32` como unica fonte ativa de referencia.
3. remover acoplamento com artefatos de log efemeros no historico de release.

Mudancas aplicadas:
1. `docs/NEXT_CHAT_MIGRATION.md`:
   - regras de interpretacao adicionadas no topo.
2. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`:
   - regras de interpretacao autoritativa adicionadas no topo.
3. `docs/RECOVERY_BACKLOG.md`:
   - bloco anterior de 4.32 marcado com validacao executada e commits.
4. `docs/HISTORICO_RELEASES.md`:
   - `RELEASE v4.30` marcado como `Snapshot historico`.
   - referencias de evidencia 4.32 movidas para docs estaveis.

Nao alterado:
1. nenhum arquivo runtime (`core/gui/armazenamento/extracao/interface/tests`).
2. nenhum comportamento funcional de importacao/GUI/DB.

## Update 2026-03-09 08:41 - doc sync release 4.32

Session timestamp:
1. start: `2026-03-09 08:41:42 -0300`
2. end: `2026-03-09 17:26:32 -0300`

Objetivo do slice:
1. promover baseline ativo de documentacao e metadados para `4.32`.
2. manter historico antigo sem reescrever snapshots.
3. registrar trilha de migracao para proximo chat.

Mudancas aplicadas:
1. `VERSION` -> `4.32`.
2. `config/version.json` -> `version_short=4.32`.
3. `README.md` topo promovido para `v4.32`.
4. `docs/HISTORICO_RELEASES.md` com bloco `RELEASE v4.32 - CURRENT RELEASE`.
5. `docs/FILTER_TAB_OPTIMIZATIONS.md` baseline atualizado para `v4.32`.
6. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md` topo e rodape alinhados para `v4.32`.
7. docs de controle atualizados com bloco de continuidade para `4.32`.

Validacao executada do slice:
1. scan de referencias (`rg`) para confirmar versao ativa.
2. `python -m py_compile` + `ruff` + `ty` + `pytest` focado (sanidade minima) antes do commit.
3. commit/push realizados:
   - `63a47682` (`DOC_SYNC`)
   - `09933f69` (`DEFERRED_NOTE`)

Pendencia nao bloqueante registrada:
1. `README.md` segue grande e acumulando secoes historicas; avaliar extracao para changelog/doc dedicado em ciclo proprio.

## Update 2026-03-09 06:45 - full rescan real + metricas completas em lote unico

Session timestamp:
1. start: `2026-03-09 01:08:50 -0300`
2. end: `2026-03-09 04:38:31 -0300`

Objetivo do slice:
1. executar full rescan real em ambiente local com backup previo.
2. coletar metricas completas de desempenho/confiabilidade/saude de schema.
3. consolidar evidencias e comparativo sem etapas manuais intermediarias.

Execucao e evidencias:
1. backup anterior ao rescan:
   - `data/db_backups/ssas.db.pre_full_rescan_20260309_010934.db`
2. runtime log:
   - `logs/full_rescan_runtime_20260309_010934.log`
3. report da rodada:
   - `logs/import_run_20260309_010936_830587.json`
4. consolidado tecnico:
   - `docs/indicios_importacao.md` (nova secao `Sessao 2026-03-09`)
5. artefatos comparativos:
   - `logs/full_rescan_summary_20260309_063007.json`
   - `logs/full_rescan_summary_20260309_063007.csv`
   - `logs/full_rescan_family_insert_20260309_063007.csv`
   - `logs/full_rescan_top_insert_20260309_063007.csv`
   - `logs/full_rescan_top_invalid_20260309_063007.csv`

Resultado principal:
1. full rescan concluiu com `status=updated` e `result=true`.
2. candidatos/sucessos: `431/431`; erros: `0`.
3. linhas:
   - extraidas: `497162`
   - removidas por identidade invalida: `2763`
   - inseridas: `497162`
4. saude do DB final:
   - `integrity_check=ok`
   - `rows_total=76426`
   - `distinct_numero_ssa=76426`
   - duplicados de `numero_ssa=0`
   - `id` presente
   - sem colunas `nan*`

Observacao de medicao:
1. `duration_seconds` total (`12522s`) ficou inflado por entrada no loop CLI apos finalizar import.
2. usar `run_file_processing_seconds` (`1251.979s`) como referencia de tempo efetivo do pipeline de import.

Pendencias nao bloqueantes:
1. benchmark dedicado sem loop CLI (chamada direta de `run_importer_logic`) para medicao absoluta limpa.
2. chart PNG nao foi gerado nesta maquina (sem backend disponivel); CSV/JSON ficaram completos para dashboard externo.

## Update 2026-03-09 01:05 - performance focused (sort jank + resize burst)

Session timestamp:
1. start: `2026-03-09 00:56:08 -0300`
2. end: `2026-03-09 01:05:00 -0300`

Objetivo do slice:
1. reduzir jank no sort de `num_reprogramacoes`.
2. coalescer recompute de best-fit em burst de resize.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - sort `num_reprogramacoes` agora ordena por indice de `sort_keys` (sem `assign` temporario no dataframe inteiro).
   - novo prewarm/invalidate de cache:
     - `_prime_num_reprogramacoes_sort_cache`
     - `_reset_num_reprogramacoes_sort_cache`
   - resize recompute agora usa timer unico restartavel:
     - `_schedule_resize_recompute`
     - `_on_resize_recompute_timeout`
     - removeu `QTimer.singleShot` repetitivo no `resizeEvent`.
2. `gui/ssa/gui_workers.py`
   - `on_data_loaded` agora chama prewarm de cache de sort quando disponivel.
3. `tests/test_gui_filter_logic.py`
   - `test_on_data_loaded_primes_num_reprogramacoes_sort_cache`
   - `test_resize_event_coalesces_width_recompute_with_restartable_timer`

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "on_header_clicked_sorts_num_reprogramacoes_mixed_types or on_header_clicked_reuses_num_reprogramacoes_sort_cache or on_data_loaded_primes_num_reprogramacoes_sort_cache or resize_event_coalesces_width_recompute_with_restartable_timer or prune_retired_loader_workers_removes_stale_refs_without_finished_signal"` -> `5 passed`

Pendencias nao bloqueantes (deferidas):
1. custo de primeira ordenacao ainda existe em datasets muito grandes (cache so remove custo repetido).
2. recompute de width ainda roda em UI thread (agora coalescido); offload de calculo fica para ciclo dedicado.

## Update 2026-03-09 00:30 - prune dedup + sort cache num_reprogramacoes + help version

Session timestamp:
1. start: `2026-03-09 00:12:38 -0300`
2. end: `2026-03-09 00:30:00 -0300`

Objetivo do slice:
1. remover duplicacao de manutencao entre prunes de workers.
2. reduzir custo do sort `num_reprogramacoes` no clique de header.
3. alinhar versao do guia de instalacao/help para baseline `4.31`.
4. atualizar trilha de migracao para proximo chat.

Mudancas aplicadas:
1. `gui/ssa/gui_workers.py`
   - novo helper `_process_expired_workers` para fluxo comum de worker expirado por TTL.
   - novo helper `_drop_orphaned_worker_meta` para limpar metadado orfao com mesma regra nos dois prunes.
   - `prune_retired_data_loader_workers` e `prune_retired_rescan_workers` passaram a reutilizar esses blocos.
2. `gui/gui_ssa.py`
   - cache de chaves para sort de `num_reprogramacoes`:
     - `_build_num_reprogramacoes_sort_keys`
     - `_get_num_reprogramacoes_sort_keys`
   - `_sort_num_reprogramacoes_robust` usa cache por dataset filtrado para evitar parse repetido a cada toggle.
3. `tests/test_gui_filter_logic.py`
   - novo teste: `test_on_header_clicked_reuses_num_reprogramacoes_sort_cache`.
4. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`
   - cabecalho atualizado para `v4.31`.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_filter_logic.py tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
3. `uv run --python 3.13 ty check gui/ssa/gui_workers.py gui/gui_ssa.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "on_header_clicked_sorts_num_reprogramacoes_mixed_types or on_header_clicked_reuses_num_reprogramacoes_sort_cache or prune_retired_loader_workers_removes_stale_refs_without_finished_signal"` -> `3 passed`
5. `timeout 300s uv run --python 3.13 pytest -q tests/test_gui_workers_rescan_data.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> `19 passed`

Pendencias nao bloqueantes (deferidas):
1. debt amplo de arquitetura/performance na `SSAMainWindow` (fora de escopo do patch minimo).
2. custo de operacoes pesadas ainda no thread da GUI em outros pontos nao tocados neste slice.
3. naming/UX de `Reescanear` vs prompt continua para ciclo dedicado.
4. semantica de tooltip/placeholder da busca geral vs modos avancados de termos (revisar texto x comportamento).
5. hardening adicional de path opener (bloqueio extra para argumentos iniciados com `-` e allow-list mais estrita).
6. possivel lock contention em prune/retain de workers sob carga intensa (avaliar tuning de frequencia/lock granularity).

## Update 2026-03-09 00:04 - hardening semantico/security/status worker

Session timestamp:
1. start: `2026-03-08 23:22:00 -0300`
2. end: `2026-03-09 00:04:10 -0300`

Objetivo do slice:
1. corrigir contradicao semantica no cabecalho da busca geral.
2. hardening de abertura de pasta/arquivo (menu) contra caminhos invalidos.
3. eliminar uso direto de `status_label.setText` no worker de carga/rescan.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - comentario de topo alinhado ao comportamento real da busca.
   - novos helpers estaticos:
     - `_validate_local_open_target`
     - `_resolve_platform_open_command`
   - `open_settings_file_with_backup`, `open_installation_guide` e `_open_folder_non_blocking`
     com validacao de caminho e fallback seguro.
2. `gui/ssa/gui_workers.py`
   - substituicoes de `window.status_label.setText(...)` por `_set_status_label_text(...)`
     nos fluxos de load/rescan.

Validacao multi-OS (implementacao):
1. caminho principal: `QDesktopServices.openUrl` (Qt cross-platform).
2. fallback por plataforma:
   - Windows: `explorer`
   - macOS: `open`
   - Linux/Debian: `xdg-open`
3. fallback agora usa caminho validado + comando resolvido via `shutil.which`.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `19 passed`

Pendencias nao bloqueantes (deferidas nesta rodada):
1. duplicacao entre `prune_retired_data_loader_workers` e `prune_retired_rescan_workers` (debt de manutencao).
2. `rescan_data` (modo `prompt`) e naming de entrada principal `Reescanear` requer definicao de UX em slice proprio.
3. performance ampla: sort de `num_reprogramacoes`, custo de `_get_canonical_available_columns`, recompute de best-fit em resize (fora do escopo deste hotfix).
4. debt arquitetural em `SSAMainWindow` (classe grande) permanece fora de escopo de patch minimo.
5. check `Nao esta em STE/SCA` permanece oculto por politica atual; revisar visibilidade em slice de UX dedicado.
6. retencao global de workers requer avaliacao de ciclo longo (cleanup periodico vs modelo atual).

## Update 2026-03-08 23:05 - padronizacao final de menu e prompt de reescaneamento

Session timestamp:
1. start: `2026-03-08 22:52:00 -0300`
2. end: `2026-03-08 23:05:15 -0300`

Objetivo do slice:
1. aplicar exatamente os textos e ordem de menus aprovados pelo usuario.
2. padronizar prompt de reescaneamento sem sufixo `(diff)` no texto e botao.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menu `Arquivo` reduzido para: `Recarregar Dados`, `Atualizar Dados`, `Exportar lista`, `Sair`.
   - menu `Importacao` atualizado com 7 itens na ordem aprovada.
   - menu `Database` atualizado com 4 itens diretos (sem submenu `Avancado`).
   - menu `Ajuda` agora com `Instalacao` + `Ajuda`.
   - nova acao `open_installation_guide` para abrir `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`.
2. `gui/ssa/gui_workers.py`
   - prompt `Reescanear` atualizado:
     - informativo usa `Atualizar Dados` (sem `(diff)`).
     - botao usa `Atualizar Dados`.
3. `tests/test_gui_menu_import_external.py`
   - asserts de contagem/ordem/rotulo atualizados para o novo contrato de menus.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> `16 passed`

Pendencias nao bloqueantes (deferidas nesta rodada):
1. `gui/gui_ssa.py`: kluster sinalizou debts antigos de arquitetura/performance em `SSAMainWindow` (fora do escopo deste slice de texto/menu).
2. `gui/ssa/gui_workers.py`: kluster sinalizou debts antigos de acoplamento/organizacao (fora do escopo deste slice de texto/menu).

## Update 2026-03-08 21:38 - tema em caixa e barra principal simplificada

Session timestamp:
1. start: `2026-03-08 21:07:19 -0300`
2. end: `2026-03-08 21:38:26 -0300`

Objetivo do slice:
1. abrir selecao de tema em caixa/dialogo (nao popup de menu).
2. tornar o texto do Database avancado user-friendly.
3. simplificar botoes da barra principal conforme pedido.

Mudancas aplicadas:
1. `gui/ssa/gui_theme.py`
   - `toggle_theme_menu` agora abre `QDialog` modal:
     - combo de temas
     - checkbox para tema padrao
     - botoes OK/Cancelar
2. `gui/gui_ssa.py`
   - barra principal removeu botoes:
     - `Carregar Outro DB`
     - `Abrir Pasta`
     - `Ajuda`
   - manteve:
     - `Carregar Dados`
     - `Reescanear`
     - `Atualizar Derivadas`
     - `Tema` no lado direito
   - `Database > Avancado` continua funcional e com texto amigavel:
     - prompt: `Compactar DB e atualizar estatisticas agora?`
     - status: `DB compactado e estatisticas atualizadas`
3. `tests/test_gui_menu_import_external.py`
   - assert de texto de sucesso do `Compactar DB` atualizado.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_theme.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_theme.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_theme.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py tests/test_rescan_worker_cleanup.py tests/test_rescan_worker_advanced.py` -> `48 passed`

Pendencias nao bloqueantes (deferidas):
1. `gui/gui_ssa.py`: classe `SSAMainWindow` segue com alta concentracao de responsabilidades (debt arquitetural, sem refatoracao ampla neste ciclo).
2. `gui/gui_ssa.py`: recalculo de largura em `resizeEvent` pode gerar jank em bases grandes; requer estudo dedicado de performance fora deste slice.
3. `gui/ssa/gui_theme.py`: reaplicacao global de QSS a cada refresh de tema pode congelar UI em arvore grande; requer tuning de cache/escopo.
4. `gui/ssa/gui_theme.py`: ajuste de fonte do painel de detalhes em cada refresh de tema pode gerar custo acumulado; requer condicao de short-circuit por tamanho base.

## Update 2026-03-08 22:28 - micro hardening de tema (cache + short-circuit)

Session timestamp:
1. start: `2026-03-08 22:18:00 -0300`
2. end: `2026-03-08 22:28:00 -0300`

Objetivo do slice:
1. reduzir custo no apply de tema sem alterar layout.
2. manter robustez e evitar suppress opaco.

Mudancas aplicadas:
1. `gui/ssa/gui_theme.py`
   - `_apply_global_palette`: short-circuit adicional para pular rebuild de QSS quando tema global cacheado ja corresponde ao tema solicitado.
   - `_apply_theme_widget_styles`: cache da fonte reduzida de `details_text` por base size, com reuso quando nao ha mudanca.
2. `tests/test_gui_filter_logic.py`
   - novo teste para reuso do cache da fonte reduzida.
   - novo teste para pular rebuild global de QSS com cache valido.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_theme.py tests/test_gui_filter_logic.py` -> pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_theme.py tests/test_gui_filter_logic.py` -> pass
3. `uv run --python 3.13 ty check gui/ssa/gui_theme.py tests/test_gui_filter_logic.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "theme_cycle_smoke_latency_on_filters_tab or reuses_cached_details_font or skips_global_qss_rebuild or switch_to_filters_tab_does_not_reapply_same_theme"` -> `4 passed`

Pendencias nao bloqueantes (deferidas nesta rodada):
1. `gui/ssa/gui_theme.py`: funcao `_apply_global_palette` ainda concentra palette + estilo global + QSS (debt de separacao de responsabilidade).
2. `gui/ssa/gui_theme.py`: `_apply_theme_widget_styles` segue extensa e com custo de setStyleSheet em varios widgets; requer plano dedicado para tuning sem risco.
3. `gui/ssa/gui_theme.py`: acoplamento com atributos privados de janela (`_last_global_theme_qss`, `_details_text_small_font_cached`, `_current_theme_roles`) requer avaliacao de encapsulamento dedicado.

## Update 2026-03-08 21:06 - menu final conforme texto aprovado + box de reescaneamento

Session timestamp:
1. start: `2026-03-08 20:36:00 -0300`
2. end: `2026-03-08 21:06:05 -0300`

Objetivo do slice:
1. aplicar os rotulos do menu exatamente como solicitado pelo usuario.
2. substituir textos repetidos em todas as ocorrencias equivalentes.
3. melhorar texto do box de reescaneamento para diff sem alteracoes.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menus e rotulos ajustados conforme lista aprovada:
     - `Arquivo` com fluxo diario final.
     - `Importacao` com a lista solicitada.
     - `Database` e `Database > Avancado` (`Compactar DB`).
     - `Opcoes` com 3 itens finais.
     - novo menu top-level `Ajuda` com acao `Ajuda`.
2. `gui/ssa/gui_workers.py`
   - textos do prompt de reescanear ajustados:
     - titulo `Reescanear`
     - mensagens com `Atualizar Dados (diff)` e `Reescaneamento Completo`
   - status final atualizado para `Recarregar Dados`.
3. `gui/workers/rescan_worker.py`
   - modo diff sem alteracoes agora conclui como sucesso (nao erro vermelho).
   - mensagem final do output: `Nenhum arquivo novo ou alterado foi encontrado.`
4. `tests/test_gui_menu_import_external.py`
   - validacao explicita das labels de todos os menus e submenu.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py tests/test_rescan_worker_cleanup.py tests/test_rescan_worker_advanced.py` -> `48 passed`

## Update 2026-03-08 20:29 - opcoes claras: editor externo + restaurar padrao

Session timestamp:
1. start: `2026-03-08 20:11:09 -0300`
2. end: `2026-03-08 20:29:39 -0300`

Objetivo do slice:
1. remover ambiguidade de "backup failsafe" no menu de opcoes.
2. manter abertura do arquivo principal em editor externo.
3. adicionar acao explicita de restaurar opcoes padrao.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - `Opcoes > Abrir arquivo de opcoes (editor externo)` (renomeado).
   - nova acao `Opcoes > Restaurar opcoes padrao`.
   - nova funcao `reset_settings_to_defaults`:
     - carrega `default_settings.json`,
     - confirma (fora de pytest),
     - cria backup de `settings.json`,
     - salva defaults em `settings.json`.
   - status de abertura atualizado para deixar claro que abre o arquivo principal.
2. `tests/test_gui_menu_import_external.py`
   - menu `Opcoes` passa a 4 acoes.
   - novo teste de restauracao de defaults com backup e escrita no arquivo real.
   - assert da acao de abrir opcoes ajustado para texto novo.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `19 passed`

## Update 2026-03-08 20:10 - refino de menu diario e redundancia controlada

Session timestamp:
1. start: `2026-03-08 19:53:36 -0300`
2. end: `2026-03-08 20:10:10 -0300`

Objetivo do slice:
1. refinar `Arquivo` como fluxo diario com ordem previsivel.
2. manter as mesmas operacoes nos menus de origem (sem remover).
3. manter hardening de pasta inexistente e tema via menu.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - `Arquivo` reorganizado em ordem de uso diario + separadores.
   - `Importacao` passou a conter tambem:
     - importar externo
     - reescaneamento diff
   - `Database` e `Opcoes` mantidos como menus especializados.
2. `tests/test_gui_menu_import_external.py`
   - contagens ajustadas para nova distribuicao de acoes.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `18 passed`

## Update 2026-03-08 19:56 - hardening de menus e abertura de pastas

Session timestamp:
1. start: `2026-03-08 19:53:36 -0300`
2. end: `2026-03-08 19:56:37 -0300`

Objetivo do slice:
1. melhorar menu `Arquivo` como fluxo diario sem remover itens dos menus de origem.
2. aumentar usabilidade do menu `Database`.
3. corrigir acao `Tema` quando acionada pelo menu.
4. endurecer abertura de pasta com prompt de criacao quando ausente.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menu `DB` renomeado para `Database`.
   - `Arquivo` passou a concentrar atalhos do fluxo diario (com duplicacao segura):
     - carregar dados/outro DB
     - reescaneamento diff/perguntar/completo
     - atualizar derivadas
     - consolidar arquivos
     - exportar
     - abrir pastas
     - tema/ajuda
     - sair
   - menus de origem (`Importacao`, `Database`, `Opcoes`) foram mantidos.
   - `_open_folder_non_blocking` agora:
     - pergunta se deseja criar pasta quando nao existe
     - cria pasta sob confirmacao
     - depois abre pasta com Qt/fallback.
2. `gui/ssa/gui_theme.py`
   - `toggle_theme_menu` ganhou fallback para abrir menu no cursor quando acionado por menu action.
3. testes:
   - `tests/test_gui_menu_import_external.py` atualizado para nova estrutura de menus.
   - `tests/test_open_docs_folder_nonblocking.py` ganhou cobertura de criacao de pasta via prompt.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_theme.py tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `18 passed`

## Update 2026-03-08 19:32 - release runtime 4.31 e equivalencia de menu

Session timestamp:
1. start: `2026-03-08 19:27:58 -0300`
2. end: `2026-03-08 19:32:24 -0300`

Objetivo do slice:
1. corrigir metadata de versao runtime para 4.31.
2. completar equivalencia principal entre botoes e menu.

Mudancas aplicadas:
1. versao:
   - `VERSION` atualizado para `4.31`.
   - `config/version.json` atualizado para `4.31`.
2. menu GUI (`gui/gui_ssa.py`):
   - `Importacao` ganhou `Reescaneamento (perguntar modo)` para equivaler ao botao `Reescanear`.
   - `Opcoes` ganhou `Ajuda` para equivaler ao botao `Ajuda`.
3. testes:
   - `tests/test_gui_menu_import_external.py` ajustado para nova contagem/handlers.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py utils/version.py main.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py utils/version.py main.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py utils/version.py main.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `17 passed`
5. `uv run --python 3.13 python main.py --version` -> `4.31`

## Update 2026-03-08 19:23 - reorganizacao de menus por atividade

Session timestamp:
1. start: `2026-03-08 19:19:55 -0300`
2. end: `2026-03-08 19:23:20 -0300`

Objetivo do slice:
1. organizar menus da GUI por tipo de atividade com rotulos curtos.
2. remover termos tecnicos com underscore da navegacao.
3. mover manutencao pesada de DB para submenu avancado.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menus agora separados em:
     - `Arquivo`
     - `Importacao`
     - `DB`
     - `Opcoes`
   - `DB` recebeu submenu `Avancado` com:
     - `Executar VACUUM/ANALYZE`
   - renomes de rotulos:
     - `Abrir pasta de entrada`
     - `Abrir pasta processadas`
     - `Abrir pasta sem sobreviventes`
     - `Reescaneamento completo`
   - novo handler manual:
     - `run_vacuum_analyze`
2. `tests/test_gui_menu_import_external.py`
   - cobertura atualizada para estrutura nova de menus/submenu.
   - novos testes para `run_vacuum_analyze` (sucesso e DB ausente).

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `17 passed`

## Update 2026-03-08 19:02 - atalhos de pasta processadas no menu DB

Session timestamp:
1. start: `2026-03-08 18:59:29 -0300`
2. end: `2026-03-08 19:02:26 -0300`

Objetivo do slice:
1. expor atalhos operacionais para abrir pastas de consolidacao sem alterar layout.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menu `DB` ganhou:
     - `Abrir pasta processadas`
     - `Abrir pasta processadas/nosurvivor`
   - novo helper reutilizavel `_open_folder_non_blocking(folder_path, folder_label)`.
   - `open_docs_folder` passou a reutilizar o mesmo helper (sem mudanca funcional).
   - novos handlers:
     - `open_processadas_folder`
     - `open_nosurvivor_folder`
2. `tests/test_gui_menu_import_external.py`
   - contagem de acoes do menu `DB` atualizada para `10`.
   - novos testes cobrindo roteamento dos 2 atalhos para o helper de abertura.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `15 passed`

## Update 2026-03-08 18:36 - GUI rescan explicito (Diff/Full) sem prompt

Session timestamp:
1. start: `2026-03-08 18:35:01 -0300`
2. end: `2026-03-08 18:36:52 -0300`

Objetivo do slice:
1. deixar o modo de reescaneamento explicito no menu (`Diff` e `Full`) sem depender de prompt.
2. manter compatibilidade com acao antiga por prompt na toolbar.

Mudancas aplicadas:
1. `gui/ssa/gui_workers.py`
   - `rescan_data` recebeu parametro `rescan_mode` (`prompt|diff|full`).
   - `diff` força `force_import=False` sem dialogo.
   - `full` força `force_import=True` sem dialogo.
   - `prompt` preserva fluxo anterior.
2. `gui/gui_ssa.py`
   - menu `DB` agora expõe:
     - `Reescanear Diff (hash)`
     - `Reescanear Full (zera e reprocessa)`
   - novas funcoes:
     - `rescan_diff_data`
     - `rescan_full_data`
   - `rescan_data` da toolbar continua em modo `prompt` para compatibilidade.
3. testes:
   - `tests/test_gui_workers_rescan_data.py`
     - cobertura de `rescan_mode=diff` e `rescan_mode=full` sem prompt.
   - `tests/test_gui_menu_import_external.py`
     - ajuste de contagem de acoes do menu `DB` para 8.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/ssa/gui_workers.py tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py` -> pass
4. `timeout 420s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_gui_workers_rescan_data.py tests/test_open_docs_folder_nonblocking.py` -> `13 passed`

## Update 2026-03-08 18:32 - GUI menu (slice 2/2): consolidacao + opcoes com failsafe

Session timestamp:
1. start: `2026-03-08 18:30:46 -0300`
2. end: `2026-03-08 18:32:58 -0300`

Objetivo do slice:
1. concluir o agrupamento operacional no menu da GUI.
2. entregar acao de opcoes com backup failsafe.
3. entregar acao dedicada de consolidacao de arquivos de entrada.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - menu `DB` ganhou:
     - `Consolidar arquivos de entrada`
     - `Abrir opcoes (backup failsafe)`
   - metodo `open_settings_file_with_backup`:
     - resolve `settings.json`
     - cria backup timestampado (`settings.json.bak_YYYYmmdd_HHMMSS`)
     - abre arquivo para edicao (Qt/fallback do sistema)
   - metodo `consolidate_input_files`:
     - usa ultimo `import_run_*.json` do projeto com `file_reports`
     - move arquivos de `docs_entrada` para:
       - `processadas/` (quando `rows_inserted > 0`)
       - `processadas/nosurvivor/` (quando `rows_inserted <= 0`)
     - arquivos sem evidencia no ultimo report ficam em `docs_entrada` como `pending`
2. `tests/test_gui_menu_import_external.py`
   - cobertura nova para:
     - backup failsafe ao abrir opcoes
     - consolidacao por ultimo report
   - ajuste da contagem de acoes no menu `DB` (7 acoes).

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 420s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `11 passed`

## Update 2026-03-08 18:19 - baseline docs 4.31 + GUI menu (slice 1/2)

Session timestamp:
1. start: `2026-03-08 18:13:44 -0300`
2. end: `2026-03-08 18:19:21 -0300`

Objetivo do slice:
1. promover baseline de documentacao para `4.31`.
2. iniciar agrupamento de operacoes em menu superior da GUI sem mexer no layout da toolbar.
3. adicionar importacao externa de XLS/XLSX para `docs_entrada` com copia segura.

Mudancas aplicadas:
1. `gui/gui_ssa.py`
   - novo menu superior com grupos `Arquivo` e `DB` e acoes:
     - importar XLS/XLSX externo
     - abrir pasta docs_entrada
     - exportar lista atual
     - carregar dados / carregar outro DB / reescanear (Diff/Full) / atualizar derivadas / tema
   - novo handler `import_external_excel_files`:
     - copia para `docs_entrada`
     - evita sobrescrita silenciosa (`__N` quando houver colisao)
     - atualiza status e retorna sumario de resultado
   - stub headless atualizado com `QFileDialog.getOpenFileNames`.
2. `tests/test_gui_menu_import_external.py` (novo)
   - cobre montagem do menu
   - cobre importacao externa com colisao de nome e sufixo `__1`.
3. docs/baseline:
   - `README.md` promovido para `v4.31`.
   - controle de ciclo segue sincronizado em NEXT/HANDOFF.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_menu_import_external.py` -> pass
4. `timeout 360s uv run --python 3.13 pytest -q tests/test_gui_menu_import_external.py tests/test_open_docs_folder_nonblocking.py tests/test_gui_workers_rescan_data.py` -> `9 passed`

## Update 2026-03-08 17:56 - fechamento dos pendentes de organizacao de importacao

Session timestamp:
1. start: `2026-03-08 17:37:15 -0300`
2. end: `2026-03-08 17:55:42 -0300`

Objetivo do slice:
1. fechar os pendentes de curto prazo sem refatoracao ampla:
   - politica de short-circuit via config,
   - consolidacao de alias de tabela no upsert,
   - regra final de subpastas para full rescan.

Mudancas aplicadas:
1. `config/default_settings.json`
   - nova chave: `import_settings.upsert_short_circuit_policy` (default `consulta_only`).
2. `core/app_logic.py`
   - aplica politica de upsert do settings no runtime (`database.configure_upsert_short_circuit_policy`).
   - em `force_import=true`, aplica enforcement de politica:
     - `include_processadas=false`
     - `ignore_nosurvivor=true`
     - `move_processed_after_import=false`
3. `armazenamento/database.py`
   - wrapper novo `configure_upsert_short_circuit_policy`.
4. `armazenamento/database_upsert_logic.py`
   - suporte a politica runtime (nao apenas env var).
   - resolucao de tabela passou a usar resolvedor unico de `database.py` (remove loops duplicados de alias).

Regra final de subpastas (estado atual):
1. full rescan:
   - nao varre `processadas/`
   - ignora `processadas/nosurvivor/`
   - nao move arquivos ao final
2. incremental/controlado:
   - pode mover para `processadas/`
   - zero-survivor pode ir para `processadas/nosurvivor/`

Gates do slice:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_import_run_report.py tests/test_default_settings_import_settings.py` -> pass
2. `uv run --python 3.13 ruff check core/app_logic.py armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_import_run_report.py tests/test_default_settings_import_settings.py` -> pass
3. `uv run --python 3.13 ty check core/app_logic.py armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_import_run_report.py tests/test_default_settings_import_settings.py` -> pass
4. `timeout 360s uv run --python 3.13 pytest -q tests/test_default_settings_import_settings.py tests/test_import_run_report.py tests/test_upsert_fast_path.py tests/test_database_upsert_canonical_write.py` -> `33 passed`
5. `timeout 240s uv run --python 3.13 pytest -q tests/test_app_logic_postprocess_moves.py tests/test_app_logic_full_rescan_lock.py` -> `4 passed`

## Update 2026-03-08 17:39 - comparativo final A/B consolidado

Objetivo do slice:
1. consolidar em tabela unica os resultados das duas rodadas A/B.
2. registrar diretriz operacional final para full rescan.

Tabela consolidada (dados reais):

| scenario | move_enabled | duration_s | extract_s | validate_s | insert_s | moved_xlsx | root_xlsx_left |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pair_with_xls / on_first | true | 2089.784 | 169.827 | 248.129 | 1660.315 | 409 | 22 |
| pair_with_xls / off_second | false | 1543.888 | 129.326 | 163.671 | 1220.099 | 0 | 431 |
| pair_xlsx_only / off_first | false | 1391.946 | 124.522 | 158.853 | 1097.499 | 0 | 431 |
| pair_xlsx_only / on_second | true | 1610.010 | 139.968 | 181.384 | 1277.147 | 409 | 22 |

Leitura consolidada:
1. efeito de `move_on` em full rescan ficou consistente nas duas rodadas:
   - par com `.xls`: `+35.36%` em duracao, `+36.08%` em `sum_insert`.
   - par so `.xlsx`: `+15.67%` em duracao, `+16.37%` em `sum_insert`.
2. no par `.xlsx` (mais limpo), `move_on` foi pior em todas as familias de `insert_seconds`:
   - `Consulta SSA`: `+76.350s`
   - `Todas as SSAs`: `+62.529s`
   - `SSAs Executadas`: `+33.565s`
3. decisao operacional consolidada:
   - full rescan: manter `move_processed_after_import=false`.
   - incremental/controlado: `move` pode seguir habilitado.

Artefatos de evidencia:
1. `logs/full_ab_move_policy_summary_20260308_154314.json`
2. `logs/full_ab_move_policy_reverse_summary_20260308_171101.json`
3. `logs/move_policy_comparison_20260308_172923.csv`
4. `logs/move_policy_family_insert_20260308_172923.csv`
5. `logs/move_policy_comparison_20260308_172923.svg`

## Update 2026-03-08 17:18 - instrumentacao de fases e full A/B reverso

Session timestamp:
1. start: `2026-03-08 16:20:19 -0300`
2. end: `2026-03-08 17:18:45 -0300`

Objetivo do slice:
1. medir com evidencia o impacto real de `move_processed_after_import` no full rescan.
2. separar no report JSON o tempo de fase de arquivo (extracao/validacao/upsert) vs pos-processamento (move/cache).

Evidencia de benchmark full:
1. par full anterior (on primeiro, com espelho incluindo `.xls`):
   - `logs/full_ab_move_policy_summary_20260308_154314.json`
   - resultado: `on` mais lento que `off` em `+35.36%` (duracao) e `+36.08%` (`sum_insert`).
2. par full reverso (off primeiro, espelho rapido so `.xlsx`):
   - `logs/full_ab_move_policy_reverse_summary_20260308_171101.json`
   - resultado: `on` mais lento que `off` em `+15.67%` (duracao) e `+16.37%` (`sum_insert`).

Leitura consolidada:
1. o impacto negativo de `move_processed_after_import` em full rescan foi confirmado por dois pares full.
2. o efeito nao e mais tratado como `+687%`; o intervalo observado agora ficou entre ~`+16%` e ~`+36%` conforme cenario.
3. maior pressao segue no hot path de upsert (campo `sum_insert`).

Correcao entregue no runtime (patch minimo):
1. arquivo alterado: `core/app_logic.py`.
2. arquivo de teste alterado: `tests/test_import_run_report.py`.
3. regra operacional aplicada em runtime:
   - se `force_import=true` e `move_processed_after_import=true`, o fluxo desativa move com warning explicito.
4. novo bloco `durations` no `import_run_*.json` com:
   - `sum_file_extraction_seconds`
   - `sum_file_validation_seconds`
   - `sum_file_insert_seconds`
   - `run_file_processing_seconds`
   - `run_postprocess_move_seconds`
   - `run_success_cache_update_seconds`
   - `run_deterministic_cache_update_seconds`
5. comportamento funcional de importacao nao foi alterado.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_run_report.py` -> pass
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_run_report.py` -> pass
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_import_run_report.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_import_run_report.py` -> `6 passed`
5. `timeout 300s uv run --python 3.13 pytest -q tests/test_app_logic_postprocess_moves.py tests/test_app_logic_full_rescan_lock.py` -> `4 passed`

Artefatos comparativos (report visual):
1. `logs/move_policy_comparison_20260308_172923.csv`
2. `logs/move_policy_family_insert_20260308_172923.csv`
3. `logs/move_policy_comparison_20260308_172923.svg`

## Update 2026-03-08 12:44 - full rescan real com move pos-processamento ligado

Session timestamp:
1. start: `2026-03-08 11:52:23 -0300`
2. end: `2026-03-08 12:44:05 -0300`

Objetivo do slice:
1. executar full rescan completo com `move_processed_after_import=true` e comparar com baseline anterior.

Evidencia gerada:
1. report do run:
   - `logs/import_run_20260308_115621_528621.json`
2. resumo consolidado da rodada:
   - `logs/move_policy_full_rescan_summary_20260308_115621.json`
3. baseline comparado:
   - `logs/import_run_20260307_213713_316719.json`

Resultado funcional:
1. `total_candidates=431`
2. `success_count=431`
3. `error_count=0`
4. `rows_inserted_total=497162`
5. `rows_removed_invalid_identity_total=2763`
6. comportamento de move/caching permaneceu consistente.

Resultado de performance (comparativo):
1. baseline: `354.675s`
2. novo run com move ligado: `2791.239s`
3. delta: degradacao de aproximadamente `+687%` no tempo total.
4. degradacao apareceu em todas as familias (insert_seconds):
   - `Consulta SSA`: `102.823s -> 897.742s`
   - `Todas as SSAs`: `25.631s -> 367.059s`
   - `SSAs Executadas`: `56.000s -> 758.644s`
   - `SSAs Pendentes`: `7.526s -> 82.346s`
   - `SSAscomReprogramacoes`: `2.253s -> 38.676s`
   - `Outros`: `6.451s -> 80.111s`

Decisao operacional recomendada:
1. manter `move_processed_after_import=false` para full rescan pesado ate isolar causa da degradacao.
2. usar move pos-processamento apenas em importacoes controladas/incrementais por enquanto.
3. abrir slice tecnico especifico para diagnostico de impacto no hot path do upsert durante full rescan com move ligado.

Higiene:
1. diretorio pesado temporario removido:
   - `data/full_rescan_move_policy_20260308_115621`
2. apenas JSONs de evidencia foram mantidos em `logs/`.

## Update 2026-03-08 11:54 - mini importacao runtime com move pos-processamento

Session timestamp:
1. start: `2026-03-08 11:52:23 -0300`
2. end: `2026-03-08 11:54:18 -0300`

Objetivo do slice:
1. validar runtime real do fluxo `move_processed_after_import` sem editar codigo.

Evidencia de execucao:
1. mini corpus controlado com 2 arquivos:
   - `ok.xlsx` (1 linha valida)
   - `empty.xlsx` (linha sem identidade, removida na extracao)
2. run executado com move habilitado apenas para a sessao (monkeypatch de runtime de settings), sem alterar config do projeto.
3. resultado:
   - `updated=True`
   - `ok.xlsx` movido para `processadas/ok.xlsx`
   - `empty.xlsx` movido para `processadas/nosurvivor/empty.xlsx`
   - cache gerado com chaves finais:
     - `processadas/ok.xlsx`
     - `processadas/nosurvivor/empty.xlsx`
   - DB final `mini.db`: `1` linha
4. relatorio JSON:
   - `logs/import_run_20260308_115306_645961.json`
   - contagens:
     - `total_candidates=2`
     - `success_count=2`
     - `rows_extracted_total=1`
     - `rows_removed_invalid_identity_total=1`
     - `rows_inserted_total=1`
5. limpeza pos-validacao:
   - removido diretorio temporario `data/tmp_runtime_move_validation_20260308_115306`

Status:
1. fluxo validado com sucesso.
2. nenhum ajuste de codigo necessario neste slice.

## Update 2026-03-08 00:50 - regressao de testes apos mudanca de assinatura e cobertura de move

Session timestamp:
1. start: `2026-03-08 00:50:58 -0300`
2. end: `2026-03-08 00:53:36 -0300`

Diagnostico com evidencia:
1. `tests/test_import_deterministic_failure_cache.py` quebrou em runtime de teste:
   - mocks de `_update_cache_for_deterministic_failures` com assinatura antiga (`2` args)
   - runtime atual chama `3` args (`failed_files, cache_file, docs_dir`)
   - evidencia: `2 failed` no pacote focado.

Correcao aplicada:
1. ajuste minimo nos dois mocks do arquivo para assinatura de `3` args.
2. novo teste de integracao em `tests/test_import_run_report.py`:
   - valida que `run_importer_logic` move arquivo com linhas para `processadas/`
   - valida que `record_count==0` vai para `processadas/nosurvivor/`
   - valida que cache recebe os caminhos finais movidos.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile tests/test_import_deterministic_failure_cache.py tests/test_import_run_report.py` -> pass
2. `uv run --python 3.13 ruff check tests/test_import_deterministic_failure_cache.py tests/test_import_run_report.py` -> pass
3. `uv run --python 3.13 ty check tests/test_import_deterministic_failure_cache.py tests/test_import_run_report.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_import_deterministic_failure_cache.py tests/test_import_run_report.py tests/test_app_logic_postprocess_moves.py` -> `11 passed`
5. kluster (chat_id `x6pbpykege`): clean

## Update 2026-03-08 00:37 - import_settings explicitos no config padrao

Session timestamp:
1. start: `2026-03-08 00:37:06 -0300`
2. end: `2026-03-08 00:39:52 -0300`

Decisao entregue:
1. `config/default_settings.json` recebeu bloco `import_settings` com contrato explicito:
   - `include_processadas_in_full_rescan`
   - `processadas_subdir`
   - `ignore_nosurvivor_in_full_rescan`
   - `nosurvivor_subdir`
   - `move_processed_after_import`
   - `route_zero_survivor_to_nosurvivor`
2. backup de seguranca criado antes da alteracao de config:
   - `config/default_settings.json.bak_20260308_003720`
3. teste de contrato adicionado:
   - `tests/test_default_settings_import_settings.py`
4. comportamento runtime nao foi alterado neste slice (somente explicitacao de defaults no arquivo padrao).

Gates do slice:
1. `uv run --python 3.13 python -m py_compile tests/test_default_settings_import_settings.py` -> pass
2. `uv run --python 3.13 ruff check tests/test_default_settings_import_settings.py` -> pass
3. `uv run --python 3.13 ty check tests/test_default_settings_import_settings.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_default_settings_import_settings.py tests/test_app_logic_postprocess_moves.py tests/test_caching.py` -> `13 passed`
5. kluster (chat_id `x6pbpykege`): clean

## Update 2026-03-08 00:29 - postprocess move para processadas/nosurvivor (flag)

Session timestamp:
1. start: `2026-03-08 00:29:00 -0300`
2. end: `2026-03-08 00:35:23 -0300`

Decisao entregue:
1. `core/app_logic.py` ganhou pos-processamento opcional de arquivo apos importacao bem-sucedida:
   - `move_processed_after_import` (default `false`)
   - `route_zero_survivor_to_nosurvivor` (default `true`)
2. quando habilitado, o runtime move:
   - arquivo com `record_count > 0` para `processadas/`
   - arquivo com `record_count == 0` para `processadas/nosurvivor/`
3. a movimentacao ocorre no fim do fluxo de import (apos promocao do DB candidato), para evitar mover arquivo em execucao que falhou.
4. cache passa a ser atualizado com caminho final apos movimentacao.
5. risco de sobrescrita mitigado por destino unico (`__N`) quando nome de arquivo ja existir.

Teste adicionado:
1. `tests/test_app_logic_postprocess_moves.py`:
   - roteamento normal para `processadas`
   - roteamento de zero-survivor para `nosurvivor`
   - comportamento com `route_zero_survivor_to_nosurvivor=false`

Gates do slice:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_postprocess_moves.py` -> pass
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_postprocess_moves.py` -> pass
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_postprocess_moves.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_app_logic_postprocess_moves.py tests/test_caching.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py` -> `19 passed`
5. kluster (chat_id `x6pbpykege`): clean

## Update 2026-03-08 00:24 - discovery processadas/nosurvivor com cache por caminho relativo

Session timestamp:
1. start: `2026-03-08 00:24:01 -0300`
2. end: `2026-03-08 00:28:00 -0300`

Decisao entregue:
1. `core/app_logic.py` agora aplica flags de discovery no runtime de import:
   - `include_processadas_in_full_rescan` (default `false`)
   - `processadas_subdir` (default `processadas`)
   - `ignore_nosurvivor_in_full_rescan` + `nosurvivor_subdir` (default `true` + `nosurvivor`)
2. `utils/caching.py` agora:
   - descobre `.xlsx` da raiz e, opcionalmente, de `processadas/*` com ignore de subdirs.
   - usa chave de cache por caminho relativo (ex.: `processadas/lote_x/arquivo.xlsx`) para evitar colisao de basename.
   - preserva fallback legado por basename para compatibilidade do cache existente.
3. cache de sucesso e cache de falha deterministica agora usam `docs_dir` para chave consistente.
4. testes focados adicionados/atualizados em `tests/test_caching.py` para:
   - discovery com `processadas` + ignore de `nosurvivor`;
   - gravacao de cache com chave relativa;
   - leitura de cache relativo no diff hash.
5. sem mudanca de GUI/layout e sem mudanca de semantica de extracao.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py utils/caching.py tests/test_caching.py` -> pass
2. `uv run --python 3.13 ruff check core/app_logic.py utils/caching.py tests/test_caching.py` -> pass
3. `uv run --python 3.13 ty check core/app_logic.py utils/caching.py tests/test_caching.py` -> pass
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_app_logic_full_rescan_lock.py` -> `12 passed`
5. kluster (chat_id `x6pbpykege`):
   - `core/app_logic.py`: clean
   - `utils/caching.py;tests/test_caching.py`: clean

Pendencia curta (nao bloqueante):
1. Slice B: mover arquivos importados para `processadas/` e `processadas/nosurvivor/` via flag, com integracao ao hash/cache.

## Update 2026-03-07 22:59 - sentinela A/B e limpeza de artefatos pesados

Session timestamp:
1. start: `2026-03-07 22:34:15 -0300`
2. end: `2026-03-07 22:59:29 -0300`

Decisao entregue:
1. replay sentinela executado em ambiente isolado com 4 arquivos criticos:
   - `Consulta SSA - 02-03-2026_0540PM.xlsx`
   - `SSAscomReprogramacoes_07-01-2026_0225PM.xlsx`
   - `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`
   - `Todas as SSAs - 18-08-2022_1144AM.xlsx`
2. comparacao de politicas no mesmo corpus:
   - `consulta_only`: `40.064s` (melhor)
   - `no_short`: `40.590s` (`+1.31%`)
   - `all_short`: `41.644s` (`+3.95%`)
3. sem erro funcional no sentinela:
   - `files_processed=4`
   - `error_count=0`
4. limpeza local concluida para evitar lixo pesado no repo:
   - removidos: `data/sentinel_replay_20260307_224052`
   - removidos: `data/sentinel_ab_consulta_only_20260307_224225`
   - removidos: `data/sentinel_ab_no_short_20260307_224225`
   - removidos: `data/sentinel_ab_all_short_20260307_224225`
5. logs de evidencia preservados:
   - `logs/import_run_20260307_224052_346788.json`
   - `logs/import_run_20260307_224225_365396.json`
   - `logs/import_run_20260307_224305_447338.json`
   - `logs/import_run_20260307_224346_053142.json`

Residual local auditado:
1. tracked modified (pre-existente, fora deste slice): `armazenamento/database.py`, `armazenamento/database_integrity.py`, `armazenamento/database_validation.py`, `core/app_logic.py`, `data/ssas.db`, `docs_entrada/Copia de SSAPendSectorEjecutorConsulta_26-02-2021.xls`, `extracao/extractor.py`, `tests/test_db_reset_and_upsert.py`.
2. untracked pesados de benchmark anterior (nao subir para GH):
   - `data/ablation_all_short/` (~106M)
   - `data/ablation_consulta_only/` (~106M)
   - `data/ablation_no_short/` (~106M)
3. untracked de documentacao/apoio: `docs/ARCH_*.md`, `shared/semantic_duplicate_resolution.py`.

Status:
1. concluido

## Update 2026-03-07 22:23 - upsert lazy cache no ramo sem short-circuit

Session timestamp:
1. start: `2026-03-07 22:20:48 -0300`
2. end: `2026-03-07 22:23:00 -0300`

Decisao entregue:
1. em `armazenamento/database_upsert_logic.py`, o cache de linhas existentes passou a ser lazy tambem no ramo sem short-circuit.
2. removido custo inutil de montar tuple de comparacao por linha quando `enable_exact_overlap_short_circuit` esta desligado.
3. `_perform_upsert` teve decomposicao minima (helper `_collect_chunk_upsert_delta`) para reduzir complexidade sem mudar semantica.
4. contrato do helper foi documentado no codigo para manter foco (somente delta em memoria, sem IO/schema).
5. sem mudanca de semantica de merge/upsert; apenas reducao de trabalho interno no hot path.

Teste de regressao adicionado:
1. `tests/test_upsert_fast_path.py`:
   - `test_perform_upsert_non_short_policy_uses_lazy_existing_cache`
   - garante que o ramo nao chama `_build_existing_series_cache` no modo normal.

Gates do slice:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py` -> pass
2. `uv run --python 3.13 ruff check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py` -> pass
3. `uv run --python 3.13 ty check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py` -> pass
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_upsert_fast_path.py` -> `22 passed`
5. kluster:
   - rodada 1: 1 item P4 (complexidade em `_perform_upsert`)
   - rodada 2 apos fix: clean

Status:
1. concluido

## Update 2026-03-07 (A/B policy de short-circuit no upsert em full rescan real)

## Update 2026-03-07 22:14 - slice de contrato upsert/robust separado

Session timestamp:
1. start: `2026-03-07 22:14:00 -0300`
2. end: `2026-03-07 22:14:47 -0300`

Decisao entregue:
1. adicionado teste unitario em `tests/test_upsert_fast_path.py` para provar que:
   - `consulta_only` depende de `arquivo_origem` com prefixo `consulta ssa`.
   - `all_short` depende somente de chunk com arquivo unicos.
   - `no_short` sempre desliga o atalho.
2. adicionado teste em `tests/test_extracao.py` para provar separacao de caminho:
   - `extract_data_from_excel` roda caminho padrao sem chamar `import_excel_robust`.
   - `read_report` roda o caminho robust via `import_excel_robust`.
3. resultado dos gates para o slice:
   - py_compile: pass
   - ruff: pass
   - ty: pass
   - pytest: `43 passed`
4. impacto:
   - nenhum ajuste funcional em runtime.
   - contrato de responsabilidade entre upsert policy e robust ficou explicitamente travado em teste.

Arquivos alterados:
1. `tests/test_upsert_fast_path.py`
2. `tests/test_extracao.py`

Status:
1. concluido

Session timestamp:
1. start: `2026-03-07 21:37:13 -0300`
2. end: `2026-03-07 22:02:16 -0300`

Decisao entregue:
1. executado benchmark real com isolamento de banco em 3 runs com mesma base de entrada (`431` arquivos):
   - `SSA_UPSERT_SHORT_CIRCUIT_POLICY=consulta_only`
   - `SSA_UPSERT_SHORT_CIRCUIT_POLICY=no_short`
   - `SSA_UPSERT_SHORT_CIRCUIT_POLICY=all_short`
2. resultados de duracao:
   - `consulta_only`: `354.675s`
   - `no_short`: `479.403s` (`+35.17%`)
   - `all_short`: `654.330s` (`+84.49%`)
3. resultado funcional consolidado nas 3 politicas:
   - `431/431` arquivos processados com sucesso
   - sem erro e sem falha deterministica
   - `rows_extracted_total=497162`
   - `rows_removed_invalid_identity_total=2763`
   - `rows_inserted_total=497162`
4. integridade do DB final idêntica entre os 3 modos:
   - `76426` linhas e `76426` numero_ssa distintos
   - `82` colunas finais
   - `663` nulos em `data_cadastro`
   - sem colunas `nan*`
5. top arquivos com maior `rows_removed_invalid_identity` (igual entre os cenarios):
   - `SSAscomReprogramacoes_07-01-2026_0225PM.xlsx: 1778`
   - `SSAs Pendentes com Execução Parcial_02-02-2026_1141AM.xlsx: 323`
   - `SSAs Pendentes com Execução Parcial_10-09-2025_0317PM.xlsx: 261`
   - `SSAscomReprogramações_07-01-2026_0226PM.xlsx: 30`
6. decisão de risco:
   - manter `consulta_only` como default no fluxo de rescan
   - **NÃO** adotar `all_short` nem `no_short` como default por impacto de tempo negativo comprovado
7. arquivos de evidência:
   - `logs/import_run_20260307_213713_316719.json`
   - `logs/import_run_20260307_214318_967821.json`
   - `logs/import_run_20260307_215122_180024.json`
8. status do slice:
   - concluido

Acoes deferidas (nao bloqueantes):
1. manter monitoramento de comportamento dessa politica em novos lotes de entrada com `ssas.db` legado.
2. revalidar impacto de `no_short/all_short` apenas se surgirem cenarios com alteracao massiva de arquivos muito pequenos, pois neste corpus real eles pioraram.

## Update 2026-03-07 (slice: short-circuit policy switch no upsert)

Session timestamp:
1. start: `2026-03-07 21:35:00 -0300`

Decisao entregue:
1. implementada policy de controle para `_should_enable_exact_overlap_short_circuit` em `armazenamento/database_upsert_logic.py`:
   - `consulta_only` (padrao, comportamento atual preservado)
   - `no_short` (desabilita o short-circuit)
   - `all_short` (ativa para lote single-file)
2. atualizados `tests/test_upsert_fast_path.py` para cobrir policy default/invalid/no_short/all_short.
3. o slice de hoje **nao muda semantica de import**; prepara terreno para benchmark A/B sem risco.

Arquivos alterados:
1. `armazenamento/database_upsert_logic.py`
2. `tests/test_upsert_fast_path.py`
3. `docs/ARCH_DB_UPSERT.md`
4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
5. `docs/NEXT_CHAT_MIGRATION.md`

Validacao local:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_upsert_fast_path.py`: `20 passed`.

## Update 2026-03-07 (slice: documentacao estrutural e licao de processo)

Session timestamp:
1. start: `2026-03-07 19:22:00 -0300`

Licao de processo registrada:
1. houve falha de planejamento no sub-bloco de tuning fino do upsert:
   - leitura estrutural insuficiente antes de novos micro-ajustes
   - dependencia excessiva de sinais curtos de kluster/gates sem mapa global atualizado
   - iteracao em patch local sem documentacao arquitetural suficiente
2. a correcao de processo aprovada e:
   - manter docs estruturais por dominio
   - manter headers curtos nos modulos centrais
   - registrar experimentos locais bloqueados nos docs de controle, nao so no chat

Estado do experimento local bloqueado:
1. patch local nao commitado em `armazenamento/database_upsert_logic.py` tentou reduzir custo de no-op overlap em `Consulta SSA`.
2. resultado:
   - melhora forte em `Consulta SSA - 02-03-2026_0540PM.xlsx`
   - melhora em `SSAscomReprogramacoes_07-01-2026_0225PM.xlsx`
   - regressao inaceitavel em `Todas as SSAs - 18-08-2022_1144AM.xlsx` e `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`
3. decisao:
   - nao commitar esse patch
   - documentar arquitetura e responsabilidades antes de nova tentativa

Artefatos novos deste slice:
1. `docs/ARCHITECTURE_OVERVIEW.md`
2. `docs/ARCH_IMPORT_PIPELINE.md`
3. `docs/ARCH_DB_UPSERT.md`
4. `docs/ARCH_VALIDATION_AND_INTEGRITY.md`
5. `docs/ARCH_GUI_LOAD_AND_FILTER.md`

Pendencia aberta:
1. retomar tuning do upsert so depois da leitura estrutural desses docs e de novo plano aprovado.

## Update 2026-03-07 (slice: hardening do helper generico e tuning do merge real)

Session timestamp:
1. start: `2026-03-07 11:45:49 -0300`
2. parcial consolidado: `2026-03-07 13:35:00 -0300`

Decisao entregue:
1. `armazenamento/database.py` foi endurecido para impedir `if_exists='replace'` em `ssa_table` e aliases legados:
   - schema de SSA continua nascendo por schema canonico
   - `replace` permanece permitido apenas para tabelas genericas nao-SSA
2. o helper generico recebeu rollback explicito em falha e modularizacao interna minima, sem mudar a API publica.
3. o benchmark correto do merge real mostrou que:
   - medir `_perform_upsert()` em tabela vazia era enganoso
   - o cenario certo e tabela ja populada
4. no merge real do arquivo `Todas as SSAs - 18-08-2022_1144AM.xlsx`:
   - `chunk_size=100` -> `95.3781s`
   - `chunk_size=250` -> `75.8729s`
   - `chunk_size=500` -> `95.1726s`
5. a heuristica de upsert foi corrigida para bucket seguro:
   - ate `1000` linhas -> `100`
   - acima de `1000` -> `250`
6. `_prepare_upsert_target_row()` agora faz short-circuit em modo normal quando:
   - a linha nova e mais antiga e nao deve substituir
   - o merge resulta exatamente igual ao registro existente
7. evidencia do short-circuit no mesmo arquivo de `18.5k` linhas sobre tabela ja populada:
   - antes do short-circuit com bucket `250`: `75.8729s`
   - depois: `44.9060s`
   - `processed=0`, `rows_after=18513`

Arquivos alterados:
1. `armazenamento/database.py`
2. `armazenamento/database_upsert_logic.py`
3. `tests/test_database.py`
4. `tests/test_upsert_fast_path.py`

Validacao local:
1. `uv run --python 3.13 python -m py_compile armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_database.py tests/test_upsert_fast_path.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_database.py tests/test_upsert_fast_path.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database.py armazenamento/database_upsert_logic.py tests/test_database.py tests/test_upsert_fast_path.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_database.py tests/test_upsert_fast_path.py`: `22 passed`.

Observacao operacional:
1. um full rescan real foi iniciado com a heuristica intermediaria errada (`500`) e cancelado apos evidenciar regressao forte no merge real.
2. a causa foi diagnosticada e corrigida no mesmo sprint.
3. rerun completo final executado com sucesso:
   - report: `logs/import_run_20260307_135928_727735.json`
   - log: `logs/full_rescan_runtime_20260307_135927.log`
   - `result=True`
   - `duration_seconds=930.885`
   - DB final: `76426` linhas, `76426` SSAs distintas, `82` colunas, `0` `BLOB` em `semana_programada`
4. delta agregado contra a baseline anterior (`logs/import_run_20260307_102956_247952.json`):
   - tempo total: `1161.133s` -> `930.885s`
   - ganho: `-230.248s` (`-19.83%`)
5. delta por arquivos pesados:
   - `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`: `36.294s` -> `16.774s` (`-53.78%`)
   - `Todas as SSAs - 18-08-2022_1144AM.xlsx`: `19.083s` -> `12.348s` (`-35.29%`)
6. regressao localizada a investigar no proximo ciclo:
   - `Consulta SSA - 02-03-2026_0540PM.xlsx`: `10.050s` -> `32.887s` (`+227.23%`)
   - `SSAscomReprogramações_07-01-2026_0225PM.xlsx`: `10.537s` -> `17.922s` (`+70.09%`)

## Update 2026-03-07 (fechamento do sprint: comparacao padrao vs robust e ajuste final de filtro)

Session timestamp:
1. start: `2026-03-06 23:37:50 -0300`
2. end: `2026-03-07 00:39:00 -0300`

Decisao entregue:
1. `core.app_logic.py` fechou o ajuste final do cache de busca e do matching `prefix/suffix/exact` com separador de campo, removendo warnings de regex sem alterar a semantica aprovada.
2. o conflito do kluster sobre `rule_13/rule_23` foi mantido como decisao intencional:
   - nao reintroduzir parser exotico `OR/OU` na busca geral
   - filtros de coluna continuam com comportamento de OR no fluxo proprio da GUI/worker
3. foi rodada comparacao direta padrao vs robust em ambiente isolado, no corpus completo, usando o mesmo `run_importer_logic()` e trocando apenas a funcao de extracao no modo robust.

Arquivos alterados:
1. `core/app_logic.py`
2. `docs/RECOVERY_BACKLOG.md`
3. `docs/NEXT_CHAT_MIGRATION.md`
4. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`

Validacao do ajuste local:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_filter_contract.py tests/test_filter_modes.py tests/test_filter_regression.py tests/test_import_single_error_classification.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_filter_contract.py tests/test_filter_modes.py tests/test_filter_regression.py tests/test_import_single_error_classification.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_filter_contract.py tests/test_filter_modes.py tests/test_filter_regression.py tests/test_import_single_error_classification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_app_logic_filter_contract.py tests/test_filter_modes.py tests/test_filter_regression.py tests/test_import_single_error_classification.py`: `20 passed`.

Comparacao direta padrao vs robust:
1. artefato consolidado: `LocalTemp/compare_standard_vs_robust_20260306_234004/comparison_summary.json`
2. padrao:
   - report: `logs/import_run_20260306_234004_171299.json`
   - elapsed: `1707.121s`
   - `431/431` arquivos com sucesso
   - DB final: `76426` linhas, `82` colunas, sem `nan_*`, sem `BLOB` em `semana_programada`
3. robust:
   - report: `logs/import_run_20260307_000831_376554.json`
   - elapsed: `1812.105s`
   - `431/431` arquivos com sucesso
   - DB final: `76426` linhas, `84` colunas, sem `nan_*`, mas com colunas extras `sn` e `sn_1`
4. delta fim-a-fim:
   - robust ficou `104.984s` mais lento
   - padrao foi `6.15%` mais rapido no total
5. delta por fase:
   - extracao: robust `236.106%` mais lento (`530.664s` vs `157.886s`)
   - validacao: robust `27.627%` mais rapido (`160.659s` vs `221.986s`)
   - insercao: robust `15.421%` mais rapido (`1111.881s` vs `1314.608s`)
6. diferenca de contagem:
   - robust extraiu `2` linhas a menos no total
   - divergencia restrita a duplicatas exatas em:
     - `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`
     - `Todas as SSAs - 18-08-2022_1144AM.xlsx`
   - DB final permaneceu identico em linhas e `numero_ssa` distintos

Conclusao operacional:
1. com o estado atual do branch, o gargalo dominante continua no merge/upsert.
2. o robust nao e o melhor caminho fim-a-fim hoje, apesar de ganhar em `validacao` e `insercao`.
3. o robust ainda carrega debt proprio de schema/cabecalho, evidenciado por `sn`, `sn_1` e repeticao de warnings de sanitizacao de colunas dinamicas.

Deferido por controle de escopo:
1. revisar por que o robust ainda produz `sn` e `sn_1`.
2. decidir se o proximo ciclo ataca performance do upsert ou cleanup especifico do caminho robust.

## Update 2026-03-07 (slice minimo: cleanup local do robust sem aceitar `.1/.2`)

Session timestamp:
1. start: `2026-03-07 10:08:22 -0300`
2. end: `2026-03-07 10:26:42 -0300`

Decisao entregue:
1. `utils/robust_importer.py` passou a reescrever qualquer duplicata pontuada remanescente sem preservar ponto no nome final:
   - duplicata semantica conhecida continua indo para canones dedicados
   - duplicata pontuada desconhecida agora vira sufixo com underscore
2. o helper compartilhado experimental nao foi ligado ao runtime neste slice; o caminho adotado foi o patch local de menor risco no robust.
3. o criterio funcional do usuario foi validado no corpus inteiro do robust:
   - `TOTAL 431`
   - `BAD_COUNT 0`
   - nenhum `.1/.2`
   - nenhum `sn` ou `sn_1`

Arquivos alterados:
1. `utils/robust_importer.py`
2. `tests/test_robust_importer.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile utils/robust_importer.py tests/test_robust_importer.py`: pass.
2. `uv run --python 3.13 ruff check utils/robust_importer.py tests/test_robust_importer.py`: pass.
3. `uv run --python 3.13 ty check utils/robust_importer.py tests/test_robust_importer.py`: pass.
4. `timeout 300s uv run --python 3.13 pytest -q tests/test_robust_importer.py tests/test_real_spreadsheet_import.py tests/test_import_novas_colunas.py`: `15 passed`.
5. varredura real do corpus robust:
   - `431` arquivos `.xlsx`
   - `BAD_COUNT 0`

Deferido por controle de escopo:
1. qualquer centralizacao posterior da resolucao semantica em modulo compartilhado fica para outro ciclo, somente se houver ganho concreto alem do patch local atual.

## Update 2026-03-06 (slice minimo: mensagens de log operacionais no import)

Session timestamp:
1. start: `2026-03-06 22:02:55 -0300`
2. end: `2026-03-06 22:17:44 -0300`

Decisao entregue:
1. logs de validacao em `core.app_logic` deixaram de usar texto generico para regras sem label dedicado e agora exibem `Violacao de validacao [...]`.
2. mensagens de validacao critica, conclusao de import e skip por extracao vazia ficaram explicitas e com contexto do arquivo.
3. warnings do extrator para `sem numero de SSA`, `sem semana de cadastro` e resumo final agora carregam o nome do arquivo e contagens operacionais.

Arquivos alterados:
1. `core/app_logic.py`
2. `extracao/extractor.py`
3. `tests/test_extracao.py`
4. `tests/test_import_single_error_classification.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_single_error_classification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_import_single_error_classification.py`: `25 passed`.

Deferido por controle de escopo:
1. qualquer mudanca adicional de semantica de import, schema ou tratamento de invalidos continua fora deste slice.

## Update 2026-03-06 (slice minimo: observabilidade por arquivo e classificacao de invalidos)

Session timestamp:
1. start: `2026-03-06 21:52:12 -0300`
2. end: `2026-03-06 21:58:35 -0300`

Decisao entregue:
1. `_import_single_file()` agora coleta tempos por arquivo em `extracao`, `validacao` e `insercao`, alem de contadores de linhas extraidas, removidas e prontas para inserir.
2. `run_importer_logic()` agora persiste `file_reports` no `import_run_*.json`, com totais agregados do slice.
3. o extrator agora classifica invalidos sem identidade em dois grupos:
   - vazios
   - com payload
4. a classificacao considera tambem linhas totalmente vazias removidas cedo e ignora whitespace puro ao decidir se ha payload.

Arquivos alterados:
1. `core/app_logic.py`
2. `extracao/extractor.py`
3. `tests/test_extracao.py`
4. `tests/test_import_run_report.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_import_run_report.py tests/test_import_single_error_classification.py`: `30 passed`.

Deferido por controle de escopo:
1. medir o ganho agregado do patch de upsert em full rescan completo fica para o proximo passo, com nova aprovacao explicita.

## Update 2026-03-06 (slice minimo: fast path seguro no upsert de banco vazio)

Session timestamp:
1. start: `2026-03-06 21:10:49 -0300`
2. end: `2026-03-06 21:19:55 -0300`

Decisao entregue:
1. `_perform_upsert()` agora usa fast path de append direto quando o chunk tem `numero_ssa` unicos e nao existe nenhum desses SSAs no banco.
2. `_persist_upsert_chunk()` agora converte `numpy scalar` para escalar Python antes do `to_sql`, evitando serializacao indevida como `BLOB`.
3. o fast path reabre transacao quando `to_sql` encerra o contexto, alinhado com o bloco `no_ssa`.

Arquivos alterados:
1. `armazenamento/database_upsert_logic.py`
2. `tests/test_upsert_fast_path.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database_upsert_logic.py tests/test_upsert_fast_path.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_upsert_fast_path.py`: `5 passed`.

Prova pratica:
1. lote real: `Todas as SSAs - 18-08-2022_1144AM.xlsx`
2. `processed_fast=18513`, `rows_fast=18512`
3. `processed_legacy=18513`, `rows_legacy=18512`
4. `blob_fast=0`, `blob_legacy=0`
5. `time_fast=1.476s`, `time_legacy=3.902s`, `speedup=2.644x`

Deferido por controle de escopo:
1. rerun completo do full rescan para medir ganho agregado no corpus inteiro fica para o proximo passo.

## Update 2026-03-06 (slice minimo: mensagem de log para duplicidade exata/conflitante)

Session timestamp:
1. start: `2026-03-06 21:03:07 -0300`
2. end: `2026-03-06 21:07:25 -0300`

Decisao entregue:
1. o runtime de validacao em `_import_single_file()` agora traduz:
   - `duplicate_numero_ssa_exact` -> `Duplicidade exata no export`
   - `duplicate_numero_ssa_conflict` -> `Duplicidade conflitante no export`
2. regras nao mapeadas continuam no formato generico `Regra ...`.
3. nao houve mudanca de import, schema ou resultado final do banco.

Arquivos alterados:
1. `core/app_logic.py`
2. `tests/test_import_single_error_classification.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_single_error_classification.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_single_error_classification.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_import_single_error_classification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_import_single_error_classification.py`: `5 passed`.

Deferido por controle de escopo:
1. validacao detalhada dos registros invalidos por arquivo/lote segue para o proximo slice.

## Update 2026-03-06 (slice minimo: classificar duplicidade exata e silenciar bootstrap esperado)

Session timestamp:
1. start: `2026-03-06 19:59:55 -0300`
2. end: `2026-03-06 20:21:09 -0300`

Decisao entregue:
1. `duplicate_numero_ssa` agora distingue:
   - duplicidade exata de linha
   - duplicidade conflitante
2. bootstrap de DB ausente em `repair_database_if_needed()` deixou de emitir warning generico de problema.
3. o fluxo funcional de criacao/reparo nao mudou.
4. licao registrada:
   - nao assumir etapa como concluida sem confirmacao explicita
   - nao iniciar slice secundario sem aprovacao explicita
   - manter PT-BR ASCII nos blocos ativos de controle

Arquivos alterados:
1. `armazenamento/database_validation.py`
2. `armazenamento/database_integrity.py`
3. `tests/test_database_verification.py`

Validacao:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database_validation.py armazenamento/database_integrity.py tests/test_database_verification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_database_verification.py`: `16 passed`.

Deferido por controle de escopo:
1. investigacao do lote com `1778` registros invalidos segue para o proximo grupo de acoes.

## Update 2026-03-06 (slice minimo: cobertura por fase do extrator)

Session timestamp:
1. start: `2026-03-06 19:37:53 -0300`
2. end: `2026-03-06 19:40:49 -0300`

Decision delivered:
1. extractor now exposes optional phase snapshots for tests only via `_debug_phases`.
2. no runtime path changed unless the caller explicitly passes the debug dict.
3. the historical malformed execution-tail cases are now asserted by phase, not only by final output.

Files changed:
1. `extracao/extractor.py`
2. `tests/test_extracao.py`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `19 passed`.

Deferred by scope control:
1. if deeper extractor observability is needed in the future, keep it test-only unless a production debugging requirement is explicitly approved.

## Update 2026-03-06 (slice minimo: remap TEX em trailing unnamed do bloco de execucao)

Session timestamp:
1. start: `2026-03-06 16:17:08 -0300`
2. end: `2026-03-06 17:00:15 -0300`

Decision delivered:
1. the extractor now handles the second historical malformed pattern from `SSAs Executadas_22-07-2025_*`:
   - after empty-column pruning, a single trailing unnamed numeric column in the execution block is remapped to `total_tempo_tex_executada`
2. the remap stays guarded by signature checks:
   - execution-tail columns present
   - trailing unnamed column only
   - numeric payload only
3. robust importer path was not changed.

Files changed:
1. `extracao/extractor.py`
2. `tests/test_extracao.py`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `19 passed`.
5. real-file extractor repro for the 6 historical files:
   - all 6 now return `nan_cols=[]`
   - all 6 now expose `total_tempo_tex_executada`
6. full rescan confirmation:
   - JSON: `logs/import_run_20260306_162834_535342.json`
   - log: `logs/full_rescan_runtime_20260306_162833.log`
   - duration: `1043.059s`
   - `success_count=431`, `error_count=0`, `deterministic_failure_count=0`
   - placeholder warning count for `['nan']`: `0`
   - final DB columns: `82`
   - `nan_*` columns absent from `ssa_table`

Deferred by scope control:
1. if desired, the next semantic review is whether any other historical export family still contains unlabeled execution-tail fields beyond TEX.

## Update 2026-03-06 (runtime validation: full rescan apos remap de colunas sem header)

Session timestamp:
1. start: `2026-03-06 16:00:09 -0300`
2. end: `2026-03-06 16:15:00 -0300`

Runtime validation delivered:
1. full rescan completed successfully after the extractor remap hotfix.
2. result JSON: `logs/import_run_20260306_160032_646798.json`
3. runtime log: `logs/full_rescan_runtime_20260306_160032.log`
4. duration: `868.266s`
5. processed files: `431`
6. import errors: `0`
7. deterministic failures: `0`
8. ignored legacy `.xls`: `135`

Final DB outcome:
1. promoted backup path: `data/ssas.db.full_rescan_backup_20260306_161500`
2. rows: `76426`
3. distinct `numero_ssa`: `76426`
4. columns: `82`
5. null `data_cadastro`: `608`
6. `nan_1` and `nan_2` no longer exist in `ssa_table`

Residual risk after this run:
1. runtime still logged raw placeholder discard `['nan']` in some historical `SSAs Executadas_22-07-2025_*` files.
2. final schema is clean, but those single unlabeled columns may still deserve semantic review to confirm whether any valid data is being discarded.

## Update 2026-03-06 (slice minimo: remapear colunas finais sem header apos anomalia)

Session timestamp:
1. start: `2026-03-06 15:48:57 -0300`
2. end: `2026-03-06 15:54:02 -0300`

Decision delivered:
1. the extractor now remaps the concrete malformed pattern `anomalia + 3 unnamed trailing columns` directly to:
   - `total_tempo_tpe_executada`
   - `total_tempo_tex_executada`
   - `total_tempo_tpo_executada`
2. the rule is structural and no longer depends on the filename.
3. robust importer path was not changed.

Files changed:
1. `extracao/extractor.py`
2. `tests/test_extracao.py`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `16 passed`.
5. real-file repro:
   - `docs_entrada/SSAs Executadas_22-07-2025_0309PM.xlsx`
   - result: `has_nan_cols=[]`
   - tail columns: `anomalia`, `total_tempo_tpe_executada`, `total_tempo_tex_executada`, `total_tempo_tpo_executada`, `status_execucao_prazo`

Deferred by scope control:
1. run a fresh full-corpus rescan to confirm whether any other source still creates `nan_*`.
2. keep historical-system `.xls` files outside the main DB path until a dedicated legacy storage design is approved.

## Update 2026-03-06 (slice minimo: blindagem explicita contra .xls legado no pipeline principal)

Session timestamp:
1. start: `2026-03-06 15:29:53 -0300`
2. end: `2026-03-06 15:46:30 -0300`

Decision delivered:
1. the main runtime still processes only `.xlsx`, but now also records ignored legacy `.xls` files explicitly.
2. import JSON reports now include:
   - `counts.ignored_legacy_excel_count`
   - `files.ignored_legacy_excel`
3. this is observability and governance hardening only; no legacy `.xls` ingestion was enabled.

Files changed:
1. `utils/caching.py`
2. `core/app_logic.py`
3. `tests/test_caching.py`
4. `tests/test_import_run_report.py`

Validation:
1. `uv run --python 3.13 python -m py_compile utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
2. `uv run --python 3.13 ruff check utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
3. `uv run --python 3.13 ty check utils/caching.py core/app_logic.py tests/test_caching.py tests/test_import_run_report.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_caching.py tests/test_import_run_report.py`: `11 passed`.

Evidence:
1. new regression `test_get_ignored_legacy_excel_files_lists_only_xls`
2. import report tests now assert ignored legacy `.xls` accounting in the JSON payload

Deferred by scope control:
1. actual historical-system ingestion remains disabled and out of scope.
2. routing legacy `.xls` into another DB/table remains a future design slice.

## Update 2026-03-06 (slice minimo: GUI reescaneamento nao modal, sem mudar layout)

Session timestamp:
1. start: `2026-03-06 14:09:22 -0300`
2. end: `2026-03-06 14:20:07 -0300`

Decision delivered:
1. the reescaneamento dialog no longer blocks the main window.
2. the existing dialog layout, texts, buttons, and workflow were preserved.
3. `rescan_data()` now shows the progress dialog non-modally and returns immediately.
4. the active dialog reference is retained on the window during the run and released when the dialog finishes.
5. worker cleanup and retired-worker pruning now happen on worker finish callbacks instead of after `exec()`.

Files changed:
1. `gui/widgets/rescan_progress_dialog.py`
2. `gui/ssa/gui_workers.py`
3. `tests/test_rescan_progress_dialog.py`
4. `tests/test_gui_workers_rescan_data.py`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
2. `uv run --python 3.13 ruff check gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
3. `uv run --python 3.13 ty check gui/widgets/rescan_progress_dialog.py gui/ssa/gui_workers.py tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_rescan_progress_dialog.py tests/test_gui_workers_rescan_data.py tests/test_rescan_worker_cleanup.py`: `13 passed`.
5. GUI smoke:
   - `timeout 30s env QT_QPA_PLATFORM=offscreen uv run --python 3.13 python main.py --gui`
   - result: process stayed alive until timeout (`124`) with no Python traceback.

Evidence:
1. new regression `test_rescan_progress_dialog_starts_non_modal`
2. new regression `test_rescan_data_shows_progress_dialog_without_blocking`
3. updated worker-dialog lifecycle coverage in `tests/test_gui_workers_rescan_data.py`

Deferred by scope control:
1. root-cause cleanup for `nan_1` and `nan_2` remains a separate import/schema slice.
2. optional auto-load of the new DB after rescan completion remains unchanged.

## Update 2026-03-06 (doc sync: runtime validation of staged full rescan)

Session timestamp:
1. start: `2026-03-06 13:53:56 -0300`
2. end: `2026-03-06 14:09:22 -0300`

Runtime validation delivered:
1. real full rescan completed successfully with staged candidate DB promotion.
2. run result: `true`
3. duration: `918.206s`
4. candidate DB was promoted and not preserved.
5. deterministic failures: `0`
6. import errors: `0`

Evidence:
1. runtime log: `logs/full_rescan_runtime_20260306_135403.log`
2. JSON report: `logs/import_run_20260306_135404_209159.json`
3. promoted backup path: `data/ssas.db.full_rescan_backup_20260306_140922`
4. final DB metrics:
   - rows: `76426`
   - distinct `numero_ssa`: `76426`
   - columns: `84`
   - null `data_cadastro`: `608`
   - non-null `total_de_reprogramacoes`: `3987`
   - non-null `num_reprogramacoes`: `36603`

Residual risk confirmed by runtime:
1. schema drift is reduced but not eliminated:
   - `nan_1`: `12082` non-null values
   - `nan_2`: `11835` non-null values
2. `sn_retirado` and `sn_instalado` remain populated and appear intentional; `sn_extra` stayed empty in this run.
3. placeholder warnings still occurred during upsert (`Colunas dinamicas placeholder foram descartadas: ['nan']`), which means GUI cleanup alone would only hide the symptom, not solve the import/schema source.
4. an old preserved candidate from the aborted pre-fix run still exists for forensic comparison:
   - `data/ssas.db.full_rescan_candidate_20260306_121612_837677`

Next follow-up slices:
1. GUI non-modal reescaneamento can proceed now without changing layout.
2. import/schema cleanup for unlabeled numeric columns (`nan_1`, `nan_2`) remains a separate high-priority runtime hardening item.

## Update 2026-03-06 (slice minimo: extrator tradicional tolera header duplicado e NaN no full rescan real)

Session timestamp:
1. start: `2026-03-06 13:29:39 -0300`
2. end: `2026-03-06 13:51:22 -0300`

Decision delivered:
1. the traditional extractor now evaluates fully empty columns by physical column index instead of raw header label lookup.
2. duplicate header labels no longer trigger ambiguous truth-value errors during the empty-column preservation pass.
3. `NaN` header labels are skipped safely in that pass and no longer trigger `drop(columns=...)` failures.
4. the functional rule from the prior slice remains unchanged: aliases that map to mandatory schema fields are still preserved until canonical normalization.
5. robust importer path remains unchanged.

Files changed:
1. `extracao/extractor.py`
2. `tests/test_extracao.py`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py`: `15 passed`.
5. real-file repro after fix:
   - `SSAs Pendentes de Aprovação na Emissão_02-02-2026_1141AM.xlsx`: `rows=38`, `has_data_cadastro=True`
   - `SSAs Executadas_22-07-2025_0303PM (2).xlsx`: `rows=223`, `has_data_cadastro=True`
   - `Pendentes de Planejamento_02-02-2026_1142AM.xlsx`: `rows=57`, `has_data_cadastro=True`

Evidence:
1. blocked real rescan log before the fix: `logs/full_rescan_runtime_20260306_121612.log`
2. real corpus failures reproduced there:
   - duplicate header label `Desde` caused `ValueError: The truth value of a Series is ambiguous`
   - repeated `NaN` headers caused `KeyError: '[np.float64(nan)] not found in axis'`
3. new regressions:
   - `test_extract_data_from_excel_handles_duplicate_header_labels_without_ambiguity`
   - `test_extract_data_from_excel_drops_nan_header_columns_safely`

Deferred by scope control:
1. rerun the full real-corpus staged rescan after this hotfix is committed.
2. GUI non-modal rescan remains a separate next slice after the real rescan validation completes.

## Update 2026-03-06 (slice minimo: full rescan com DB candidato e promocao final)

Session timestamp:
1. start: `2026-03-06 10:09:56 -0300`
2. end: `2026-03-06 10:28:06 -0300`

Decision delivered:
1. `force_import=True` no longer rotates the primary DB at the beginning of the run.
2. full rescan now imports into an isolated candidate DB path first.
3. the candidate DB is validated before promotion.
4. the primary DB is rotated and replaced only after successful import completion.
5. if full rescan fails or is cancelled after processing starts, the primary DB remains untouched and the candidate DB is preserved for evidence.

Files changed:
1. `core/app_logic.py`
2. `tests/test_import_run_report.py`

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: pass.
4. `timeout 240s uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_run_report.py`: `6 passed`.

Evidence:
1. `test_run_importer_logic_full_rescan_failure_preserves_primary_db`
2. `test_run_importer_logic_full_rescan_success_promotes_candidate_at_end`
3. import JSON payload now records:
   - `primary_db_path`
   - `working_db_path`
   - `candidate_db_path`
   - `promoted_backup_path`
   - `candidate_preserved`

Deferred by scope control:
1. GUI still uses modal progress dialog during rescan.
2. user-facing choice to load/promote the new DB after validation is still pending.
3. broader end-to-end runtime smoke on the real corpus remains a separate follow-up step.

## Update 2026-03-06 (slice minimo: tabela canonica explicita + guard do DataLoaderWorker)

Session timestamp:
1. start: `2026-03-06 09:41:48 -0300`
2. end: `2026-03-06 10:09:56 -0300`

Decision delivered:
1. canonical SSA table naming is now explicit in shared runtime constants and primary entry points.
2. legacy aliases `ssas` and `ssa_chamados` remain accepted only as compatibility inputs.
3. `DataLoaderWorker` now guarantees a non-empty canonical fallback table name even when the requested identifier is invalid.
4. robust importer path remains unchanged.

Files changed:
1. `shared/db_names.py`
2. `interface/cli.py`
3. `gui/workers/data_loader_worker.py`
4. `gui/gui_ssa.py`
5. `armazenamento/database_validation.py`
6. `armazenamento/database_integrity.py`
7. `armazenamento/database.py`
8. `tests/test_cli_get_ssa_query_identifier_guard.py`
9. `tests/test_data_loader_worker.py`
10. `tests/test_database_verification.py`

Validation:
1. `uv run --python 3.13 python -m py_compile shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check shared/db_names.py interface/cli.py gui/workers/data_loader_worker.py gui/gui_ssa.py armazenamento/database_validation.py armazenamento/database_integrity.py armazenamento/database.py tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_cli_get_ssa_query_identifier_guard.py tests/test_data_loader_worker.py tests/test_database_verification.py`: `28 passed`.

Evidence:
1. new tests:
   - `test_get_ssa_query_accepts_second_legacy_alias`
   - `test_resolve_target_table_accepts_second_legacy_alias`
   - `test_resolve_target_table_invalid_identifier_falls_back_to_canonical`
2. `DataLoaderWorker` item from Kluster was fixed and re-verified clean.

Deferred by explicit scope decision in this round:
1. structural Kluster findings outside the approved slice were not implemented:
   - CLI interactive scan performance
   - GUI naming cleanup around clear-all filters
   - logging-system migration
   - pagination deduplication
   - circular-import redesign
   - GUI resize performance refactor
2. deeper runtime/test cleanup of legacy table aliases outside the touched entry points remains incremental work, not a one-shot refactor.

## Update 2026-03-06 (slice minimo: extrator preserva alias obrigatorio vazio)

Session timestamp:
1. start: `2026-03-06 00:28:26 -0300` (branch-cycle diagnostic baseline)
2. end: `2026-03-06 09:41:48 -0300`

Decision delivered:
1. the traditional extractor now preserves fully empty columns when they map to mandatory schema fields, instead of dropping them before canonical normalization.
2. a shared import contract now defines:
   - mandatory schema columns for extraction,
   - required validation columns and severities,
   - allowed statuses for missing `data_cadastro`.
3. this slice does not change the robust importer path and does not touch upsert/runtime table swap behavior.

Files changed:
1. `extracao/extractor.py`
2. `armazenamento/database_validation.py`
3. `shared/import_contract.py`
4. `tests/test_extracao.py`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py armazenamento/database_validation.py shared/import_contract.py tests/test_extracao.py tests/test_database_verification.py`: pass.
4. `timeout 180s uv run --python 3.13 pytest -q tests/test_extracao.py tests/test_database_verification.py`: `26 passed`.

Evidence:
1. new regression: `test_extract_data_from_excel_preserves_empty_required_alias_until_normalization`.
2. verified mandatory alias coverage in `config/column_mappings.json` for `numero_ssa`, `descricao_ssa`, and `data_cadastro`.
3. expected runtime impact: files with header `Emitida Em` present but fully empty no longer fail early with `Missing required columns after normalization: ['data_cadastro']`.

Deferred to next approved slice:
1. canonical table-name alias cleanup across runtime/tests (`ssas`, `ssa_table`, `ssa_chamados`).
2. safe staging DB for full rescan so swap happens only after import/validation completion.
3. broader hardcode reduction for import/upsert policy beyond this minimal contract.

## Update 2026-03-05 (slice minimo: import_run json automatico)

Session timestamp:
1. start: `2026-03-05 21:27:29 -0300`
2. end: `2026-03-05 21:31:20 -0300`

Decision delivered:
1. every `run_importer_logic` execution now emits a structured JSON report in `logs/`.
2. file naming: `logs/import_run_<timestamp>.json`.
3. behavior is unchanged for import rules; this is observability only.

Files changed:
1. `core/app_logic.py`
2. `tests/test_import_run_report.py`

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_import_run_report.py`: pass.
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_import_run_report.py`: pass.
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_import_run_report.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_import_run_report.py tests/test_import_cache_integrity.py`: `3 passed`.

Evidence:
1. runtime smoke for no-change path generated: `logs/import_run_20260305_213050_586834.json`.
2. smoke status: `no_changes`, total candidates `0`.

Deferred by explicit user request:
1. treatment for `1778` continuation rows from `SSAscomReprogramacoes_*` remains deferred to next action group.

## Update 2026-03-05 (slice minimo: bootstrap sem falso no-such-table)

Session timestamp:
1. start: `2026-03-05 20:24:05 -0300`
2. end: `2026-03-05 20:27:24 -0300`

Decision delivered:
1. `ensure_column_exists` now exits safely when target table does not exist yet.
2. this removes false startup noise (`no such table: ssa_table`) during early full-rescan/bootstrap phase.

Files changed:
1. `armazenamento/database.py`
2. `tests/test_database_verification.py`

Technical note:
1. guard added before `ALTER TABLE`:
   - checks `sqlite_master` for target table existence.
   - if absent, returns `False` with debug message and no error log.

Validation:
1. `uv run --python 3.13 python -m py_compile armazenamento/database.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database.py tests/test_database_verification.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "ensure_column_exists_no_error_when_table_absent or validate_missing_data_cadastro_status_exceptions_are_allowed or verify_valid_database"`: `3 passed`.

## Update 2026-03-05 (slice minimo: ADI/ASE sem data_cadastro)

Session timestamp:
1. start: `2026-03-05 20:08:35 -0300`
2. end: `2026-03-05 20:09:06 -0300`

Decision delivered:
1. `ADI` and `ASE` now join `SCC` as statuses allowed to have missing `data_cadastro` in validation.
2. no queue/list retry mechanism added; approach kept minimal to preserve throughput and reliability.

Files changed:
1. `armazenamento/database_validation.py`
2. `tests/test_database_verification.py`

Behavior impact:
1. lane `missing_data_cadastro` can drop from `221` residual (after SCC patch) to `0` under this rule.
2. baseline lane progression:
   - before exceptions: `2171`
   - after SCC only: `221`
   - after SCC+ADI+ASE: `0` (expected for current corpus)

Validation:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "validate_missing_data_cadastro_status_exceptions_are_allowed or validate_missing_data_cadastro_scc_is_allowed or validate_valid_dataframe or validate_invalid_dates"`: `3 passed, 9 deselected`.

## Update 2026-03-05 (cross-file diagnostico ADI/ASE sem data_cadastro)

Session timestamp:
1. start: `2026-03-05 19:29:06 -0300`
2. end: `2026-03-05 19:42:55 -0300`

Executed in this slice (diagnostic only, no runtime edit):
1. cross-file join by `numero_ssa` over all valid extractor outputs.
2. target set: rows with `situacao in {ADI, ASE}` and missing `data_cadastro`.
3. comparison lanes:
   - same SSA in other files (status and data presence),
   - file date parsed from filename vs SSA prefix year,
   - file date vs `semana_cadastro` (iso week monday approximation).

Evidence:
1. scan scope:
   - files total: `431`
   - files ok: `406`
   - extraction errors: `25`
2. target population:
   - unique SSAs with ADI/ASE + missing date: `213`
   - affected rows: `279`
3. cross-file outcomes:
   - with data in another occurrence: `158/213` (`74.18%`)
   - without data in all occurrences: `55/213` (`25.82%`)
   - with status change to states outside ADI/ASE: `164/213` (`76.99%`)
   - only ADI/ASE states across occurrences: `49/213` (`23.00%`)
   - still ADI/ASE but with data somewhere: `7/213` (`3.29%`)
4. status where data appears (same SSA family):
   - top states: `STE=864`, `SPG=123`, `AAT=71`, `SEE=69`, `APG=59`
   - ADI/ASE with data also exist but low (`ADI=8`, `ASE=6`)
5. date consistency checks:
   - for all `279` ADI/ASE missing rows: `file_year - ssa_year = 0`
   - week approximation (`semana_cadastro` -> monday) vs file date:
     - count `279`, p50 `3` days, p75 `8` days
     - within 14 days: `254`
     - within 30 days: `276`

Conclusion:
1. there is no strict one-to-one rule `ADI/ASE => always no data_cadastro`.
2. missing date in ADI/ASE is often transient and later replaced by dated records in other files.
3. behavior is strongly concentrated in same-year and near-week snapshots, consistent with temporal lifecycle snapshots.

## Update 2026-03-05 (diagnostico ADI/ASE + mini importacao de validacao)

Session timestamp:
1. start: `2026-03-05 18:51:56 -0300`
2. end: `2026-03-05 19:26:00 -0300`

Executed in this slice (diagnostic only, no runtime edits):
1. full dataset status scan (excluding lock files `~$*.xlsx`) using extractor pipeline.
2. targeted mini importacao in temporary DB to validate new `SCC` exception behavior.
3. verification of ADI/ASE incidence over missing `data_cadastro`.

Evidence summary:
1. scan scope:
   - files total: `431`
   - files ok: `406`
   - extraction errors: `25` (same family already known: `Derivadas e Relacionadas` and `Pendentes de Aprovacao na Emissao` missing required columns).
2. global status vs missing `data_cadastro`:
   - `ADI`: total `208`, missing `155`, non-missing `53` (`74.519%` missing)
   - `ASE`: total `179`, missing `124`, non-missing `55` (`69.274%` missing)
   - `SCC`: total `3044`, missing `2409`, non-missing `635` (`79.139%` missing)
3. conclusion:
   - NOT all ADI are missing `data_cadastro`.
   - NOT all ASE are missing `data_cadastro`.
4. full-run baseline cross-check kept valid:
   - missing drop lane total remains `2171`.
   - split confirmed: `1950` SCC + `221` non-SCC (`ADI/ASE`).
5. file-level note:
   - `SSAs Pendentes Geral - 02-02-2026_1142AM.xlsx` has `ADI=16` and `ASE=22`, both `100%` missing `data_cadastro` in that file.
6. mini importacao validation:
   - temporary run completed `ok=true`, ~`7.101s`.
   - final DB kept only SCC rows with missing `data_cadastro` (`non-SCC missing = 0`), confirming current patch behavior.

Open interpretation item:
1. no canonical textual definition for ADI/ASE was found in repository docs/config; meaning remains domain-owned and should be documented by product/data owner.

Risk assessment for next low-risk hardening (deferred):
1. `LOW`: suppress false startup warning by skipping `ALTER TABLE` when target table does not exist yet (avoid `no such table: ssa_table` noise).
2. `LOW-MED`: improve observability by including source file name in extractor log `Removidos X registros invalidos`, for direct traceability.

## Update 2026-03-05 (slice minimo: SCC sem data_cadastro e valido)

Session timestamp:
1. start: `2026-03-05 16:38:52 -0300`
2. end: `2026-03-05 17:20:00 -0300`

Decision approved and delivered:
1. rows with `situacao=SCC` and missing `data_cadastro` are no longer treated as critical missing data for validation/drop.
2. scope limited to validation layer only; no extraction mapping or schema/bootstrap changes.

Files changed:
1. `armazenamento/database_validation.py`
2. `tests/test_database_verification.py`

Evidence from prior diagnostics reused in this decision:
1. baseline full-run `missing_data_cadastro`: `2171` rows.
2. `SCC` subset inside those rows: `1950`.
3. expected reduction if rule is active: `-89.820%` in missing-data drops (`2171 -> 221`).

Validation:
1. `uv run --python 3.13 python -m py_compile armazenamento/database_validation.py tests/test_database_verification.py`: pass.
2. `uv run --python 3.13 ruff check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
3. `uv run --python 3.13 ty check armazenamento/database_validation.py tests/test_database_verification.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_database_verification.py -k "validate_missing_data_cadastro_scc_is_allowed or validate_valid_dataframe or validate_invalid_dates"`: `3 passed`.

Deferred non-blocking:
1. non-SCC missing `data_cadastro` (`ADI`/`ASE`) remains strict and should be reviewed in a separate approved slice.

## Update 2026-03-05 (diagnostico full rescan zero-db: evidencia operacional)

Session timestamp:
1. start: `2026-03-05 13:26:54 -0300`
2. end parcial: `2026-03-05 14:12:23 -0300`

Executed in this slice (status: partial, with blockers):
1. backup manual do banco atual para `data/db_backups/ssas.db.pre_manual_rescan_20260305_132803.db`.
2. full rescan forcado executado (log: `logs/full_rescan_20260305_132813.log`), com termino anomalo no shell sem linha final `RESULT`.
3. passada de retomada (`force_import=False`) executada (log: `logs/rescan_resume_20260305_140405.log`) com retorno `ok=False`.
4. auditoria completa do DB gerado e comparacao contra backup pre-rescan.
5. smoke GUI executado com sucesso (`logs/gui_smoke_20260305_140702.log`, exit 0).
6. relatorio tecnico detalhado gravado em `docs/indicios_importacao.md`.

Evidence summary:
1. log full rescan: 570 linhas; janela observada ~2104s (35m04s).
2. `missing_data_cadastro`: 138 arquivos; 2171 linhas removidas.
3. removidos por "sem numero_ssa e sem descricao": 2393 linhas.
4. arquivos pulados por missing required column apos normalizacao: 2.
5. DB atual: `integrity_check=ok`, `73999` linhas, `73999` SSAs distintos, sem duplicatas.
6. schema drift critico detectado:
   - backup: 82 colunas com `id`
   - atual: 73 colunas, `id` ausente, colunas espurias `nan`, `nan_1`, `nan_2`.

Critical findings (BUG_REAL):
1. risco alto de perda de schema canonico no full rescan (perda de `id` e colunas relacionadas).
2. regra de descarte por `missing_data_cadastro` remove volume alto de linhas.
3. caso reproduzivel de skip completo de planilha (`SSAs Pendentes de Aprovacao na Emissao_*`) porque `Emitida Em` vem 100% vazio e a coluna e removida por `dropna(axis=1, how='all')` antes de fallback por colunas alternativas.

Deferred for next approved slice:
1. `HOTFIX_BLOCKER`: impedir criacao de tabela por `to_sql(... if_exists='replace')` em caminho de full rescan quando tabela ainda nao existe.
2. `STABILITY_PATCH`: preservar header de colunas criticas (ex.: `Emitida Em`) para permitir fallback de `data_cadastro` sem skip total de arquivo.
3. `STABILITY_PATCH`: adicionar observabilidade/progresso no full rescan para evitar terminos anomalos sem status final claro.

## Update 2026-03-05 (sprint importacao grave lane: strict numeric reprogramacoes)

Session timestamp:
1. start: `2026-03-05 13:05:56 -0300`
2. end: `2026-03-05 13:15:48 -0300`

Delivered in this slice:
1. `extracao/extractor.py` `_normalize_datatypes` now enforces strict numeric conversion for `num_reprogramacoes`.
2. non-numeric legacy text in `num_reprogramacoes` is coerced to null.
3. when `num_reprogramacoes` is null and `total_de_reprogramacoes` is present, a controlled backfill is applied from `total_de_reprogramacoes`.
4. focused regression tests added in `tests/test_extracao.py`:
   - `test_normalize_datatypes_num_reprogramacoes_uses_total_when_text_legacy`
   - `test_normalize_datatypes_num_reprogramacoes_keeps_numeric_value`
   - `test_normalize_datatypes_num_reprogramacoes_text_without_total_becomes_null`

Validation:
1. `uv run --python 3.13 python -m py_compile extracao/extractor.py tests/test_extracao.py`: pass.
2. `uv run --python 3.13 ruff check extracao/extractor.py tests/test_extracao.py`: pass.
3. `uv run --python 3.13 ty check extracao/extractor.py tests/test_extracao.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_extracao.py -k "normalize_datatypes_num_reprogramacoes or read_report or extract_data_from_excel"`: `9 passed, 3 deselected`.
5. kluster auto in this slice: clean -> clean.

Decision and scope:
1. this is `HOTFIX_BLOCKER` for import normalization only.
2. no GUI/layout changes.
3. no DB schema migration in this slice.
4. import concept unchanged; only numeric integrity for `num_reprogramacoes` was hardened.

## Update 2026-03-05 (pr44 review triage: critical-only fix lane)

Session timestamp:
1. start: `2026-03-05 09:30:55 -0300`
2. end: `2026-03-05 09:41:00 -0300`

Delivered in this slice:
1. fixed cubic P1 date-negation regression in date display/raw merge path.
2. fixed cubic P2 hash-column min width regression (`#` kept at 24).
3. removed silent exception suppression in width manager capture/restore path with explicit debug logs.
4. added regressions in `tests/test_gui_filter_logic.py`:
   - `test_data_cadastro_column_filter_negation_matches_display_date`
   - `test_compute_optimal_widths_keeps_hash_column_minimum_24`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/simple_width_manager.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "data_cadastro_column_filter_accepts_display_date_on_first_apply or data_cadastro_column_filter_negation_matches_display_date or best_fit_width_respects_predefined_max_for_long_columns or compute_optimal_widths_keeps_hash_column_minimum_24 or on_header_clicked_preserves_column_widths_after_sort or header_context_menu_exposes_best_fit_visible_action"`: `6 passed`.
5. kluster auto in this slice: clean -> clean -> clean -> clean -> clean.

Decision and scope:
1. this is `HOTFIX_BLOCKER` limited to real bugs in existing replay PR (#44).
2. no layout repositioning and no DB/runtime schema mutation.
3. deferred comments (non-blocking / broad changes) were kept out of this slice and remain tracked:
   - gui_table setColumnWidth try/except hardening (`comment 2890593020`)
   - test helper dedup refactor (`comment 2890610562`)
   - dynamic width limits by DPI (`comment 2890684063`)
   - affinity fallback heuristic for unknown columns (`comment 2890684069`)
   - skip-flag architectural refactor (`comment 2890684081`)
   - wider date separator heuristic (`comment 2890684089`)
   - optional sort unification with advanced helper (`comment 2890654323`)
   - process-only config backup warning (`comment 2890631211`)

## Update 2026-03-05 (safe reapply from clean base, d4 excluded)

Session timestamp:
1. start: `2026-03-05 08:37:14 -0300`
2. end: `2026-03-05 08:40:47 -0300`

Delivered in this slice:
1. created clean replay branch from fixed base `bf78666e`.
2. replayed approved commits only:
   - `9601ffb8`
   - `a87c72d7`
   - `88de4155`
   - `8400fe42`
   - `df65682c`
   - `6899894b`
   - `956c0f4a`
3. explicitly excluded `d4c2c5ca` from replay.

Validation:
1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "num_reprogramacoes or best_fit or show_all_columns_by_affinity or data_cadastro_column_filter_accepts_display_date_on_first_apply"`: `7 passed`.
5. kluster auto in replay cycle: clean -> clean -> clean.

Decision and scope:
1. this replay is `STABILITY_PATCH` + `DOC_SYNC` only.
2. no DB schema/data mutation in this cycle.
3. short-term deferred item: evaluate controlled reimplementation of `d4c2c5ca` requirements in separate slice (do not replay raw commit).

## Update 2026-03-04 (sprint7 stability: width guardrails + sort stability + show-all affinity)

Session timestamp:
1. start: `2026-03-04 10:11:48 -0300`
2. end: `2026-03-04 10:29:08 -0300`

Delivered in this slice:
1. added predefined max width guardrails for long columns:
   - `descricao_ssa`
   - `descricao_execucao`
   - `solicitante`
2. stabilized sort behavior to preserve current column widths after asc/desc sort:
   - avoids lateral "runaway" width effect after header click.
3. added header context action:
   - `Exibir todas colunas (afinidade)`
4. new affinity model (`coluna -> score desc`) introduced for ordered "show all" flow.
5. action contract aligned to existing selector:
   - source columns come from same select-all base (`ColumnSelector` available list/order).

Validation:
1. `uv run --python 3.13 python -m py_compile core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check core/config_manager.py gui/simple_width_manager.py gui/gui_ssa.py gui/ssa/gui_table.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or header_context_menu_exposes_show_all_columns_by_affinity_action or show_all_columns_by_affinity_reorders_same_select_all_set or on_header_clicked_preserves_column_widths_after_sort or best_fit_width_respects_predefined_max_for_long_columns or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `7 passed`.
5. kluster auto in this slice: clean across all touched files.

Decision and scope:
1. this is a `STABILITY_PATCH` with no GUI layout/position change.
2. no DB/schema/data mutation.
3. affinity ranking is now explicit and reusable for future column-order flows.

## Update 2026-03-04 (sprint6 hotfix: data_cadastro column filter trigger consistency)

Session timestamp:
1. start: `2026-03-04 09:53:38 -0300`
2. end: `2026-03-04 10:01:00 -0300`

Delivered in this slice:
1. root cause fixed in `gui/mixins/filter_gui_ssa_mixin.py`:
   - column-filter comparison used raw `data_cadastro` values (`YYYY-MM-DD HH:MM:SS`) only;
   - table displays dates as `DD/MM/YYYY`, causing user-visible mismatch and apparent delayed application.
2. `_apply_column_filters` now supports date display matching for slash-based terms:
   - keeps raw comparison path;
   - adds OR match against cached `DD/MM/YYYY` projection for date-like columns.
3. added helper methods for maintainability/performance:
   - `_should_match_date_display_filter(...)`
   - `_get_column_filter_date_display_series(...)` with per-DataFrame cache.
4. added regression `tests/test_gui_filter_logic.py::test_data_cadastro_column_filter_accepts_display_date_on_first_apply`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "data_cadastro_column_filter_accepts_display_date_on_first_apply or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_filter_button_state_syncs_across_tabs_without_switch"`: `4 passed`.
5. kluster auto in this slice: issue(P4,P4) -> clean -> clean -> clean.

Decision and scope:
1. this is a `HOTFIX_BLOCKER` in filter consistency path only.
2. no GUI layout/positioning change.
3. no DB schema/data mutation.

## Update 2026-03-04 (sprint5 canonical reprogramacoes numeric lane)

Session timestamp:
1. start: `2026-03-04 09:40:56 -0300`
2. end: `2026-03-04 09:44:37 -0300`

Delivered in this slice:
1. added `gui/ssa/reprogramacoes_numeric.py` with canonical helper for numeric extraction:
   - `total_de_reprogramacoes` as primary source;
   - fallback numeric parse of `num_reprogramacoes`;
   - final digit extraction fallback for legacy text rows.
2. `gui/gui_ssa.py`: robust sort for `num_reprogramacoes` now uses the shared helper.
3. `gui/ssa/gui_filters_advanced_logic.py` and `gui/ssa/gui_filters_advanced_ui.py`: advanced reprogramacoes filter/cache now use the same helper, avoiding divergent conversions.
4. `gui/gui_ssa.py`: best-fit baseline probe now guarded (`sizeHintForColumn` only when `rowCount <= 500`) to avoid O(R*C) UI cost on large tables.
5. added focused regressions:
   - `tests/test_gui_filters_advanced_logic.py::test_apply_advanced_filters_reprogramacoes_prefers_total_de_reprogramacoes_when_available`
   - `tests/test_gui_filter_logic.py::test_reprogramacoes_menu_uses_total_de_reprogramacoes_with_legacy_text_values`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/ssa/reprogramacoes_numeric.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_logic.py gui/ssa/gui_filters_advanced_ui.py tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filters_advanced_logic.py tests/test_gui_filter_logic.py -k "reprogramacoes or on_header_clicked_sorts_num_reprogramacoes_mixed_types or best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action"`: `8 passed`.
5. kluster auto in this slice: clean -> clean -> clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` without DB schema or layout change.
2. legacy text (`Reprogramacao #1`) remains accepted as input artifact; runtime now normalizes numeric behavior consistently.
3. `situacao_reprogramacao` (`(SPG)`) remains informational/legacy in this sprint and is not promoted to active filter logic.
4. deferred note kept active: legacy non-ASCII content in old scripts/tests is not globally normalized in this slice to avoid transversal high-risk edits.

## Update 2026-03-04 (sprint4 best-fit calibration against real Qt auto-fit)

Session timestamp:
1. start: `2026-03-04 09:21:19 -0300`
2. end: `2026-03-04 09:27:28 -0300`

Delivered in this slice:
1. `gui/simple_width_manager.py`: best-fit algorithm recalibrated from synthetic `"W"*N` estimate to sampled real-text pixel widths.
2. added baseline clamp against Qt real auto-fit (`sizeHintForColumn`) to avoid width over-expansion.
3. reduced sampling pressure (`sample_limit` default now `800`) and added measurement cache to reduce repeated font-metric calls.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "best_fit_width_guard_ignores_single_extreme_outlier or header_context_menu_exposes_best_fit_visible_action or table_header_uses_merged_default_alias_for_extra_column"`: `3 passed`.
5. kluster auto in this slice: issue(P4 intent/perf) -> clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` for width behavior only.
2. no GUI layout/positioning change.
3. dedicated follow-up slice opened next for `num_reprogramacoes`/`total_de_reprogramacoes`/`situacao_reprogramacao` evidence and risk handling.

## Update 2026-03-04 (sprint3 display-label merge hardening for table and add-columns)

Session timestamp:
1. start: `2026-03-04 09:02:15 -0300`
2. end: `2026-03-04 09:11:13 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: initialization now always uses canonical `load_display_mappings()` merge path.
2. guarantees merged aliases (`DEFAULT_DISPLAY_MAPPINGS` + `column_display_names` + `display_mappings`) are applied to:
   - table headers
   - add-column/filter selectors that rely on `internal_to_display`.
3. `tests/test_gui_filter_logic.py`: added regression `test_table_header_uses_merged_default_alias_for_extra_column`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "table_header_uses_merged_default_alias_for_extra_column or on_header_clicked_sorts_num_reprogramacoes_mixed_types or header_context_menu_exposes_best_fit_visible_action"`: `3 passed`.
5. kluster auto in this slice: clean -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` in display-label lane only (no DB/runtime schema mutation).
2. no GUI layout/positioning change.
3. next step remains label curation refinement (if needed) and separate DB-saneamento sprint.

## Update 2026-03-04 (sprint2 best-fit visible columns via width manager)

Session timestamp:
1. start: `2026-03-04 08:31:10 -0300`
2. end: `2026-03-04 08:39:30 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: added header context-menu action `Best fit colunas visiveis`.
2. `gui/gui_ssa.py`: added reusable orchestration methods:
   - `_compute_best_fit_width_for_column`
   - `_best_fit_column_width`
   - `best_fit_visible_columns`
3. `gui/simple_width_manager.py`: added centralized `compute_best_fit_width(...)` with anti-outlier guard.
4. `gui/gui_ssa.py`: `auto_fit_column` now reuses best-fit path first.
5. `tests/test_gui_filter_logic.py`: added regressions:
   - `test_header_context_menu_exposes_best_fit_visible_action`
   - `test_best_fit_width_guard_ignores_single_extreme_outlier`

Validation:
1. `uv run --python 3.13 python -m py_compile gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/simple_width_manager.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "header_context_menu_exposes_best_fit_visible_action or best_fit_width_guard_ignores_single_extreme_outlier or on_header_clicked_sorts_num_reprogramacoes_mixed_types"`: `3 passed`.
5. kluster auto in this slice: clarification(P4 centralize width logic) -> issue(P3 map contract) -> issue(P4 pandas constructor compatibility) -> clean.

Decision and scope:
1. this is a `STABILITY_PATCH` focused on reusable best-fit behavior only.
2. no GUI layout/positioning change.
3. db/runtime schema migration remains deferred to next sprint lane.

## Update 2026-03-04 (sprint1 hotfix: robust sort for num_reprogramacoes)

Session timestamp:
1. start: `2026-03-04 08:24:32 -0300`
2. end: `2026-03-04 08:28:21 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: added `_sort_num_reprogramacoes_robust` and routed header sort for `num_reprogramacoes` to mixed-type-safe path.
2. `tests/test_gui_filter_logic.py`: added regression `test_on_header_clicked_sorts_num_reprogramacoes_mixed_types`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass.
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "on_header_clicked_sorts_num_reprogramacoes_mixed_types or reprogramacoes_menu_builds_without_responsavel_materialized"`: `2 passed`.
5. kluster auto in this slice: clean -> clean.

Decision and scope:
1. this is a `HOTFIX_BLOCKER` for active runtime warning/failure in column sort.
2. no GUI layout/positioning change.
3. next prioritized slice remains sprint2 (`best fit all visible columns` with anti-outlier guard + label cleanup).

## Update 2026-03-04 (release snapshot v4.29 + baseline promote to v4.30)

Session timestamp:
1. start: `2026-03-04 08:14:11 -0300`
2. end: `2026-03-04 08:22:31 -0300`

Delivered in this slice:
1. created GitHub tag `v4.29` on commit `bf78666e`.
2. created GitHub release `SSA Consulta Rapida v4.29` as pre-sprint stable snapshot.
3. promoted local baseline metadata to `4.30` (`VERSION` + `config/version.json`).
4. synchronized active release docs to `4.30`.

Validation:
1. `gh release view v4.29`: published.
2. `git tag -l v4.29`: present.

Decision and scope:
1. this is a `DOC_SYNC` + release housekeeping slice before runtime changes.
2. runtime bug fix (`num_reprogramacoes` mixed-type sorting) remains prioritized for next slice.

## Update 2026-03-04 (post-merge environment cleanup and branch hygiene)

Session timestamp:
1. start: `2026-03-04 07:50:00 -0300`
2. end: `2026-03-04 07:50:20 -0300`

Delivered in this slice:
1. `.gitignore`: added `config/gui_main_preferences.json` to repository ignore policy.
2. local git index: applied `skip-worktree` to `config/gui_main_preferences.json` to stop local noise for tracked preference changes.
3. branch hygiene (local): removed all branches except `dev` and `main`.
4. branch hygiene (remote): removed non-core remote branches; remaining refs are `origin/main` and `origin/dev` (plus `origin/HEAD` pointer).
5. stash triage: `stash@{0}` inspected; contains only `config/gui_main_preferences.json` and `data/ssas.db`.

Validation:
1. `git branch --list`: only `dev`, `main`.
2. `git fetch --prune && git branch -r`: only `origin/main`, `origin/dev`, `origin/HEAD -> origin/main`.
3. `git status --short`: local residue from `config/gui_main_preferences.json` neutralized by `skip-worktree`.

Decision and scope:
1. this is a `STABILITY_PATCH` for environment hygiene only; no runtime behavior change.
2. no GUI layout/positioning changes.
3. pending explicit user confirmation: final action for `stash@{0}` (recommended path: drop).

## Update 2026-03-04 (PR #43 comments triage: real bugs fixed, noise deferred)

Session timestamp:
1. start: `2026-03-04 06:27:03 -0300`
2. end: `2026-03-04 06:29:30 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets OR-group metadata via `_reset_or_groups()`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: `_mk_remove_line` no longer uses broad silent `except Exception`.
3. `gui/gui_ssa.py`: `debounce_delay` parsing now catches only `(TypeError, ValueError)` and logs explicit fallback.
4. `gui/mixins/tab_context_gui_ssa_mixin.py`: removed duplicated `_sync_clear_filter_button_state()` call in bind flow.
5. `tests/test_gui_filter_logic.py`: added regression `test_clear_all_filters_global_resets_or_group_metadata`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_or_group_metadata or clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_button_state_syncs_across_tabs_without_switch or undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore"`: `5 passed`
5. kluster auto review run in this slice: clean -> clean -> clean -> clean

PR comment status mapping:
1. fixed now (`BUG_REAL`): stale OR-group metadata after global clear.
2. fixed now (`BUG_REAL`): broad/no-log fallback in debounce parse.
3. fixed now (`BUG_REAL`): silent broad `except` in `_mk_remove_line`.
4. fixed now (`BUG_REAL`): duplicated cross-tab clear-button sync call in bind.
5. deferred (`DECISAO_INTENCIONAL`): make debounce floor configurable now; current fixed floor is approved policy for this lane.
6. deferred (`NAO_BLOQUEANTE_DEFERIDO`): wide cleanup of broad `except` patterns across legacy GUI path (outside this minimal slice).
7. rejected (`FALSO_POSITIVO`): speculative suggestions with weak/no anchored evidence (regex over-restriction claims without reproducible regression).

Decision and scope:
1. this is a `STABILITY_PATCH` focused on real, reproducible PR findings only.
2. no layout/positioning changes.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (tab-specific search handlers and regex guard hardening)

Session timestamp:
1. start: `2026-03-04 01:40:00 -0300`
2. end: `2026-03-04 01:44:21 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: search controls now route through dedicated per-tab handlers (`main`/`filters`) for `Aplicar` and `Limpar Busca`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: added dedicated handler methods `_on_general_search_apply_clicked` and `_on_general_search_clear_clicked`.
3. `gui/mixins/filter_gui_ssa_mixin.py`: strengthened regex safety guard in `_build_column_mask` (`meta_char_count` and alternation+quantifier blocking).
4. `tests/test_gui_filter_logic.py`: added regression `test_search_buttons_route_to_tab_specific_handlers`.
5. `tests/test_gui_filter_logic.py`: added regression `test_build_column_mask_blocks_heavy_regex_patterns`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "search_buttons_route_to_tab_specific_handlers or clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or clear_filter_button_state_syncs_across_tabs_without_switch or build_column_mask_blocks_heavy_regex_patterns"`: `4 passed`
5. kluster auto review run in this slice: clean -> issue(P4 regex safety) -> clean

Decision and scope:
1. this is a `STABILITY_PATCH` focused on handler identity per tab and safety hardening for regex filter path.
2. no layout/positioning change.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (cross-tab sync for undo button state)

Session timestamp:
1. start: `2026-03-04 01:20:00 -0300`
2. end: `2026-03-04 01:39:47 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: added centralized helpers to sync `undo_filter_btn` enabled-state across all tab contexts.
2. `gui/mixins/filter_gui_ssa_mixin.py`: `_update_undo_button_state` now updates all tab undo buttons, not only active tab.
3. `tests/test_gui_filter_logic.py`: added regression `test_undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "undo_button_state_syncs_across_tabs_after_advanced_clear_and_restore or clear_advanced_filters_forces_refresh_when_pending_schedule or test_header_context_menu_apply_stores_undo_snapshot"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` for undo-state consistency and advanced-filter undo coverage.
2. no layout/positioning changes.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (cross-tab sync for clear-search button state)

Session timestamp:
1. start: `2026-03-04 00:27:39 -0300`
2. end: `2026-03-04 01:02:15 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: added central helpers to sync `clear_filter_button` state across all tab contexts.
2. `gui/mixins/filter_gui_ssa_mixin.py`: replaced single-widget `clear_filter_button.setEnabled(...)` calls with shared cross-tab sync.
3. `gui/mixins/tab_context_gui_ssa_mixin.py`: bind step now uses shared clear-button sync method.
4. `tests/test_gui_filter_logic.py`: added regression `test_clear_filter_button_state_syncs_across_tabs_without_switch`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py gui/mixins/tab_context_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter_button_state_syncs_across_tabs_without_switch or clear_filter_button_reflects_active_filters or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` for state consistency only; no layout or positioning change.
2. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (clear-search button wording clarity)

Session timestamp:
1. start: `2026-03-04 00:23:12 -0300`
2. end: `2026-03-04 00:25:01 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: changed clear-search button text from `Limpar Filtro` to `Limpar Busca`.
2. `gui/gui_ssa.py`: added explicit tooltip clarifying that only general search is cleared.
3. `tests/test_gui_filter_logic.py`: added regression `test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_clear_search_button_label_and_tooltip_are_explicit_on_both_tabs or test_clear_filter_clears_only_general_search_and_keeps_advanced_filters or test_clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `3 passed`
5. kluster auto review run in this slice: clean -> clean

Decision and scope:
1. this is a low-risk `STABILITY_PATCH` for UX wording clarity only; no filter logic behavior change.
2. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.
3. evidence commit: `182c51b0` (`STABILITY_PATCH`: clear-search button wording clarity).

## Update 2026-03-04 (tooltip encoding fix and column-filter 3-button row)

Session timestamp:
1. start: `2026-03-04 00:08:50 -0300`
2. end: `2026-03-04 00:14:10 -0300`

Delivered in this slice:
1. `gui/gui_ssa.py`: fixed corrupted week tooltip text and simplified to `Semana ISO atual`.
2. `gui/mixins/filter_gui_ssa_mixin.py`: column-filter row now has `Aplicar`, `Limpar`, `Ocultar`.
3. `gui/mixins/filter_gui_ssa_mixin.py`: `Limpar` clears current column value and reapplies filters without hiding the row.
4. `gui/widgets/filter_help_dialog.py`: help text updated to reflect `Aplicar + Limpar + Ocultar`.
5. `tests/test_gui_filter_logic.py`: updated control parser and added regression `test_column_filter_row_clear_button_clears_value_without_hiding_row`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "default_column_filter_rows_show_apply_clear_and_hide_buttons or column_filter_buttons_flow or column_filter_row_clear_button_clears_value_without_hiding_row or clear_all_filters_global_restores_default_column_filter_keys or clear_filter_on_filters_tab_clears_search_in_all_tabs"`: `5 passed`
5. kluster auto review run in this slice: clean

Diagnostic scan:
1. global scan for mojibake patterns in `*.py` completed.
2. no remaining mojibake pattern found in touched runtime/test files after this patch.
3. deferred note (approved): "existem muitos caracteres nao-ASCII legados em scripts/tests antigos (texto PT-BR), mas isso nao e necessariamente erro de codificacao; normalizei apenas erros reais neste slice para evitar mudanca transversal de alto risco."
4. where to clean in future controlled slice:
   - `scripts_manutencao/*.py`
   - `tests/teste_*.py`
   - legacy CLI/script text blocks under `interface/cli.py` and `interface/command_handlers.py`

Decision and scope:
1. this is a `STABILITY_PATCH` focused on user-visible filter button behavior and encoding fix in GUI tooltip.
2. no change in startup/import policy or out-of-scope modules.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-04 (global clear baseline consistency in filter buttons)

Session timestamp:
1. start: `2026-03-04 00:00:27 -0300`
2. end: `2026-03-04 00:07:25 -0300`

Delivered in this slice:
1. `gui/mixins/filter_gui_ssa_mixin.py`: `_clear_all_filters_global` now resets column filters using `_column_filter_default_columns()` instead of hardcoded subset.
2. `tests/test_gui_filter_logic.py`: added regression `test_clear_all_filters_global_restores_default_column_filter_keys`.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/mixins/filter_gui_ssa_mixin.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_all_filters_global_resets_full_filter_state_matrix or clear_all_filters_global_restores_default_column_filter_keys or clear_all_filters_global_resets_exclude_and_advanced_filters"`: `3 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a `STABILITY_PATCH` to remove inconsistent reset behavior between related clear actions.
2. runtime outside filter-clear path unchanged.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Evidence commit:
1. `98269107` (`STABILITY_PATCH`: global clear baseline consistency).

## Update 2026-03-03 (follow-up regression for header context-menu undo path)

Session timestamp:
1. start: `2026-03-03 23:55:05 -0300`
2. end: `2026-03-03 23:59:04 -0300`

Delivered in this slice:
1. added direct regression in `tests/test_gui_filter_logic.py` to validate header context-menu apply path stores undo snapshot end-to-end.

Validation:
1. `uv run --python 3.13 python -m py_compile tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "test_header_context_menu_apply_stores_undo_snapshot"`: `1 passed`
5. kluster auto review run in this slice: clean

Decision and scope:
1. this is a test-only `STABILITY_PATCH` follow-up to close previously deferred coverage gap.
2. runtime behavior unchanged in this slice.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Evidence commit:
1. `22bbd3dc` (`STABILITY_PATCH`: header context-menu undo regression test).

## Update 2026-03-03 (filter buttons stability hardening on feature branch)

Session timestamp:
1. start: `2026-03-03 23:46:42 -0300`
2. end: `2026-03-03 23:53:25 -0300`

Delivered in this slice:
1. fixed high-risk stale async state after `clear_filter` by resetting request-scoped search markers in `gui/mixins/filter_gui_ssa_mixin.py`.
2. raised effective general-search debounce floor to `1400 ms` in `gui/gui_ssa.py` to encourage explicit `Aplicar`.
3. completed undo snapshot coverage for column filter activation/deactivation and header context-menu apply path.
4. aligned help text to real column-filter controls (`Aplicar` + `Ocultar`) in `gui/widgets/filter_help_dialog.py`.
5. added focused regressions in `tests/test_gui_filter_logic.py` for stale state clear path, debounce floor, and undo snapshots in column filter entry points.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
2. `uv run --python 3.13 ruff check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
3. `uv run --python 3.13 ty check gui/gui_ssa.py gui/mixins/filter_gui_ssa_mixin.py gui/widgets/filter_help_dialog.py tests/test_gui_filter_logic.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_filter_logic.py -k "clear_filter or debounce or activate_column_filter_stores_undo_snapshot or deactivate_column_filter_stores_undo_snapshot"`: `15 passed, 1 skipped`
5. kluster auto review runs in this slice: clean -> clean -> clean -> clean

Decision and scope:
1. this is a `STABILITY_PATCH` focused on filter-state consistency and undo coverage with minimal behavioral changes.
2. branch used by explicit approval: `codex/fix-filter-buttons-state-sync`.
3. local residues kept out of scope: `config/gui_main_preferences.json` and `stash@{0}`.

Deferred non-blocking:
1. add a direct regression for the full Qt header context-menu interaction path that asserts undo snapshot behavior end-to-end (current coverage validates internal entry points and data path).

Evidence commit:
1. `2c7982b1` (`STABILITY_PATCH`: runtime + tests for filter-state hardening).

## Update 2026-03-03 (slice G targeted regression coverage for A/B/C)

Session timestamp:
1. start: `2026-03-03 22:20:26 -0300`
2. end: `2026-03-03 22:24:33 -0300`

Delivered in this slice:
1. `tests/test_app_logic_full_rescan_lock.py`: added regression to assert sidecar move (`-wal`/`-shm`) into full-rescan backup path.
2. `tests/test_import_deterministic_failure_cache.py`: added regression to assert `OPERATION_CANCELLED` does not mark deterministic failed file list.
3. `tests/test_cli_enhancement_manager_lock_usage.py`: added regression to assert lock file created by current process is removed when lock acquisition fails.

Validation:
1. `uv run --python 3.13 python -m py_compile tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
2. `uv run --python 3.13 ruff check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
3. `uv run --python 3.13 ty check tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_import_deterministic_failure_cache.py tests/test_cli_enhancement_manager_lock_usage.py`: `14 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. this is a test-only `STABILITY_PATCH` slice; runtime behavior unchanged.
2. local residues remain unchanged by policy: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-03 (slice F control-doc current-truth normalization)

Session timestamp:
1. start: `2026-03-03 22:16:00 -0300`
2. end: `2026-03-03 22:17:56 -0300`

Delivered in this slice:
1. `docs/NEXT_CHAT_MIGRATION.md`: normalized heading model to keep exactly one `CURRENT TRUTH` block at top and reclassified older `CURRENT TRUTH` sections as `HISTORICAL SNAPSHOT`.
2. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`: normalized heading model to keep exactly one `CURRENT TRUTH` block at top and reclassified older `CURRENT TRUTH` sections as `HISTORICAL SNAPSHOT`.
3. top blocks in migration/handoff now record this normalization as the active doc state.

Validation:
1. structural grep check: `NEXT_CHAT_MIGRATION.md` has `1` `CURRENT TRUTH` heading.
2. structural grep check: `AGENTS_HANDOFF_NEXT_CYCLE.md` has `1` `CURRENT TRUTH` heading.
3. runtime files unchanged in this slice.

Decision and scope:
1. this is a docs-only `DOC_SYNC` slice, no runtime/test/gui code edits.
2. local residues remain unchanged by policy: `config/gui_main_preferences.json` and `stash@{0}`.

## Update 2026-03-03 (sprint E controlled technical debt in gui table)

Delivered in this slice:
1. Removed dead helper `_calculate_max_chars_for_column` from `gui/ssa/gui_table.py`.
2. Removed dead facade pass-through `_calculate_max_chars_for_column` from `gui/gui_ssa.py`.
3. No visual/layout/position behavior changed.

Validation:
1. `uv run --python 3.13 python -m py_compile gui/ssa/gui_table.py gui/gui_ssa.py`: pass
2. `uv run --python 3.13 ruff check gui/ssa/gui_table.py gui/gui_ssa.py`: pass
3. `uv run --python 3.13 ty check gui/ssa/gui_table.py gui/gui_ssa.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_gui_table_render_resilience.py tests/test_gui_filter_logic.py -k "display_current_page or column_width"`: `5 passed, 109 deselected`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint E closed as low-risk debt cleanup with dead code removal only.
2. Runtime behavior outside removed dead symbols unchanged.

## Update 2026-03-03 (sprint D docs consistency and portability)

Delivered in this slice:
1. `docs/OHMYOPENCODE_MANUAL.md`: replaced local hardcoded path with `$HOME` for portability.
2. `docs/OPENCODE_CONFIG.md`: aligned Gemini model identifier in provider list to match table usage (`google/antigravity-gemini-3-pro`).
3. `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`: replaced fixed `--python 3.13` examples with `--python $PY_RUNTIME` and added explicit fallback chain (`3.13 -> 3.12 -> 3.11 -> 3.10`).

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py interface/cli_enhancement_manager.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py interface/cli_enhancement_manager.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py interface/cli_enhancement_manager.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_import_deterministic_failure_cache.py`: `11 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint D closed as docs-only (`DOC_SYNC`) with no runtime code edits.
2. GUI layout/position unchanged.

Deferred (next slices):
1. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint B structured extraction classification)

Delivered in this slice:
1. `ExtractionError` now supports structured `error_code` in both `core/app_logic.py` and `extracao/extractor.py`.
2. Import loop in `core/app_logic.py` now classifies extraction outcomes by `error_code` (no substring matching for deterministic failure detection).
3. Added focused tests in `tests/test_import_deterministic_failure_cache.py`:
   - preserve extractor `error_code` when normalized into core layer;
   - update deterministic-failure cache by `MISSING_REQUIRED_COLUMNS` code path.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py extracao/extractor.py tests/test_import_deterministic_failure_cache.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_deterministic_failure_cache.py tests/test_extracao.py tests/test_import_derivadas_trigger.py`: `24 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint B closed with minimal runtime change in extraction error contract and deterministic cache trigger.
2. No GUI layout or position change in this slice.

Deferred (next slices):
1. Sprint D: docs-only portability and consistency cleanup.
2. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint C lock-file TOCTOU hardening)

Delivered in this slice:
1. `interface/cli_enhancement_manager.py` lock-file creation now uses atomic open-first flow (`O_EXCL`) with explicit fallback when lock file already exists.
2. Removal of lock file on lock acquisition failure remains restricted to files created by the current process.
3. Added focused race regression in `tests/test_cli_enhancement_manager_lock_usage.py` to validate no removal of preexisting lock file during lock contention failure.

Validation:
1. `uv run --python 3.13 python -m py_compile interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
2. `uv run --python 3.13 ruff check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
3. `uv run --python 3.13 ty check interface/cli_enhancement_manager.py tests/test_cli_enhancement_manager_lock_usage.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`: `10 passed`
5. kluster auto review runs in this slice: clean -> clean

Decision and scope:
1. Sprint C closed as `BUG_REAL` with minimal patch in lock path and focused regression.
2. Runtime outside CLI settings lock path unchanged.

Deferred (next slices):
1. Sprint B: structured extraction error classification and deterministic-failure cache test coverage.
2. Sprint D: docs-only portability and consistency adjustments.
3. Sprint E: controlled technical debt cleanup in GUI table helper path.

## Update 2026-03-03 (sprint A lock checkpoint hotfix)

Delivered in this slice:
1. `core/app_logic.py` full-rescan DB preparation now runs `PRAGMA wal_checkpoint(TRUNCATE)` without explicit `BEGIN IMMEDIATE` in the same block, avoiding self-lock during checkpoint.
2. Added focused regression `tests/test_app_logic_full_rescan_lock.py` to validate WAL checkpoint + DB rotation path without external lock contention.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py tests/test_app_logic_full_rescan_lock.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_app_logic_full_rescan_lock.py`: `1 passed`
5. kluster auto review runs in this slice: clean -> clean (no issues, no agent_todo_list)

Decision and scope:
1. Sprint A is closed as `BUG_REAL` with minimal patch in runtime + focused test.
2. No GUI layout/position change in this slice.

Deferred (next slices):
1. Sprint C: review TOCTOU path in `interface/cli_enhancement_manager.py`.
2. Sprint B: migrate extraction deterministic-failure classification from message substring to structured signal.
3. Sprint D/E: docs portability consistency and controlled technical debt cleanup.

## Update 2026-03-03 (control files hard-sync for next chat)

Delivered in this slice:
1. all operational rules negotiated in chat were persisted into repository control docs (no longer chat-only).
2. `AGENTS.md` now includes explicit XP+SDLC flow, slice contract, scope protocol, change categories, PR comment policy, git stash policy, timestamp policy, and tooling policy.
3. kluster detailed mandatory block was restored in full after regression introduced by full-file overwrite.

Traceability:
1. initial consolidation commit: `e3c7cdcb`.
2. kluster block full restore commit: `ce0d3fc1`.
3. control-file sync commit: this slice (DOC_SYNC).

Operational rule reinforced:
1. conversation outputs must be mirrored into control files for continuity.
2. chat log is historical evidence, but repository control files are the authoritative migration source.

Deferred follow-up (non-blocking):
1. unify old duplicated `CURRENT TRUTH` blocks in migration docs into a single active block + historical snapshots only.

## Update 2026-03-03 (startup import policy + rescan modes)

Delivered in this slice:
1. startup import is disabled by default in `main.py`; app starts using current DB state.
2. full rescan now recreates DB from zero by rotating current `ssas.db` to timestamped backup and then reimporting all files.
3. derivadas auto-sync now runs only in full import flows (`force_import=True`) or manual GUI action (`Atualizar Derivadas`).
4. GUI `Reescanear` now offers explicit mode choice:
   - `Diff (hash)`: process only changed files.
   - `Full (zera e reprocessa)`: recreate DB and reimport all.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py main.py gui/ssa/gui_workers.py gui/workers/rescan_worker.py tests/test_import_derivadas_trigger.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_derivadas_trigger.py tests/test_derivadas_sync.py tests/test_gui_workers_rescan_data.py`: `35 passed`

Deferred long-term item (do not implement in this slice):
1. background import into a separate candidate DB file and user prompt to switch when ready:
   - run import without blocking normal usage;
   - on success, show prompt like `Novo banco pronto. Deseja usar agora?`;
   - keep current DB untouched until explicit user confirmation.

## Update 2026-03-02 (golden release 2 baseline)

Decision logged for this cycle:
1. mark current advanced-filter behavior as `golden release 2` official recovery baseline.
2. from this point, changes in advanced filters must be minimal and theme-consistent only.
3. no geometry expansion or broad layout refactor is allowed in this lane.
4. target for this slice:
   - consistent theme application across all advanced-filter controls;
   - centered `Cancelar` and `Fechar` footer actions in multiselect popup.

## Update 2026-03-01 (gui filters stability + importer noise control)

Delivered in this slice:
1. `core/app_logic.py`:
   - fixed indentation regression in derivadas error progress path.
   - added deterministic-failure cache mark for extraction errors with message:
     `missing required columns after normalization`.
   - kept dedicated derivadas phase trigger behavior compatible with existing tests.
2. `gui/ssa/gui_filters_advanced_ui.py`:
   - reduced effective width budget for `Aplicar` and `Limpar`.
   - removed visual separator between action buttons and kept compact spacing.
   - constrained multiselect popup width by trigger width + screen cap.
   - hardened parent traversal and checkbox mutual-exclusion callbacks against stale Qt objects.
3. `gui/gui_ssa.py`:
   - canonical column candidate source cleaned to avoid profile placeholder noise.
   - active column candidates now come from visible/default/current + rendered/filled filters.
4. `gui/ssa/gui_theme.py`:
   - advanced filter options refresh is triggered when theme changes on filters tab.
5. `scripts/env/direnv_common.sh`:
   - ensure `${VIRTUAL_ENV}/bin` is prepended to `PATH` when active.
   - refresh shell command cache after path exports.

Validation:
1. `uv run --python 3.13 python -m py_compile core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
2. `uv run --python 3.13 ruff check core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
3. `uv run --python 3.13 ty check core/app_logic.py gui/gui_ssa.py gui/ssa/gui_filters_advanced_ui.py gui/ssa/gui_theme.py`: pass
4. `uv run --python 3.13 pytest -q tests/test_import_derivadas_trigger.py tests/test_import_cancellation.py tests/test_gui_filters_advanced_logic.py`: `28 passed`

Deferred (non-blocking, structural):
1. further breakup of `_rebuild_multiselect_menu` (out of scope for minimal stability patch).
2. wider `SSAMainWindow` responsibility split (tracked as structural work, no refactor in this slice).

## Update 2026-03-01 (streamlit single-file policy note)

Decision logged for this cycle:
1. `dev_env/streamlit_app.py` remains intentionally centralized due explicit sidequest policy (single-file Streamlit scope).
2. deferred (non-blocking) technical debt:
   - extract CSS/theme helpers only when policy allows;
   - extract advanced-filter helper registry only when policy allows.
3. current priority remains functional stability and regression prevention in the existing single-file workflow.

## Update 2026-03-01 (v4.27 uv-first + matrix)

Delivered in this slice:
1. release bump:
   - `VERSION` -> `4.27`
   - `config/version.json` -> `v4.27`
2. runtime compatibility completed (previously inconclusive):
   - isolated uv environments validated in 3.10, 3.11, 3.12, 3.13
   - result: all pass for focused gates/tests
3. docs normalization:
   - uv-first command format standardized to `uv run --python 3.13 ...`
   - fallback policy explicitly documented (`3.12 -> 3.11 -> 3.10`)
   - `requirements*.txt` kept as compatibility path.
4. GUI continuity docs added:
   - `ANALISE_PROFUNDA_GUI.md`
   - `GUI_SSA_REFACTOR_NOTES.md`
5. local directories clarified for operations:
   - `.uv-matrix`: isolated uv virtualenvs used for multi-version validation.
   - `.alma-snapshots`: local snapshot/cache artifacts, not runtime source.
   - `launchers/*`: build/packaging scripts and platform configs.
   - `.venv`: default local development virtualenv.

## Update 2026-02-28 (release alignment v4.27)

Delivered in this pre-PR slice:
1. release metadata aligned to `v4.27`:
   - `VERSION`
   - `config/version.json`
2. release docs aligned to remove drift between `v4.24.1`, `v4.25.0`, and current baseline:
   - `README.md`
   - `docs/HISTORICO_RELEASES.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs_saida/CHANGELOG_IMPLEMENTACOES.md`
3. scope note:
   - no streamlit code/layout changes.
   - no hardening logic changes.

## Update 2026-02-28 (id 92 closed + situacao quick usability)

Delivered in this streamlit micro-slice:
1. Cache architecture item (`92`) closed:
   - shared internal helpers now centralize get/store behavior in `StreamlitFilterCache`.
   - duplicated logic removed with contract preserved.
2. Filters usability adjusted per feedback:
   - situacao no longer hidden; now always visible.
   - added quick mode selector (`Manual`, `Todas`, `Abertas`, `Executadas`, `Nenhuma`).
   - situacao entries now show count labels.
3. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `38 passed`

## Update 2026-02-28 (streamlit usability polish v2)

Delivered in this follow-up slice:
1. executor/emissor compacted to single-select controls with `(Todos)` option.
2. search row now includes explicit `Filtrar agora` submit button.
3. source path controls moved to collapsed advanced section in sidebar.
4. table render height now adapts to current page row count.
5. column picker now omits fully empty columns by default.
6. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability polish v3)

Delivered in this follow-up:
1. source controls removed from quick sidebar and moved to hidden advanced section in `Cache e API`.
2. situacao quick mode moved inline with core filters for denser layout.
3. additional chart context added in table view (`Top executor`, `Top emissor`).
4. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability polish v4)

Delivered in this pass:
1. improved compactness in key filter row and moved quick mode inline.
2. renamed presets/actions to business labels.
3. expanded table context metrics and adjusted dataframe surface styling.
4. validation:
   - `py_compile`, `ruff`, `ty`: pass
   - focused pytest (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `40 passed`

## Update 2026-02-28 (streamlit usability slice: layout + discoverability)

Delivered in this streamlit-focused slice:
1. Theme visibility:
   - theme selector moved to header (top-right), no longer hidden in ops tab.
2. Filters usability:
   - situacao moved to optional expander to avoid tall multi-line chips by default.
   - setor executor/emissor kept in main filter row.
   - limit rows moved to dedicated line.
3. Table discoverability:
   - quick shortcut for "colunas exibidas" added directly in table tab.
4. Sidebar utilization:
   - source snapshot and quick metrics added.
5. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `36 passed`

## Update 2026-02-28 (streamlit theme slice: colors + behavior)

Delivered in this focused streamlit slice:
1. Added visual theme system with explicit palettes and CSS variable mapping.
2. Added runtime theme selector in Streamlit ops tab.
3. Added persistence for selected theme in Streamlit UI state file.
4. Validation:
   - `py_compile`, `ruff`, `ty` on touched streamlit/tests: pass
   - focused `pytest` (`tests/test_streamlit_filter_cache.py` + `tests/test_filter_cache_locking.py`): `36 passed`
5. Scope:
   - no broad refactor and no PyQt GUI layout change.

## Update 2026-02-28 (sprint D optional P3 delivered + doc hygiene)

Delivered in this optional slice:
1. Matrix optional items delivered with minimal risk:
   - item `104` resolved: width profile persistence across sessions (`width_profile` + `width_profile_by_bucket`).
   - item `107` resolved: render telemetry persistence across sessions (`streamlit_render_stats`).
2. Validation evidence:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py tests/test_filter_cache_locking.py`: pass (`34 passed`)
3. Scope note:
   - no GUI layout/position change.
   - no broad refactor.
4. Doc hygiene note:
   - top blocks in matrix/backlog/handoff/migration are canonical.
   - older blocks remain as historical trace.

## Update 2026-02-28 (sprint D closeout: cache guard + optional scope map)

Delivered in this closeout slice:
1. Sprint D P1 fix marked done:
   - matrix item `9` is now `resolved` (was deferred in older snapshot).
   - cache size guard implemented in:
     - `gui/cache/filter_cache.py`
     - `dev_env/streamlit_app.py`
   - env gate: `SSA_CACHE_MAX_MB` (default unset keeps prior behavior).
   - cache stats now expose `skipped_large_entries` and `max_entry_mb`.
2. Focused validation evidence:
   - `uv run --python 3.13 python -m py_compile gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check gui/cache/filter_cache.py dev_env/streamlit_app.py tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_filter_cache_locking.py tests/test_streamlit_filter_cache.py`: pass (`32 passed`)
3. Optional product items in this block are now superseded by a later delivery update:
   - persistent user-resizable widths (item `104`) now resolved.
   - telemetry persistence across sessions (item `107`) now resolved.
4. Structural items kept deferred for dedicated sprint:
   - `SSAMainWindow` split and streamlit god-module split: P2, difficulty alta.

## Update 2026-02-28 (sprints A+B+C delivered with minimal risk)

Delivered in this cycle:
1. Sprint A:
   - divisao filtering capability hardened in advanced logic without layout change.
   - focused regression added in `tests/test_gui_filters_advanced_logic.py`.
2. Sprint B:
   - low-risk ruff cleanup scope validated green for selected scripts/launchers/tests.
3. Sprint C:
   - optional large-page guard for streamlit (`SSA_STREAMLIT_LARGE_PAGE_GUARD`) added.
   - focused regression added in `tests/test_streamlit_filter_cache.py`.
4. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `40 passed`.
5. Matrix result:
   - deferred queue reduced and structural-only deferred items preserved for dedicated sprints.

## Update 2026-02-28 (queue compression to <=20)

Delivered in this triage-only slice:
1. Removed duplicate legacy review-tracking block from this backlog file.
2. Kept `docs/PENDING_ACTION_MATRIX.md` as the canonical active status source.
3. Reclassified historical deferred duplicates that are already delivered in recent streamlit/typing/runtime slices.
4. Result in canonical matrix:
   - `pending`: 0
   - `deferred`: 16
   - open queue total: 16 (<=20 target reached)

## Update 2026-02-28 (sprint long-loop v2: runtime hardening micro-slices)

Delivered in this loop:
1. `interface/command_handlers.py`
   - save success/error feedback now references resolved settings path.
   - unexpected save exception now surfaces terminal feedback.
2. `armazenamento/database_optimized.py`
   - update branch with FK references now quotes/validates update columns before SQL generation.
3. `main.py`
   - optimized cleanup path now logs debug when disable hook import is unavailable.
4. Tests:
   - `tests/test_command_handlers_save_settings.py`
   - `tests/test_database_optimized_identifier_guards.py`
   - focused regression suites for command handlers, db optimized, and main import fallback.
5. Validation:
   - `py_compile`, `ruff`, `ty`: pass on touched scope.
   - focused pytest:
     - command handlers: `10 passed`
     - db optimized: `6 passed`
     - main fallback/skip: `3 passed`
6. Kluster:
   - all auto review runs in this loop: clean.

## Update 2026-02-28 (sprint long-loop: config/extractor grave queue verification)

Delivered in this verification slice:
1. Confirmed and locked severe-path behavior already implemented in runtime:
   - `core/config_manager.py`:
     - atomic write/copy cleanup logs failures explicitly.
     - mappings integrity restore keeps safe fallback to defaults in memory.
   - `extracao/extractor.py`:
     - extraction handle lifecycle is context-managed via `with pd.ExcelFile(...)`.
     - extraction return/raise contract aligned with current importer flow.
2. Validation:
   - `uv run pytest -q tests/test_config_manager_mappings_integrity.py tests/test_config_manager_atomic_save.py tests/test_extracao.py`: `18 passed`
   - `uv run --python 3.13 python -m py_compile core/config_manager.py extracao/extractor.py`: pass
   - `uv run ruff check ...`: pass
   - `uv run ty check core/config_manager.py extracao/extractor.py`: pass
3. Operational effect:
   - reduced active severe queue noise by separating already-covered items from unresolved runtime work.

## Update 2026-02-28 (sprint 25 graves v5: closure docs + release bump)

Delivered in this closure slice:
1. Continuity docs synchronized:
   - `docs/NEXT_CHAT_MIGRATION.md` received a new top `CURRENT TRUTH` block.
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` received a new top authoritative block.
2. Local release bumped by +0.1:
   - `VERSION` now `4.25.0`.
   - `config/version.json` updated to `version_short=4.25`.
   - `README.md` and `docs/HISTORICO_RELEASES.md` aligned to `v4.25.0`.
3. Scope guard:
   - no GUI layout/position change in this slice.
   - no broad refactor; docs and release metadata only.

## Update 2026-02-28 (sprint 25 graves v4: command handlers + importer + stream wrappers)

Delivered in this sprint extension:
1. `interface/command_handlers.py`
   - mapping path validation and centralized path resolution.
   - guarded fallback for `display_mappings` loading failures.
   - mapping cache clear after save and broader save fallback guard.
2. `core/app_logic.py`
   - early cancel check immediately after extraction.
   - explicit guard for unexpected `None` from extractor.
   - extractor error normalization with non-empty fallback message.
3. `scripts/pytest_stream_common.py`
   - configurable reader thread join timeout via env.
   - timeout/normal/exception paths now share the configured join timeout.
4. Tests:
   - `tests/test_command_handlers_load_mappings.py`
   - `tests/test_command_handlers_save_settings.py`
   - `tests/test_import_single_error_classification.py`
   - `tests/test_stream_log_wrapper_guards.py`
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest package: `30 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 20 graves v3: rescan + stream robustness)

Delivered in this sprint package:
1. `gui/widgets/rescan_progress_dialog.py`
   - finish path is now idempotent under duplicated signals.
   - dialog close remains blocked during running cancel phase.
2. `gui/ssa/gui_workers.py`
   - start path now prunes retired rescan workers before active checks.
   - stale active worker refs are cleared before spawning a new worker.
   - cancel status is deterministic even if worker already stopped.
   - post-dialog running path refreshes metadata timestamp and cap cleanup remains consistent.
   - post-dialog non-running path now re-prunes retired workers.
3. `scripts/pytest_stream_common.py`
   - queue poll timeout is now configurable via `PYTEST_STREAM_QUEUE_POLL_TIMEOUT_MS`.
   - loop exit conditions were tightened to avoid unnecessary waits after process completion.
   - sentinel path does not increase dropped-line counters.
4. Focused tests updated:
   - `tests/test_rescan_progress_dialog.py`
   - `tests/test_gui_workers_rescan_data.py`
   - `tests/test_stream_log_wrapper_guards.py`
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `15 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 10 graves v2: rescan dialog/worker + stream wrapper)

Delivered in this sprint package:
1. `gui/widgets/rescan_progress_dialog.py`
   - cancel now keeps dialog open until process completion; no premature close while running.
2. `gui/ssa/gui_workers.py`
   - active-worker gate now uses robust running helper and clears stale active ref before start.
   - global worker cap now drops matching metadata entries.
3. `scripts/pytest_stream_common.py`
   - added dropped-warning interval parser (`PYTEST_STREAM_DROPPED_WARN_EVERY`) with bounds.
   - warning cadence made deterministic (`1` then each configured interval).
   - sentinel path excluded from dropped-line accounting.
4. Tests:
   - updated/added focused coverage in `tests/test_rescan_progress_dialog.py`, `tests/test_gui_workers_rescan_data.py`, `tests/test_stream_log_wrapper_guards.py`.
5. Validation:
   - touched-scope `py_compile`, `ruff`, `ty`: pass.
   - focused pytest: `12 passed`.
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean.

## Update 2026-02-28 (sprint 10 graves: config/lifecycle/streamlit hardening)

Delivered in this sprint package:
1. `gui/gui_config.py`
   - runtime path resolver API added and loader now resolves GUI config path dynamically.
2. `tests/test_gui_main_configuration.py`
   - runtime env path reflection regression (`SSA_CONFIG_DIR`).
   - explicit `config_path` precedence regression over env.
3. `dev_env/streamlit_app.py`
   - width-profile memory now ignores unknown bucket keys.
   - non-positive viewport hints now fallback to profile baseline width.
   - API snapshot clear helper now has explicit idempotent guard.
4. `tests/test_streamlit_filter_cache.py`
   - regressions for invalid bucket filtering, non-positive viewport fallback, and idempotent API snapshot clear.
5. `gui/gui_ssa.py` + `tests/test_gui_filter_logic.py`
   - closeEvent rescan shutdown keeps defensive stop/quit path when worker is globally retained.
   - regression verifies running-helper path under unstable `isRunning` behavior.
6. Validation:
   - `py_compile`, `ruff`, `ty`: pass on touched scope.
   - focused `pytest`: `150 passed, 1 skipped`.
7. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (sprint 5 slices graves: lifecycle/config/canonical/api)

Delivered in this sprint package:
1. `gui/gui_ssa.py`
   - closeEvent rescan retention now enforces cap with metadata cleanup for dropped workers.
   - retain path now refreshes worker timestamp on each retain operation.
2. `tests/test_gui_filter_logic.py`
   - new coverage for rescan global cap/meta consistency.
   - new coverage for canonical available columns keeping active filter columns when outside non-null cache.
3. `tests/test_gui_main_configuration.py`
   - new fallback regression for missing `SSA_CONFIG_DIR`.
4. `dev_env/streamlit_app.py` + `tests/test_streamlit_filter_cache.py`
   - centralized API snapshot clear helper and focused regression.
5. Validation:
   - `py_compile`: pass
   - `ruff`: pass
   - `ty`: pass
   - focused `pytest`: `145 passed, 1 skipped`
6. Kluster:
   - all `kluster_code_review_auto` runs in this package: clean

## Update 2026-02-28 (streamlit width-profile memory + tabs/api smoke)

Delivered in this streamlit slice:
1. Item 2 delivered first:
   - added width-profile memory by width bucket in `dev_env/streamlit_app.py` (`width_profile_by_bucket`).
   - no GUI layout/position changes.
2. Item 1 delivered after item 2:
   - stabilized tab labels via `MAIN_TAB_LABELS`.
   - added `_api_snapshot_available(...)` helper and used it in API snapshot render gate.
3. Focused tests added in `tests/test_streamlit_filter_cache.py`:
   - width bucket thresholds
   - width-profile memory normalize/resolve/remember
   - stable tab labels
   - API snapshot permutations
4. Validation:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`21 passed`)
5. Kluster:
   - `kluster_code_review_auto` on touched files: clean

## Update 2026-02-28 (streamlit telemetry profile window cap)

Delivered in this streamlit slice:
1. Added bounded profile window for render telemetry stats in `dev_env/streamlit_app.py`.
2. Added focused regression in `tests/test_streamlit_filter_cache.py`.
3. Validation:
   - `uv run --python 3.13 python -m py_compile dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ruff check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run ty check dev_env/streamlit_app.py tests/test_streamlit_filter_cache.py`: pass
   - `uv run pytest -q tests/test_streamlit_filter_cache.py`: pass (`16 passed`)

## Update 2026-02-28 (kluster package closeout: config hierarchy + closeevent lifecycle)

Delivered in this package:
1. `gui/gui_config.py` now resolves GUI preferences path with `SSA_CONFIG_DIR` (safe fallback kept).
2. `gui/gui_ssa.py::closeEvent` now has defensive global-retention fallback for active rescan worker.
3. Focused regressions added:
   - `tests/test_gui_main_configuration.py::test_load_gui_main_preferences_honors_ssa_config_dir`
   - `tests/test_gui_filter_logic.py::test_close_event_retains_rescan_worker_when_isrunning_check_fails_mid_shutdown`
4. Focused validation:
   - `uv run --python 3.13 python -m py_compile` (touched files): pass
   - `uv run ruff check` (touched files): pass
   - `uv run ty check` (touched files): pass
   - focused `pytest`: pass

## Update 2026-02-27 (residual main-config-gui closeout)

Delivered in this doc slice:
1. Closed residual runtime group in control docs:
   - `39, 46, 49, 50, 70, 76` now marked `resolved` in `docs/PENDING_ACTION_MATRIX.md`.
2. Synced top authoritative blocks for continuation:
   - `docs/NEXT_CHAT_MIGRATION.md`
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
3. Kept scope strictly documentation-only (no runtime code edits).

Operational next step:
1. Continue with minimal slices from active residual queue:
   - none (matrix pending queue is now empty).
2. Keep streamlit stabilization as separate track.
3. Item `9` status in this historical block is superseded by Sprint D closeout (`resolved`).

## Update 2026-02-27 (id 27 testing closure)

Delivered in this minimal slice:
1. Closed matrix item `27` by reinforcing the cancellation progress contract test.
2. Test update:
   - `tests/test_import_cancellation.py` now asserts `finish_payload["errors"] == []`.
3. Validation:
   - `uv run --python 3.13 python -m py_compile tests/test_import_cancellation.py`: pass
   - `uv run ruff check tests/test_import_cancellation.py`: pass
   - `uv run ty check tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancellation.py`: pass
   - `uv run pytest -q tests/test_import_cancel_before_insert.py`: pass

## Update 2026-02-27 (ids 22-23 testing closure)

Delivered in this minimal slice:
1. Closed matrix items `22` and `23` in `tests/test_database_optimized_alias_views.py`.
2. Test update:
   - explicit `initialize_database(...)` success assertion in both tests.
   - explicit db-file cleanup in `finally` remains in place.
3. Validation:
   - `uv run --python 3.13 python -m py_compile tests/test_database_optimized_alias_views.py`: pass
   - `uv run ruff check tests/test_database_optimized_alias_views.py`: pass
   - `uv run ty check tests/test_database_optimized_alias_views.py`: pass
   - `uv run pytest -q tests/test_database_optimized_alias_views.py`: pass

## Update 2026-02-27 (id 21 testing closure)

Delivered in this minimal slice:
1. Closed matrix item `21` based on existing concurrent-write test coverage.
2. Evidence:
   - `tests/test_caching_atomic_save.py::test_save_cache_concurrent_writes_remain_valid_json`.
3. Validation:
   - `uv run pytest -q tests/test_caching_atomic_save.py`: pass

## Update 2026-02-27 (ids 24-25 testing closure)

Delivered in this minimal slice:
1. Closed matrix items `24` and `25` using existing hardened regression tests.
2. Evidence:
   - lock coverage: `tests/test_filter_cache_locking.py`
   - modal skip coverage: `tests/test_filter_error_skips_modal_in_pytest.py`
3. Validation:
   - `uv run pytest -q tests/test_filter_cache_locking.py`: pass
   - `uv run pytest -q tests/test_filter_error_skips_modal_in_pytest.py`: pass

## Update 2026-02-27 (id 9 deferred by decision)

Delivered in this doc slice:
1. Matrix item `9` moved from `pending` to `deferred`.
2. Rationale:
   - explicit user decision (Opcao A) to avoid runtime behavior change in current sprint.
3. Historical note:
   - status later superseded in 2026-02-28 Sprint D closeout (`resolved`).

## Update 2026-02-27 (continuity triage validation closeout)

Delivered in this doc-only slice:
1. Ran continuity triage for interrupted runtime patch scope.
2. Local validation rerun completed and green:
   - `uv run --python 3.13 python -m py_compile` (touched runtime files)
   - `uv run ruff check` (touched runtime files)
   - `uv run ty check` (touched runtime files)
   - `uv run pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
     - `121 passed, 1 skipped`
3. kluster auto rerun on touched runtime files returned clean (no issues).

Operational next step:
1. Continue with next minimal runtime slice only.
2. Keep same gate sequence after any new edit.

## Update 2026-02-27 (interrupted handoff sync for continuation)

Delivered in this doc-only slice:
1. Added top authoritative continuity blocks in:
   - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
   - `docs/NEXT_CHAT_MIGRATION.md`
2. Captured interrupted runtime patch evidence for active filter stability work:
   - `gui/ssa/gui_filters_advanced_ui.py`
   - `gui/mixins/filter_gui_ssa_mixin.py`
   - `gui/widgets/column_manager_dialog.py`
   - `gui/gui_ssa.py`
   - `gui/ssa/gui_workers.py`
3. Added explicit restart order for the next chat before any new slice.

Pending before closing runtime slice:
1. Run kluster auto on touched files and resolve findings with minimal patch.
2. Run local gates on touched scope:
   - `python -m py_compile`
   - `ruff check`
   - `ty check`
   - focused `pytest`
3. Update pending matrix status after verification outcome.

## Update 2026-02-26 (lower panel single height lock)

Delivered in this slice:
1. Implemented single synchronized height lock for all 3 lower panels:
   - details panel
   - advanced filters panel
   - column filters panel
2. Added centralized methods in main window:
   - `_compute_bottom_panel_target_height()`
   - `_queue_bottom_panel_height_sync()`
   - `_sync_bottom_panel_heights()`
3. Hooked sync in:
   - initial UI build (`singleShot`)
   - tab change
   - resize event
   - column-filter panel rebuild
4. Added regression lock test:
   - `tests/test_gui_filter_logic.py::test_bottom_panels_keep_single_synced_height_after_resize`

Validation:
1. `python -m py_compile` pass.
2. `ruff check` pass.
3. `ty check` pass.
4. focused pytest pass.
5. full `uv run pytest -q` pass (`582 passed, 6 skipped, 11 subtests passed`).
6. Code evidence:
   - `gui/gui_ssa.py`: centralized sync methods and resize/tab/init hooks.
   - `gui/mixins/tab_context_gui_ssa_mixin.py`: deferred queue sync on bind.
   - `gui/mixins/filter_gui_ssa_mixin.py`: sync call after column-filter panel rebuild.
   - `tests/test_gui_filter_logic.py`: equal-height regression test.

Notes:
1. This slice does not change horizontal distribution policy.
2. Remaining visual tuning is limited to future micro-adjustments if required by user screenshots.

## Update 2026-02-26 (md audit + ssa tab consistency)

Delivered in this slice:
1. General MD audit re-run:
   - active operational docs refreshed;
   - version-specific/historical docs preserved by design.
2. GUI status consistency in filter flows:
   - clear search and clear-all paths now use `Status: SSAs filtradas: N de M`.
3. Column-filter footer button styling consistency:
   - `Adicionar filtro de coluna` and `Limpar todos filtros de colunas` now share the same theme style.
4. Validation gate executed for touched scope:
   - `python -m py_compile` pass
   - `ruff check` pass
   - `ty check` pass
   - `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py tests/test_gui_main_configuration.py tests/test_display.py`
     => `117 passed, 1 skipped`.
5. Structural note from kluster kept deferred:
   - `FilterGUISSAMixin` monolith split remains out of scope for this stabilization slice and stays in dedicated refactor sprint queue.
6. Compatibility-null fields policy applied in GUI selectors:
   - hidden from add-column-filter and column manager offerings:
     `registros_espera`, `num_reprobaciones`, `situacao_espera`, `numero_desvios`,
     `ate`, `justificativa`, `parciais`, `situacao_da_parcial`.
   - kept in DB for compatibility only.
7. Long-term pending:
   - investigate ingestion/data lineage for compatibility-null fields to determine if they are expected-null
     or import defects before any schema cleanup decision.

## Update 2026-02-26 (md audit + gui table/status hardening)

Delivered in this slice:
1. Global MD audit executed with separation:
   - updated active docs;
   - preserved version-specific/historical docs for consultation.
2. GUI table rendering now normalizes multiline cell text to single line before paint, avoiding clipping in fixed row height.
3. Filter status now reports consistent counter format:
   - `Status: SSAs filtradas: N de M ...`
4. Added/updated focused tests in `tests/test_gui_filter_logic.py` for:
   - multiline text rendering without newline clipping;
   - filtered status counter consistency.

MD scope decision:
1. Maintained as historical by design:
   - release-specific notes (`docs/RELEASE_NOTES_*`, historical release files);
   - handoff archives with explicit top status pointers.
2. Updated as active:
   - `README.md`, `docs/HISTORICO_RELEASES.md`, `docs/FILTER_TAB_OPTIMIZATIONS.md`,
     `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`, `docs/NEXT_CHAT_MIGRATION.md`,
     `docs/PENDING_ACTION_MATRIX.md`, `docs/GUI_PYQT6_REGRAS_GERAIS.md`,
     `docs/QWEN_CODE_DELEGATION_CONFIG.md`.

Deferred (non-blocking, dedicated sprint only):
1. `gui/mixins/filter_gui_ssa_mixin.py` remains structurally large.
2. Scope split into managers/resolvers is intentionally deferred to dedicated refactor sprint to avoid transversal risk in this stabilization cycle.

## Update 2026-02-26 (column filter regression tests lock)

Delivered in this slice:
1. Added focused regression tests in `tests/test_gui_filter_logic.py`:
   - `test_add_column_menu_includes_full_candidates_and_excludes_legacy_aliases`
   - `test_clear_all_column_filters_restores_defaults_and_hidden_lines`
   - `test_default_column_filter_rows_show_apply_and_hide_buttons`
2. Locked previously uncovered behavior for:
   - full add-column candidate menu;
   - legacy ghost alias exclusion (`No SSA`, `Data Cadastro`);
   - clear-all restoring default visible rows with empty values;
   - hidden line reset on clear-all.

Validation:
1. `python -m py_compile tests/test_gui_filter_logic.py` pass.
2. `ruff check tests/test_gui_filter_logic.py` pass.
3. `ty check tests/test_gui_filter_logic.py` pass.
4. `.venv/bin/python -m pytest -q tests/test_gui_filter_logic.py` pass (`97 passed, 1 skipped`).
5. Related suites:
   - `.venv/bin/python -m pytest -q tests/test_gui_main_configuration.py` pass.
   - `.venv/bin/python -m pytest -q tests/test_display.py tests/test_streamlit_filter_cache.py` pass.

## Update 2026-02-26 (GUI column filter alias hardening)

Delivered in this slice:
1. Removed legacy invalid alias keys from GUI main preferences:
   - dropped `Numero da SSA`/`No SSA` legacy key path.
   - dropped `Data Cadastro` legacy key path.
2. Hardened GUI preferences merge to ignore only known legacy invalid keys, without blocking custom valid keys.
3. Hardened add-column-filter menu to avoid showing legacy ghost aliases while preserving valid internal `numero_ssa`.
4. Kept DB schema unchanged; verified `ssa_table`/`ssas` contain `numero_ssa` and do not contain `No SSA`.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched Python files.
2. focused pytest:
   - `tests/test_gui_filter_logic.py -k "clear_all_column_filters or column_filter or add_column_filter"` => pass
   - `tests/test_gui_config.py` => pass
3. kluster auto: clean after final patch set.

Non-blocking deferred item:
1. `config/gui_poc_preferences.json` still contains legacy non-internal display-mapping keys (`Numero da SSA`, `Semana de Cadastro`, `Data Cadastro`, `Descricao Execucao`).
2. This file is not part of the active main GUI runtime path; schedule cleanup in dedicated low-risk config slice to keep parity.

## Update 2026-02-26 (sprints A B C delivered on codex/dev-filtros-stability)

- Sprint A delivered (extractor contract hardening):
  - ids closed: `6, 7, 33, 34, 35, 58`
  - evidence: focused extractor contract tests added and passing.
- Sprint B delivered (rescan worker/dialog hardening):
  - ids closed: `11, 12, 28, 29, 38, 79`
  - id `71` moved to `stale-doc` by expected behavior with explicit tests.
- Sprint C delivered (cli enhancement lock/write consistency):
  - ids closed: `13, 26, 30, 31, 41, 80`
  - evidence: lockfile-based serialization, bounded nonblocking retries, and atomic write path validated in focused tests.

Current next queue (post A/B/C):
1. Main/config/gui residual pending group: closed (`39, 46, 49, 50, 70, 76` resolved; `42` resolved; `43/44` stale-doc).
2. Active residual queue now: `9, 21, 22, 23, 24, 25, 27`.
3. Streamlit stabilization queue (separate track, approved by user).

## Update 2026-02-26 (deep analysis snapshot: kluster + lint/type gate)

Validation snapshot (no runtime code changes in this slice):
1. `py_compile`: pass.
2. `ruff check .`: pass.
3. `ty check .`: pass.
4. `flake8`:
   - full repo run produced heavy noise from `.venv` and generated trees;
   - targeted run confirms large style baseline debt (mainly `E501` and spacing).
5. `mypy`:
   - baseline type debt remains (missing stubs and typed-union issues on GUI/data modules).
6. `pylama`:
   - failed in current environment due missing `pkg_resources` (no dependency change applied by request).

Kluster manual review snapshot (chat `8fyr5a0z7ot`):
1. `scripts/run_pytest_stream_and_log.py`: P3 perf, P4 semantic/quality/perf, and P4 security path handling.
2. `scripts/run_pytest_stream_and_log_v2.py`: P3 security path handling plus P4 semantic/quality/perf.
3. `main.py`: P4 semantic/quality/perf (god function and logging overhead observations).
4. `core/config_manager.py`: P4 semantic/quality suggestions.
5. `gui/gui_ssa.py`: P3 quality (god class) plus P4 semantic/perf observations.

Pending horizon after deep analysis:
1. Curto prazo (bloqueante/alto risco, patch minimo):
   - add path traversal guard for `--log` in `scripts/run_pytest_stream_and_log.py` and `_v2.py`;
   - adjust flush policy in stream scripts to reduce I/O overhead without changing timeout/cancel semantics.
2. Medio prazo (alto impacto, media complexidade):
   - close remaining Batch 09/10 behavior points with focused tests (queue-full, warning dedupe, sentinel delivery).
   - harden `main.py` semantics only in minimal slices (no broad refactor).
3. Longo prazo (sprint exclusivo):
   - `SSAMainWindow` structural decomposition.
   - broad mypy/flake8 baseline cleanup across GUI and data layers.

Next execution steps (recommended order):
1. Stream scripts security/perf mini-slice (2 files + focused tests).
2. Stream scripts residual behavior lock (Batch 09/10 completion).
3. Main flow resilience slice (Batch 11).
4. Keep structural refactors in dedicated sprint only.

## Update 2026-02-26 (stream scripts security/perf mini-slice delivered)

Files changed:
1. `scripts/pytest_stream_common.py` (new shared runtime helper).
2. `scripts/run_pytest_stream_and_log.py` (now consumes shared runner).
3. `scripts/run_pytest_stream_and_log_v2.py` (now consumes shared runner).
4. `tests/test_stream_log_wrapper_guards.py` (new focused guards).

Delivered in this slice:
1. `--log` path guard hardened with shared validation and explicit deny outside `local_ai_private`.
2. flush policy changed to batched strategy (`PYTEST_STREAM_FLUSH_EVERY`, bounded) to avoid flush-per-line overhead.
3. stream runtime duplication reduced by centralizing queue/timeout/process-tree handling into shared helper.
4. sentinel handling changed to non-blocking best-effort path; main loop now closes by process state + reader_done signal.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `pytest -q tests/test_stream_log_wrapper_guards.py` green (`4 passed`).
3. kluster residual after fixes:
   - `scripts/pytest_stream_common.py::run_streaming_pytest` flagged as structural complexity (`god function`).
   - decision: defer to dedicated refactor sprint (non-blocking for current security/perf patch).

## Update 2026-02-26 (batch11 main resilience delivered)

Files changed:
1. `main.py`
2. `tests/test_main_import_fallback.py`

Delivered:
1. optimized import failure now has explicit context logging and deterministic fail-fast by default.
2. no automatic legacy retry is attempted, including `--force-rescan`, avoiding duplicated heavy reprocess.
3. `--version` path simplified (no broad `except`).
4. log-level invalid message normalized to ASCII.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `pytest -q tests/test_main_import_fallback.py tests/test_main_skip_import.py` green (`3 passed`).
3. kluster auto for `main.py` + focused test returned clean.

## Update 2026-02-26 (config mappings restore fallback lock)

Files changed:
1. `tests/test_config_manager_mappings_integrity.py`

Delivered:
1. added regression lock for `load_display_mappings_integrity` when restore write fails.
2. added regression lock for `load_column_mappings_integrity` when restore write fails.
3. both paths are asserted to return in-memory defaults without crash.

Validation:
1. `py_compile`, `ruff`, `ty` green for touched files.
2. `uv run pytest -q tests/test_config_manager_mappings_integrity.py` green (`4 passed`).
3. kluster auto clean.

## Update 2026-02-25 (approved execution marker: filtros avancados ui stabilization)

Status:
1. user approved execution plan before code edits.
2. next implementation will run in 4 slices with minimal scope drift and focused validation.

Approved scope for next slice:
1. prevent advanced filters panel from stealing table reading area.
2. replace fixed breakpoint layout policy (wide/mid/narrow) with continuous responsive distribution.
3. restore reprogramacoes behavior in initial refresh and apply flow.
4. more aggressive control redesign in advanced filters panel:
   - ste control migration from checkbox to toggle-style button.
   - stronger cleanup of button width policy to remove fragile fixed-width behavior.

## Current sprint status snapshot (PR 31)

- Operational:
  - `gh pr checks 31` voltou a responder.
  - estado atual:
    - `code/snyk (mauriciomenon)` falha por limite de plano (`Code test limit reached`).
    - `security/snyk (mauriciomenon)` falha por limite de plano (`You have used your limit of private tests`).
    - demais checks principais em `pass` (DeepScan, DeepSource, submit-pypi, GitGuardian, Socket, cubic).
- Delivered hardening slices (low risk, no GUI layout change):
  - `utils/caching.py`: removed silent suppress in temp cleanup, added explicit warnings.
  - `armazenamento/database.py`: removed silent suppress in config listing fallback, added explicit warning.
  - `interface/table_printer.py`: removed silent suppress in label normalization fallback, added explicit debug log.
  - `shared/numero_ssa.py`: replaced silent year-parse suppress with explicit `try/except ValueError`.
- Remaining sprint recommendation (kept as pending by decision):
  - E delivered: removed pytest ignores from `pyproject.toml` and converted legacy script-like files into deterministic tests.
  - Ty warning cleanup (non-blocking): remove legacy unused `type: ignore` comments in `armazenamento/database.py` in a dedicated low-risk slice, after PR #31 stabilization.

- Quality hardening adopted for advanced-filters facade:
  - Fixed runtime contract break where `gui/gui_ssa.py` expected symbol `_has_active_advanced_filters` from aggregated module.
  - Added guarded fallback path in facade and regression tests for primary/fallback/no-handler flows.
  - Added direct logic coverage for:
    - `solicitante` include/exclude compatibility (`solicitante` and legacy `responsavel_solicitante`);
    - `num_reprogramacoes` activation detection in `_has_active_advanced_filters`;
    - week-range filter path with explicit nonlocal mask update.
    - priority key/column mapping (`prioridade_*_values` and dataset `grau_prioridade_*`).
  - Added static key coverage test to prevent UI-key drift against logic/active detector.
  - New dedicated docs for this flow:
    - `docs/QA_FACADE_FILTERS.md`
    - `docs/NEXT_CHAT_MIGRATION.md`

- External IA intake workflow (active):
  - Accept report only with `arquivo:linha` evidence.
  - Re-validate every finding locally with `rg -n` and `nl -ba`.
  - Patch in atomic slices only.
  - Keep non-blocking findings in this backlog.

## External IA intake snapshot (2026-02-17)

- Revalidated findings with local evidence:
  - `RPT-P1-02` confirmed: `_has_active_advanced_filters` missing in aggregated exports.
  - `RPT-P1-01` confirmed: `responsavel_emissor` key exists in UI/logic but column is missing in `config/schema.sql`.
  - `RPT-P2-06` confirmed: coverage test was one-way and also had invalid regex under Python 3.13.
- Action now completed:
  - Re-exported `_has_active_advanced_filters` in `gui/ssa/gui_filters_advanced.py`.
  - Fixed regex and added reverse key-coverage guard in `tests/test_gui_filters_advanced_logic.py`.
- Decision applied:
  - `RPT-P1-01` resolved with path B:
    - removed/disabled `responsavel_emissor` advanced-filter flow from UI/logic detector.
    - kept backward-safe UI context attrs only to avoid tab binding regressions.
- Deferred to backlog (non-blocking in current slice):
  - `RPT-P2-03` dead branch `data_execucao` in year execucao filter.
  - `RPT-P2-04` `semana_*_exclude` hardcoded false in UI.
  - `RPT-P2-05` add dedicated migration tests for legacy `ano_*` keys.
  - `RPT-P3-07` evaluate cache key extension to include advanced filters context.
  - `RPT-P3-08` nomenclature normalization for priority keys/columns.

## Rescan evidence snapshot (2026-02-17)

- Input from latest modular rescan:
  - total files: 75
  - processed successfully: 64
  - errors: 11
- All 11 errors are from `SSAs Derivadas e Relacionadas_*.xlsx` with:
  - `Missing required columns after normalization: ['data_cadastro', 'descricao_ssa']`
- New action item (high priority):
  - keep main importer strict required columns for regular SSA sheets.
  - done: automatic derivadas sync trigger now consumes `SSAs Derivadas e Relacionadas_*.xlsx` through `armazenamento/derivadas_sync.py` (sheet source), not through main SSA extractor gate.
  - done: trigger runs after import loop; special files are skipped from main extractor and handled by derivadas sync.
  - current behavior: when multiple special sheets are present, importer picks the latest file by mtime for sync and marks all special files in cache on successful sync.

## P0 blockers

- Clear legacy `CHANGES_REQUESTED` state from old bot reviews on PR #25.
- Define repo policy for external check waivers when provider plan limits are hit.

## P1 hardening targets

- SSAMainWindow God Class (gui/gui_ssa.py ~6k lines):
  - Split UI layout, filtering/controller logic, and theming into separate modules.
  - Plan refactor in a dedicated sprint; avoid cross-cutting changes in this PR.
  - Define seams for unit tests before extraction to reduce regression risk.
- Derivadas c2 follow-up (db and related tools only):
  - Keep derivadas sync/maintenance decoupled from import flow; trigger via `scripts/derivadas_cli.py` or scheduler only.
  - Add controlled runbook for `scripts/derivadas_cli.py sync --full-rebuild` with rollback notes.
  - Validate external sheet column aliases (`parent_ssa`, `child_ssa`, `relation_label`) against real files.
  - Add focused regression test for mixed-source conflict reporting (db vs sheet) with stable fixtures.
  - Add migration smoke check for legacy `ssa_derivada_matrix` variants before enabling auto-sync broadly.
- Extract shared process termination helper for:
  - `scripts/run_pytest_stream_and_log.py`
  - `scripts/run_pytest_stream_and_log_v2.py`
  - `scripts/run_pytest_with_timeout.py`
  - `scripts/run_pytest_with_timeout_v2.py`
- Reduce broad `except Exception` in pytest wrapper scripts where specific exceptions are known.
- Start timeout clock at process start (`Popen`) for wrapper consistency.
- Improve fallback hash in `gui/workers/filter_worker.py` to include columns in fallback path.
- Revisit `concat + drop_duplicates` in `gui/workers/filter_worker.py` for large DataFrame performance.
- Standardize log levels and use `logger.exception` where traceback is required in `gui/gui_ssa.py`.
- Plan transversal `except ... pass` cleanup in GUI code, no layout changes.
- Add stronger user-facing diagnostics for config fallback cases in `gui/gui_config.py`.
- Validate worker retention strategy in long runs and add simple retention telemetry.
- Refactor `gui/ssa/gui_theme.py` (apply_theme muito grande) em sprint dedicado, sem mudar layout.
- Revisar cleanup/retention em `gui/ssa/gui_workers.py` (fluxo complexo) em sprint dedicado.
- Tratar diagnosticos estruturais de `ty` em `gui/gui_ssa.py` (stubs/headless e unions PyQt), com estrategia de tipagem dedicada e sem mexer em layout.

## P2 cleanup and consistency

- Align dependency declarations between `pyproject.toml` and `requirements*.txt`.
- Revisit `requires-python >=3.13` and confirm minimum supported version.
- Remove redundant imports and unused logger references in import verification scripts.
- Normalize success/failure contract in `tests/run_import_detailed.py`.
- Improve `.gitignore` pattern tests in `tests/test_release_artifact_guard.py`.
- Add integration tests for stream wrapper edge cases:
  - full queue,
  - closed pipe while reader is active,
  - forced timeout with kill escalation.
- Mark performance-sensitive tests explicitly to reduce CI flakiness.
- Revisit smoke GUI fixture isolation to prevent accidental real `load_data` execution.
- Define bot review cadence to reduce duplicate noise in large PRs.
- Reassess active review apps and disable redundant ones.
- Add merge checklist in PR template:
  - known risks,
  - accepted waivers,
  - mandatory follow-up links.
- Rever `pyproject.toml` addopts com ignores de testes e considerar remocao para ampliar cobertura (sugestao para relatorio final do sprint atual).
- Ajustar seletor "Configurar colunas visiveis" para sempre exibir nomes amigaveis (display names) em vez de nomes internos de coluna quando disponiveis.
- Centralizar persistencia de largura de coluna em fluxo unico (manager/config), evitando logica espalhada entre cache local de GUI e manipuladores de tabela.

## Execution model

- Use atomic commits per topic.
- Keep rollback easy by changing one concern at a time.
- Prefer low-risk defensive changes first, then structural cleanup.

## Review tracking (source PR 31)

This legacy section was replaced by the canonical active queue in docs/PENDING_ACTION_MATRIX.md.
Historical review-thread entries were removed here to avoid duplicate pending counts.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.
- Pendencia nao bloqueante: extrair a funcao `_rebuild_multiselect_menu` em blocos menores (layout/estilo/eventos) sem alterar comportamento visual.

## Atualizacao 2026-03-03 (pre-entrega PR, pendencias nao bloqueantes)
- Revisar parametrizacao de `docs_dir/data_dir/db_name/table_name` em `gui/workers/rescan_worker.py` para reduzir hardcode e facilitar teste.
- Revisar classificacao de falhas deterministicas em `core/app_logic.py` para migrar de substring de mensagem para codigo/sinal explicito.
- Padronizar instalacao de dependencias de desenvolvimento (`dependency-groups` vs `optional-dependencies`) e documentar comando oficial de `uv`.
- Nota de politica vigente: sync automatico de derivadas permanece restrito a rescan full/forcado e acao manual dedicada.
- Corrigir botao/fluxo de limpeza da pesquisa geral: apos `Enter` em pesquisa geral, o termo anterior nao esta sendo limpo de forma consistente.

## Atualizacao 2026-03-03 (pos-merge PR42 no branch dev - triagem de reviews)
- Contexto:
  - PR #42 foi aceito e mergeado em `dev`.
  - Esta secao registra triagem tecnica dos comentarios Copilot/Cubic pos-merge.

- Confirmado como bug real (prioridade alta para proximo ciclo):
  - `core/app_logic.py`:
    - `BEGIN IMMEDIATE` seguido de `PRAGMA wal_checkpoint(TRUNCATE)` no mesmo bloco pode falhar por lock no checkpoint.
    - Acao: separar checkpoint da transacao explicita e validar com teste focado de lock.

- Confirmado como decisao intencional (nao corrigir agora):
  - `core/app_logic.py`:
    - `auto_derivadas_sync_enabled = bool(force_import)` e gate de sync pos-import.
    - Politica atual mantida: sync automatico de derivadas somente em full rescan/forcado ou acao manual (`Atualizar Derivadas`).
    - Acao opcional futura: adicionar log explicito quando houver planilha de derivadas em import incremental e sync for pulado por politica.

- Pendencias nao bloqueantes (deferidas):
  - `core/app_logic.py`: substituir classificacao por substring de erro por codigo/sinal estruturado em `ExtractionError`.
  - `armazenamento/database_upsert_logic.py` vs `armazenamento/database_optimized.py`: centralizar normalizacao/validacao canonica de SSA para evitar drift.
  - `core/app_logic.py`: adicionar teste unitario cobrindo cache de falha deterministica e skip em execucao seguinte sem mudanca de hash/mtime.
  - `AGENTS.md`: trocar caminho absoluto do backlog por caminho relativo de repo.
  - `docs/OHMYOPENCODE_MANUAL.md`: trocar `/Users/menon/...` por `$HOME/...` para portabilidade.
  - `docs/OPENCODE_CONFIG.md`: alinhar nome de modelo Gemini entre secoes para evitar identificador inconsistente.
  - `docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`: documentar fallback runtime sem hardcode fixo em `--python 3.13`.
  - `interface/cli_enhancement_manager.py`: revisar TOCTOU em lock-file (`exists` + `open` nao atomico).
  - `docs/ARQUITETURA_IMPORTACAO.md`: remover recomendacao incorreta de `pd.read_excel(..., chunksize=...)`.
  - `gui/ssa/gui_table.py`: avaliar remocao de helper morto (`_calculate_max_chars_for_column`) ou reuso explicito.

## Atualizacao 2026-03-05 (slice import schema drift nan columns)
- Decisao aprovada:
  - aplicar patch minimo no fluxo de sync de colunas dinamicas para impedir drift de schema.
  - sem alterar conceito de importacao, sem mudanca de GUI/layout.
- Alteracoes aplicadas:
  - `armazenamento/database_upsert_logic.py`
    - descarte explicito de headers placeholder (`nan`, vazio, `unnamed:*`).
    - sanitizacao deterministica com reuso de nome canonico existente.
    - whitelist reaplicada no estado final antes do `ALTER TABLE`.
    - ordem de processamento de colunas dinamicas tornou-se deterministica.
  - `tests/test_db_reset_and_upsert.py`
    - novo teste para garantir que reimport nao cria `nome_paciente_1`.
    - novo teste para garantir descarte de `nan/nan_1/nan_2`.
    - novo teste para garantir whitelist apos sanitizacao dinamica.
- Evidencia tecnica:
  - `uv run --python 3.13 python -m py_compile ...` -> pass
  - `uv run --python 3.13 ruff check ...` -> pass
  - `uv run --python 3.13 ty check ...` -> pass
  - `timeout 420s uv run --python 3.13 pytest -q ...` -> `39 passed`
  - reproducao manual local confirmou:
    - `has_nome_paciente_1=False`
    - `nan_like_cols=[]`
- Nao bloqueante deferido:
  - `opencode run` indisponivel por billing no ambiente atual.
  - `snyk test --all-projects` sem resultado util por timeout nesta rodada.
