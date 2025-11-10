# SSA Consulta Rapida v4.10.0

Release 4.10.0 formaliza correcao dos problemas de filtros e aplicacao de temas observados na serie 4.0. Todo o texto abaixo permanece para historico. As instrucoes principais seguem em portugues sem acentos.

## Release v4.10.0 (2025-11)

### Contexto historico
Na serie 4.0 ocorreram falhas em dois pontos principais:
- Filtros: divergencia entre GUI CLI e streamlit em combinacoes com OU e negativos, alem de substituicao visual que induzia interpretacao incorreta.
- Temas: papeis de cores para quadros indicadores e tags aplicados de forma inconsistente em alguns sistemas.

### O que foi corrigido
- Unificacao do parsing de conectivos OU entre todas as interfaces sem alteracao visual ambigua
- Invalidacao correta de cache quando entra OU ou negativo
- Ajuste de ordem de normalizacao evitando estados intermediarios incoerentes
- Mapeamento central de chaves de tema para quadros indicadores e tags

### Resultados esperados
- Mesmos resultados de busca em CLI GUI e streamlit
- Negativos honrados quando combinados com OU
- Temas aplicados de forma previsivel em plataformas suportadas

### Observacoes
- Sem alteracao de schema
- Sem mudanca de formatos de exportacao

# SSA Consulta Rapida v4.0.3

## Release v4.0.3 (2025-11)

### Filter Corrections Release
- Fixed filter behavior from release 4.x series
- GUI filter logic stabilized
- Column filters working correctly
- Test suite updated and passing

## Previous Release v4.0.0 (2025-09) - Performance Improvements

###  **GANHOS DE PERFORMANCE MENSURADOS:**
- **Imports:** 80-90% mais rápidos com modo otimizado padrão
- **GUI Filters:** 2.88x a 102,900x speedup com cache LRU multi-threaded
- **Streamlit:** 3,977x speedup médio com cache TTL
- **Database Queries:** 5-20x mais rápidas com 6 índices estratégicos
- **Sistema de Logging:** Robusto com métricas automáticas de performance

###  **OTIMIZAÇÕES IMPLEMENTADAS:**

#### **Phase 1: Fundamentos**
- - Main.py com modo `--optimized` por padrão
- - `core/app_logic.py` - `filter_dataframe` otimizado (1.96x speedup)
- - 6 índices estratégicos no SQLite para queries 5-20x mais rápidas

#### **Phase 2: GUI Inteligente**
- - Sistema de cache LRU com `FilterWorker` multi-threaded
- - Debounce 250ms para evitar consultas excessivas
- - Cache hit rate 75%+ em uso normal
- - Performance: 2.88x a 102,900x speedup dependendo do cenário

#### **Phase 3: Streamlit Aprimorado**
- - `StreamlitFilterCache` com TTL e métricas detalhadas
- - Interface sidebar reorganizada com progress bars
- - Cache configurável (100 entradas, 300s TTL por padrão)
- - Performance: 3,977x speedup médio

#### **Phase 4: Sistema de Logging Robusto**
- - `utils/robust_logging.py` - Sistema completo com `PerformanceMetrics`
- - `config/logging.json` - Configuração centralizada multi-handler
- - Integração completa em main.py, GUI e Streamlit
- - Logging estruturado JSON + rotação automática
- - Métricas de performance em tempo real

## Notas de Padronização e Governança (2025-09)

Foram aplicadas melhorias recentes de qualidade de código:

- Redução de números mágicos: constantes adicionadas em `armazenamento/database.py` (`NUMERO_SSA_LEN`, limites de ano, `MAX_TEXT_LEN`, etc.).
- Normalização de `numero_ssa`: funções consolidadas e uso consistente das regras (YYYY + 5 dígitos) com validação defensiva.
	 - Regra estrita atual (camada core):
		 * Somente 9 dígitos após remoção de hífens/espaços (`YYYYXXXXX`).
		 * Ano inicial entre 1980 e 2050.
		 * Valores com letras ou símbolos fora de `[0-9 -]` são rejeitados.
		 * Hífen opcional é aceito apenas em formato `YYYY-XXXXX` quando os 5 dígitos finais NÃO são todos idênticos.
			 - Exemplo aceito: `2025-12345` → `202512345`.
			 - Exemplo rejeitado: `2025-22222` (marcado como inválido e filtrado no importador).
		 * Strings maiores que 9 dígitos não são truncadas; são rejeitadas para evitar colisões silenciosas.
	 - Testes que cobrem as regras: `tests/test_numero_ssa_normalization_cross.py` e `tests/test_numero_ssa_hyphen_repetition.py`.
