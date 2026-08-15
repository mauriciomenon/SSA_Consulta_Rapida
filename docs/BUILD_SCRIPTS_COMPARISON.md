# Comparacao: build_simple.py vs build_multiplatform.py

Este documento sumariza as diferencas principais entre os scripts de build existentes em `launchers/` e explica para que cada um foi projetado, com foco especial em builds Windows.

## Nota de versao

Exemplos de nomes de artefato com versao fixa neste documento sao historicos.
No baseline ativo, considerar sempre a versao corrente definida em `VERSION`.

Arquivos comparados:
- `launchers/build_simple.py`
- `launchers/build_multiplatform.py`

## Resumo rapido
- `build_simple.py`: script leve e rapido para gerar um executavel de desenvolvimento (usa `dist_simple`, limpa automaticamente). Ideal para developers que querem validar um exe localmente em poucos segundos.
- `build_multiplatform.py`: sistema completo e robusto para builds reproduziveis em multiplas plataformas (Windows, macOS, Debian). Gerencia virtualenvs por plataforma com `uv`, configuracoes por plataforma, pos-processamento (UPX), manifests e integracao git/CI.

## Diferencas por categoria

### Proposito
- build_simple.py: build de triagem/desenvolvimento rapido. Nao pretende ser usado em release automatizado.
- build_multiplatform.py: build oficial/CI para produzir artefatos distribuiveis para diferentes plataformas.

### Ambiente e dependencias
- build_simple.py: usa o Python/ambiente atual e executa PyInstaller diretamente (sem criar venv isolado).
- build_multiplatform.py: cria e gerencia um `venv` por plataforma em `launchers/platforms/{platform}/venv` com `uv venv` e instala `requirements.txt` via `uv pip`.

### Configuracao e parametrizacao
- build_simple.py: flags PyInstaller hardcoded (alguns `hidden-imports`) e nome fixo do executavel (`SSA_CLI_v3.10_SIMPLES`).
- build_multiplatform.py: carrega `build_config.json` por plataforma (`launchers/platforms/{platform}/build_config.json`) e monta as flags dinamicamente (`pyinstaller_args`, `cli_config`, `gui_config`).

### Pos-processamento e metadados
- build_simple.py: nao possui pos-processamento.
- build_multiplatform.py: compressao opcional com UPX, criacao de `build_manifest.json` contendo metadados (tamanho, nome, versao), limpeza avancada e rotacao de logs.

### Integracao com git e CI
- build_simple.py: sem integracao git automatizada.
- build_multiplatform.py: pode commitar/pushar artefatos e metadados (`--auto-git`), alem de oferecer limpeza online de arquivos rastreados indevidamente.

### Limpeza de artefatos
- build_simple.py: `dist_simple` temporario e removido automaticamente (atexit).
- build_multiplatform.py: possui `cleanup_build_artifacts()` que remove caches, builds antigos, `dist_simple`, arquivos temporarios e mantem apenas os ultimos logs.

### Teste do executavel
- build_simple.py: testa o exe gerado com `--help` e valida o retorno (quick smoke test).
- build_multiplatform.py: foca em gerar artefatos e manifest; integracao de testes geralmente e feita no pipeline externo (mas o script pode ser estendido para isso).

## Comportamento especifico no Windows
- `build_multiplatform.py` roda em modo uv-first (`uv run --python 3.13 ...`) e usa o Python do `venv` da plataforma para invocar `PyInstaller` via `-m`.
- `build_simple.py` funciona em Windows desde que `pyinstaller` esteja disponivel no PATH.

## Onde os artefatos Windows aparecem (exemplo no repositorio)
- `launchers/dist/windows_amd64/SSA_CLI_v3.11_windows_amd64.exe`
- `launchers/dist/windows_amd64/SSA_GUI_v3.11_windows_amd64.exe`
- `launchers/dist/windows_amd64/build_manifest.json`

## Como usar (comandos exemplares)

Build rapido (desenvolvimento):
```powershell
uv run --python 3.13 launchers/build_simple.py
```

Build Windows (reprodutivel, plataforma atual):
```powershell
uv run --python 3.13 launchers/build_multiplatform.py --platform windows_amd64
```

Build atual detectado (faz build para a plataforma atual):
```powershell
uv run --python 3.13 launchers/build_multiplatform.py
```

Passos para CI / release recomendados:
1. Usar `build_multiplatform.py` em runner correspondente (Windows runner para windows_amd64, macOS runner para macos_arm64, etc.).
2. Habilitar `--auto-cleanup` e `--auto-git` se quiser que manifests e docs sejam committados automaticamente (cautela: script evita commitar executaveis).
3. Anexar `build_manifest.json` e executaveis ao GitHub Release (ex.: `gh release upload`).

## Recomendacoes de consolidacao (opcional)
- Mantenha ambos: `build_simple.py` como wrapper rapido para dev, e `build_multiplatform.py` como sistema oficial de build/CI.
- Alternativa: transformar `build_simple.py` em um pequeno wrapper que chama internamente as funcoes de `build_multiplatform.py` com um perfil `dev` (gera `dist_simple`). Isso evita duplicacao de logica (construir comando PyInstaller).

## Observacoes finais
- `build_simple.py` e intencionalmente limitado (simplicidade e limpeza automatica). `build_multiplatform.py` e mais complexo por design: venvs, configs por plataforma, pos-processamento e operacoes git.
- Antes de automatizar uploads de executaveis para releases, confirme politica de versao e checagens de integridade (assinatura, checksums) se necessario.

---

Arquivo gerado automaticamente pelo agente em: `docs/BUILD_SCRIPTS_COMPARISON.md`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

