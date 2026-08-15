# SSA Consulta Rapida v4.47

Release estavel atual: `v4.47`.
Tag anterior: `v4.46`.
Publicacao: GitLab e Bitbucket a partir da branch `dev`.

Notas da release: [docs/RELEASE_NOTES_v4.47.md](docs/RELEASE_NOTES_v4.47.md)

## Current Truth (2026-08-09)

- Estado operacional:
  - metadata ativa: `4.47`
  - release estavel atual: `v4.47`
  - tag anterior: `v4.46`
  - branch `dev` inclui ciclo tri-state dos atalhos de situacao e indicador `...` para multiplos setores executores
  - mapa de remotos: `origin` = GitLab, `bitbucket` = Bitbucket, `gh` = GitHub
  - `dev`, `origin/dev` e `bitbucket/dev` ficam sincronizados por politica de commit do projeto; `git pull` padrao usa `origin/dev`
  - o HTTP 403 por conta suspensa afeta somente `gh`; nao bloqueia GitLab nem Bitbucket
  - docs centrais de import/upsert seguem alinhados com o contrato runtime atual
  - grupos criticos de banco, importacao, release, filtros, nullable e cache estao verdes no Windows nativo
  - `uv lock --check` e `pip-audit` nao reportam vulnerabilidade conhecida; suite consolidada, scanners e build real serao registrados antes da tag
  - banco real passou integridade SQLite, schema funcional e consistencia de dados
  - o harness de `tests/test_gui_filter_logic.py` agora isola e restaura o lifecycle global de workers aposentados por teste, sem vazar estado entre casos
  - a v4.47 nao muda schema, operadores centrais de filtro, layout ou posicao de controles
- Contrato de update por SSA (resumo):
  - `STE` e `SCA` no banco sao imutaveis para update
  - usa timestamp de snapshot (`data_planilha`/`data_arquivo_origem`/nome do arquivo) antes de olhar `data_cadastro`
  - se o arquivo novo tem contexto mas nao tem timestamp confiavel, update e bloqueado (insert-only)
  - importacao explicita e ordenada por data de arquivo (antigo -> novo)
  - `data_cadastro` fica como criterio auxiliar/tie-break
- Slices recentes apos o sprint GUI inicial:
  - `02ec4a30` `DOC_SYNC: add ultra technical audit report`
    - publicou `docs_saida/ULTRA_AUDITORIA_TECNICA_REPO_20260330.md` para continuidade entre maquinas
  - `b7af8aef` `STABILITY_PATCH: support non-text search columns`
    - `filter_dataframe()` passou a aceitar `search_columns` numericas/datetime sem retornar vazio por exclusao precoce de dtype
  - `d6fbb4fe` `STABILITY_PATCH: unify advanced filter state`
    - `setor_executor` agora sincroniza estado aplicado entre filtro rapido e painel avancado
    - materializacao de `solicitante` aceita alias `responsavel_solicitante`
    - prefixo de area/setor de responsaveis deixou de depender apenas do subconjunto filtrado
- Sprint GUI entregue nesta frente:
  - implementacao runtime consolidada nos commits `b343c621` e `07ebfe1d`
  - `[f]` no cabecalho agora sincroniza filtros por coluna e filtros avancados
  - resumo `Filtros ativos` deixou de duplicar entradas equivalentes
  - caixa `Filtros ativos` ganhou borda destacada e texto em negrito quando ha filtro ativo
  - macro `Baixar` passou a excluir `SAD` alem de `SCA`, `SES` e `STE`
  - o prompt `Filtrar "nome da coluna"` ganhou hint `Aceita termo, !termo para exclusao` e largura minima padronizada
  - `update_derivadas_from_sources()` saiu do thread principal em runtime normal
  - botao `Abrir SAM`
  - caixa nova `Status: X de Y SSAs` ficou separada da caixa operacional
  - `Semana Atual` ficou recentralizado entre os controles da barra superior
  - o `#` da lista abre a SSA no SAM externo
  - o detalhe da SSA expande `situacao` para `SIGLA - descricao`
  - o numero da SSA no detalhe copia para a area de transferencia por duplo clique
  - a area de derivadas ficou mais larga e passou a usar arvore textual com `numero (STATUS)`
  - `load_other_database()` passou a validar o arquivo em background no runtime normal
  - dialogo de detalhes agora tem aba dedicada `Arvore`:
    - metade superior com subabas `Grafo`, `Arvore` e `Mermaid`
    - `Grafo` renderiza visualmente as relacoes de derivadas (SVG)
    - metade inferior continua com os detalhes da SSA selecionada
    - implementacao em codigo: commit `07ebfe1d`
    - historico: este item estava como refinamento e foi promovido para entrega por comando explicito no ciclo atual
- Hotfix de banco entregue nesta frente:
  - upsert nao-complementar preserva `STE` e `SCA` como estados terminais imutaveis
  - caso real protegido: manter `STE` e bloquear sobrescrita para `ADM`, inclusive quando `data_cadastro` empata
  - tie-breaker por ranking de `situacao` no merge de mesma data
  - regressao coberta em testes de upsert e importacao explicita
- Follow-up apos o sprint GUI:
  - reproduzir de forma dirigida o caso `svp-03` / SSA `202604849`
  - desenhar patch minimo para historico de filtros com `undo` e `redo`
  - agrupar ajustes pontuais de ordem/labels sem reabrir layout geral
  - confirmar suporte minimo para drag de cabecalho sem refactor amplo
  - continuar a varredura de chamadas pesadas restantes na thread principal
- Validacao atual:
  - baseline amplo registrado em `2026-03-30`:
    - `uv run --python 3.13 python -m py_compile` em tracked Python -> verde
    - `uv run --python 3.13 ruff check .` -> verde
    - `uv run --python 3.13 ty check` -> verde
    - `uv run --python 3.13 python -m pytest -q tests` -> `993 passed, 4 skipped, 11 subtests passed`
  - validacao focada do hotfix de busca nao textual:
    - `py_compile`, `ruff`, `ty` -> verdes
    - `pytest -q tests/test_app_logic_filter_contract.py` -> `20 passed`
  - validacao focada do patch de sincronizacao de filtros:
    - `py_compile`, `ruff`, `ty` -> verdes
    - `pytest -q tests/test_gui_filter_logic.py -k "...executor...responsavel..."` -> `8 passed`
- Contrato atual que nao deve ser reaberto:
  - `numero_ssa`, `derivada_de` e `numero_ssa_relacionada_*` seguem canonicos em texto
  - strings `"<NA>"`, `"None"`, `"nan"`, `"null"` e equivalentes nao devem ser persistidas como texto literal no banco
  - a busca textual nao usa nem documenta operadores textuais legados
- Prioridades reais antes da proxima tag:
  - `P0`: manter fechado o contrato de `numero_ssa` sem reabrir truncagem, heuristica de exibicao ou teste synthetic
  - `P0`: manter fechado o contrato anti-downgrade de `situacao` para empate de `data_cadastro`
  - `P1`: reproduzir o caso `svp-03` / SSA `202604849` com evidencia tecnica
  - `P1`: definir historico de filtros para `undo` e `redo`
  - `P1`: fechar ajustes pontuais de ordem/labels sem reabrir layout geral
  - `P1`: validar habilitacao de drag de cabecalho de colunas
  - `P2`: revisar hotspots restantes da thread principal apos o sprint GUI
  - `P2`: decidir a paridade CLI vs GUI para diff/full import e discovery
  - `P2`: tratar hardening residual de rollback/error boundary em `database*`
  - `P2`: manter somente documentacao operacional publica necessaria no repositorio