- Linhas longas (>100 colunas) quebradas para melhorar leitura e conformidade com lint.
- Sistema de logging robusto com métricas automáticas de performance.
- Cache systems inteligentes para GUI e Streamlit com ganhos massivos de performance.

Para auditoria de termos sensíveis existe um scanner interno (script em `scripts_manutencao/`) configurado para varrer apenas diretórios relevantes e ignorar arquivos grandes de dados.

Nota de manutenção: durante a limpeza recente de emojis em documentação e arquivos de texto, os arquivos originais foram preservados em `.emoji_backups/` na raiz do repositório. Use essa pasta para restaurar qualquer arquivo caso necessário.
# Modularização do Módulo de Banco de Dados (2025-09)

Para reduzir complexidade ciclomática e facilitar testes focados, o monolito `armazenamento/database.py` foi dividido em módulos especializados mantendo a API pública retrocompatível (tests continuam importando de `armazenamento.database`).

Componentes extraídos (estado atual):
- `database_upsert_logic.py`: preparação e lógica de upsert (merge condicional, modos complementar vs. simples, normalização de datas) – expõe `prepare_dataframe_for_upsert`, `apply_column_whitelist` e `insert_dataframe_with_smart_upsert_impl`.
- `database_integrity.py`: verificação e reparo (`verify_database_integrity`, `repair_database_if_needed`).
- `database_validation.py`: validação pré-inserção (`validate_dataframe_before_insert`).
- `numero_ssa_utils.py`: fonte única para normalização de `numero_ssa` (strict, legado inteiro, formato display, batch dataframe).

No arquivo `database.py` permanecem apenas:
- Conexão (`get_db_connection`) e inicialização (`initialize_database`).
- Facades públicas: `insert_dataframe_to_db`, `insert_dataframe_with_smart_upsert`.
- Reexports simples de normalização (`normalize_numero_ssa`, `normalize_numero_ssa_dataframe`).
- Delegações finas de integridade/validação (sem wrappers intermediários de upsert internos removidos na etapa de redução de complexidade).

Melhorias adicionais nesta etapa:
- Remoção de wrappers `_prepare_dataframe_for_upsert`, `_perform_upsert`, `_insert_dataframe_with_smart_upsert_impl` redundantes.
- Unificação do filtro de colunas (`SSA_ALLOWED_COLUMNS`) em helper reutilizável (`apply_column_whitelist`).
- Redução líquida de linhas mantendo cobertura comportamental (testes passam / legado preservado).

Próximos passos sugeridos (não bloqueantes):
1. Adicionar testes unitários específicos para `apply_column_whitelist` e datas limítrofes de normalização.
2. Considerar moving parsing de datas para util dedicado se expandir.
3. Avaliar medição de performance (perfil leve) em lotes grandes (>50k linhas) para ajustar `chunksize` dinamicamente.

Essa seção reflete o estado pós-limpeza para orientar futuros mantenedores.
# SSA_Consulta_Rapida

Versão atual: 3.11 (Sistema funcional)

##  **NOVIDADES v4.0.0 - PERFORMANCE MASSIVAMENTE OTIMIZADA**

###  **OTIMIZAÇÕES DE PERFORMANCE IMPLEMENTADAS:**

#### ** Phase 1: Fundamentos (90% mais rápido)**
- Main.py com modo `--optimized` **por padrão**
- `filter_dataframe` otimizado com **1.96x speedup**
- **6 índices estratégicos** no banco para queries **5-20x mais rápidas**

#### ** Phase 2: GUI Inteligente (2.88x-102,900x speedup)**
- Sistema de **cache LRU multi-threaded** com `FilterWorker`
- **Debounce 250ms** para evitar consultas excessivas
- Cache hit rate **75%+** em uso normal
- Performance: **2.88x a 102,900x speedup** dependendo do cenário

