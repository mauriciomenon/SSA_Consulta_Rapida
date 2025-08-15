# CHANGELOG_IMPLEMENTACOES – Diário Técnico Completo

Linha do tempo abrangente do projeto SSA_Consulta_Rapida: decisões, arquitetura, correções, otimizações e cobertura de testes. Foco em previsibilidade, desempenho e paridade CLI/GUI. Atualizado em 2025-08-15.

## 2025-08-15
- Correção de regressão na CLI: consertado bloco de exibição inicial e `try/except` após adição de `-clear`, `-clearall` e `-f/-filtros`. 50 → 51 testes.
- Seleção de colunas em terminais estreitos: colunas `always_visible` nunca são descartadas; estimativa de largura usa `short_labels`. Novo teste para largura extremamente pequena.
- Novo documento de rastreabilidade criado: `MAPA_PEDIDOS_IMPLEMENTACOES.md` mapeando pedidos → commits, incluindo ajustes e itens pendentes de commit (integrity checks de configs e proteções adicionais de arquivos críticos).

## 2025-08-14
- Paridade CLI/GUI de formatação: detalhes na CLI usam `utils.formatting.format_cell` (datas dd/mm/YYYY, suprimir .0, `nan/NaT/None` escondidos, semanas inteiras, SSA normalizado).
- Lista e manipulação de filtros (CLI):
	- `-f`/`-filtros`: mostra filtros atuais da pilha.
	- `-clear`: limpa filtros do usuário, mantendo default da sessão.
	- `-clearall`: limpa filtros do usuário e default para a sessão, recarregando o estado.
- Banner/versão: versão curta e longa de `config/version.json` via `utils/version.py`.

## 2025-08-13
- Resolução de conflito e restauração de `config/column_priority.json` (versão mais detalhada):
	- Campos: `essential`, `always_visible`, `priority_order`, `fixed_widths`, `short_labels`.
	- `interface/table_printer.py` passa a: mesclar `fixed_widths` com `settings.display_settings.column_widths` (por rótulo), respeitar `column_visibility`, e usar `short_labels` nos headers.
- Testes ampliados para seleção inteligente de colunas, truncação com reticências apenas quando necessário e visibilidade obrigatória.

## 2025-08-12
- CLI: comandos restaurados e ampliados:
	- `-ordn`/`-ordni` (ordenar por nome de coluna – display ou interno).
	- `-cols` (listar colunas com índice e rótulos de exibição).
	- `-x [termo]` (remover termo do filtro atual; sem termo = `-v`).
- Atualização da ajuda e mensagens do prompt; `NO_COLOR` respeitado para destaque.
- Testes adicionados para comandos novos (subindo a suíte para ~48).

## 2025-08-10
- GUI: debounce de filtro (~350ms) e opção para desativar aplicação automática a cada tecla. Paginator robusto; correção de crash em inicialização quando não há dados.
- Fallback GUI→CLI no `main.py` com log amigável em caso de erro de GUI.

## 2025-08-08
- Formatação unificada (`utils/formatting.py`) para todas as superfícies:
	- Números sem sufixo `.0` quando inteiros aparentes.
	- Datas exibidas como dd/mm/YYYY.
	- Semanas sem casas decimais.
	- Valores nulos ocultos (mostrando `-` quando fizer sentido na UI).
	- Normalização de SSA (9 dígitos; prefixo ano quando <=5; `zfill` para 7-8).
- `interface/display.py`: detalhes usam `format_cell` e padronizam vazios.

## 2025-08-05
- Banco de dados/ingestão:
	- Reset granular (`--reset-db file|table`).
	- Índices com criação protegida/idempotente.
	- Upsert inteligente por `numero_ssa` com desempate por `data_cadastro` (mais novo vence).
	- Normalização de `numero_ssa` na extração/carga.
- Testes de ingestão, normalização e índices.

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
