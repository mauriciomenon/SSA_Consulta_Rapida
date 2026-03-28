# Documentacao SSA Consulta Rapida

## Baseline ativo

- Versao de referencia: `4.36`.
- Esta pagina e a entrada curta da pasta `docs/`.
- Navegacao oficial: `docs/INDEX.md`.
- Current truth sincronizado com commits anteriores desta frente:
  - filtros visuais da GUI foram sincronizados com filtros avancados
  - a macro `Baixar` agora exclui `SAD/SCA/SES/STE`
  - o prompt de filtro por coluna ganhou hint padronizado
  - o sync manual de derivadas saiu do thread principal em runtime normal
  - a barra superior ganhou `Abrir SAM`, status filtrado/total e semana centralizada
  - o detalhe da SSA agora expande `situacao`, copia o numero por duplo clique e mostra derivadas em arvore textual
  - `load_other_database()` passou a validar banco em background no runtime normal
  - upsert passou a bloquear downgrade de `situacao` em empate de `data_cadastro`
  - o dialogo de detalhes ganhou aba dedicada `Arvore` com subabas `Grafo`, `Arvore` e `Mermaid`, mantendo detalhes na metade inferior
  - referencia de implementacao: commit `07ebfe1d`

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