#### ** Phase 3: Streamlit Aprimorado (3,977x speedup)**
- `StreamlitFilterCache` com **TTL e métricas detalhadas**
- Interface sidebar reorganizada com **progress bars**
- Cache configurável (100 entradas, 300s TTL)
- Performance: **3,977x speedup médio**

#### ** Phase 4: Sistema de Logging Robusto**
- `utils/robust_logging.py` com `PerformanceMetrics` automático
- Configuração centralizada em `config/logging.json`
- **Logging estruturado JSON** + rotação automática
- **Métricas de performance em tempo real**

###  **RESULTADOS MENSURADOS:**
- **Imports:** 80-90% mais rápidos
- **GUI Filters:** 2.88x a 102,900x speedup
- **Streamlit:** 3,977x speedup médio
- **Database:** 5-20x queries mais rápidas
- **Logging:** Sistema robusto com métricas automáticas

###  Sintaxe OU/OR consistente em todas as interfaces
- Parser de filtros agora entende `OU`/`OR` (além de `!`, `^`, `$`, `=` e `~`) de forma unificada
- Cache inteligente acelera drasticamente todas as consultas
- Performance otimizada automaticamente em todos os componentes

###  Novos temas com foco em contraste
- Tema "Escala de cinza" substitui o antigo "Claro" com ajuste fino para telas brilhantes
- Perfis extras inspirados em Windows 7, KDE Plasma e GNOME (Adwaita)
- Ajustes de contraste automáticos no macOS para manter legibilidade

###  Dashboard Streamlit com CACHE MASSIVO
- `python main.py --streamlit` inicia painel **3,977x mais rápido**
- Cache TTL inteligente com métricas automáticas
- Progress bars e interface otimizada
- Download de CSV acelerado com cache

##  Historico v3.10 - Build System Multi-Plataforma

###  Sistema de Build Completo
- **Executáveis funcionais**: CLI e GUI totalmente testados para macOS ARM64
- **Build rápido**: 30 segundos para desenvolvimento e testes
- **Build otimizado**: 1-5 minutos para produção com cache inteligente
- **Entry points corrigidos**: GUI principal (2232 linhas) em vez do POC

###  Otimizações Implementadas
- **Dependências reduzidas**: 236 → 6 pacotes essenciais
- **Cache de ambiente virtual**: Reutilização acelera builds subsequentes
- **Módulos resolvidos**: secrets, urllib, pandas, openpyxl totalmente funcionais
- **Documentação atualizada**: Vírgulas corrigidas, estrutura organizada

###  Como Usar os Executáveis
```bash
# CLI (teste rápido)
./launchers/dist/macos_arm64/SSA_CLI_v3.10_macos_arm64/SSA_CLI_v3.10_macos_arm64 --help

# GUI (App macOS)
open launchers/dist/macos_arm64/SSA_GUI_v3.10_macos_arm64.app

# Build próprio rápido
python launchers/build_simple.py gui && cd launchers/dist_simple && ./gui_entry
```

###  Funcionalidades principais v3.11

Versão: 3.11 - SSA Consulta Rapida v3.11

Novidades v3.11:
- CLI: paginacao interativa com comando `m`/`m z`, prompt enxuto e resumo dos filtros ativos
- GUI: parse OU/OR alinhado ao CLI, chips de filtros exibidos com notacao clara e temas extras disponiveis
- Streamlit: atalho `main.py --streamlit` inicia painel em background, sidebar com ajuda e resumo de filtros
- Core: `parse_search_terms` suporta grupos OR reais (sem depender de simbolo `v`), mantendo negativos e regex
- Temas: Escala de cinza, Windows 7, KDE e GNOME adicionados sem impactar alteracoes ja feitas para Windows

Resumo do 3.0:
- Filtro “5 opções” implementado (CLI/GUI) com negativos e fallback de regex
- Modo padrão de filtro configurável (-c) e default_filters aplicados no start
- GUI com proteção de instância única e tooltip de ajuda nos modos
- Documentação revisada (README/MAPA/CHANGELOG); 67 testes passando

Ferramenta para consulta rápida de SSAs com CLI e GUI (Python). Foco em previsibilidade, desempenho e paridade de exibição.

