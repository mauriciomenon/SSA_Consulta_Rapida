# Build Tooling Lessons Learned (PyInstaller/Nuitka/PyOxidizer)

## CURRENT TRUTH 2026-05-04 01h14

- Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`, bloco `CURRENT TRUTH`.
- PR #58 e PR #59: merged; usar base minima `4705c2e5722c4f3a5266ac02a5d15a1928d5a223`, ou sucessor sincronizado em `main`/`dev`.
- Este documento registra aprendizados; nao deve duplicar a matriz completa de release.

## HISTORICAL SNAPSHOT (4.37 local / v4.36 published)

- Sync: `2026-03-27 04:10 -0300`
- Objetivo: registrar erros reais, causa-raiz, fix aplicado e comandos de validacao.
- Escopo: Windows 11 + Debian 13 via WSL, com build via `uv`.
- Regra atual: copia de DB/Excel locais para build agora e opt-in no script; usar `--with-local-data` no script quando o operador realmente quiser empacotar dados locais. O script repassa `--allow-local-data` apenas para `copy_data_to_builds.py`.
- Relatorio operacional consolidado:
  - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
- Runbook operacional:
  - `docs/BUILD_3X3_RUNBOOK.md`

## Licao 1 - PyInstaller DLL load failure no Windows (`python313.dll`)

- Sintoma:
  - `Failed to load Python DLL ... python313.dll`
  - `LoadLibrary: Acesso invalido ao local de memoria`
- Causa-raiz:
  - build com `strip` em Windows pode corromper/invalidar runtime para alguns hosts.
- Fix:
  - desativar `strip` em `launchers/platforms/windows_amd64/build_config.json`.
- Validacao:
  - `dev_env/build/build_pyinstaller.bat --silent`
  - executar CLI/GUI de `builds/pyinstaller/windows_amd64` sem erro de DLL.
- Regra reutilizavel:
  - em Windows, evitar `strip` por padrao em bundles com Python embutido.

## Licao 2 - Rescan GUI com erro `main.py nao encontrado`

- Sintoma:
  - GUI mostra: `Arquivo main.py nao encontrado em ...AppData...`
- Causa-raiz:
  - codigo antigo exigia `main.py` no runtime user dir.
  - fluxo atual de rescan e modular (`run_importer_logic`) e nao depende de subprocess.
- Fix:
  - remover bloqueio por existencia de `main.py` em `gui/ssa/gui_workers.py`.
  - manter apenas warning em log e seguir com worker modular.
- Validacao:
  - abrir GUI empacotada, acionar reescaneamento, confirmar que nao bloqueia por `main.py`.
- Regra reutilizavel:
  - se worker for modular, nao validar arquivo de entrypoint como hard dependency.

## Licao 3 - PyOxidizer sem imports do projeto (`No module named core`)

- Sintoma:
  - app sobe em modo limitado com falhas de import (`core`, `interface`, `utils`).
- Causa-raiz:
  - pacote final sem codigo do projeto em runtime.
- Fix:
  - incluir `main.py` e pacotes do projeto no `make_install()` de `pyoxidizer.bzl`.
- Validacao:
  - `dev_env/build/build_pyoxidizer.bat --silent`
  - `dev_env/build/build_pyoxidizer_debian.sh --silent`
  - smoke dos binarios gerados.
- Regra reutilizavel:
  - sempre listar explicitamente pacotes internos no install manifest do PyOxidizer.

## Licao 4 - PyOxidizer com erro de runtime nativo (`numpy/pandas`)

- Sintoma:
  - `numpy ... do not try to import from source directory`
  - `pandas has no attribute DataFrame`
  - erro de DLL nativa ausente em extensoes C.
- Causa-raiz:
  - pastas `.libs` (ex.: `numpy.libs`) nao estavam no bundle final.
- Fix:
  - script dedicado `scripts/sync_pyoxidizer_runtime_libs.py`.
  - chamado automatico nos builds PyOxidizer Windows e Debian.
- Validacao:
  - rodar binario PyOxidizer e confirmar carga de pandas/numpy sem fallback limitado.
- Regra reutilizavel:
  - para wheel com extensao nativa, sincronizar tambem diretorios `.libs`.

## Licao 5 - PyOxidizer sensivel ao CWD

- Sintoma:
  - executavel tenta abrir `main.py` no diretorio atual (`CWD`) e falha.
- Causa-raiz:
  - config de interpretador sem `module_search_paths` robusto para runtime.
- Fix:
  - usar `run_module = "main"` e definir `module_search_paths` com `$ORIGIN`.
- Validacao:
  - rodar executavel a partir de `C:\Windows\Temp` e `/tmp`.
- Regra reutilizavel:
  - nunca depender do `CWD`; sempre usar paths relativos ao executavel.

## Licao 6 - Duplicacao de titulo no Windows/Debian

- Sintoma:
  - titulo visual duplicado (nome sem versao + titulo com versao).
- Causa-raiz:
  - `ApplicationDisplayName` + `WindowTitle` em ambientes sem menu bar global.
- Fix:
  - manter `setApplicationName/DisplayName` apenas no macOS.
  - manter titulo da janela com versao em todos os SOs.
- Validacao:
  - abrir GUI no Windows e Debian e confirmar titulo unico.
- Regra reutilizavel:
  - usar nome global da app apenas em plataformas que exibem app menu separado.

## Licao 7 - Build sujo e reproducibilidade

- Problema:
  - artefato antigo em uso bloqueia limpeza/copia e gera resultado inconsistente.
- Fix:
  - limpeza defensiva no inicio de build.
  - novo script de limpeza dedicado `scripts/cleanup_build_artifacts.py`.
  - prompt ao final dos scripts de build (modo nao silencioso).
- Validacao:
  - build seguido de cleanup opcional sem apagar artefato final por engano.
- Regra reutilizavel:
  - separar claramente:
    - temporario: `build/*`, `launchers/platforms/*/temp/*`
    - final: `builds/*`, `launchers/dist/*`, `dist_packages/*`

## Licao 8 - Diagnostico insuficiente em build silencioso (Nuitka Debian)

- Sintoma:
  - build longo em `--silent` sem contexto claro de onde falhou.
- Causa-raiz:
  - script sem marcador de etapa e sem dump de log no erro.
- Fix:
  - `dev_env/build/build_nuitka_debian.sh` agora usa:
    - `LAST_STEP` por etapa (`nuitka_gui`, `nuitka_cli`, `copy_data_to_builds`)
    - `trap on_error ERR` com tail do log no modo silencioso
    - compilacao CLI sem plugin `pyqt6` para reduzir custo desnecessario.
- Regra reutilizavel:
  - em build silencioso de longa duracao, sempre emitir etapa de falha + tail de log.

## Checklist Reutilizavel (qualquer projeto)

1. Fixar runtime e ferramentas via `uv`.
2. Separar dados persistentes de artefato empacotado.
3. Garantir path runtime independente de CWD.
4. Incluir deps nativas (`.libs`) no bundle.
5. Executar smoke em path fora do repo.
6. Registrar licoes + comandos de reproducao em doc versionado.

## Runtime folders visiveis apos empacotamento

- Pastas mandatarias no runtime user dir:
  - `config/`
  - `data/`
  - `docs_entrada/`
  - `docs_saida/`
- Pasta adicional existente:
  - `exportacao/` (saida de export CSV/XLSX gerada pela app)
- Regra:
  - nao esconder essas pastas em runtime.
  - seed inicial nao deve sobrescrever customizacao local do usuario.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
