# Diário de Implementações e Preferências

Este arquivo documenta solicitações, decisões e implementações recentes para rastreabilidade.

## Configurações e Preferências
- Prioridades/labels de colunas: `config/column_priority.json`
  - `priority_order`: ordena colunas no CLI/GUI (primeiro as essenciais).
  - `short_labels`: rótulos curtos (ex.: numero_ssa -> "No", setor_executor -> "Exec").
- Mapeamento verboso para detalhes: `config/display_mappings.json`.
- Regras de formatação em CLI/GUI:
  - SSA: normalizada para 9 dígitos; sufixos de até 5 dígitos recebem prefixo de ano atual (2025).
  - Datas: exibem somente a parte de data (removido horário) para colunas que contenham "data"/"emit" no nome.
  - Semanas (semana_*): não exibir sufixo ".0" e inteiros sem casas decimais.
  - Valores nulos: suprimidos na renderização (sem "nan"/"NaT"/"None").

## GUI
- Filtros:
  - Busca livre por texto.
  - Combo de Executor (setor_executor) e Situação (situacao).
  - Filtro opcional por período de Data de Cadastro (checkbox + QDateEdit início/fim).
- Paginação dupla: mantém alinhamento entre dados "raw" e exibidos para o diálogo de detalhes.
- Diálogo de Detalhes: acessível por duplo-clique ou botão, renderiza via `interface.display.pretty_print_details` usando rótulos verbosos.
- Cabeçalhos: usam `short_labels` do config quando disponíveis.
- Formatação compartilhada: GUI agora usa `interface.table_printer.format_cell_data` para exibição consistente (datas/semana/SSA/NaN).

## CLI
- Exibição tabular adaptativa a largura do terminal.
- Seleção de colunas baseada em `priority_order` e essenciais; primeira coluna `#` para numeração.
- Formatação aplicada antes de renomear cabeçalhos (SSA, semanas, datas).

## Banco de Dados
- Normalização de `numero_ssa` aplicada no momento do upsert (`armazenamento.database.normalize_numero_ssa`), assegurando consistência entre DB/CLI/GUI.

## Testes
- 29 testes passando.
- `tests/test_cli_formatting.py`: verifica short labels e normalização do número de SSA.
- `tests/test_table_printer.py`: largura/seleção de colunas, paginação, e pretty_print_df.

## Itens Pendentes / Próximos Passos
- Smoke test manual da GUI com dados reais (checar filtros por data, detalhes e ordenação).
- Ajustar/expandir testes para mais campos formatados (datas/semana) quando necessário.
- Opcional: mover normalização de SSA para camada de dados para consistência no banco.