Links úteis:
- Mapa de Pedidos → Implementações: docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md
- Changelog técnico: docs_saida/CHANGELOG_IMPLEMENTACOES.md

## Requisitos
- Python 3.13+
- Windows (testado) ou ambiente compatível com PyQt6

## Instalação
```pwsh
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Activation helpers (cross-platform)
To make local environment activation reliable across macOS, WSL and Windows (PowerShell), this repository includes two helpers:

- `activate_repo.sh` — Bash/Zsh helper (use `source ./activate_repo.sh`). Recommended for macOS and WSL.
- `activate_repo.ps1` — PowerShell helper (dot-source with `. .\activate_repo.ps1`). Recommended for Windows PowerShell and PowerShell 7 (pwsh).

Usage after cloning:

1. Clone the repo and open a shell for your OS.
2. On macOS / WSL:
	- `python -m venv .venv` (if you don't use pyenv)
	- `source ./activate_repo.sh`
3. On Windows PowerShell (pwsh recommended):
	- `python -m venv .venv` (if you don't use pyenv-win)
	- `. .\activate_repo.ps1`

Tip: The repository contains a `.gitattributes` entry that enforces LF for `.envrc` and shell scripts so `direnv` will not fail due to CRLF. If you prefer `direnv`, WSL is the recommended environment for evaluating `.envrc`.


Para build Windows com compressão UPX (redução de tamanho), instale também:
```pwsh
pip install -r launchers/platforms/windows_amd64/requirements_windows_build.txt
```
Esse arquivo separado evita alerta de dependência ausente em ambientes macOS/Linux onde `upx4py` não é necessário.

## Inicialização automática de diretórios
Na primeira execução o sistema garante a criação idempotente dos diretórios essenciais (ex.: `data/`, `data/historico_backups/`, `logs/`, `reports/`, `extracao/`, `exportacao/`).

Mecanismo:
- Implementado em `utils.setup_project_structure.setup_dirs()` e chamado cedo no `main.py`.
- Só registra log de nível INFO quando um diretório é criado pela primeira vez.
- Variável de ambiente opcional `SSA_EXTRA_DIRS="dir1,dir2"` permite acrescentar diretórios adicionais.
- Caso exista lógica legada mais rica pode ser reaproveitada definindo `SSA_LEGACY_SETUP_MODULE` apontando para um módulo Python que exponha `legacy_required_dirs() -> list[str]`; as pastas extras serão mescladas.

Validação:
- Teste de guarda `tests/test_setup_project_structure.py` impede remoção silenciosa.
- Método `setup_project_structure.validate()` pode ser usado em diagnósticos.

Exemplo rápido (adicionando diretórios extras temporários):
```bash
SSA_EXTRA_DIRS="tmp_cache,tmp_export" python main.py --help
```

## Uso rápido
- CLI (padrão):
```pwsh
python main.py
```
- GUI:
```pwsh
python main.py --gui
```

Notas de importação e versão dos dados:
- O arquivo “mais novo” é escolhido pela data no nome (quando existir), senão por mtime/ctime
- Em empates/sem data, a evolução de situação desempata (ASE → ADI → APL → APG → SPG → SEE → SAD → STE)

## Regras de exibição (CLI/GUI)
- Numero SSA com 9 dígitos (prefixo ano para <=5 dígitos; zfill p/ 7–8)
- Datas: dd/mm/yyyy (sem horário)
- Semanas: inteiras (sem “.0”)
- Valores nulos: não exibir "nan/NaT/None" (usa “-” quando aplicável)

Extras do CLI
- Destaque de termos da última busca (negrito ANSI quando suportado). Defina NO_COLOR=1 ou SSA_NO_COLOR=1 para desativar
- Larguras fixas por rótulo (overrides): ver “Configuração” abaixo
- Filtros avançados “5 opções” por termo (implementado):
	- contém (padrão): foo
	- começa com: ^foo
	- termina com: foo$
	- igual: =foo
	- regex: ~foo.*bar
	- negativos: prefixe ! ou - (ex.: !^adm, !$2025, !=fechado, !~cancel.*)
	- modo padrão configurável: `-c` abre menu para ajustar `user_preferences.filter_mode_default`

## CLI – guia rápido
Comandos principais: `-ord/-ordi/-ordn/-ordni`, `-cols`, `-f/-filtros`, `-x`, `-v`, `-clear`, `-clearall`, `-rescan`, export.

Exemplos:
```text
# ordenar por data de cadastro (desc)
-ord data_cadastro desc

