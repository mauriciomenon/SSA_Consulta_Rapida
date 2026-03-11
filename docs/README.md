# Documentacao SSA Consulta Rapida

## Baseline ativo

- Versao de referencia: `4.32`.
- Esta pagina e a entrada curta da pasta `docs/`.
- Navegacao oficial: `docs/INDEX.md`.

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

### Build e distribuicao

- `docs/BUILD_SYSTEM.md`
- `docs/BUILD_MULTIPLATFORM.md`
- `docs/GUIA_DISTRIBUICAO.md`
- `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
- `docs/BUILD_NUITKA_GUIA_COMPLETO.md`

## Controle de continuidade

- `docs/RECOVERY_BACKLOG.md`
- `docs/NEXT_CHAT_MIGRATION.md`
- `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
- `docs/HISTORICO_RELEASES.md`

## Tooling padrao

- Runtime principal: `uv run --python 3.13 ...`
- Fallback: `3.12 -> 3.11 -> 3.10`
- Compatibilidade sem uv: `requirements*.txt`
