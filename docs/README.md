# Documentacao SSA Consulta Rapida

## Baseline ativo

- Versao de referencia: `4.37`.
- Esta pagina e a entrada curta da pasta `docs/`.
- Navegacao oficial: `docs/INDEX.md`.
- Current truth sincronizado com commits anteriores desta frente:
  - a auditoria tecnica grande do repo foi publicada em `docs_saida/ULTRA_AUDITORIA_TECNICA_REPO_20260330.md`
  - `filter_dataframe()` voltou a aceitar `search_columns` numericas/datetime sem falso vazio
  - a busca geral da GUI agora tem contrato proprio de colunas em `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
  - a decisao de colunas da busca geral deixou de ficar escondida no default do core para o fluxo da GUI
  - `setor_executor` passou a compartilhar estado aplicado entre filtro rapido e filtro avancado
  - `solicitante` no painel avancado agora reconhece alias `responsavel_solicitante`
  - o prefixo de area/setor de responsaveis ficou estavel contra subconjuntos filtrados
  - referencias de implementacao: `02ec4a30`, `b7af8aef`, `d6fbb4fe`
  - recuperacao forense da sessao em `2026-03-31` confirmou que o ultimo commit realmente aterrado foi `7913c712` (`DOC_SYNC: align live continuity docs`)
  - nesta retomada nao havia shell/agent ativo nem patch de runtime pendente; `HEAD...origin/dev = 00`
  - existe residuo antigo `.git\REBASE_HEAD` datado de `2025-11-26`, sem `rebase-apply`/`rebase-merge`; tratar como hygiene de Git fora de escopo, nao como operacao viva desta frente

## Regras de interpretacao

1. Em caso de conflito, prevalece:
   - `AGENTS.md` (raiz)
   - `docs/POLICY_BASELINE_V1_1_FROZEN.md`
   - topo dos docs de controle (`RECOVERY_BACKLOG`, `NEXT_CHAT_MIGRATION`, `AGENTS_HANDOFF_NEXT_CYCLE`)
2. Conteudo em `docs/archive/` e historico.
3. Nao usar snapshot antigo como fonte de verdade para operacao atual.

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
- `docs/RECOVERY_BACKLOG.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/HISTORICO_RELEASES.md`
- `docs/NUNCA_CONFIE_IA.md`
- `docs/archive/LEGACY_DOCS_REORG_STUDY_20260327.md`

## Primeira leitura obrigatoria no proximo chat

1. `AGENTS.md`
2. `docs/NEXT_CHAT_MIGRATION.md`
3. `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
4. `docs/RECOVERY_BACKLOG.md`
5. `docs/NUNCA_CONFIE_IA.md`

## Passo 0 obrigatorio antes de novo patch

1. ler `docs/RECOVERY_BACKLOG.md` e `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` pelo topo
2. revisar se existe slice local aberto antes de criar frente nova
3. usar `docs/NUNCA_CONFIE_IA.md` como checklist antes de tocar em fluxos criticos de dados
4. referencias:
   - `.github/instructions/kluster-code-verify.instructions.md`
   - `docs/NUNCA_CONFIE_IA.md`

## Tooling padrao

- Runtime principal: `uv run --python 3.13 ...`
- Fallback: `3.12 -> 3.11 -> 3.10`
- Compatibilidade sem uv: `requirements*.txt`

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