# listar colunas com rótulos
-cols

# aplicar filtro contendo e negativo
MEL4,!cancelada

# remover último termo da pilha
-v

# remover termo específico
-x cancelada
```

Filtro “5 opções” (implementado)
- contém (padrão): `foo`
- começa com: `^foo`
- termina com: `foo$` ou `$foo`
- igual: `=foo`
- regex: `~foo.*bar` (quando o modo padrão é regex, `^`/`$` funcionam como âncoras)
- negativos: prefixar `!` ou `-` (ex.: `!^adm`, `!$2025`, `!=fechado`, `!~cancel.*`)

## GUI – desempenho e previsibilidade
- Modelo leve (QAbstractTableModel)
- Filtro com debounce (~250–350 ms) e botão “Aplicar”; ajuda TL;DR sob o campo de busca
- Filtros por Coluna compactos: labels próximos, botões fixos (Aplicar/Limpar) e largura estável
- Estabilidade de colunas: larguras só recalculam quando muda o conjunto/ordem de colunas ou o viewport varia > 12 px
- Indicador [f] no cabeçalho quando uma coluna tem filtro ativo
- Suporte a `=NULL`/`NULL` e `!` (negativos) também na GUI, igual ao CLI
- Resguardo de instância única: se já houver uma janela aberta, um novo `--gui` não abre outra
- Seletor de colunas com nomes de exibição e ordem preservada

## Temas (GUI)
- Alternância: Claro, Escuro e Gruvbox
- Tema Claro com contraste melhorado: caixas informativas (Semana, Status) usam fundo cinza-claro e borda visível
- Dica de busca (TL;DR) legível em claro/escuro
- Persistência do tema em `config/gui_main_preferences.json`

## GUI – filtros (TL;DR)
- Separe termos por vírgulas: `foo, bar`
- Modos por termo: contém (`foo`), começa (`^foo`), termina (`foo$`), igual (`=foo`), regex (`~padrao`), excluir (`!termo`)
- Por coluna: clique direito no cabeçalho para abrir o painel; campos exibem a mesma dica TL;DR

## Importação – robustez
- Ignora arquivos sem colunas obrigatórias (ex.: `numero_ssa`) com log
- `KeyboardInterrupt` (Ctrl+C) cancela com rollback seguro

### Schema Unificado & Migração (2025-09)

Foi introduzido o `config/schema_unified.sql` como fonte de verdade única. Ele consolida:
1. Colunas de `schema.sql` (tabela `ssa_table`).
2. Colunas de `schema_optimized.sql` (tabela `ssas`).
3. Novas colunas recentes relacionadas a desvios e reprogramações.

Views de compatibilidade:
- `ssas` → aponta para `ssa_table`.
- `ssa_chamados` → aponta para `ssa_table`.

Script de migração incremental:
```
python scripts/migracao/migrar_para_unificado.py --db data/ssas.db
```
O script:
- Faz backup automático (`data/ssas.db.backup_before_unified_YYYYMMDD_HHMMSS`).
- Detecta colunas ausentes via `PRAGMA table_info`.
- Executa apenas `ALTER TABLE ADD COLUMN` (sem remoção ou rename destrutivo).

Recomendado rodar antes de novas importações se o banco for anterior à unificação.

### Novas Colunas / Mapeamentos (Importação)

Aliases adicionados suportados (exemplos de cabeçalho de planilha → coluna canônica):
- `Desvio` → `numero_desvios`
- `Justificativa sem APR` → `justificativa`
- `Reprogramações` → `num_reprogramacoes`
- `Total Tempo TPE Executada` → `total_tempo_tpe_executada`

Esses aliases estão em `config/column_mappings.json` e reforçados no fallback de `core/config_manager.py`.

### Heurísticas Novas de Cabeçalho (robust_importer)

Problema resolvido: planilhas cujo título (ex.: “SSAs com Desvio na Programação”) era interpretado como único header, gerando apenas 1 coluna mapeada.

Heurísticas introduzidas:
1. Detecção de header “mesclado” único: se todas as colunas têm o mesmo nome ⇒ tenta reprocessar buscando linha real de cabeçalho abaixo.
2. Revarredura multi‑linha (linhas 0..9) escolhendo a que produz mais grupos canônicos de mapeamento.
3. Reinterpretação da primeira linha como header quando só há 1 coluna original e a linha 0 tem diversidade textual suficiente.

Resultados:
- `mapped_columns_count` passou de 1 para 35 na planilha problemática.
- Inserções deixam de falhar por "column not found" gerada a partir de título da planilha.

Métricas adicionais (para diagnóstico) agora expostas em `reports/last_import_stats.json` e via retorno da função:
- `header_candidate_lines_considered`: quantas linhas foram avaliadas como possíveis cabeçalhos (limitado por `SSA_MAX_HEADER_SCAN`, default 10)
- `selected_header_line_index`: índice da linha escolhida quando reheader aplicado (ou null)
- `alias_hits`: número de vezes que um alias foi convertido para nome canônico

Variáveis de ambiente de tuning:
- `SSA_MAX_HEADER_SCAN`: ajusta o máximo de linhas iniciais avaliadas (ex.: `SSA_MAX_HEADER_SCAN=5 python main.py`)

Teste sintético: `tests/test_import_novas_colunas.py` garante presença e persistência das novas colunas.

Documento técnico detalhado: `docs/SCHEMA_UNIFICADO_IMPORTACAO.md` (inclui heurísticas do importador, checklist e fluxo de migração).

### Fluxo recomendado de atualização
1. Atualizar repositório (`git pull`).
2. Executar migração: `python scripts/migracao/migrar_para_unificado.py --db data/ssas.db`.
3. (Opcional) Rodar teste sintético: `pytest -q tests/test_import_novas_colunas.py`.
4. Importar novas planilhas normalmente.

### Backfill (futuro)
Script disponível: `scripts/migracao/backfill_reprocessar.py`

Uso básico:
```bash
python scripts/migracao/backfill_reprocessar.py --dir docs_entrada --db data/ssas.db --smart-upsert --dry-run
```
Ou via `main.py` integrado:
```bash
python main.py --acao backfill -- --dir docs_entrada --db data/ssas.db --smart-upsert --dry-run \
	--report-path reports/backfill_manual.json