- Docs vivos para continuidade:
  - `AGENTS.md` -> regras, proibicoes, processo e politicas obrigatorias
  - `docs/ARCH_DB_UPSERT.md` -> ordem real de decisao no update por `numero_ssa`
  - `docs/ARQUITETURA_IMPORTACAO.md` -> discovery/import + metadados de snapshot
  - `docs/TROUBLESHOOTING_IMPORTACAO.md` -> diagnostico pratico para regressao de estado/import
  - `docs/README.md` -> indice da documentacao viva
- Estado de review auxiliar:
  - configuracao MCP local do Kluster foi corrigida para `pnpm.CMD dlx ... --server=https://api.kluster.ai`
  - timeout eventual de `manualCheck` deve ser tratado como bloqueio do review remoto, nao como bug do repo nem review clean
- Primeira acao obrigatoria na proxima conversa:
  - revisar o estado atual do PR `dev -> main` e os checks mais recentes
  - começar por `svp03-targeted-repro` antes de abrir outro patch de filtros
  - revalidar se existe residuo local antes de abrir frente nova
  - referencias operacionais:
    - `.github/instructions/kluster-code-verify.instructions.md`
    - `docs/CCR_LLM_PROVIDERS_SETUP.md`

## Historical Snapshot (2026-03-23 19:01 -0300)

- Snapshot historico preservado; nao representa o baseline ativo.
- Commits mais recentes relevantes para o estado daquele fechamento:
  - `d5a9e137` `HOTFIX_BLOCKER: fix nullable display and filter contract`
  - `25c64c58` `STABILITY_PATCH: close residual nullable filter paths`
- Contrato de dados naquele ponto:
  - `numero_ssa`, `derivada_de` e `numero_ssa_relacionada_*` sao identificadores canonicos em texto.
  - semanas e contadores de reprogramacao voltam do banco como nullable ints.
  - `pd.NA` nao deve mais vazar como `"<NA>"` em exibicao, filtro por coluna, filtros avancados nem no sort de `num_reprogramacoes`.
- Estado operacional daquele ponto:
  - branch alvo de estabilizacao: `dev`
  - working tree local pode continuar sujo por arquivos fora de escopo (`.python-version`, `config/*`, `data/ssas.db`, `docs_entrada/*`, backups locais)
  - diagnostico local do full rescan fechado sem editar runtime:
    - discovery atual considera `.xlsx` na raiz de `docs_entrada` e, opcionalmente, em `processadas/`
    - nesta maquina: `489` `.xlsx` elegiveis na raiz, `0` em `processadas/` e `135` `.xls` fora do pipeline principal
    - se o desktop de trabalho ficou preso em `439`, a primeira hipotese agora e elegibilidade/discovery, nao cache/hash viciado

## Release v4.47 (2026-08, stable)

### Destaques
- Atalhos de situacao alternam entre inclusao, exclusao (`!STATUS`) e estado neutro.
- Caixa rapida de setor executor mostra `...` quando mais de um setor esta ativo.
- Barra rapida, filtros ativos, filtros por coluna e painel avancado compartilham o mesmo estado aplicado.
- Cache de busca normalizada permanece ativo entre atualizacoes apenas visuais e reduz reprocessamento de filtros.
- Mascaras nullable de busca e faixa nao propagam `pd.NA` para combinacoes booleanas.
- Recovery preserva tabela SSA canonica, colunas funcionais, tabelas auxiliares e dados presentes em WAL ativo.
- Importacao com todas as linhas rejeitadas possui classificacao deterministica.
- `pip-audit` nao reporta vulnerabilidades conhecidas no lock atual; nenhum salto de dependencia foi feito sem necessidade reproduzida.
- Build oficial Windows AMD64 continua condicionado ao clone nativo, pacote PyInstaller `onedir`, banco externo unico e smoke funcional registrado no relatorio JSON.
- `release.ps1` e exclusivo do Windows; Debian usa clone Linux nativo e `release.sh`. WSL fica restrito ao CodeRabbit em clone proprio.
- Sem mudanca de schema, operador central, layout ou posicao de controles.

## Baseline v4.45 (2026-07, historical)

### Destaques
- Metadata local e docs ativos foram promovidos para `4.45` como inicio do ciclo de hardening PyQt6.
- A tag local `v4.45` marca o inicio do refactor; `v4.44` permanece como baseline estavel anterior.
- Plano detalhado: `docs/HARDENING_PYQT6_V4_45_PLAN.md`.
- A ultima tag publicada remota continua sendo `v4.36` ate existir ciclo de release remoto explicitamente aprovado.

## Baseline v4.44 (2026-07, historical)

### Destaques
- Metadata local e docs ativos foram promovidos para `4.44`.
- A tag local `v4.44` marca a baseline apos os fixes de validacao dos gates locais.
- A ultima tag publicada remota continua sendo `v4.36` ate existir ciclo de release remoto explicitamente aprovado.

## Baseline v4.43 (2026-06, historical)

### Destaques
- Metadata local, docs ativos e expectativas de empacotamento foram promovidos para `4.43`.
- A tag local `v4.43` marca a baseline imediatamente anterior aos slices funcionais de filtros/cache/GUI.
- A ultima tag publicada remota continua sendo `v4.36` ate existir ciclo de release remoto explicitamente aprovado.

## Baseline v4.42 (2026-04, historical)

### Destaques
- Nullable dtypes no readback agora estao estabilizados sem regressao visual:
  - `pd.NA` tratado como vazio em exibicao
  - filtros por coluna e filtros avancados sem coercao textual crua nos caminhos centrais
  - sort de `num_reprogramacoes` alinhado com nullable values
- Auditoria residual de filtros avancados fechada:
  - derivadas terminais ignoram `derivada_de` nullable/vazia
  - subset dependente de setor nao materializa `"<NA>"`
- Diagnostico de importacao/rescan atualizado:
  - `full rescan` hoje nao e recursivo sobre qualquer subpasta arbitraria da raiz
  - `.xls` legado continua contabilizado como ignorado, nao como candidato principal de importacao
  - regressao ampla de importacao, rescan, GUI lateral e contratos de nullable ficou verde; a limitacao antiga de harness em `tests/test_gui_filter_logic.py` foi fechada com reset/restore explicito do estado global de lifecycle
- README revisado com secoes obrigatorias (`Instalacao`, `Uso`, `Testes`) e alinhamento com a versao atual.
- Changelog completo (`docs_saida/CHANGELOG_IMPLEMENTACOES.md`) recriado para cobrir entregas de 2025-07/2025-08, incluindo ajustes de GUI e `column_priority.json`.
- Remocao de arquivos vazios herdados de sessoes de IA para evitar falso-positivo em verificacoes de documentacao.
- Baseline de documentacao atualizado para 4.42.
- Regras de tema aplicadas de forma geral para popups/menus/checks e textos de selecao, sem depender de casos especificos por tema.
- Lock unico de altura para os 3 blocos inferiores (detalhes, filtros avancados, filtros por coluna), com gatilho em init, troca de aba, resize e rebuild de filtros por coluna.
- Regressao nova: teste para garantir altura sincronizada unica apos resize.
- Regressao de filtros por coluna coberta por novos testes focados em:
  - menu de adicionar filtro de coluna (lista completa + exclusao de aliases legados invalidos);
  - clear-all restaurando defaults e linhas ocultas;
  - presenca de botoes Aplicar/Ocultar nas linhas default.
- Matriz de compatibilidade Python concluida no ciclo atual:
  - 3.10.18: pass
  - 3.11.14: pass
  - 3.12.11: pass
  - 3.13.12: pass

