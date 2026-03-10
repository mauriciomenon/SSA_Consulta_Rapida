# AGENTS Handoff For Next Cycle

Este handoff esta pronto para reutilizacao no proximo ciclo.

## CURRENT TRUTH 2026-03-09 22:11 - authoritative block

- Follow-up de comentarios pendentes do PR #45 concluido com patch minimo:
  1. `gui/ssa/gui_workers.py`: cap nao remove mais worker vivo; init de lista de workers sob lock antes de prune.
  2. `gui/gui_ssa.py`: importacao externa copia somente `.xlsx` e reporta `nao_suportados`; consolidacao de `nosurvivor` depende de sucesso sem sobreviventes.
  3. `utils/caching.py`: descoberta de extensoes Excel case-insensitive.
  4. `armazenamento/database_integrity.py`: resolucao de alias passa a preferir `table` sobre `view`.
  5. testes focados adicionados/ajustados para cobrir os contratos acima.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado (`47 passed`) -> pass.
- Pendencias deferidas:
  1. debts de arquitetura/performance em `gui/gui_ssa.py` e `gui/ssa/gui_workers.py` (fora deste slice).
  2. revisao de semantica de `database_exists` em arquivo SQLite vazio (ciclo dedicado).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:58

- Follow-up P2 de comentarios do PR #45 concluido:
  1. `gui/ssa/gui_workers.py`: registro global imediato de rescan worker apos `start()`.
  2. `gui/gui_ssa.py`: dedup de destino unificado em importacao externa via helper unico.
  3. `docs/CCR_LLM_PROVIDERS_SETUP.md`: padrao de instructions corrigido para `*.instructions`.
  4. `tests/test_gui_workers_rescan_data.py`: expectativa atualizada para novo contrato do registro global.
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` -> pass.
  2. `pytest` focado GUI workers/menu -> `16 passed`.
- Pendencia deferida:
  1. normalizacao nao-ascii em testes (debt transversal, nao blocker funcional imediato).
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 21:43

- PR em andamento: `#45` (`dev` <- `codex/sprint-importacao-grave-fixes-20260305`).
- Slice de hotfix de comentarios/checks concluido:
  1. ajuste de contrato no teste de cancelamento (`tests/test_import_cancellation.py`).
  2. correcao de log de warnings de integridade (`core/app_logic.py`).
  3. limpeza de retorno nao serializavel em validacao (`database_validation.py`).
  4. contrato `raise_on_error` alinhado para `ValueError` em `query_db` (`database.py`).
  5. removido suppress silencioso na whitelist do insert simples (`database.py`).
  6. removido warning falso em reparo opcional (`database_integrity.py`).
- Gates desta rodada:
  1. `py_compile`, `ruff`, `ty` (arquivos tocados) -> pass.
  2. `pytest` focado (`30 passed`) e pacote equivalente ao `quality-gates` (`73 passed`) -> pass.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:26

- Integridade de links/referencias em docs ativos concluida.
- Entregas principais:
  1. referencias quebradas em docs ativos corrigidas.
  2. stubs `docs/ARCH_*` adicionados para compatibilidade com backlog historico.
  3. referencias locais opcionais (`local_ai_private`) deixadas sem dependencia de arquivo especifico.
- Nao alterado:
  1. runtime de importacao/GUI/DB.
  2. testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 19:01

- Ciclo de refinamento de documentacao concluido no baseline `4.32`.
- Entregas principais:
  1. index e README de docs canonicos.
  2. comandos rapidos alinhados para uv-first.
  3. arquitetura e troubleshooting ativos simplificados.
  4. snapshots legados movidos para `docs/archive/`.
- Nao alterado:
  1. runtime de importacao/GUI/DB.
  2. suite de testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## HISTORICAL SNAPSHOT 2026-03-09 17:35

- Baseline ativo de versao/documentacao: `4.32`.
- Escopo consolidado atual:
  1. sync de metadados e docs para `4.32` concluido.
  2. governanca de docs refinada com fonte ativa unica no topo.
  3. historico antigo arquivado para reduzir risco de leitura ambigua.
- Nao alterado nesta rodada:
  1. runtime de importacao/GUI/DB.
  2. testes de runtime.
- Residuos locais fora de escopo (nao commitar):
  1. `data/ssas.db`
  2. `config/settings.json.bak_20260308_212715`

## REGRAS DE USO DESTE HANDOFF

1. Somente este bloco do topo e autoritativo para iniciar o proximo ciclo.
2. Informacoes antigas ficam no arquivo de historico arquivado.
3. Em caso de conflito entre historico e topo, prevalece o topo.

## ARQUIVO HISTORICO

- Historico completo anterior (ate 2026-03-09 17:35):
  - `docs/archive/AGENTS_HANDOFF_NEXT_CYCLE_legacy_until_20260309_1735.md`

## CHECKLIST OPERACIONAL PARA O PROXIMO CICLO

1. confirmar branch/pasta antes de editar.
2. registrar timestamp inicial/final no `docs/RECOVERY_BACKLOG.md`.
3. manter commits atomicos por slice e push imediato no branch alvo.
4. atualizar este handoff e `docs/NEXT_CHAT_MIGRATION.md` no mesmo slice.