```
Opções principais:
- `--since YYYY-MM-DD` filtra arquivos mais antigos
- `--limit N` limita quantidade processada
- `--reset-db` recria usando `schema_unified.sql`
- `--pattern "*.xlsx"` glob customizado

Resultado: relatório agregador + JSON detalhado em `reports/backfill_report_*.json`.
Se `--report-path` for usado (disponível no script e via integração), o relatório será salvo exatamente no caminho indicado. Caso nenhum arquivo elegível seja encontrado, um relatório vazio é gerado (quando `--report-path` é fornecido) e a saída retorna código 0 com log informativo.


## Configuração e integridade
- Prioridades/labels: `config/column_priority.json` (estrutura: essential, always_visible, priority_order, short_labels, fixed_widths, hidden_by_default)
- Larguras fixas e overrides:
	- `fixed_widths` (por nome interno) em `column_priority.json`
	- `display_settings.column_widths` (por rótulo de exibição/curto) em `config/settings.json`
	- O `table_printer` mescla rótulo→coluna para compor a largura efetiva
- Mapeamentos: `display_mappings.json` e `column_mappings.json` têm auto-restauração (integrity) via `core/config_manager.py`; respeitam `SSA_CONFIG_DIR`
- Proteção do “arquivo mais recente”: README/CHANGELOG e JSONs de config são ignorados

## Exportação
- CSV/XLSX/JSON em `docs_saida/` com rótulos consistentes (usa `display_mappings`)

## Hooks de Git (bloqueio de arquivos grandes)
- Pre-commit (>99MB): `scripts/pre-commit-size-check.ps1`
- Pre-push (objetos >=99MB no histórico): `scripts/pre-push-large-object-check.ps1`

Ativação:
```pwsh
pwsh -NoProfile -File scripts/setup-git-hooks.ps1
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