### Instalar uv (recomendado)
```bash
# macOS / Linux (curl)
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS / Linux (wget)
wget -qO- https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows PowerShell / pwsh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Execucao rapida com uv (recomendado)
```bash
# criar/sincronizar ambiente
uv venv
uv sync

# definir runtime (fallback: 3.12 -> 3.11 -> 3.10)
PY_RUNTIME=3.13

# executar GUI
uv run --python $PY_RUNTIME main.py --gui

# executar CLI
uv run --python $PY_RUNTIME main.py

# executar Streamlit
uv run --extra web --python $PY_RUNTIME main.py --streamlit
```

Fallback quando 3.13 nao estiver disponivel: 3.12, depois 3.11, depois 3.10.
`requirements*.txt` permanecem para compatibilidade em ambientes sem uv.

### Windows 11: rodar e gerar instalador
Execute no PowerShell aberto na raiz do repositorio.

```powershell
# Instalar ferramentas base
winget install --id Git.Git -e
winget install --id JRSoftware.InnoSetup -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Rodar a aplicacao
uv sync
uv run --python 3.13 main.py --gui

# Validar plano sem compilar
.\release.ps1 -Target windows -Backend pyinstaller -IncludeRuntimeDb -DryRun -Yes

# Gerar executaveis, ZIP e instalador Windows AMD64
.\release.ps1 -Target windows -Backend pyinstaller -IncludeRuntimeDb -Yes
```

Saidas esperadas:
- pacotes Windows: `builds\packages\windows_amd64\`
- pacote distribuivel adicional: `dist_packages\`
- relatorio de release: `builds\reports\release_report_windows_amd64.json`

### Debian: rodar e gerar pacote
Execute no terminal Bash aberto na raiz do repositorio.

```bash
# Instalar ferramentas base
sudo apt-get update
sudo apt-get install -y git curl build-essential python3 python3-venv python3-dev patchelf dpkg-dev
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Rodar a aplicacao
uv sync
uv run --python 3.13 main.py --gui

# Validar plano sem compilar
./release.sh --target debian --dry-run --yes

# Gerar executaveis e pacote .deb Debian AMD64
./release.sh --target debian --yes
```

Saida esperada:
- pacotes Debian: `builds/packages/debian_amd64/`

Notas de release:
- `release.ps1` e `release.sh` sao os wrappers publicos; scripts em `dev_env/build/` sao implementacao interna.
- Cada wrapper deve rodar em clone e venv nativos do proprio host; nao compartilhar checkout Windows com WSL/Linux.
- O build de release exige workspace limpo para evitar artefato stale.
- O fluxo de release roda smoke funcional de importacao no executavel gerado e bloqueia falha antes de publicar artefato.

### Ambiente com pyenv/direnv (fallback de compatibilidade, sem substituir uv)
```bash
# selecionar versao python do projeto
pyenv local 3.13.12

# carregar variaveis do direnv (quando configurado)
direnv allow

# executar no venv local existente (modo manual)
uv run --python .venv/bin/python main.py --gui
```

### Documentacao tecnica atual (v4.47)
- Algoritmo do layout dinamico (4 colunas):
  - `docs/FILTER_TAB_OPTIMIZATIONS.md` (secao v4.24 no topo)
- Regras gerais de GUI em PyQt6:
  - `docs/GUI_PYQT6_REGRAS_GERAIS.md`

---
## Historico (versoes anteriores)
As notas antigas permanecem abaixo para referencia e auditoria tecnica.

### Otimização de Requirements (2025-12-05)
- **Objetivo:** Reduzir redundâncias e melhorar manutenção
- **Ações realizadas:**
  - Consolidado dependências duplicadas entre arquivos
  - Removidas dependências de runtime de arquivos de CI/CD
  - Estrutura final com 5 arquivos versionados no repositorio
  - arquivos operacionais: requirements.txt, requirements_dev.txt, requirements_build.txt, requirements_ci.txt
  - requirements_clean.txt mantido apenas como arquivo documental
- **Impacto:**
  - Redução de 40% no número de arquivos de requirements
  - Eliminação de dependências duplicadas
  - Maior clareza na separação de responsabilidades
- **Estrutura de Requirements (Otimizada):**
  - **requirements.txt** - Dependências de runtime essenciais (PyQt6, pandas, openpyxl, tabulate)
  - **requirements_dev.txt** - Ferramentas de desenvolvimento (pytest, flake8, black, mypy, pre-commit)
  - **requirements_build.txt** - Ferramentas de build (pyinstaller, pillow, cairosvg, pywin32)
  - **requirements_ci.txt** - Ferramentas de CI/CD (pytest, flake8, black, mypy, pre-commit, pyinstaller)
  - **requirements_clean.txt** - Arquivo documental (não utilizado para instalação)

### Comandos de Instalação (Atualizados)
```bash
# Runtime (Essencial)
uv pip install --python 3.13 -r requirements.txt

# Desenvolvimento
uv pip install --python 3.13 -r requirements.txt -r requirements_dev.txt

# Build/Empacotamento
uv pip install --python 3.13 -r requirements.txt -r requirements_build.txt

