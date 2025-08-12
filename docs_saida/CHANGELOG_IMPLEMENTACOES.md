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
- Painel de detalhes inferior: mostra automaticamente os detalhes da linha selecionada; atualiza na mudança de seleção.
- Cabeçalhos: usam `short_labels` do config quando disponíveis.
- Formatação compartilhada: GUI agora usa `interface.table_printer.format_cell_data` para exibição consistente (datas/semana/SSA/NaN).

## CLI
- Exibição tabular adaptativa a largura do terminal.
- Seleção de colunas baseada em `priority_order` e essenciais; primeira coluna `#` para numeração.
- Formatação aplicada antes de renomear cabeçalhos (SSA, semanas, datas).

## Banco de Dados
- Reset do DB:
  - `reset_database(db_path, mode='file'|'table')`: apaga o arquivo e recria via schema (file) ou apenas limpa a tabela `ssas` (table).
  - `main.py` expõe `--reset-db` antes da importação para cenários de limpeza total.
- Upsert inteligente e versionamento:
  - `insert_dataframe_with_smart_upsert()` agora armazena `arquivo_origem`, `data_arquivo_origem` e `data_importacao`, e controla `versao_dados` por SSA.
  - Critério principal: data do arquivo (extraída do nome) — arquivos mais novos substituem dados antigos.
  - Empate/sem data: desempate por avanço de situação (ordem preferencial: ASE, ADI, ASE, ADI, APL, APG, SPG, SEE, SAD, STE).
  - Correção: incremento de `versao_dados` é persistido na linha inserida.
## Arquitetura, arquivos e funções (guia para devs)
- Entry point: `main.py`
  - Orquestra inicialização (pastas, DB/schema, importador), carrega dados (`armazenamento.database.query_db`), configura display map, inicia CLI ou GUI.
  - Lê e indica ao dev o arquivo `docs_saida/CHANGELOG_IMPLEMENTACOES.md` (este guia).
  - Sugere configurar hook de pre-commit para bloquear arquivos >99MB.
- Camada Core:
  - `core/app_logic.py`
    - `run_importer_logic()`: decide quais arquivos Excel importar, coordena extração, validação e inserção no DB; atualiza cache.
    - `filter_dataframe()`: filtro rápido vetorizado por termos em colunas de alta relevância; usado por CLI/GUI.
    - `advanced_filter_dataframe()`: filtros por termos, executor, situação, e período de data de cadastro; usado pela GUI.
    - `run_scheduled_exports()`: dispara exportações agendadas.
  - `core/config_manager.py`: carrega settings, mapeamentos e utilidades de configuração.
- Persistência:
  - `armazenamento/database.py`
    - `get_db_connection()`: conexão SQLite com PRAGMAs seguros.
    - `initialize_database()`: aplica schema de `config/schema.sql`.
    - `create_indexes()`: cria índices úteis.
    - `query_db()`: SELECT como DataFrame.
    - `insert_dataframe_to_db()`: inserção chunked com conversões para SQLite.
    - `normalize_numero_ssa()`: normaliza número da SSA para 9 dígitos; usada no upsert.
    - `insert_dataframe_with_smart_upsert()`: insere/atualiza por número de SSA e data do arquivo de origem (controle de versão).
- Extração/Validação:
  - `extracao/extractor.py`: extrai DataFrames dos relatórios Excel.
  - `utils/data_validation.py`: validações dos dados (mensagens de aviso).
  - `utils/file_metadata.py`: extrai data/hora do nome do arquivo e decide atualização (`should_update_ssa`).
- Interface CLI:
  - `interface/cli.py`
    - Loop de comandos com paginação ou rolagem contínua; exportação; detalhes por linha/SSA; agora com opção para adicionar filtro extra quando há muitos resultados.
  - `interface/table_printer.py`
    - `format_dataframe_for_cli()`: resolve prioridades, aplica rótulos curtos, pré-formata campos, aloca larguras e imprime tabela.
    - `format_cell_data()`: regra única de formatação (datas, semanas, SSA, NaN) compartilhada com GUI.
    - Auxiliares: seleção por largura (`_select_columns_for_width`), truncamento inteligente etc.
  - `interface/display.py`: `pretty_print_details()` imprime detalhes legíveis por humano.
- Interface GUI:
  - `gui/app_gui.py`
    - Janela principal com filtro de texto, Executor, Situação e filtro opcional por data; paginação dupla e detalhes por duplo-clique/botão.
    - Aplica `format_cell_data` a todas as colunas para consistência com CLI; usa prioridades/short_labels do config.
- Exportação:
  - `exportacao/exporter.py`, `exportacao/scheduled_exporter.py`: exportações imediatas e agendadas.
- Utilitários:
  - `utils/pagination.py`: Paginator usado em CLI/GUI.
  - `utils/caching.py`: cache de arquivos importados.
  - `utils/file_metadata.py`: extração de data/hora do nome de arquivo e decisão de atualização por data (com testes).

## Hooks de Git para arquivos grandes
- Pre-commit: `scripts/pre-commit-size-check.ps1` bloqueia arquivos >99MB por tamanho.
- Pre-push: `scripts/pre-push-large-object-check.ps1` bloqueia pushes que contenham objetos Git >99MB (histórico).
  - Para ativar: copie para `.git/hooks/pre-push` e configure `core.hooksPath` (ver comentários no `main.py`).

## Mapeamento de testes -> funções
- `tests/test_table_printer.py` → `interface.table_printer`: seleção/ordem/formatador e paginação.
- `tests/test_cli_formatting.py` → `format_dataframe_for_cli`: rótulos curtos e SSA 9 dígitos.
- `tests/test_formatting_rules.py` → `format_cell_data`, `format_dataframe_for_cli`, `advanced_filter_dataframe`: semanas sem .0, datas sem horário, cabeçalhos, filtro por período.
- `tests/test_database.py` → `armazenamento.database`: conexão, init schema, to_sql chunked, query.
- `tests/test_ssa_normalization_db.py` → `normalize_numero_ssa`: normalização de SSA.
- `tests/test_extracao.py` → `extracao.extractor`: extração básica.
- `tests/test_display.py` → `interface.display.pretty_print_details`.
- `tests/test_interface.py` → integrações leves CLI/formatador.
- `tests/test_exporter.py` → exportadores.
- `tests/test_caching.py` → `utils.caching`.

## Notas de projeto e contrato de exibição
- Prioridades de colunas e rótulos curtos em `config/column_priority.json` (GUI e CLI consomem).
- Regras fixas de exibição: sem “.0” em semanas, datas sem horário, sem “nan/NaT/None”, SSA com 9 dígitos.
- Formatação é aplicada antes de renomear cabeçalhos para evitar ambiguidades com short labels.

- Normalização de `numero_ssa` aplicada no momento do upsert (`armazenamento.database.normalize_numero_ssa`), assegurando consistência entre DB/CLI/GUI.

## Testes
- 47 testes passando.
- `tests/test_cli_formatting.py`: verifica short labels e normalização do número de SSA.
- `tests/test_table_printer.py`: largura/seleção de colunas, paginação, e pretty_print_df.
- `tests/test_db_reset_and_upsert.py`: cobre reset do DB (arquivo/tabela) e upsert com preferência por arquivo mais recente e desempate por situação.

## Itens Pendentes / Próximos Passos
- Smoke test manual da GUI com dados reais (checar filtros por data, detalhes e ordenação).
- Ajustar/expandir testes para mais campos formatados (datas/semana) quando necessário.
- Opcional: mover normalização de SSA para camada de dados para consistência no banco.