Filtrar por expressão:

```
PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh debug
```

Ambiente headless (Qt offscreen) já é configurado via `tests/conftest.py`. Se necessário reforçar manualmente:
```
QT_QPA_PLATFORM=offscreen ./scripts/run_tests.sh full
```

Documentação detalhada: `docs/TESTING_HEADLESS.md`.

### Quality Gates (Agregador)

O script `scripts/run_quality_gates.py` executa e consolida três (ou mais) gates de qualidade em uma única linha JSON:

Gates padrão:
- `validate_configs`: valida JSONs em `config/`.
- `smoke_cli`: execução mínima da CLI para garantir import e fluxo básico.
- `check_docs`: validação sintática/estrutural de arquivos Markdown selecionados.

Extensões:
- `--extra-config-dir <dir>` (pode repetir): cada diretório gera um gate adicional nomeado `validate_configs_extra_1`, `validate_configs_extra_2`, ... usando `validate_configs` apontado para aquele diretório via `--config-dir`.
- `--extra-doc <arquivo.md>` (pode repetir): adiciona arquivos ao escopo de `check_docs`.
- `--skip <gate>` / `--only <gate>`: filtram execução (`validate_configs`, `smoke_cli`, `check_docs`).
- `--no-fail-on-doc-issues`: torna problemas de documentação não-fatais (gate continua reportando issues porém status pode permanecer `ok`).

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
- `fail` tem precedência sobre `error` (um único gate `fail` define `overall_status=fail`).
- `error` usado para falhas internas (ex.: exceção inesperada, timeout, uso incorreto de argumento).

Exemplos:
```bash
# Caminho feliz completo
python scripts/run_quality_gates.py

# Apenas validar configs + dois diretórios extras
python scripts/run_quality_gates.py \
	--extra-config-dir caminho/dirA \
	--extra-config-dir caminho/dirB \
	--skip smoke_cli --skip check_docs

# Validar docs adicionais sem falhar por issues
python scripts/run_quality_gates.py --extra-doc README.md --no-fail-on-doc-issues
```

Teste dedicado: `tests/test_quality_gates_extra_config_dirs.py` assegura criação dos gates extras. Cenários de falha controlada: `tests/test_quality_gates_fail_paths.py`.

Boas práticas:
- Mantenha saída do script em **uma linha** (facilita parsing em pipelines).
- Para novos gates, seguir padrão de retorno (JSON parseável, exit codes 0/1/2) e adicionar documentação aqui.
- Evite acoplamento direto em CI: parse do `overall_status` é suficiente para bloquear.


### Estratégia de Testes (Governança)
Documento detalhado de pirâmide, fixtures, política de dtypes e limiares progressivos: consulte `docs/TESTING_STRATEGY.md`.

Executar smoke essencial (gates + núcleo integração rápido):
```
pytest -m "smoke" -q
```
Executar integração (exclui legacy/slow):
```
pytest -m "integration and not legacy and not slow" -q
```
Cobertura rápida dos módulos principais:
```
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Interface de Tabela (CLI) – Nova Implementação 2025-09

O módulo `interface/table_printer.py` foi reescrito para oferecer:

Principais características:
- Seleção dinâmica de colunas com prioridade (`essential`, `always_visible`, `priority_order`).
- Paginação estável com cabeçalho de página: `Página X de Y` e prompts interativos (`Enter`, `f`, `q`).
- Truncagem segura de descrições com largura mínima (`MIN_TRUNCATE_WIDTH = 8`) e expansão quando houver espaço.
- Heurística de largura baseada no percentil 95 do tamanho das células (evita efeito de outliers).
- Reatribuição adaptativa de espaço residual extra para `descricao_ssa` (até limite de 200 chars).
- Normalização de `numero_ssa` (_normalize_ssa) aplicada antes da renderização.
- Backwards compatibility: assinatura antiga de `_select_columns_for_width` ainda suportada por testes legados.
- Modo compacto automático quando:
	- largura do terminal < 100 colunas ou
	- número de colunas selecionadas >= 6
- Sanitização agressiva: remove controles ASCII, normaliza Unicode ⇒ ASCII, substitui vazio por `-`.
- Funções públicas exportadas: `pretty_print_df`, `format_dataframe_for_cli`, `paginate_dataframe`, `get_terminal_size`.

Constantes principais (ajude-se consultando o código):
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

### Uso Básico
```python
from interface.table_printer import pretty_print_df, format_dataframe_for_cli
import pandas as pd

