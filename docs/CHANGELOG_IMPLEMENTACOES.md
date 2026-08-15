# CHANGELOG_IMPLEMENTACOES

## v4.37 - STABILIZATION BASELINE PLUS CURRENT LOCAL TOP (2026-04-01)

### Baseline `v4.37`
- Promocao documental e local do baseline para `4.37`, mantendo `v4.36` como ultima tag publicada em GitHub.
- Endurecimento grande do contrato de GUI/filtros:
  - busca geral passa a ser dona explicita das colunas relevantes da GUI
  - reorder/sort/resize de header preservam detalhes e mapeamento visual
  - contrato de navegacao de derivadas e detalhes foi travado por regressao
- Fortalecimento de importacao e banco:
  - bloqueio de downgrade de `situacao` em empate de `data_cadastro`
  - importacao explicita por arquivo e `full rescan` com provas de atualizacao do estado do DB
  - reparo e recriacao de DB vazio quando necessario
- Larguras de colunas por plataforma e contrato de preferencias GUI alinhados entre runtime, fallback e arquivos versionados.
- Dialogo de detalhes/derivadas consolidado em popup unico com arvore textual, grafo SVG e exportacao.

### Delta local apos o baseline `v4.37`
- `404a710e` `fix(gui): Sync prefs reference and external check docs`
  - alinhou `config/gui_main_preferences.json.example` com o runtime real por plataforma
  - documentou `DeepSource` e `Snyk` como ruido externo do PR, nao como blocker local de codigo
- `4202fd37` `fix(import): auto-sync derivadas after valid db changes`
  - sincronizacao de derivadas passou a disparar apos alteracao valida do banco
  - recarga automatica dos dados passou a acompanhar importacao, rescan e adicao valida por arquivo
- `50b7796c` `fix(gui): Keep SSA detail navigation local`
  - clique em `ssa:` no painel inferior deixa de aplicar filtro global
  - popup de detalhes passa a mostrar relacionadas no HTML e no grafo
  - relacionadas ficam tracejadas e derivadas continuam solidas
- `a19c9abe` `fix(gui): raise details relations panel`
  - bloco inferior do popup ganhou altura util real para derivadas/relacionadas
- `4074ebdd` `fix(gui): restore parent in fallback graph`
  - fallback sem DB agora inclui parent imediato no popup/grafo
  - verificacao visual real confirmou ausencia de no solto no caso controlado

### Commits chave do trem `v4.36 -> topo atual`
- `c3a94526` `DOC_SYNC: promote local release baseline to 4.37`
- `185af3d0` `DOC_SYNC: keep a single current truth in continuity docs`
- `f1b676c4` `STABILITY_PATCH: normalize gui main preferences runtime config`
- `bf57520d` `STABILITY_PATCH: make GUI own general search columns`
- `21135ccf` `STABILITY_PATCH: lock derivadas detail navigation contract`
- `e92d0bae` `STABILITY_PATCH: preserve details across filter, alignment, and tab refresh`
- `79e798e2` `fix: stabilize gui sorting and workspace hygiene`
- `404a710e` `fix(gui): Sync prefs reference and external check docs`
- `4202fd37` `fix(import): auto-sync derivadas after valid db changes`
- `50b7796c` `fix(gui): Keep SSA detail navigation local`
- `a19c9abe` `fix(gui): raise details relations panel`
- `4074ebdd` `fix(gui): restore parent in fallback graph`

## v4.36 - TAGGED STABILITY TRANSITION (2026-04-01)

### Principais entregas
- `numero_ssa` e write-path de storage estabilizados com normalizacao centralizada e sanitizacao coerente.
- Contrato de filtros simplificados endurecido com preflight de aliases de derivadas.
- Slice minimo de `pytest`/`ty`/`bandit` fechado para manter a promocao da tag.
- Handoff documental preparado para a transicao de `v4.36`.

### Commits chave
- `5aeadd9e` `STABILITY_PATCH: centralize numero_ssa storage normalization`
- `40cc4662` `DOC_SYNC: record numero_ssa write-path stabilization status`
- `0d823b25` `STABILITY_PATCH: align simple insert with storage sanitization`
- `f4af8d20` `STABILITY_PATCH: stabilize simplified filter contract and derivadas alias preflight`
- `bdf612d0` `STABILITY_PATCH: close pytest ty bandit minfix slice`
- `dd2d45b1` `DOC_SYNC: prepare 4.36 transition handoff`

## v4.35 - PRE-BASELINE HARDENING TRAIN (2026-03-24)

### Principais entregas
- Discovery/import e nullable handling estabilizados para fechamento das regressos do rescan.
- Navegacao async para SSA e renderizacao de detalhes endurecidas contra selecao fria, rerender redundante e stale selection.
- `numero_ssa` e relacionadas mantidos como identificadores canonicos em texto na importacao e na GUI.
- Higiene operacional local melhorada com empacotamento explicito de opcoes de DB e reducao do ruido de `docs_entrada`.

