# CHANGELOG_IMPLEMENTACOES – Diário Técnico Completo

Linha do tempo abrangente do projeto SSA_Consulta_Rapida: decisões, arquitetura, correções, otimizações e cobertura de testes. Foco em previsibilidade, desempenho e paridade CLI/GUI. Atualizado em 2025-08-15.

Como ler:
- Cada dia traz tópicos, impacto e onde validar (arquivos/testes). Use em conjunto com o MAPA.

## 2025-08-15
Patch 3.0.2 (hotfix CLI/GUI):
- CLI tabela: restaura labels (display/short), aplica larguras fixas e ordem/prioridade; truncagem por largura fixa pós-formatação para melhor aproveitamento do terminal.
- GUI: corrige import path para utils ao executar `python .\\gui\\gui_ssa.py`.
- Ajuste de larguras padrão: `localizacao_codigo=10`, `setor_executor=6`, `setor_emissor=6`, `data_cadastro=12`, `derivada_de=11`.

Patch 3.0.1 (manutenção CI/linters):
- ESLint (SARIF): execução e upload condicionais (somente quando houver JS/TS e configuração); correção de comando multiline e remoção de `--config` inexistente.
- PSScriptAnalyzer (SARIF): execução e upload condicionais (somente quando houver PowerShell); path POSIX e passo explícito de skip.
- Remoção do workflow CodeQL avançado que conflita com o Default Setup (elimina erros de processamento de análises).

- Filtro “5 opções” implementado end-to-end:
	- Parser compartilhado `core/app_logic.parse_search_terms` e aplicação em `filter_dataframe`
	- Negativos com `!`/`-`; regex com fallback para literal quando inválida
	- Detalhe: com modo padrão `regex`, `^`/`$` agem como âncoras, não como trocadores de modo
	- CLI/GUI integram o parser; CLI ajuda e GUI tooltip atualizados
- Preferência `user_preferences.filter_mode_default` configurável via `-c` (menu simples)
- GUI: proteção de instância única (main.py) para evitar múltiplas janelas abertas
- Testes novos: `tests/test_filter_modes.py`, `tests/test_default_filter_mode.py` → suíte agora com 67 testes
- CLI: correção de regressão na exibição inicial e tratamento de exceções após `-clear`, `-clearall`, `-f/-filtros`.
- Seleção em terminais estreitos: `always_visible` nunca somem; estimativa usa `short_labels`. Adicionado teste de largura extrema.
- MAPA de pedidos criado/expandido: `docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md` com pedidos → entregas → validação, incluindo larguras fixas e plano do filtro “5 opções”.
- Integridade e proteção: `display_mappings.json` com auto-restauração e log (core/config_manager.py); adicionada a lista de protegidos (utils/file_metadata.py).
- Integridade (novo): `column_mappings.json` com loader (core/config_manager.load_column_mappings_integrity), uso no extractor e proteção em `utils/file_metadata.py`. Teste dedicado `tests/test_column_mappings_integrity.py`.

Como validar hoje:
- `pytest -q` deve reportar 56 passed.
- Remova temporariamente `display_mappings.json` ou `column_mappings.json` em um `SSA_CONFIG_DIR` de teste e rode a aplicação: os arquivos serão recriados com log.

## 2025-08-14
- Paridade CLI/GUI de formatação: detalhes na CLI usam `utils.formatting.format_cell` (datas dd/mm/YYYY, suprimir .0, `nan/NaT/None` escondidos, semanas inteiras, SSA normalizado).
- Lista e manipulação de filtros (CLI):
	- `-f`/`-filtros`: mostra filtros atuais da pilha.
	- `-clear`: limpa filtros do usuário, mantendo default da sessão.
	- `-clearall`: limpa filtros do usuário e default para a sessão, recarregando o estado.
- Banner/versão: versão curta e longa de `config/version.json` via `utils/version.py`.

Validação rápida:
- Conferir CLI com buscas contendo números inteiros e datas; verificar ocultação de nulos e formato de datas.

## 2025-08-13
- Resolução de conflito e restauração de `config/column_priority.json` (versão mais detalhada):
	- Campos: `essential`, `always_visible`, `priority_order`, `fixed_widths`, `short_labels`.
	- `interface/table_printer.py` passa a: mesclar `fixed_widths` com `settings.display_settings.column_widths` (por rótulo), respeitar `column_visibility`, e usar `short_labels` nos headers.
