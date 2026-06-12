# Documentacao SSA Consulta Rapida

## Baseline ativo

- Versao de referencia: `4.42`.
- Esta pagina e a entrada curta da pasta `docs/`.
- Navegacao oficial: `docs/INDEX.md`.
- Current truth operacional 2026-05-04 01h14:
  - `main`, `dev`, `origin/main` e `origin/dev` devem estar sincronizados; base minima `4705c2e5722c4f3a5266ac02a5d15a1928d5a223`
  - PR #58 e PR #59 merged
  - artefatos v4.42 anteriores a este HEAD seguem stale
  - proximo passo: rebuild Windows AMD64 e Debian AMD64 antes de atualizar release v4.42
- Current truth sincronizado com commits anteriores desta frente:
  - `tests/test_gui_filter_logic.py` deixou de depender de globais compartilhados entre testes para aposentadoria/limpeza de workers
  - o harness agora tira snapshot e restaura o estado global de lifecycle em `setup_method`/`teardown_method`
  - a pendencia correspondente saiu do backlog ativo como item de correcao
  - a auditoria tecnica grande do repo foi publicada em `docs_saida/ULTRA_AUDITORIA_TECNICA_REPO_20260330.md`
  - `filter_dataframe()` voltou a aceitar `search_columns` numericas/datetime sem falso vazio
  - a busca geral da GUI agora tem contrato proprio de colunas em `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
  - a decisao de colunas da busca geral deixou de ficar escondida no default do core para o fluxo da GUI
  - a frente de blindagem de contratos de estado da GUI foi consolidada em `docs/GUI_STATE_CONTRACT_POSTMORTEM_20260409.md`
  - reorder e sort de coluna agora preservam o painel `Detalhes da SSA Selecionada`
  - resize do header agora persiste largura pela coluna correta mesmo com reorder
  - reorder em schema parcial deixou de truncar colunas visiveis ausentes do schema atual
  - o contrato de derivadas ficou travado por regressao de navegacao e retorno a origem
  - `setor_executor` passou a compartilhar estado aplicado entre filtro rapido e filtro avancado
  - `solicitante` no painel avancado agora reconhece alias `responsavel_solicitante`
  - o prefixo de area/setor de responsaveis ficou estavel contra subconjuntos filtrados
  - referencias de implementacao desta frente:
    - `bf57520d`
    - `38cb9cc5`
    - `048700c4`
    - `5e581d6e`
    - `c45d9e42`
    - `3bc0d36f`
    - `21135ccf`
  - recuperacao forense da sessao em `2026-03-31` confirmou que o ultimo commit realmente aterrado foi `7913c712` (`DOC_SYNC: align live continuity docs`)
  - nesta retomada nao havia shell/agent ativo nem patch de runtime pendente; `HEAD...origin/dev = 00`
  - existe residuo antigo `.git\REBASE_HEAD` datado de `2025-11-26`, sem `rebase-apply`/`rebase-merge`; tratar como hygiene de Git fora de escopo, nao como operacao viva desta frente

## Regras de interpretacao

1. Em caso de conflito, prevalece:
   - `AGENTS.md` (raiz)
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
   - `README.md`
2. Nao usar snapshot antigo como fonte de verdade para operacao atual.

## Leitura rapida por objetivo

### Operar e manter

- `docs/COMANDOS_RAPIDOS.md`
- `docs/TROUBLESHOOTING.md`
- `docs/TROUBLESHOOTING_IMPORTACAO.md`
- `docs/DERIVADAS_SYNC_RUNBOOK.md`

### Entender importacao e schema

- `docs/ARQUITETURA_IMPORTACAO.md`
- `docs/SCHEMA_UNIFICADO_IMPORTACAO.md`
- `docs/IMPORTACAO_ROBUSTA.md`
- `docs/indicios_importacao.md`

### GUI e comportamento de filtros

- `docs/GUI_PYQT6_REGRAS_GERAIS.md`
- `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
- `docs/GUI_STATE_CONTRACT_POSTMORTEM_20260409.md`
- `docs/FILTER_TAB_OPTIMIZATIONS.md`
- `docs/GUI_ASYNC_LOADING_GUARDRAILS.md`
- `docs/WORKERS_API_DOCUMENTATION.md`
- `README.md` (topo vivo do sprint atual)

### Build e distribuicao

- `docs/BUILD_SYSTEM.md`
- `docs/BUILD_MULTIPLATFORM.md`
- `docs/GUIA_DISTRIBUICAO.md`
- `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
- `docs/BUILD_NUITKA_GUIA_COMPLETO.md`

## Controle de continuidade

- `AGENTS.md`
- `docs/HISTORICO_RELEASES.md`

## Primeira leitura obrigatoria no proximo chat

1. `AGENTS.md`
2. `README.md`
3. `docs/README.md`
4. `docs/HISTORICO_RELEASES.md`

## Passo 0 obrigatorio antes de novo patch

1. revisar se existe slice local aberto antes de criar frente nova
2. ler `AGENTS.md`, `README.md` e `docs/README.md`
3. registrar pendencias na conversa ou no PR, sem publicar backlog interno no repositorio

## Tooling padrao

- Runtime principal: `uv run --python 3.13 ...`
- Fallback: `3.12 -> 3.11 -> 3.10`
- Compatibilidade sem uv: `requirements*.txt`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