df = pd.DataFrame([
		{"numero_ssa": "202512345", "situacao": "APL", "descricao_ssa": "Trocar válvula"},
		{"numero_ssa": "123", "situacao": "ADI", "descricao_ssa": "Inspeção"},
])

# Impressão paginada interativa
pretty_print_df(df, display_map={"numero_ssa": "Número SSA", "situacao": "Sit.", "descricao_ssa": "Descrição"}, settings={})

# Obter string formatada (sem paginação) – útil para logs ou export improvisado
table_str = format_dataframe_for_cli(df, display_map={"numero_ssa": "Número SSA"})
print(table_str)
```

### Configuração de Larguras e Visibilidade
- `config/column_priority.json` define: `essential`, `always_visible`, `priority_order`, `short_labels`, `fixed_widths`.
- `config/settings.json` (chave `display_settings`):
	- `column_widths`: mapeamento por rótulo (full/short) → largura fixa.
	- `column_visibility`: `{ "coluna_interna": true/false }` (false oculta, exceto se estiver em `always_visible`).

Mesclagem de larguras:
1. `fixed_widths` (por nome interno)
2. Override por rótulo em `display_settings.column_widths` (se rótulo curto/full corresponder)
3. Caso nada definido, estima via `_estimate_column_width` (percentil 95).

### Normalização do Número SSA
Regra (_resumida_):
- Remove não-dígitos.
- Menos que 5 dígitos ⇒ retorna como está (sem prefixo artificial nesta versão).
- 9 dígitos começando com `2025` ⇒ mantido.
- >=9 dígitos sem atender condição anterior ⇒ últimos 9.

### Comportamento de Paginação
- Tamanho de página = `linhas_terminal - LOW_HEIGHT_MARGIN` (margem = 8).
- `f` após qualquer página ativa “auto-scroll” até o fim.
- Se `auto_scroll_to_end=true` nas preferências e total de páginas > `max_auto_scroll_pages`, o auto-scroll é desativado silenciosamente para evitar flood.

### Boas Práticas / Extensão
- Para adicionar nova coluna “sempre visível” sem quebrar testes: inclua em `always_visible` no JSON e garanta que mapeamentos (`display_mappings.json`) tenham rótulo correspondente.
- Evite aumentar `MAX_DESC_WIDTH` acima de 200 sem avaliar quebra de layout em terminais pequenos.
- Se precisar suportar terminal extremamente estreito (<40 colunas), considere fallback adicional reduzindo ainda mais cabeçalhos (ex.: siglas).

### Testes Cobertos
- `_normalize_ssa`: casos curtos, 9 dígitos, excesso, caracteres mistos, `None`.
- `paginate_dataframe`: vazio, divisão exata, resto, page_size=1.
- Backward compatibility: testes antigos que chamam assinatura anterior de `_select_columns_for_width` continuam funcionando (wrapper aceita kwargs legados).

### Roadmap Futuro (Sugestões)
- Cache leve de larguras por hash de amostra para grandes DataFrames.
- Modo “raw export” ignorando truncagem (para piping em scripts): flag em settings.
- Otimização de re-render parcial quando apenas filtros alteram subconjunto de linhas (mantendo colunas fixas).

---


## Solução de problemas
- “Headers sumindo” em terminal estreito: use `-cols` e aumente a largura; colunas `always_visible` nunca são descartadas
- “Rótulo curto” inesperado: desative `prefer_short_labels` no `settings.json`
- “Filtro lento” na GUI: debounce já ativo; desmarque “Aplicar automaticamente” para aplicar só ao clicar
- “Mapeamento ausente/corrompido”: defina `SSA_CONFIG_DIR` e deixe o loader recriar os JSONs

## Notas
- Consulte `docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md` para pedidos/entregas/validação
- Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para decisões e linha do tempo técnica