- Testes ampliados para seleção inteligente de colunas, truncação com reticências apenas quando necessário e visibilidade obrigatória.

Validação rápida:
- Reduzir o terminal e confirmar que `numero_ssa` permanece visível; observar headers alternando para short_labels quando necessário.

## 2025-08-12
- CLI: comandos restaurados e ampliados:
	- `-ordn`/`-ordni` (ordenar por nome de coluna – display ou interno).
	- `-cols` (listar colunas com índice e rótulos de exibição).
	- `-x [termo]` (remover termo do filtro atual; sem termo = `-v`).
- Atualização da ajuda e mensagens do prompt; `NO_COLOR` respeitado para destaque.
- Testes adicionados para comandos novos (subindo a suíte para ~48).

Validação rápida:
- `-ordn` com nome de rótulo e `-x` para remoção de termo específico.

## 2025-08-10
- GUI: debounce de filtro (~350ms) e opção para desativar aplicação automática a cada tecla. Paginator robusto; correção de crash em inicialização quando não há dados.
- Fallback GUI→CLI no `main.py` com log amigável em caso de erro de GUI.

Validação rápida:
- Habilitar/desabilitar “Aplicar automaticamente” e observar a diferença de desempenho.

## 2025-08-08
- Formatação unificada (`utils/formatting.py`) para todas as superfícies:
	- Números sem sufixo `.0` quando inteiros aparentes.
	- Datas exibidas como dd/mm/YYYY.
	- Semanas sem casas decimais.
	- Valores nulos ocultos (mostrando `-` quando fizer sentido na UI).
	- Normalização de SSA (9 dígitos; prefixo ano quando <=5; `zfill` para 7-8).
- `interface/display.py`: detalhes usam `format_cell` e padronizam vazios.

Validação rápida:
- Abrir o painel de detalhes na GUI e comparar com a tabela.

## 2025-08-05
- Banco de dados/ingestão:
	- Reset granular (`--reset-db file|table`).
	- Índices com criação protegida/idempotente.
	- Upsert inteligente por `numero_ssa` com desempate por `data_cadastro` (mais novo vence).
	- Normalização de `numero_ssa` na extração/carga.
- Testes de ingestão, normalização e índices.

Validação rápida:
- Rodar `--reset-db table` e reimportar; conferir que SSAs com mesma chave respeitam desempate por `data_cadastro`.

## 2025-07-31
- CLI tabela: seleção adaptativa por largura do terminal; truncação inteligente de descrições com reticências apenas se houver truncamento; cabeçalhos com `short_labels` quando disponíveis.
- Integração do `display_mappings.json` e `column_mappings.json` na apresentação.

## 2025-07-28
- Recuperação de recursos históricos perdidos após merge: alias de journal, versionamento, prioridades ricas, e testes que haviam sumido.
- Aliases de comandos: `--rescan` no main e CLI, suporte a execução a partir de subpastas (import relativo robusto).

## 2025-07-25
- CLI: novos comandos
	- `-ordn`/`-ordni` para ordenar por nome (interno/exibição).
	- `-cols` para listar colunas com índices e nomes de exibição.
	- `-x [termo]` para remover termo do filtro atual.
- Testes: +3 casos para a CLI.

## 2025-07-20
- Infra de testes consolidada (pytest), cobrindo: CLI, seleção de colunas, formatação, exibição de detalhes, exportação, caching de arquivos e metadados, reset/upsert de DB, normalização SSA.

## 2025-07-10 – 2025-07-18 (Fundação)
- Estrutura inicial do projeto (CLI e GUI) com `main.py` orquestrando modos.
- `extracao/` e `armazenamento/` com schema em `config/schema.sql`.
- `exportacao/` com exportador CSV/JSON/XLSX.
- Configurações em `config/settings.json`, labels em `display_mappings.json` e prioridades em `column_priority.json`.
- Primeiros testes de ponta a ponta e utilitários (`utils/file_metadata.py`, `utils/caching.py`).

---

Decisões de design e políticas de qualidade
- Foco em previsibilidade e paridade CLI/GUI: toda lógica de formatação é compartilhada.
- Desempenho e UX: GUI com debounce e paginação; CLI com seleção adaptativa de colunas.
- Segurança de dados: upsert determinístico; índices idempotentes; resets explícitos.
- Config > código: labels, prioridades, larguras e visibilidade por JSON; versão via `version.json`.
- Testes para tudo: não encerrar com build quebrado; aumentar cobertura junto com features.