# CI/CD
uv pip install --python 3.13 -r requirements.txt -r requirements_ci.txt
```

### Resultados esperados
- Pipelines de qualidade deixam de falhar por falta de seções obrigatorias no README.
- Testes `test_docs_and_priority.py` voltam a passar com o changelog reconstruido.
- Repositorio mais enxuto, sem documentos vazios que confundiam revisores.

## Release v4.10.0 (2025-11)

### Contexto historico
Na serie 4.0 ocorreram falhas em dois pontos principais:
- Filtros: divergencia entre GUI CLI e streamlit em combinacoes de filtros e negativos, alem de substituicao visual que induzia interpretacao incorreta.
- Temas: papeis de cores para quadros indicadores e tags aplicados de forma inconsistente em alguns sistemas.

### O que foi corrigido
- Unificacao do parsing de filtros entre todas as interfaces sem alteracao visual ambigua
- Invalidacao correta de cache quando entram combinacoes de filtros ou negativos
- Ajuste de ordem de normalizacao evitando estados intermediarios incoerentes
- Mapeamento central de chaves de tema para quadros indicadores e tags

### Resultados esperados
- Mesmos resultados de busca em CLI GUI e streamlit
- Negativos honrados nas combinacoes suportadas
- Temas aplicados de forma previsivel em plataformas suportadas

### Observacoes
- Sem alteracao de schema
- Sem mudanca de formatos de exportacao

## Politica de Remocao de Artefatos de IA / Sessoes

Este repositorio foi sanitizado para remover documentos de sessoes, planos de acao automatizados, relatorios gerados por modelos (Claude, Gemini, Copilot, etc.) e historicos de conversas. Esses arquivos agora sao mantidos apenas localmente em `local_ai_private/` (gitignored) para referencia pessoal e nunca devem ser cometados.

Diretrizes:

- Nao adicionar novamente logs de conversa, relatorios de “AI Assistant”, planos de refatoracao automatizados ou snapshots de sessao.
- Se for realmente necessario manter um registro tecnico, sintetize em documentacao neutra sem autoria de modelo ou linguagem de sessao.
- Scripts de verificacao e codigo fonte permanecem; apenas artefatos narrativos de IA foram excluidos.
- A lista de arquivos banidos esta ancorada em `.gitignore` (secao Local AI / TODO) para evitar regressao.

Beneficios:

- Reduz ruido e volume de documentacao nao essencial.
- Minimiza risco de vazamento acidental de chaves ou contexto sensivel em logs extensos.
- Mantem foco em documentacao tecnica estavel (README, guias, schemas, changelogs tecnicos).

Em caso de duvida, tratar o conteudo como temporario e armazenar em `local_ai_private/`.

# SSA Consulta Rapida v4.0.3

## Release v4.0.3 (2025-11)

Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para decisoes e linha do tempo tecnica.
- Fixed filter behavior from release 4.x series
- GUI filter logic stabilized
- Column filters working correctly
- Test suite updated and passing

- **Non-destructive wrappers (v2)**: added under `scripts/` as `run_pytest_with_timeout_v2.py` and `run_pytest_stream_and_log_v2.py`. They are additive (do not replace existing scripts) and contain improved Windows/Unix process-tree termination fallbacks and stable imports.
- **pwsh detection helper**: `scripts/pwsh_discovery.py` centralizes discovery of `pwsh`/`powershell` executables across common paths, PATH, and workspace `.vscode` settings.
- **Logs and local docs**: runtime logs and notas locais podem existir em `local_ai_private/` (diretorio gitignored, opcional por maquina).
- **Usage examples**:
	- Run with a 10s timeout and write log:
		uv run --python 3.13 scripts/run_pytest_with_timeout_v2.py --test tests/test_terminal_integration.py --timeout 10
	- Stream live output and save log:
		uv run --python 3.13 scripts/run_pytest_stream_and_log_v2.py --test tests/test_terminal_integration.py --timeout 10

If streaming is not available in your shell, the instructions file shows a PowerShell `Tee-Object` alternative to both print and save output.
## Previous Release v4.0.0 (2025-09) - Performance Improvements

###  **GANHOS DE PERFORMANCE MENSURADOS:**
- **Imports:** 80-90% mais rapidos com modo otimizado padrao
- **GUI Filters:** 2.88x a 102,900x speedup com cache LRU multi-threaded
- **Streamlit:** 3,977x speedup medio com cache TTL
- **Database Queries:** 5-20x mais rapidas com 6 indices estrategicos
- **Sistema de Logging:** Robusto com metricas automaticas de performance

###  **OTIMIZACOES IMPLEMENTADAS:**

#### **Phase 1: Fundamentos**
- - Main.py com modo `--optimized` por padrao
- - `core/app_logic.py` - `filter_dataframe` otimizado (1.96x speedup)
- - 6 indices estrategicos no SQLite para queries 5-20x mais rapidas

#### **Phase 2: GUI Inteligente**
- - Sistema de cache LRU com `FilterWorker` multi-threaded
- - Debounce 250ms para evitar consultas excessivas
- - Cache hit rate 75%+ em uso normal
- - Performance: 2.88x a 102,900x speedup dependendo do cenario

#### **Phase 3: Streamlit Aprimorado**
- - `StreamlitFilterCache` com TTL e metricas detalhadas
- - Interface sidebar reorganizada com progress bars
- - Cache configuravel (100 entradas, 300s TTL por padrao)
- - Performance: 3,977x speedup medio

#### **Phase 4: Sistema de Logging Robusto**
- - `utils/robust_logging.py` - Sistema completo com `PerformanceMetrics`
- - `config/logging.json` - Configuracao centralizada multi-handler
- - Integracao completa em main.py, GUI e Streamlit
- - Logging estruturado JSON + rotacao automatica
- - Metricas de performance em tempo real

## Notas de Padronizacao e Governanca (2025-09)

Foram aplicadas melhorias recentes de qualidade de codigo:

- Reducao de numeros magicos: constantes adicionadas em `armazenamento/database.py` (`NUMERO_SSA_LEN`, limites de ano, `MAX_TEXT_LEN`, etc.).
- Normalizacao de `numero_ssa`: funcoes consolidadas e uso consistente das regras com validacao defensiva.
	 - Regra estrita atual (camada core):
		 * Referencia operacional atual: 9 digitos (`YYYYXXXXX`) nas planilhas validadas do fluxo principal.
		 * Ano inicial entre 1980 e 2050.
		 * Valores com letras ou simbolos fora de `[0-9 -]` sao rejeitados.
			 * Hifen opcional e aceito apenas em formato `YYYY-XXXXX` quando os 5 digitos finais NAO sao todos identicos.
				 - Exemplo aceito: `2025-12345` → `202512345`.
				 - Exemplo rejeitado: `2025-22222` (marcado como invalido e filtrado no importador).
			 * No formato sem hifen, a checagem de repeticao dos 5 ultimos digitos nao e aplicada por compatibilidade historica.
			 * Valores longos e compatibilidades legadas nao devem ser usados como referencia de export atual sem evidencia de planilha real.
	 - Fachada publica retrocompativel:
		 * `normalize_numero_ssa(...)` agora segue o mesmo contrato canonico de 9 digitos.
		 * Entradas curtas, letras e sobrecomprimento nao viram SSA valida por exibicao.
		 * A referencia operacional validada nesta rodada continua sendo `202600654` e demais SSAs reais de 9 digitos.
	 - Testes que cobrem as regras: `tests/test_numero_ssa_normalization_cross.py` e `tests/test_numero_ssa_hyphen_repetition.py`.
- Importacao externa pela GUI:
	 - `Importar XLS/XLSX externo` aceita um ou mais `.xlsx` de qualquer pasta escolhida pelo usuario.
	 - Cada arquivo selecionado e copiado com seguranca para `docs_entrada` quando ainda estiver fora da pasta.
	 - Se o arquivo ja estiver em `docs_entrada`, ele nao e recopiado.
	 - A aplicacao no banco ocorre somente para os arquivos explicitamente selecionados nessa acao.
- Linhas longas (>100 colunas) quebradas para melhorar leitura e conformidade com lint.
- Sistema de logging robusto com metricas automaticas de performance.
- Cache systems inteligentes para GUI e Streamlit com ganhos massivos de performance.

Para auditoria de termos sensiveis existe um scanner interno (script em `scripts_manutencao/`) configurado para varrer apenas diretorios relevantes e ignorar arquivos grandes de dados.

Nota de manutencao: durante a limpeza recente de emojis em documentacao e arquivos de texto, os arquivos originais foram preservados em `.emoji_backups/` na raiz do repositorio. Use essa pasta para restaurar qualquer arquivo caso necessario.
# Modularizacao do Modulo de Banco de Dados (2025-09)

Para reduzir complexidade ciclomatica e facilitar testes focados, o monolito `armazenamento/database.py` foi dividido em modulos especializados mantendo a API publica retrocompativel (tests continuam importando de `armazenamento.database`).

Componentes extraidos (estado atual):
- `database_upsert_logic.py`: preparacao e logica de upsert (merge condicional, modos complementar vs. simples, normalizacao de datas) – expoe `prepare_dataframe_for_upsert`, `apply_column_whitelist` e `insert_dataframe_with_smart_upsert_impl`.
- `database_integrity.py`: verificacao e reparo (`verify_database_integrity`, `repair_database_if_needed`).
- `database_validation.py`: validacao pre-insercao (`validate_dataframe_before_insert`).
- `numero_ssa_utils.py`: fonte unica para normalizacao de `numero_ssa` (strict, storage textual canonico, helper numerico interno legado e batch dataframe).

No arquivo `database.py` permanecem apenas:
- Conexao (`get_db_connection`) e inicializacao (`initialize_database`).
- Facades publicas: `insert_dataframe_to_db`, `insert_dataframe_with_smart_upsert`.
- Reexports simples de normalizacao (`normalize_numero_ssa`, `normalize_numero_ssa_dataframe_storage` e alias de nome `normalize_numero_ssa_dataframe`, todos com retorno textual canonico).
- Delegacoes finas de integridade/validacao (sem wrappers intermediarios de upsert internos removidos na etapa de reducao de complexidade).

Melhorias adicionais nesta etapa:
- Remocao de wrappers `_prepare_dataframe_for_upsert`, `_perform_upsert`, `_insert_dataframe_with_smart_upsert_impl` redundantes.
- Unificacao do filtro de colunas (`SSA_ALLOWED_COLUMNS`) em helper reutilizavel (`apply_column_whitelist`).
- Reducao liquida de linhas mantendo cobertura comportamental (testes passam / legado preservado).

Proximos passos sugeridos (nao bloqueantes):
1. Adicionar testes unitarios especificos para `apply_column_whitelist` e datas limitrofes de normalizacao.
2. Considerar moving parsing de datas para util dedicado se expandir.
3. Avaliar medicao de performance (perfil leve) em lotes grandes (>50k linhas) para ajustar `chunksize` dinamicamente.

Essa secao reflete o estado pos-limpeza para orientar futuros mantenedores.
# SSA_Consulta_Rapida (snapshot historico legado)

Versao de referencia deste bloco historico: 3.11

##  **NOVIDADES v4.0.0 - PERFORMANCE MASSIVAMENTE OTIMIZADA**

###  **OTIMIZACOES DE PERFORMANCE IMPLEMENTADAS:**

#### ** Phase 1: Fundamentos (90% mais rapido)**
- Main.py com modo `--optimized` **por padrao**
- `filter_dataframe` otimizado com **1.96x speedup**
- **6 indices estrategicos** no banco para queries **5-20x mais rapidas**

#### ** Phase 2: GUI Inteligente (2.88x-102,900x speedup)**
- Sistema de **cache LRU multi-threaded** com `FilterWorker`
- **Debounce 250ms** para evitar consultas excessivas
- Cache hit rate **75%+** em uso normal
- Performance: **2.88x a 102,900x speedup** dependendo do cenario

#### ** Phase 3: Streamlit Aprimorado (3,977x speedup)**
- `StreamlitFilterCache` com **TTL e metricas detalhadas**
- Interface sidebar reorganizada com **progress bars**
- Cache configuravel (100 entradas, 300s TTL)
- Performance: **3,977x speedup medio**

#### ** Phase 4: Sistema de Logging Robusto**
- `utils/robust_logging.py` com `PerformanceMetrics` automatico
- Configuracao centralizada em `config/logging.json`
- **Logging estruturado JSON** + rotacao automatica
- **Metricas de performance em tempo real**

###  **RESULTADOS MENSURADOS:**
- **Imports:** 80-90% mais rapidos
- **GUI Filters:** 2.88x a 102,900x speedup
- **Streamlit:** 3,977x speedup medio
- **Database:** 5-20x queries mais rapidas
- **Logging:** Sistema robusto com metricas automaticas

###  Sintaxe de filtros consistente entre interfaces
- Parser de filtros padronizado entre as interfaces suportadas
- Cache inteligente acelera drasticamente todas as consultas
- Performance otimizada automaticamente em todos os componentes

###  Novos temas com foco em contraste
- Tema "Escala de cinza" substitui o antigo "Claro" com ajuste fino para telas brilhantes
- Perfis extras inspirados em Windows 7, KDE Plasma e GNOME (Adwaita)
- Ajustes de contraste automaticos no macOS para manter legibilidade

###  Dashboard Streamlit com CACHE MASSIVO
- `uv run --python $PY_RUNTIME main.py --streamlit` inicia painel **3,977x mais rapido**
- Cache TTL inteligente com metricas automaticas
- Progress bars e interface otimizada
- Download de CSV acelerado com cache

##  Historico v3.10 - Build System Multi-Plataforma

###  Sistema de Build Completo
- **Executaveis funcionais**: CLI e GUI totalmente testados para macOS ARM64
- **Build rapido**: 30 segundos para desenvolvimento e testes
- **Build otimizado**: 1-5 minutos para producao com cache inteligente
- **Entry points corrigidos**: GUI principal (2232 linhas) em vez do POC

###  Otimizacoes Implementadas
- **Dependencias reduzidas**: 236 → 6 pacotes essenciais
- **Cache de ambiente virtual**: Reutilizacao acelera builds subsequentes
- **Modulos resolvidos**: secrets, urllib, pandas, openpyxl totalmente funcionais
- **Documentacao atualizada**: Virgulas corrigidas, estrutura organizada

###  Como Usar os Executaveis
```bash
# CLI (teste rapido)
./launchers/dist/macos_arm64/SSA_CLI_v3.10_macos_arm64/SSA_CLI_v3.10_macos_arm64 --help