### Commits chave
- `3be31666` `STABILITY_PATCH: prefer current python for streamlit launcher`
- `19e68ba5` `STABILITY_PATCH: clarify CLI shortcuts and time filter refresh`
- `7283d506` `STABILITY_PATCH: centralize DataLoaderWorker identifier policy`
- `1c6851a0` `STABILITY_PATCH: harden derivadas excel parse flow`
- `99342167` `STABILITY_PATCH: lock robust importer raw mode contract`
- `824e1f94` `STABILITY_PATCH: harden gui table batch state`
- `f03b9721` `HOTFIX_BLOCKER: stabilize async jump to SSA`
- `113b12a1` `STABILITY_PATCH: normalize related SSA identifiers in import`
- `d5a9e137` `HOTFIX_BLOCKER: fix nullable display and filter contract`
- `bd14e3d7` `STABILITY_PATCH: close full regression gaps`
- `53def322` `STABILITY_PATCH: package explicit db options and clean local tracking`
- `b4b995a8` `STABILITY_PATCH: ignore local docs_entrada excel noise`

## v4.33 - DOC_SYNC TOTAL (2026-03-10)

- Sincronizacao completa da documentacao ativa para baseline `4.33`.
- Controle de estado atualizado com evidencia operacional do PR `#45`:
  - sem threads abertas.
  - bloqueios externos restantes em `CodeFactor`, `code/snyk`, `security/snyk`.
- Guias de build/distribuicao e docs de migracao/handoff alinhados na mesma rodada.

##  v4.0.0 - OTIMIZACOES MASSIVAS DE PERFORMANCE (2025-09-26)

### **RELEASE COMPLETO - PERFORMANCE MASSIVAMENTE OTIMIZADA**

#### ** Phase 1: Fundamentos (90% mais rapido)**
-  Main.py com modo `--optimized` por padrao
-  `core/app_logic.py` - `filter_dataframe` otimizado (1.96x speedup)
-  6 indices estrategicos no SQLite para queries 5-20x mais rapidas

#### ** Phase 2: GUI Inteligente (2.88x-102,900x speedup)**
-  Sistema de cache LRU multi-threaded com `FilterWorker`
-  Debounce 250ms para evitar consultas excessivas
-  Cache hit rate 75%+ em uso normal

#### ** Phase 3: Streamlit Aprimorado (3,977x speedup)**
-  `StreamlitFilterCache` com TTL e metricas detalhadas
-  Interface sidebar reorganizada com progress bars
-  Cache configuravel (100 entradas, 300s TTL)

#### ** Phase 4: Sistema de Logging Robusto**
-  `utils/robust_logging.py` com `PerformanceMetrics` automatico
-  `config/logging.json` - Configuracao centralizada multi-handler
-  Logging estruturado JSON + rotacao automatica
-  Integracao completa em main.py, GUI e Streamlit

#### ** RESULTADOS FINAIS MENSURADOS:**
- **Imports:** 80-90% mais rapidos (modo otimizado padrao)
- **GUI Filters:** 2.88x a 102,900x speedup com cache LRU
- **Streamlit:** 3,977x speedup medio com cache TTL
- **Database Queries:** 5-20x mais rapidas com indices estrategicos
- **Sistema de Logging:** Robusto com metricas automaticas

### ** ARQUIVOS IMPLEMENTADOS:**
- `utils/robust_logging.py` - Sistema completo de logging robusto
- `config/logging.json` - Configuracao centralizada
- `tests/test_robust_logging.py` - Testes abrangentes
- Integracoes em main.py, gui/gui_ssa.py, streamlit_app.py

---

Arquivo legado mantido para compatibilidade com testes automatizados. O historico completo e detalhado permanece em `docs_saida/CHANGELOG_IMPLEMENTACOES.md`.

## 2025-08-15
- Removida GUI PoC `gui/gui_ssa_poc.py` e testes correlatos para reduzir ruido de manutencao.
- Estruturado novo conjunto de quality gates iniciais (validacao de configs / smoke CLI rascunho).

## 2025-08-28
- Refatoracao do pipeline de importacao e normalizacao de `numero_ssa`.
- Introducao de testes de upsert garantindo nao regressao de datas mais novas.

## 2025-09-05
- Adicionado modo de filtragem sincrona (`SSA_SYNC_FILTER`) para estabilizar testes GUI evitando race com `QThread`.
- Simplificacao de layout de filtros duplicados na janela principal.

## 2025-09-10
- Ajustes de compatibilidade retroativa nas funcoes de banco para aceitar tanto `db_path` quanto conexoes SQLite abertas.
- Melhoria na logica de comparacao de datas no upsert (nao sobrescrever com registro mais antigo).

## 2025-09-12
- Revisao dos mapeamentos de exibicao de colunas e restauracao de acentuacao (`Numero SSA` / fallback sem acento para caminhos legados).
- Correcoes de assinatura de slots de menu de contexto (ex.: `copy_cell_value`).

Para historico completo e decisoes arquiteturais ver: `docs/HISTORICO_RELEASES.md` e `docs_saida/CHANGELOG_IMPLEMENTACOES.md`.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
