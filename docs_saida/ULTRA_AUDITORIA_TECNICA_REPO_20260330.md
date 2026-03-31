# Ultra auditoria tecnica do repositorio SSA_Consulta_Rapida

Status: work in progress

Objetivo deste documento:

- registrar uma auditoria profunda do repositorio inteiro
- reduzir redescoberta em outra maquina ou outra sessao
- separar arquitetura real de debt historico e residuos locais
- apontar problemas de alta relevancia tecnica antes de qualquer reimplementacao
- servir como base para um possivel plano de refactor pesado ou migracao parcial/total

---

## Sumario

1. [Escopo e metodo](#escopo-e-metodo)
2. [Current truth desta auditoria](#current-truth-desta-auditoria)
3. [Inventario estrutural do repositorio](#inventario-estrutural-do-repositorio)
4. [Entry points e modos de runtime](#entry-points-e-modos-de-runtime)
5. [Arquitetura por dominios](#arquitetura-por-dominios)
6. [Fluxos de dados principais](#fluxos-de-dados-principais)
7. [Hotspots de tamanho e concentracao](#hotspots-de-tamanho-e-concentracao)
8. [Achados fortes ja confirmados](#achados-fortes-ja-confirmados)
9. [Codigo legado, paralelo ou suspeito](#codigo-legado-paralelo-ou-suspeito)
10. [GUI PyQt: estado atual](#gui-pyqt-estado-atual)
11. [CLI: estado atual](#cli-estado-atual)
12. [Streamlit: estado atual](#streamlit-estado-atual)
13. [Integracao entre GUI, CLI e Streamlit](#integracao-entre-gui-cli-e-streamlit)
14. [Banco, importacao e derivadas](#banco-importacao-e-derivadas)
15. [Estado atual dos testes](#estado-atual-dos-testes)
16. [Tooling, build e operacao](#tooling-build-e-operacao)
17. [Debt estrutural e backlog de alto impacto](#debt-estrutural-e-backlog-de-alto-impacto)
18. [Reimplementacao parcial ou total em Rust ou Zig](#reimplementacao-parcial-ou-total-em-rust-ou-zig)
19. [Recomendacoes por horizonte](#recomendacoes-por-horizonte)
20. [Apontamentos ainda em aprofundamento](#apontamentos-ainda-em-aprofundamento)

---

## Escopo e metodo

Esta auditoria esta sendo feita com quatro fontes de evidencia:

1. leitura direta dos arquivos centrais do repo
2. metricas do workspace excluindo `.venv` e caches
3. leitura dos docs vivos que descrevem o baseline real
4. agentes auxiliares especializados para arquitetura, GUI e qualidade

Regras de interpretacao desta auditoria:

- runtime e docs vivos vencem docs historicos
- arquivo grande nao e automaticamente ruim
- arquivo pequeno nao e automaticamente bom
- teste numeroso nao significa boa cobertura
- codigo de recovery, maintenance ou build nao pode ser marcado como morto sem evidencia
- qualquer achado abaixo deve ser lido como uma hipotese classificada em um destes niveis:
  - confirmado
  - fortemente provavel
  - suspeito, mas precisa prova adicional

---

## Current truth desta auditoria

### Baseline tecnico observado

- Linguagem principal: Python
- Runtime declarado: `>=3.10`
- Runtime preferido do projeto: `uv run --python 3.13 ...`
- Frontends ativos:
  - CLI
  - GUI PyQt6
  - Streamlit
- Banco principal: SQLite
- Dominio central compartilhado: `core/app_logic.py`

### Dependencias centrais

Segundo `pyproject.toml`, o pacote principal depende de:

- `pandas`
- `openpyxl`
- `pyqt6`
- `numpy`
- `tabulate`

Ferramentas dev declaradas:

- `ruff`
- `flake8`
- `pytest`
- `ty`
- `black`

### Metricas do projeto

Metricas coletadas excluindo `.venv`, `.git`, caches comuns e derivados de ambiente:

- arquivos Python do projeto: `408`
- arquivos Markdown do projeto: `157`
- arquivos JSON do projeto: `45`
- testes Python em `tests\`: `201`

### Maiores arquivos Python do projeto

1. `tests\test_gui_filter_logic.py`
2. `gui\gui_ssa.py`
3. `gui\mixins\filter_gui_ssa_mixin.py`
4. `dev_env\streamlit_app.py`
5. `gui\ssa\gui_filters_advanced_ui.py`
6. `core\app_logic.py`
7. `armazenamento\derivadas_sync.py`
8. `gui\ssa\gui_details.py`
9. `gui\ssa\gui_workers.py`
10. `interface\cli.py`

Primeira conclusao importante: o maior arquivo do projeto nao e de runtime, e sim um megateste de GUI/filtros. Isso por si so ja indica alta concentracao de regra de negocio de filtros em um unico funil de testes.

---

## Inventario estrutural do repositorio

### Pastas de codigo mais relevantes

- `core\`
  - orquestracao de importacao
  - busca e filtro
  - configuracao
  - cache auxiliar

- `armazenamento\`
  - SQLite
  - upsert
  - validacao
  - integridade
  - derivadas

- `extracao\`
  - leitura e normalizacao de planilhas

- `gui\`
  - janela principal PyQt6
  - mixins
  - widgets
  - workers
  - detalhes
  - filtros avancados
  - tema

- `interface\`
  - CLI
  - printers
  - display formatters
  - enhancement manager

- `dev_env\`
  - frontend Streamlit

- `shared\`
  - contratos e utilitarios compartilhados de dominio

- `utils\`
  - logging
  - cache
  - path safety
  - temas
  - import helpers

- `exportacao\`
  - exportacao de dados

- `tests\`
  - suite principal

### Pastas que merecem triagem especial

- `LocalTemp\`
  - contem residuos/legado local
  - nao parece parte do runtime principal

- `docs_entrada\`
  - contem insumos pesados reais

- `data\`
  - contem banco principal e backups grandes

- `docs_saida\`
  - local apropriado para saidas tecnicas como este arquivo

---

## Entry points e modos de runtime

### `main.py`

`main.py` e o bootstrap principal. Ele mistura:

- monkey patch de PyOxidizer para `pandas`
- configuracao de logging
- resolucao de path de runtime
- parse de argumentos
- dispatch entre interfaces

Isto faz dele um entry point real, mas tambem um mini-orquestrador de empacotamento. O arquivo e relativamente grande para um bootstrap, o que indica que responsabilidades de runtime congelado e runtime de desenvolvimento nao estao totalmente separadas.

### `launchers\*.py`

Os launchers existem para cenarios frozen e parecem cuidar de:

- preparar diretorios de runtime
- semear config/data
- iniciar CLI ou GUI

Isto e um sinal de maturidade operacional, mas tambem um segundo ponto de verdade para setup do ambiente.

### GUI

O ponto de entrada da GUI converge em `gui\gui_ssa.py` e em `SSAMainWindow`.

### CLI

O ponto de entrada da CLI converge em `interface\cli.py`.

### Streamlit

O frontend Streamlit mora em `dev_env\streamlit_app.py`.

Conclusao de alto nivel: o projeto ja e multiplataforma no sentido de interfaces, nao apenas no sentido de build.

---

## Arquitetura por dominios

### 1. Dominio central

O repo tem uma boa decisao arquitetural de base: GUI, CLI e Streamlit convergem em boa parte da regra compartilhada de `core/app_logic.py`.

Pontos observados:

- CLI importa `filter_dataframe`, `parse_search_terms` e `run_importer_logic`
- GUI importa `filter_dataframe` e `parse_search_terms`
- Streamlit importa `filter_dataframe`, `get_filtered_data`, `import_files_to_database` e `parse_search_terms`

Isso reduz duplicacao de regra de busca. O problema e que o arquivo central parece misturar import pipeline e search pipeline em um unico modulo grande.

### 2. Persistencia

`armazenamento\database.py` e a porta de entrada da camada de banco, mas ele nao e sozinho:

- `database.py`
- `database_optimized.py`
- `database_upsert_logic.py`
- `database_validation.py`
- `database_integrity.py`
- `derivadas_sync.py`
- `derivadas_schema.py`

Isto mostra uma camada de persistencia mais refinada do que o resto do projeto. A parte de banco parece mais conscientemente modularizada do que GUI e CLI.

### 3. Extracao

`extracao\extractor.py` parece ser a extracao classica, mas o projeto tambem carrega `utils\robust_importer.py` e ate `utils\robust_importer_old.py`. Isso sugere pelo menos duas geracoes de estrategia de importacao convivendo no repo.

### 4. GUI

A GUI ja esta parcialmente fatiada:

- `gui\gui_ssa.py`
- `gui\mixins\*`
- `gui\ssa\gui_filters_advanced_*`
- `gui\ssa\gui_details.py`
- `gui\ssa\gui_workers.py`
- `gui\workers\*`

Mas a janela principal ainda segue como hotspot estrutural.

### 5. CLI

A CLI e menos modular que a camada de banco e mais modular que o monolito antigo de GUI, mas ainda concentra muito estado e fluxo interativo em um unico arquivo grande.

### 6. Streamlit

O Streamlit nao parece ser apenas um experimento trivial. Ele consome de fato o dominio central e implementa cache proprio, filtros e logica de exibicao.

---

## Fluxos de dados principais

### Fluxo 1 - importacao

Fluxo observado a partir de docs vivos e leitura de `core/app_logic.py`:

1. descoberta e validacao de paths
2. leitura de planilhas
3. normalizacao de colunas e tipos
4. consolidacao/staging
5. upsert em SQLite
6. validacao
7. sincronizacao de derivadas
8. promocao do banco candidato quando aplicavel

Ponto positivo:

- o baseline documental de importacao esta relativamente claro
- a camada de upsert tem contratos explicitos

Ponto de risco:

- `core/app_logic.py` centraliza demais o pipeline

### Fluxo 2 - busca e filtros

Fluxo compartilhado:

1. parse do texto de busca
2. escolha das colunas relevantes
3. normalizacao/search cache
4. filtro do DataFrame
5. apresentacao na interface correspondente

Ponto positivo:

- ha reaproveitamento entre interfaces

Ponto de risco:

- a GUI ainda adiciona muito estado local por cima do dominio compartilhado

### Fluxo 3 - derivadas

`armazenamento\derivadas_sync.py` parece ser um subsistema praticamente proprio:

- coleta relacoes do banco
- coleta relacoes de planilha opcional
- monta matriz de arestas
- materializa closure/resumos
- expoe metricas de reconciliacao

Isto sugere que derivadas merece ser tratado como subdominio, nao apenas helper.

---

## Hotspots de tamanho e concentracao

### `gui\gui_ssa.py`

Classificacao: hotspot critico confirmado.

Motivos:

- arquivo centralizador
- mistura janela principal, wiring, estado, pathing, fallback de Qt e interacoes amplas
- segue muito maior que os modulos auxiliares extraidos dele

Leitura arquitetural:

- houve tentativa real de modularizacao
- essa modularizacao ainda esta incompleta

### `core\app_logic.py`

Classificacao: hotspot critico confirmado.

Motivos:

- orquestra importacao
- concentra busca/filtro
- carrega cache e utilitarios de fluxo

Leitura arquitetural:

- e um modulo de "core" no sentido historico, nao no sentido de single responsibility

### `tests\test_gui_filter_logic.py`

Classificacao: hotspot de testes confirmado.

Motivos:

- concentra grande parte da cobertura de filtros/GUI
- tende a virar funil de regressao e tambem gargalo de manutencao

Leitura arquitetural:

- pode conter cobertura valiosa
- mas o tamanho sugere que a estrutura do dominio de filtros nao esta espelhada pela estrutura dos testes

### `dev_env\streamlit_app.py`

Classificacao: hotspot medio a alto.

Motivos:

- frontend inteiro em um unico arquivo grande
- mistura import dinamico, cache, filtros, estado de session e exibicao

---

## Fragmentacao, arquivos gigantes e arquivos pequenos demais

### Visao por linhas, nao so por KB

Metricas coletadas por contagem de linhas:

1. `gui\gui_ssa.py` - `4660` linhas
2. `tests\test_gui_filter_logic.py` - `4340` linhas
3. `gui\mixins\filter_gui_ssa_mixin.py` - `3498` linhas
4. `gui\ssa\gui_filters_advanced_ui.py` - `3255` linhas
5. `dev_env\streamlit_app.py` - `3169` linhas
6. `core\app_logic.py` - `2623` linhas
7. `armazenamento\derivadas_sync.py` - `1940` linhas
8. `gui\ssa\gui_workers.py` - `1512` linhas
9. `gui\ssa\gui_details.py` - `1484` linhas
10. `tests\test_import_run_report.py` - `1397` linhas
11. `interface\cli.py` - `1270` linhas

Leitura tecnica:

- GUI e filtros continuam hiperconcentrados
- Streamlit tambem e um monolito de frontend
- `core\app_logic.py` segue como concentrador real
- ha um segundo monolito importante no lado de testes

### Distribuicao de arquivos Python por pasta de topo

Levantamento coletado:

- `tests`: `201`
- `gui`: `37`
- `scripts`: `36`
- `scripts_manutencao`: `35`
- `LocalTemp`: `27`
- `utils`: `17`
- `armazenamento`: `12`
- `launchers`: `11`
- `core`: `9`
- `interface`: `8`
- `shared`: `7`

Leitura tecnica:

- o volume de `scripts` + `scripts_manutencao` + `LocalTemp` e alto demais para ser ignorado
- isso sugere ecosistema operacional grande e risco de conhecimento espalhado fora da superficie principal do produto

### Arquivos muito pequenos

Alguns arquivos pequenos sao bons sinais de modulo puro:

- `shared\db_names.py`
- `shared\import_contract.py`
- `armazenamento\identifier_utils.py`

Esses parecem wrappers/contratos pequenos e uteis.

Outros pequenos sao sinais de fragmentacao ou ruina residual:

- arquivos em `tests\legacy_tests\`
- varios utilitarios em `LocalTemp\...`
- testes muito curtos que validam um comportamento isolado quase trivial

Conclusao:

- o repo nao sofre so de monolitos
- ele sofre tambem de fragmentacao auxiliar e residuos paralelos
- o risco e duplo:
  - hotspots gigantes demais
  - periferia ruidosa demais

---

## Achados fortes ja confirmados

### A. O projeto tem um desenho de dominio melhor do que um monolito puro

Confirmado por leitura:

- CLI, GUI e Streamlit compartilham parte da regra central
- `shared\` contem contratos reaproveitados
- a persistencia esta relativamente fatiada

### B. A GUI segue sendo o maior centro de acoplamento

Confirmado por leitura de `gui\gui_ssa.py` e por analise do agente de GUI.

### C. O core mistura import e filtro em um mesmo modulo grande

Confirmado por leitura direta de `core\app_logic.py`.

### D. Ha residuos legados explicitos no repo

Confirmado por exemplos:

- `utils\robust_importer_old.py`
- `tests\debug_frankenstein.py`
- residuos em `LocalTemp\legacy\...`

### E. Existe pelo menos uma estrategia ativa de "modularizacao parcial"

Confirmado por coexistencia de:

- `gui\gui_ssa.py`
- `gui\mixins\*`
- `gui\ssa\*`
- `gui\workers\*`

Ou seja: o projeto nao esta parado; ele esta em transicao controlada.

### F. Existem bugs reais de corretude no miolo de filtro

#### F.1 `filter_dataframe` pode derrubar buscas quando as colunas pesquisadas nao sao texto

Classificacao: bug real confirmado.

Evidencia direta em `core\app_logic.py:2572-2580`:

```python
base_str_df = (
    df[available_search_cols]
    .select_dtypes(include=["object", "string"])
    .fillna("")
    .astype(str)
)
if base_str_df.shape[1] == 0:
    return FilterSearchCacheManager.clear_result_attrs(df.iloc[0:0])
```

Leitura tecnica:

- se o chamador restringe `search_columns` para uma coluna numerica ou datetime
- e essa coluna chega com dtype nao textual
- o `select_dtypes` a remove antes do cast para string
- o fluxo conclui que nao ha nenhuma coluna onde buscar
- o resultado volta vazio

Isso e um bug de corretude, nao apenas de performance ou estilo.

#### F.2 `pattern_cache` e parcialmente morto

Classificacao: implementacao pela metade confirmada.

Evidencia em `core\app_logic.py:2624-2689`:

- o codigo precomputava patterns para `contains`, `prefix`, `suffix`, `exact`, `regex`
- mas os ramos `prefix`, `suffix` e `exact` recalculam regex especifico logo depois
- o valor precomputado e ignorado nesses modos

Leitura tecnica:

- cache nao esta totalmente morto
- mas esta conceitualmente errado ou incompleto
- isto aumenta ruido cognitivo e pode mascarar custo extra por termo

### G. Ha cache de filtro avancado fora da lista oficial de caches

Classificacao: bug real confirmado.

Evidencia:

- `gui\ssa\gui_filters_advanced_state.py:11-16` define `ADV_FILTER_CACHE_ATTRS` sem `_adv_year_emissao_cache`
- `gui\ssa\gui_filters_advanced_logic.py:378-391` usa `state.get_cache("_adv_year_emissao_cache")`

Leitura tecnica:

- esse cache existe na pratica quando usado
- mas nao participa da limpeza padrao em `clear_caches()`
- isso abre caminho para cache stale depois de reload/troca de dataset

### H. Sync automatico de derivadas esta acoplado a full rescan

Classificacao: bug real ou, no minimo, comportamento perigosamente subdocumentado.

Evidencia em `core\app_logic.py:2072`:

```python
auto_derivadas_sync_enabled = bool(force_import)
```

Leitura tecnica:

- `force_import` e o gatilho de full import/full rescan
- logo o nome `auto_derivadas_sync_enabled` e enganoso
- no caminho incremental normal, derivadas podem ficar defasadas

Isso precisa ser tratado como:

- bug funcional, se a expectativa de produto e derivadas atualizadas apos import incremental
- ou debt grave de contrato, se a politica atual for mesmo essa mas estiver mal comunicada

### I. Existe framework inteiro praticamente sem tracao real

Classificacao: codigo morto ou framework morto fortemente confirmado.

Arquivo:

- `core\handler_base.py`

Evidencia:

- `rg` encontrou definicoes e testes artificiais do framework
- nao encontrou handlers concretos reais do runtime usando essa hierarquia

Leitura tecnica:

- nao e um helper pequeno
- e um mini-framework proprio de handlers CLI
- manter isso sem adocao real aumenta manutencao e confunde quem entra no repo

### J. Existe importer "enhanced" que ainda e essencialmente um stub

Classificacao: implementacao pela metade confirmada.

Arquivo:

- `utils\enhanced_importer.py`

Evidencia:

- `EnhancedAMSImporter` existe
- ha teste de deteccao de formato
- `_apply_format_transformations()` literalmente retorna `df` sem fazer nada

Leitura tecnica:

- o nome sugere um subsistema funcional
- na pratica, ele ainda nao entrega a principal parte prometida

### K. Ha duplicacoes utilitarias concretas

Classificacao: redundancia confirmada.

Casos ja confirmados:

1. `_ASCIIOnlyFilter`
   - `main.py`
   - `dev_env\streamlit_app.py`

2. `_resolve_cache_max_entry_bytes`
   - `gui\cache\filter_cache.py`
   - `dev_env\streamlit_app.py`

3. `build_unique_destination_path`
   - `core\import_consolidation.py`
   - `core\import_staging.py`
   - alem de uma variante local em `gui\gui_ssa.py`

Leitura tecnica:

- nem toda duplicacao aqui e identica em escopo
- mas ha o suficiente para afirmar que pequenos forks utilitarios ja existem e podem divergir

---

## Codigo legado, paralelo ou suspeito

### `utils\robust_importer_old.py`

Classificacao: legado explicito, provavelmente nao-runtime.

Evidencia textual forte no proprio arquivo:

- "REFERENCE FILE - NOT USED IN PRODUCTION"
- "old version"
- "DO NOT import this file in production code"

Interpretacao:

- nao e codigo morto acidental
- e arquivo historico mantido no repo
- precisa decisao de governanca: manter como referencia historica ou mover para `docs\archive` / `LocalTemp` / outra area claramente nao-runtime

### `tests\debug_frankenstein.py`

Classificacao: altamente suspeito como teste de suite principal.

Motivos:

- nome indica script diagnostico, nao teste de regressao
- usa heuristicas textuais sobre fontes de config, imports e nomenclatura
- parece mais auditor local do que teste automatizado de produto

Interpretacao:

- provavelmente deveria estar em `scripts_manutencao\` ou `tools\`, nao em `tests\`

### `LocalTemp\legacy\extracao\extractor_dev.py`

Classificacao: residuo local/legado.

Interpretacao:

- nao parece fazer parte da superficie ativa do produto
- deve entrar na secao de higiene do repo, nao na de arquitetura runtime

### `scripts_manutencao\detector_frankenstein.py`

Classificacao: ferramenta auxiliar de auditoria, nao runtime.

Risco:

- se esse tipo de script comecar a ser usado como "fonte de verdade" de qualidade, ele produz muito falso positivo

### `gui\tabs\base_tab.py` e `gui\tabs\main_tab.py`

Classificacao: implementacao paralela nao integrada, fortemente suspeita.

Evidencia:

- `main_tab.py` declara explicitamente "CLEAN implementation without legacy code"
- `rg` nao encontrou consumo real dessa arvore fora do proprio pacote `gui.tabs`
- os dois arquivos dependem de `PyQt6` direto e nao seguem o caminho de fallback/headless usado em outras partes da GUI
- o `MainTab` implementa uma versao propria de busca, tabela e detalhes, com `print()` de debug no meio do fluxo

Leitura tecnica:

- isso parece uma tentativa de reescrever parte da GUI "do jeito certo"
- mas sem integrar na janela principal
- portanto virou implementacao paralela congelada

Esse tipo de artefato e perigoso porque:

- da a impressao de arquitetura melhor do que a realmente em uso
- atrai refactors para uma trilha que nao move o produto de verdade

### `LocalTemp\`

Classificacao: superficie ruidosa do workspace.

Ponto importante:

- nao devo tratar `LocalTemp\` automaticamente como runtime
- mas sua mera existencia com `27` arquivos Python aumenta atrito de busca, grep e onboarding

Para auditoria do projeto, `LocalTemp\` deve ser lido como:

- contexto historico/local
- nao como centro de verdade do sistema

---

## GUI PyQt: estado atual

### Resumo

A GUI e a camada mais sofisticada do projeto em superficie de produto e, ao mesmo tempo, a mais fragil em complexidade acidental.

### Achados confirmados pelo laudo especializado

1. `gui\gui_ssa.py` ainda e um monolito relevante mesmo apos extracoes para mixins e modulos auxiliares.
2. Ha mais de uma estrategia de fallback/stub de Qt no projeto.
3. Ha forte uso de flags booleanas de reentrada, com risco de fragilidade em handlers.
4. Existem duplicacoes auxiliares entre workers e mixins.
5. Ha um risco de thread safety em torno do cache de `FilterWorker`.
6. Existe uma trilha paralela em `gui\tabs\` que parece tentativa nao integrada de limpar a arquitetura.

### Leitura tecnica importante

A GUI nao parece estar "mal feita" no sentido trivial. Ela parece resultado de varias rodadas de endurecimento em producao:

- workers
- cache
- retencao defensiva
- fallback headless
- tema
- filtros complexos
- detalhes/derivadas

O problema e outro: o volume de remendos corretos acumulados sem uma segunda rodada grande de consolidacao estrutural.

### Sintoma arquitetural

Quando um modulo continua centralizando wiring depois que mixins e submodulos ja nasceram, normalmente significa:

- o corte original dos modulos auxiliares foi mais tatico que arquitetural
- a "casca" nao foi afinada depois da extracao

### Leitura ainda mais dura

A GUI atual parece ter:

1. codigo produtivo em uso
2. camada de extração parcial para mixins/modulos
3. uma tentativa paralela de GUI mais limpa em `gui\tabs\`
4. multiplos fallbacks e stubs

Isso e tipico de sistema que acumulou varias ondas de "arrumar sem poder parar tudo".

Em outras palavras:

- nao falta capacidade tecnica
- falta uma rodada dedicada de consolidacao estrutural

---

## CLI: estado atual

### Resumo

`interface\cli.py` parece ser uma CLI rica e stateful, nao apenas um wrapper de comandos.

### Sinais positivos

- chama regra central compartilhada
- tem printers dedicados
- mantem experiencia interativa mais elaborada

### Sinais de debt

- arquivo unico ainda grande
- injecao manual de `sys.path`
- estado global de paginacao
- coexistencia de printer novo e fallback antigo

Isto sugere uma CLI madura funcionalmente, mas ainda pouco consolidada como arquitetura.

---

## Streamlit: estado atual

### Resumo

`dev_env\streamlit_app.py` e um frontend real, nao um simples demo.

### Sinais positivos

- reutiliza `core.app_logic`
- lida com cache
- usa import dinamico para sobreviver fora do runtime Streamlit

### Sinais de debt

- arquivo muito grande
- cache proprio com logica semelhante a outros caches do projeto
- copia de alguns helpers/utilitarios

Leitura: o Streamlit esta mais perto de "terceira interface de verdade" do que de "utilitario de dev".

---

## Integracao entre GUI, CLI e Streamlit

### O que parece bom

- o dominio de busca/filtro e razoavelmente compartilhado
- o dominio de importacao tambem aparece centralizado

### O que parece ruim

- cada interface ainda tem seu proprio estado de apresentacao, cache e wiring
- ha sinais de helpers duplicados e pequenos forks utilitarios
- o boundary entre "core puro" e "adaptacao de interface" ainda nao esta limpo

### Sintese

O projeto nao esta em tres implementacoes totalmente independentes do mesmo produto.

Mas tambem nao esta em um modelo "thin adapters over a clean domain".

Ele esta no meio do caminho:

- dominio parcialmente compartilhado
- apresentacao e cache parcialmente duplicados

---

## Banco, importacao e derivadas

### Estado observado

Esta parece ser a parte mais conscientemente tratada do sistema.

Sinais:

- docs vivos especificos para importacao e upsert
- camada `armazenamento\` relativamente fatiada
- pipeline de derivadas com contrato proprio

### Risco principal

O risco nao parece ser falta de regra, e sim espalhamento de orquestracao entre:

- `core\app_logic.py`
- `armazenamento\database.py`
- `database_optimized.py`
- `database_upsert_logic.py`
- `derivadas_sync.py`

Isto pode ser bom do ponto de vista de separacao, mas gera superficie cognitiva alta para onboarding e manutencao.

---

## Estado atual dos testes

### Sinais bons

- suite numerosa
- variedade de testes por dominio
- baseline recente do README aponta `993 passed, 4 skipped, 11 subtests passed`

### Sinais de cuidado

Nem todo arquivo em `tests\` parece teste de regressao de produto.

Exemplos suspeitos:

- `tests\debug_frankenstein.py`
- `tests\run_comprehensive_tests.py`
- `tests\automated_system_tests.py`
- `tests\performance_tests.py`

### Leitura preliminar desses arquivos

#### `tests\automated_system_tests.py`

Parece mais harness de sistema do que teste idiomatico de `pytest`.

Riscos:

- depende de arquivos reais em `docs_entrada`
- depende de banco real ou quasi real
- mistura criacao de ambiente, execucao e relatorio
- parece mais proximo de script operacional

#### `tests\performance_tests.py`

Parece benchmark manual/operacional, nao teste deterministico de regressao.

Riscos:

- mede memoria e CPU em runtime local
- depende de `psutil` e opcionalmente `memory_profiler`
- tende a produzir ruido entre maquinas

#### `tests\run_comprehensive_tests.py`

Parece orquestrador externo de suites, nao teste unitario.

Riscos:

- chama subprocessos
- gera relatorio markdown
- mistura smoke checks locais e verificacao de ambiente com "suite de testes"

Conclusao parcial:

O diretorio `tests\` provavelmente mistura pelo menos tres categorias:

1. testes reais de regressao
2. harnesses operacionais
3. scripts diagnosticos e benchmarks

Isso nao invalida a suite, mas aumenta o risco de inflar a contagem de testes com artefatos que deveriam morar em outra pasta.

### Achados mais objetivos sobre higiene da suite

#### 1. `tests\conftest.py` parece ter cicatriz de concatenacao

O review estatico apontou um shebang perdido no meio do arquivo. Isso e sinal classico de merge manual ou colagem de blocos heterogeneos. Mesmo que nao quebre o runtime, e um cheiro de manutencao.

#### 2. Existem arquivos em `tests\` que parecem scripts, nao testes `pytest`

Exemplos:

- `automated_system_tests.py`
- `run_comprehensive_tests.py`
- `performance_tests.py`
- `debug_frankenstein.py`

Esses arquivos:

- usam subprocesso
- criam relatorios
- medem ambiente local
- operam como harness manual

Interpretacao:

- isso pode ser util
- mas idealmente deveria estar separado de regressao automatica comum

#### 3. Parte da suite parece testar wrappers ou construtos artificiais

Exemplo confirmado:

- `_recreate_database_for_full_rescan` em `core\app_logic.py` e um wrapper trivial sobre `_rotate_database_for_full_rescan`
- `tests\test_app_logic_full_rescan_lock.py` foca nesse wrapper

Leitura tecnica:

- o teste nao esta necessariamente inutil
- mas o alvo testado nao e o lugar onde mora a maior parte da logica relevante

#### 4. Ha suspeita forte de arquivo gigante agregando demais

`tests\test_gui_filter_logic.py` sozinho ja merece auditoria especifica por blocos:

- cobertura util que deve ser preservada
- casos duplicados
- fixtures repetitivas
- cenarios synthetic demais
- responsabilidades demais no mesmo arquivo

### Leitura mais estrategica da suite

Hoje o diretorio `tests\` parece conter pelo menos cinco classes de artefato:

1. unitarios reais
2. testes de integracao reais
3. harnesses operacionais
4. benchmarks/performance
5. scripts de debug/diagnostico

Enquanto isso estiver tudo misturado sob o mesmo guarda-chuva, a "sensacao de cobertura" sera maior que a "clareza de cobertura".

---

## Tooling, build e operacao

### Dependencias

Ha coexistencia de:

- `pyproject.toml`
- `requirements.txt`
- `requirements_dev.txt`
- `requirements_ci.txt`
- outros requirements auxiliares no repo

Isto sugere compatibilidade gradual, nao uma stack totalmente consolidada em torno de uma unica estrategia.

### Observacoes preliminares

- `pyproject.toml` esta relativamente minimalista
- `requirements*.txt` estao mais detalhados
- ha chance de duplicacao documental entre grupos de dependencias e metadata moderna do projeto

### Build

Pelos arquivos e docs, o projeto convive com:

- PyInstaller
- Nuitka
- PyOxidizer

Se isso estiver mesmo ativo e nao apenas historico, a superficie de build do projeto e muito alta para um produto desse porte.

### Leitura tecnica sobre a superficie de build

Este ponto merece cuidado porque pode enganar:

- ter multiplos caminhos de build nao e automaticamente ruim
- mas cada empacotador extra aumenta matriz de falha, docs, scripts e suporte

Se PyInstaller, Nuitka e PyOxidizer estiverem todos realmente vivos, o projeto carrega:

- complexidade de bootstrap
- complexidade de path/runtime
- complexidade de suporte para bugs "so no build X"

Isto pesa especialmente num projeto que ja tem multiplos frontends.

---

## Debt estrutural e backlog de alto impacto

### Debt confirmado

1. decomposicao incompleta de `gui\gui_ssa.py`
2. decomposicao incompleta de `core\app_logic.py`
3. mistura de harnesses e testes de regressao na pasta `tests\`
4. coexistencia de codigo legado explicito no repo principal
5. caches e helpers potencialmente duplicados entre interfaces
6. existencia de frameworks e importers que parecem mais promessa do que runtime real
7. coexistencia de scripts operacionais dentro da pasta de testes
8. naming e contratos que por vezes sugerem comportamento maior do que a implementacao real entrega

### Debt fortemente provavel

1. fronteira imperfeita entre dominio puro e estado de interface
2. caminhos paralelos de configuracao e runtime frozen
3. modularizacao tatico-historica em vez de modularizacao orientada por dominio

### Debt que merece triagem antes de qualquer rewrite

1. codigo morto ou quase morto:
   - `core\handler_base.py`
   - `utils\enhanced_importer.py`
   - `utils\robust_importer_old.py`

2. debt por duplicacao:
   - filtros ASCII/logging
   - helpers de cache
   - helpers de path de destino

3. debt por mismatch entre nome e comportamento:
   - `auto_derivadas_sync_enabled`
   - `_recreate_database_for_full_rescan`
   - importer "enhanced" sem transformacoes reais

---

## Reimplementacao parcial ou total em Rust ou Zig

### Julgamento preliminar

Antes mesmo do estudo profundo fechar, a leitura tecnica inicial ja aponta:

#### Reescrever tudo em Zig

Probabilidade de bom custo-beneficio: baixa.

Motivos:

- pandas e ecossistema de dados sao ativos fortes do projeto atual
- GUI atual esta em PyQt6, com ecossistema maduro
- Zig ainda nao entrega a mesma produtividade em stack de dados de escritorio

#### Reescrever tudo em Rust

Probabilidade de bom custo-beneficio: baixa a media, dependendo do objetivo.

Motivos:

- mais plausivel que Zig para nucleos especificos
- menos plausivel para reescrever toda a UX atual rapidamente
- custo de reescrita de filtros, importacao Excel, GUI e packaging e alto

#### Reescrita parcial em Rust

Probabilidade de bom custo-beneficio: media, para partes certas.

Candidatos naturais:

- kernels de importacao pesada
- validacao/normalizacao intensiva
- reconciliacao de derivadas se houver ganho real
- utilitarios de performance/IO isolados

#### Permanecer em Python com refactor pesado

Probabilidade de melhor retorno imediato: alta.

Motivos:

- maior parte do valor do produto ja existe
- problema principal parece ser estrutura, nao inviabilidade da linguagem
- ha docs, testes e contratos que ja sustentam uma consolidacao incremental

### Estudo mais frio de viabilidade

#### Opcao 1 - manter Python e refatorar pesado

Veredito: caminho principal recomendado.

Motivos:

- a maior parte do valor do produto ja existe
- `pandas` nao e acessorio; ele e parte estruturante do pipeline
- PyQt6 continua sendo uma escolha pragmatica para esse tipo de desktop app
- a suite de testes e a documentacao viva reduzem risco de refactor incremental

O que isso exigiria:

1. decompor `gui\gui_ssa.py`
2. decompor `core\app_logic.py`
3. unificar logica de filtro
4. limpar frameworks mortos e duplicacoes
5. separar harnesses de testes da regressao real

#### Opcao 2 - Rust parcial

Veredito: condicional, para nucleos muito especificos.

Casos que fazem algum sentido:

- algum kernel pesado de derivadas, se metricas reais provarem gargalo
- alguma etapa de importacao/normalizacao se houver ganho mensuravel
- possivel aceleracao do Excel reader por backend nativo, em vez de reescrever o app

Ponto importante:

- Rust parcial so vale onde o gargalo e comprovado
- nao vale como fuga abstrata da complexidade atual

#### Opcao 3 - Rust total

Veredito: anti-recomendado no estado atual.

Motivos:

- o bloqueio principal nao e "Python lento"
- o bloqueio principal e consolidacao estrutural
- reescrever toda GUI e UX de escritorio custaria caro demais
- a paridade funcional demoraria muito

#### Opcao 4 - Zig parcial

Veredito: anti-recomendado.

Motivos:

- ecossistema fraco para esse tipo de aplicacao
- interop com Python pior que Rust
- pouco beneficio frente ao custo de integracao

#### Opcao 5 - Zig total

Veredito: totalmente anti-pragmatico para este projeto.

Motivos:

- GUI
- stack de dados
- Excel
- ergonomia de produto
- custo de ecossistema

### Matriz resumida de decisao

| opcao | custo | risco | aderencia ao produto atual | retorno esperado |
| --- | --- | --- | --- | --- |
| Python + refactor | medio | baixo | alto | muito alto |
| Rust parcial | medio | medio | medio | situacional |
| Rust total | muito alto | muito alto | baixo | duvidoso |
| Zig parcial | alto | alto | muito baixo | baixo |
| Zig total | extremo | extremo | muito baixo | muito baixo |

### Recomendacao honesta

Se o objetivo e entregar produto melhor:

- primeiro: refactor serio em Python
- depois: profiling real
- so depois: avaliar Rust em pontos cirurgicos

Se o objetivo for "reescrever para sentir que agora esta limpo", o risco de perder anos e terminar com produto pior e alto.

---

## Recomendacoes por horizonte

### Horizonte 1 - consolidacao sem reescrita

1. cortar `gui\gui_ssa.py` por fronteiras reais de responsabilidade
2. separar `core\app_logic.py` em:
   - import pipeline
   - search/filter engine
   - facades publicas pequenas
3. separar `tests\` em:
   - regressao
   - benchmark
   - harness operacional
   - scripts diagnosticos
4. mover legados explicitos para area arquivada/nao-runtime
5. podar codigo morto ou framework morto antes de qualquer novo modulo
6. renomear funcoes/flags cujo nome hoje promete mais do que o comportamento entrega

### Horizonte 2 - endurecimento da plataforma

1. padronizar caches compartilhaveis
2. reduzir helpers duplicados
3. unificar fallback/stub de Qt
4. reduzir estados globais e side effects de import
5. separar de vez runtime, harness operacional e ferramentas de auditoria

### Horizonte 3 - migracao seletiva

1. medir hotspots reais de CPU/IO
2. isolar funcoes elegiveis para Rust
3. manter UI em Python enquanto dominio e consolidado
4. avaliar backend de leitura Excel mais rapido antes de qualquer rewrite amplo

### Horizonte 4 - replatforming radical

Somente considerar depois de:

- fatiar o dominio
- provar hotspots reais
- estabilizar contratos
- separar debt estrutural de comportamento de produto

---

## Apontamentos ainda em aprofundamento

Blocos ainda sendo aprofundados nesta auditoria:

- leitura do laudo de qualidade/codigo morto do agente de review
- estudo tecnico comparando Rust parcial/total e Zig parcial/total
- triagem mais fina dos testes para separar alto valor de baixo valor
- levantamento mais detalhado de arquivos pequenos demais ou fragmentados demais
- levantamento de duplicacoes concretas adicionais entre GUI, Streamlit e CLI
- releitura do que `explore-codebase` encontrou para comparar com a auditoria principal

---

## Conclusao parcial

O projeto nao pede uma reescrita total por desespero tecnico. O que ele pede, primeiro, e uma consolidacao estrutural dura do codigo Python que ja existe.

Hoje a fotografia mais honesta parece ser esta:

- dominio de negocio parcialmente bem compartilhado
- camada de banco mais madura que a camada de interface
- GUI muito poderosa, mas com acoplamento e volume acumulados
- Streamlit e CLI reais, nao cascas triviais
- suite de testes grande, porem provavelmente heterogenea demais
- residuos legados e ferramentas auxiliares misturados ao repo principal

A pergunta certa ainda nao e "vamos reescrever em Zig ou Rust agora?".

A pergunta certa e:

"qual parte do sistema esta realmente pronta para ser isolada, medida e substituida sem destruir o que ja funciona?"

Este documento vai continuar sendo expandido nas secoes acima.
