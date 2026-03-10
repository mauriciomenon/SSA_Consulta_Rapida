# Next Chat Migration Guide

Use este arquivo para migrar contexto para um novo chat sem perder qualidade de execucao.

## CURRENT TRUTH 2026-03-09 21:43 - start from here

- PR ativo: `#45` (base `dev`, head `codex/sprint-importacao-grave-fixes-20260305`).
- Hotfix aplicado para comentarios/checks bloqueantes:
  1. contrato de cancelamento em `tests/test_import_cancellation.py` alinhado ao runtime atual.
  2. warning de integridade em `core/app_logic.py` voltou a logar no caminho valido.
  3. `database_validation` nao retorna mais `set` interno em retorno precoce.
  4. `database.query_db` respeita `raise_on_error=False` tambem para `ValueError`.
  5. removido suppress silencioso em whitelist de colunas no insert simples.
  6. removido warning falso `Problemas detectados no banco: []` em `database_integrity`.
- Evidencia de qualidade desta rodada:
  1. pacote focado: `30 passed`.
  2. pacote equivalente ao `quality-gates`: `73 passed`.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:26

- Integridade de documentacao reforcada no baseline `4.32`.
- Entregas principais:
  1. referencias quebradas de `.md` corrigidas nos docs ativos.
  2. referencias locais opcionais (`local_ai_private`) tratadas como nao obrigatorias.
  3. stubs `docs/ARCH_*` adicionados para compatibilidade com backlog historico.
  4. ponteiro de plano legado criado em `docs/archive/PLANO_REFATORACAO_SSA_CONSULTA_RAPIDA.md`.
- Evidencia de qualidade:
  1. varredura de referencias markdown em `README.md` + `docs/*.md` com resultado final `missing=0`.
  2. kluster limpo apos ajustes finais por arquivo.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:01

- Ciclo de refinamento documental concluido para baseline `4.32`.
- Principais entregas:
  1. `docs/INDEX.md` e `docs/README.md` canonicos e consistentes.
  2. `docs/COMANDOS_RAPIDOS.md` atualizado para uv-first.
  3. `docs/ARQUITETURA_IMPORTACAO.md` ativo simplificado e snapshot arquivado.
  4. `docs/TROUBLESHOOTING*.md` ativos simplificados e snapshots arquivados.
  5. `docs/HISTORICO_RELEASES.md` atualizado com governanca de docs.
- Regra de continuidade:
  1. usar somente o bloco do topo deste arquivo.
  2. consultar `docs/archive/` apenas para contexto historico.
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 17:35

- Baseline ativo de versao/documentacao: `4.32`.
- Refinamento de governanca documental concluido:
  1. somente o bloco de topo e fonte ativa.
  2. historico antigo foi movido para arquivo dedicado para reduzir ambiguidade.
  3. referencias de release evitam logs efemeros.
- Escopo desta rodada:
  1. apenas docs e metadados de versao.
  2. nenhum runtime alterado (`core/gui/armazenamento/extracao/interface/tests`).
- Residuos locais fora de escopo mantidos:
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## REGRAS DE INTERPRETACAO

1. Este bloco do topo e a unica fonte ativa para continuidade.
2. Todo historico de iteracoes anteriores deve ser lido no arquivo de arquivo.
3. Em caso de conflito, prevalece sempre o topo deste arquivo.

## ARQUIVO HISTORICO

- Historico completo anterior (ate 2026-03-09 17:35):
  - `docs/archive/NEXT_CHAT_MIGRATION_legacy_until_20260309_1735.md`

## CHECKLIST DE CONTINUIDADE

1. confirmar branch alvo antes de editar.
2. validar residuos locais fora de escopo antes de commit.
3. registrar inicio/fim da sessao em `docs/RECOVERY_BACKLOG.md`.
4. atualizar `docs/AGENTS_HANDOFF_NEXT_CYCLE.md` no mesmo slice.