# GUI (App macOS)
open launchers/dist/macos_arm64/SSA_GUI_v3.10_macos_arm64.app

# Build proprio rapido
uv run --python 3.13 launchers/build_simple.py gui && cd launchers/dist_simple && ./gui_entry
```

###  Funcionalidades principais v3.11

Versao: 3.11 - SSA Consulta Rapida v3.11

Novidades v3.11:
- CLI: paginacao interativa com comando `m`/`m z`, prompt enxuto e resumo dos filtros ativos
- GUI: parse de busca alinhado ao CLI, chips de filtros exibidos com notacao clara e temas extras disponiveis
- Streamlit: atalho `main.py --streamlit` inicia painel em background, sidebar com ajuda e resumo de filtros
- Core: `parse_search_terms` alinhado ao contrato simplificado atual, mantendo previsibilidade de busca
- Temas: Escala de cinza, Windows 7, KDE e GNOME adicionados sem impactar alteracoes ja feitas para Windows

Resumo do 3.0:
- Filtro “5 opcoes” implementado (CLI/GUI) com negativos e fallback de regex
- Modo padrao de filtro configuravel (-c) e default_filters aplicados no start
- GUI com protecao de instancia unica e tooltip de ajuda nos modos
- Documentacao revisada (README/MAPA/CHANGELOG); 67 testes passando

Ferramenta para consulta rapida de SSAs com CLI e GUI (Python). Foco em previsibilidade, desempenho e paridade de exibicao.

Links uteis:
- Mapa de Documentacao Ativa: docs/INDEX.md
- Changelog tecnico: docs/CHANGELOG_IMPLEMENTACOES.md

## Requisitos
- Python 3.10+ (preferir 3.13+ quando disponivel)
- Windows (testado) ou ambiente compativel com PyQt6

## Instalacao
```bash
# preferencial
uv venv
uv sync
PY_RUNTIME=3.13
uv run --python $PY_RUNTIME main.py --gui
```

```pwsh
# compatibilidade (sem uv)
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Activation helpers (cross-platform)
To make local environment activation reliable across macOS, WSL and Windows (PowerShell), this repository includes two helpers:

- `activate_repo.sh` — Bash/Zsh helper (use `source ./activate_repo.sh`). Recommended for macOS and WSL.
- `activate_repo.ps1` — PowerShell helper (dot-source with `. .\activate_repo.ps1`). Recommended for Windows PowerShell and PowerShell 7 (pwsh).

Usage after cloning:

1. Clone the repo and open a shell for your OS.
2. On macOS / WSL:
	- `uv venv --python 3.13 .venv` (if you don't use pyenv)
	- `source ./activate_repo.sh`
3. On Windows PowerShell (pwsh recommended):
	- `uv venv --python 3.13 .venv` (if you don't use pyenv-win)
	- `. .\activate_repo.ps1`

Tip: The repository contains a `.gitattributes` entry that enforces LF for `.envrc` and shell scripts so `direnv` will not fail due to CRLF. If you prefer `direnv`, WSL is the recommended environment for evaluating `.envrc`.

**Windows + direnv (scoop):** se `direnv exec` nao achar o binario, aponte `DIRENV_BIN` para o caminho retornado por `where direnv` (converta para formato WSL com `cygpath -u` se estiver dentro do bash). Evite hardcode de usuario/caminho; ajuste tambem `XDG_*` se necessario. Em caso de duvida, ative o ambiente manualmente com `.venv\\Scripts\\Activate.ps1`.


Para build Windows com compressao UPX (reducao de tamanho), instale o binario `upx` pelo gerenciador do sistema.

```pwsh
scoop install upx
```

O build continua sem compressao se `upx` nao estiver disponivel no `PATH`.

## Inicializacao automatica de diretorios
Na primeira execucao o sistema garante a criacao idempotente dos diretorios essenciais (ex.: `data/`, `data/historico_backups/`, `logs/`, `reports/`, `extracao/`, `exportacao/`).

Mecanismo:
- Implementado em `utils.setup_project_structure.setup_dirs()` e chamado cedo no `main.py`.
- So registra log de nivel INFO quando um diretorio e criado pela primeira vez.
- Variavel de ambiente opcional `SSA_EXTRA_DIRS="dir1,dir2"` permite acrescentar diretorios adicionais.
- Caso exista logica legada mais rica pode ser reaproveitada definindo `SSA_LEGACY_SETUP_MODULE` apontando para um modulo Python que exponha `legacy_required_dirs() -> list[str]`; as pastas extras serao mescladas.

Validacao:
- Teste de guarda `tests/test_setup_project_structure.py` impede remocao silenciosa.
- Metodo `setup_project_structure.validate()` pode ser usado em diagnosticos.

Exemplo rapido (adicionando diretorios extras temporarios):
```bash
SSA_EXTRA_DIRS="tmp_cache,tmp_export" uv run --python $PY_RUNTIME main.py --help
```

## Uso rapido
- CLI (padrao):
```pwsh
uv run --python $PY_RUNTIME main.py
```
- GUI:
```pwsh
uv run --python $PY_RUNTIME main.py --gui
```

Notas de importacao e versao dos dados:
- O arquivo “mais novo” e escolhido pela data no nome (quando existir), senao por mtime/ctime
- Em empates/sem data, a evolucao de situacao desempata (ASE → ADI → APL → APG → SPG → SEE → SAD → STE)

## Regras de exibicao (CLI/GUI)
- Numero SSA exibido conforme normalizacao atual: nao cria prefixo de ano em identificador curto; detalhes na secao `Normalizacao do Numero SSA`.
- Datas: dd/mm/yyyy (sem horario)
- Semanas: inteiras (sem “.0”)
- Valores nulos: nao exibir "nan/NaT/None" (usa “-” quando aplicavel)

Extras do CLI
- Destaque de termos da ultima busca (negrito ANSI quando suportado). Defina NO_COLOR=1 ou SSA_NO_COLOR=1 para desativar
- Larguras fixas por rotulo (overrides): ver “Configuracao” abaixo
- Filtros avancados “5 opcoes” por termo (implementado):
	- contem (padrao): foo
	- comeca com: ^foo
	- termina com: foo$
	- igual: =foo
	- regex: ~foo.*bar
	- negativos: prefixe ! ou - (ex.: !^adm, !$2025, !=fechado, !~cancel.*)
	- modo padrao configuravel: `-c` abre menu para ajustar `user_preferences.filter_mode_default`

## CLI – guia rapido
Comandos principais: `-ord/-ordi/-ordn/-ordni`, `-cols`, `-f/-filtros`, `-x`, `-v`, `-clear`, `-clearall`, `-rescan`, export.

Exemplos:
```text
# ordenar por data de cadastro (desc)
-ord data_cadastro desc

# listar colunas com rotulos
-cols

# aplicar filtro contendo e negativo
MEL4,!cancelada

# remover ultimo termo da pilha
-v

# remover termo especifico
-x cancelada
```

Filtro “5 opcoes” (implementado)
- contem (padrao): `foo`
- comeca com: `^foo`
- termina com: `foo$` ou `$foo`
- igual: `=foo`
- regex: `~foo.*bar` (quando o modo padrao e regex, `^`/`$` funcionam como ancoras)
- negativos: prefixar `!` ou `-` (ex.: `!^adm`, `!$2025`, `!=fechado`, `!~cancel.*`)

## GUI – desempenho e previsibilidade
- Modelo leve (QAbstractTableModel)
- Filtro com debounce (~250–350 ms) e botao “Aplicar”; ajuda TL;DR sob o campo de busca
- Filtros por Coluna compactos: labels proximos, botoes fixos (Aplicar/Limpar) e largura estavel
- Estabilidade de colunas: larguras so recalculam quando muda o conjunto/ordem de colunas ou o viewport varia > 12 px
- Indicador [f] no cabecalho quando uma coluna tem filtro ativo
- Suporte a `=NULL`/`NULL` e `!` (negativos) tambem na GUI, igual ao CLI
- Resguardo de instancia unica: se ja houver uma janela aberta, um novo `--gui` nao abre outra
- Seletor de colunas com nomes de exibicao e ordem preservada

## Temas (GUI)
- Alternancia: Claro, Escuro e Gruvbox
- Tema Claro com contraste melhorado: caixas informativas (Semana, Status) usam fundo cinza-claro e borda visivel
- Dica de busca (TL;DR) legivel em claro/escuro
- Persistencia do tema em `config/gui_main_preferences.json`

## GUI - filtros (TL;DR)
- Separe termos por virgulas: `foo, bar`
- Modos por termo: contem (`foo`), comeca (`^foo`), termina (`foo$`), igual (`=foo`), regex (`~padrao`), excluir (`!termo`)
- Por coluna: clique direito no cabecalho para abrir o painel; o dialogo agora exibe hint explicito `Aceita termo, !termo para exclusao`
- O marcador `[f]` no cabecalho reflete tanto filtro por coluna quanto filtro avancado equivalente

## Importacao – robustez
- Ignora arquivos sem colunas obrigatorias (ex.: `numero_ssa`) com log
- `KeyboardInterrupt` (Ctrl+C) cancela com rollback seguro

### Schema runtime e migracao

O runtime default inicializa o banco com `config/schema.sql`.
`config/schema_unified.sql` permanece disponivel para fluxos que o selecionam
explicitamente e para a migracao historica; ele nao e a fonte unica do runtime.
Ambos usam `ssa_table` como tabela canonica e declaram `ssa_event_records`.

Views de compatibilidade:
- `ssas` → aponta para `ssa_table`.
- `ssa_chamados` → aponta para `ssa_table`.

Script de migracao incremental:
```
uv run --python $PY_RUNTIME scripts/migracao/migrar_para_unificado.py --db data/ssas.db
```
O script:
- Faz backup automatico (`data/ssas.db.backup_before_unified_YYYYMMDD_HHMMSS`).
- Detecta colunas ausentes via `PRAGMA table_info`.
- Executa apenas `ALTER TABLE ADD COLUMN` (sem remocao ou rename destrutivo).

Recomendado rodar antes de novas importacoes se o banco for anterior a unificacao.

### Novas Colunas / Mapeamentos (Importacao)

Aliases adicionados suportados (exemplos de cabecalho de planilha → coluna canonica):
- `Desvio` → `numero_desvios`
- `Justificativa sem APR` → `justificativa`
- `Total Tempo TPE Executada` → `total_tempo_tpe_executada`

Esses aliases estao em `config/column_mappings.json`. No fluxo default, o
lookup preserva acentos e caixa e aplica apenas `strip`; nao existe fallback
semantico para grafias diferentes.

### Caminhos de importacao atuais

O fluxo principal de SSA usa `extracao.extractor.extract_data_from_excel` em
`core/import_single_file.py`, `scripts/import_excel_file.py` e
`scripts/migracao/backfill_reprocessar.py`.

Contratos do fluxo principal:

1. `--mappings` compara o header somente com os aliases literais do JSON
   fornecido, usando normalizacao mecanica de caixa, acentos e espacos. Nao
   inventa sinonimos nem coalesce campos de negocio; aliases ambiguos ou alvos
   internos reservados encerram a extracao em erro.
2. Linhas hierarquicas sem `numero_ssa` nao recebem forward-fill. Elas sao
   associadas ao pai comprovado e persistidas separadamente em
   `ssa_event_records`.
3. Linha sem identidade que ainda contenha payload nao e aceita por nenhum
   caller canonico. O core interrompe a rodada antes de metadata/upsert e os
   CLIs auxiliares retornam erro.
4. Escrita em tabela SSA exige `--smart-upsert`, com metrica que confirma todos
   os eventos capturados.
5. `arquivo_origem`, `data_planilha` e `data_arquivo_origem` vem do arquivo
   fisico importado e nao de colunas eventualmente embutidas na planilha.

`utils/robust_importer.py` continua ativo para `read_report`, sincronizacao de
derivadas e simulacao. Ele nao e o parser de escrita dos dois CLIs auxiliares de
SSA.

Contrato aprovado neste ciclo para `--mappings`: preservar a compatibilidade do
CLI anterior ao encaminhar o arquivo customizado ao extractor canonico. O diff
previsto ficou restrito a esse encaminhamento e ao lookup mecanico. Os termos
afetados sao exatamente os nomes canonicos e aliases presentes no JSON escolhido
em cada execucao; nenhum termo foi adicionado ao mapping default. Justificativa:
um alias fornecido pelo operador deve continuar reconhecido apesar de variacao
de caixa, acento ou espaco. Cobertura positiva:
`test_extract_data_from_excel_uses_explicit_mapping_file`. Cobertura negativa:
`test_extract_data_from_excel_preserves_unmapped_header_without_explicit_mapping`
e `test_extract_data_from_excel_rejects_unsafe_explicit_mapping`.

Documento tecnico detalhado: `docs/IMPORTACAO_ROBUSTA.md`.

### Fluxo recomendado de atualizacao
1. Atualizar repositorio (`git pull`).
2. Executar migracao: `uv run --python $PY_RUNTIME scripts/migracao/migrar_para_unificado.py --db data/ssas.db`.
3. (Opcional) Rodar teste sintetico: `pytest -q tests/test_import_novas_colunas.py`.
4. Importar novas planilhas normalmente.

### Backfill auxiliar
Script disponivel: `scripts/migracao/backfill_reprocessar.py`

Uso basico:
```bash
uv run --python $PY_RUNTIME scripts/migracao/backfill_reprocessar.py --dir docs_entrada --db data/ssas.db --smart-upsert --dry-run
```
Ou via `main.py` integrado:
```bash
uv run --python $PY_RUNTIME main.py --acao backfill -- --dir docs_entrada --db data/ssas.db --smart-upsert --dry-run \
	--report-path reports/backfill_manual.json
```
Opcoes principais:
- `--since YYYY-MM-DD` filtra arquivos mais antigos
- `--limit N` limita quantidade processada
- `--reset-db` e rejeitado neste utilitario; recriacao pertence ao full rescan
  com banco candidato e promocao validada
- `--pattern "*.xlsx"` glob customizado
- escrita exige `--smart-upsert`; `--dry-run` nao grava no banco

Resultado: relatorio agregador + JSON detalhado em `reports/backfill_report_*.json`.
Se `--report-path` for usado (disponivel no script e via integracao), o relatorio sera salvo exatamente no caminho indicado. Caso nenhum arquivo elegivel seja encontrado, um relatorio vazio e gerado (quando `--report-path` e fornecido) e a saida retorna codigo 0 com log informativo.


## Configuracao e integridade
- Prioridades/labels: `config/column_priority.json` (estrutura: essential, always_visible, priority_order, short_labels, fixed_widths, hidden_by_default)
- Larguras fixas e overrides:
	- `fixed_widths` (por nome interno) em `column_priority.json`
	- `display_settings.column_widths` (por rotulo de exibicao/curto) em `config/settings.json`
	- O `table_printer` mescla rotulo→coluna para compor a largura efetiva
- Mapeamentos: `display_mappings.json` e `column_mappings.json` tem auto-restauracao (integrity) via `core/config_manager.py`; respeitam `SSA_CONFIG_DIR`
- Protecao do “arquivo mais recente”: README/CHANGELOG e JSONs de config sao ignorados

## Exportacao
- CSV/XLSX/JSON em `docs_saida/` com rotulos consistentes (usa `display_mappings`)

## Hooks de Git (bloqueio de arquivos grandes)
- Pre-commit (staged >=95MB): `scripts/git_hooks/pre-commit`
- Pre-push (blobs >=95MB no push): `scripts/git_hooks/pre-push`

Ativacao:
```bash
bash scripts/install_hooks.sh
```

## Testes

### Script Unificado / Headless

Agora utilize o script para modos padronizados:

```
./scripts/run_tests.sh        # quiet
./scripts/run_tests.sh full   # verbose (-vv)
./scripts/run_tests.sh debug  # verbose + prints (-s)
./scripts/run_tests.sh cov    # cobertura
```

Filtrar por expressao:

```
PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh debug
```

Ambiente headless (Qt offscreen) ja e configurado via `tests/conftest.py`. Se necessario reforcar manualmente:
```
QT_QPA_PLATFORM=offscreen ./scripts/run_tests.sh full
```

Documentacao detalhada: `docs/TESTING_HEADLESS.md`.

### Quality Gates (Agregador)

O script `scripts/run_quality_gates.py` executa e consolida tres (ou mais) gates de qualidade em uma unica linha JSON:

Gates padrao:
- `validate_configs`: valida JSONs em `config/`.
- `smoke_cli`: execucao minima da CLI para garantir import e fluxo basico.
- `check_docs`: validacao sintatica/estrutural de arquivos Markdown selecionados.

Extensoes:
- `--extra-config-dir <dir>` (pode repetir): cada diretorio gera um gate adicional nomeado `validate_configs_extra_1`, `validate_configs_extra_2`, ... usando `validate_configs` apontado para aquele diretorio via `--config-dir`.
- `--extra-doc <arquivo_markdown>` (pode repetir): adiciona arquivos ao escopo de `check_docs`.
- `--skip <gate>` / `--only <gate>`: filtram execucao (`validate_configs`, `smoke_cli`, `check_docs`).
- `--no-fail-on-doc-issues`: torna problemas de documentacao nao-fatais (gate continua reportando issues porem status pode permanecer `ok`).

Formato JSON (resumido):
```json
{
	"overall_status": "ok|fail|error",
	"summary": { "overall_status": "ok", "executed_gates": ["validate_configs", "smoke_cli", ...] },
	"gates": {
		"validate_configs": {"status": "ok", "exit_code": 0, ...},
		"validate_configs_extra_1": {"status": "ok", ...}
	},
	"validate_configs": {"status": "ok", ...} // flatten redundante para compatibilidade de testes
}
```

Regras de severidade:
- `fail` tem precedencia sobre `error` (um unico gate `fail` define `overall_status=fail`).
- `error` usado para falhas internas (ex.: excecao inesperada, timeout, uso incorreto de argumento).

Exemplos:
```bash
# Caminho feliz completo
uv run --python 3.13 scripts/run_quality_gates.py

# Apenas validar configs + dois diretorios extras
uv run --python 3.13 scripts/run_quality_gates.py \
	--extra-config-dir caminho/dirA \
	--extra-config-dir caminho/dirB \
	--skip smoke_cli --skip check_docs

# Validar docs adicionais sem falhar por issues
uv run --python 3.13 scripts/run_quality_gates.py --extra-doc README.md --no-fail-on-doc-issues
```

Teste dedicado: `tests/test_quality_gates_extra_config_dirs.py` assegura criacao dos gates extras. Cenarios de falha controlada: `tests/test_quality_gates_fail_paths.py`.

Boas praticas:
- Mantenha saida do script em **uma linha** (facilita parsing em pipelines).
- Para novos gates, seguir padrao de retorno (JSON parseavel, exit codes 0/1/2) e adicionar documentacao aqui.
- Evite acoplamento direto em CI: parse do `overall_status` e suficiente para bloquear.


### Estrategia de Testes (Governanca)
Documento detalhado de piramide, fixtures, politica de dtypes e limiares progressivos: consulte `docs/TESTING_STRATEGY.md`.

Executar smoke essencial (gates + nucleo integracao rapido):
```
pytest -m "smoke" -q
```
Executar integracao (exclui legacy/slow):
```
pytest -m "integration and not legacy and not slow" -q
```
Cobertura rapida dos modulos principais:
```
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Interface de Tabela (CLI) – Nova Implementacao 2025-09

O modulo `interface/table_printer.py` foi reescrito para oferecer:

Principais caracteristicas:
- Selecao dinamica de colunas com prioridade (`essential`, `always_visible`, `priority_order`).
- Paginacao estavel com cabecalho de pagina: `Pagina X de Y` e prompts interativos (`Enter`, `f`, `q`).
- Truncagem segura de descricoes com largura minima (`MIN_TRUNCATE_WIDTH = 8`) e expansao quando houver espaco.
- Heuristica de largura baseada no percentil 95 do tamanho das celulas (evita efeito de outliers).
- Reatribuicao adaptativa de espaco residual extra para `descricao_ssa` (ate limite de 200 chars).
- Normalizacao de `numero_ssa` (_normalize_ssa) aplicada antes da renderizacao.
- Backwards compatibility: assinatura antiga de `_select_columns_for_width` ainda suportada por testes legados.
- Modo compacto automatico quando:
	- largura do terminal < 100 colunas ou
	- numero de colunas selecionadas >= 6
- Sanitizacao agressiva: remove controles ASCII, normaliza Unicode ⇒ ASCII, substitui vazio por `-`.
- Funcoes publicas exportadas: `pretty_print_df`, `format_dataframe_for_cli`, `paginate_dataframe`, `get_terminal_size`.

Constantes principais (ajude-se consultando o codigo):
```
HASH_COLUMN = '#'
HASH_WIDTH = 4
MAX_COL_WIDTH = 70
MAX_DESC_WIDTH = 200
PERCENTIL_WIDTH = 0.95
MIN_TRUNCATE_WIDTH = 8
SMALL_COLUMN_THRESHOLD = 4
SSA_FULL_LENGTH = 9
SSA_SHORT_THRESHOLD = 5
SSA_YEAR_PREFIX = '2025'
```

### Uso Basico
```python
from interface.table_printer import pretty_print_df, format_dataframe_for_cli
import pandas as pd

df = pd.DataFrame([
		{"numero_ssa": "202512345", "situacao": "APL", "descricao_ssa": "Trocar valvula"},
		{"numero_ssa": "123", "situacao": "ADI", "descricao_ssa": "Inspecao"},
])

# Impressao paginada interativa
pretty_print_df(df, display_map={"numero_ssa": "Numero SSA", "situacao": "Sit.", "descricao_ssa": "Descricao"}, settings={})

# Obter string formatada (sem paginacao) – util para logs ou export improvisado
table_str = format_dataframe_for_cli(df, display_map={"numero_ssa": "Numero SSA"})
print(table_str)
```

### Configuracao de Larguras e Visibilidade
- `config/column_priority.json` define: `essential`, `always_visible`, `priority_order`, `short_labels`, `fixed_widths`.
- `config/settings.json` (chave `display_settings`):
	- `column_widths`: mapeamento por rotulo (full/short) → largura fixa.
	- `column_visibility`: `{ "coluna_interna": true/false }` (false oculta, exceto se estiver em `always_visible`).

Mesclagem de larguras:
1. `fixed_widths` (por nome interno)
2. Override por rotulo em `display_settings.column_widths` (se rotulo curto/full corresponder)
3. Caso nada definido, estima via `_estimate_column_width` (percentil 95).

### Normalizacao do Numero SSA
Regra (_resumida_):
- Remove nao-digitos.
- Vazio ou sem digitos ⇒ exibe `-`.
- Menos que 5 digitos ⇒ preserva os digitos encontrados; nao prefixa ano nem faz padding.
- 9 digitos comecando com `2025` ⇒ mantem o valor completo.
- Mais que 9 digitos ⇒ aplica compatibilidade legada da CLI: se comecar com `2025`, usa a janela de 9 digitos validada em teste; nos demais casos, usa os ultimos 9 digitos.
- `SSA_YEAR_PREFIX` identifica valores completos com ano conhecido; nao autoriza criar prefixo novo em identificador curto.

### Comportamento de Paginacao
- Tamanho de pagina = `linhas_terminal - LOW_HEIGHT_MARGIN` (margem = 8).
- `f` apos qualquer pagina ativa “auto-scroll” ate o fim.
- Se `auto_scroll_to_end=true` nas preferencias e total de paginas > `max_auto_scroll_pages`, o auto-scroll e desativado silenciosamente para evitar flood.

### Boas Praticas / Extensao
- Para adicionar nova coluna “sempre visivel” sem quebrar testes: inclua em `always_visible` no JSON e garanta que mapeamentos (`display_mappings.json`) tenham rotulo correspondente.
- Evite aumentar `MAX_DESC_WIDTH` acima de 200 sem avaliar quebra de layout em terminais pequenos.
- Se precisar suportar terminal extremamente estreito (<40 colunas), considere fallback adicional reduzindo ainda mais cabecalhos (ex.: siglas).

### Testes Cobertos
- `_normalize_ssa`: casos curtos, 9 digitos, excesso, caracteres mistos, `None`.
- `paginate_dataframe`: vazio, divisao exata, resto, page_size=1.
- Backward compatibility: testes antigos que chamam assinatura anterior de `_select_columns_for_width` continuam funcionando (wrapper aceita kwargs legados).

### Roadmap Futuro (Sugestoes)
- Cache leve de larguras por hash de amostra para grandes DataFrames.
- Modo “raw export” ignorando truncagem (para piping em scripts): flag em settings.
- Otimizacao de re-render parcial quando apenas filtros alteram subconjunto de linhas (mantendo colunas fixas).

---


## Solucao de problemas
- “Headers sumindo” em terminal estreito: use `-cols` e aumente a largura; colunas `always_visible` nunca sao descartadas
- “Rotulo curto” inesperado: desative `prefer_short_labels` no `settings.json`
- “Filtro lento” na GUI: debounce ja ativo; desmarque “Aplicar automaticamente” para aplicar so ao clicar
- “Mapeamento ausente/corrompido”: defina `SSA_CONFIG_DIR` e deixe o loader recriar os JSONs

## Notas
- Consulte `docs/INDEX.md` para navegacao canonica da documentacao
- Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para decisoes e linha do tempo tecnica

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
