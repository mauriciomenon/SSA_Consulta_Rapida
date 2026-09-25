# Schema Unificado e Importacao

## Current truth

O schema canonico usa `ssa_table` e mantem `ssas` e `ssa_chamados` como nomes de
compatibilidade. A importacao principal usa
`extracao.extractor.extract_data_from_excel` e o smart upsert.

## Arquivos de schema

- `config/schema.sql`: schema runtime padrao.
- `config/schema_unified.sql`: schema unificado mantido para fluxos que o
  selecionam explicitamente.
- `config/column_mappings.json`: aliases de cabecalho comprovados.

Novas equivalencias de negocio nao devem ser inferidas a partir do nome
sanitizado de uma coluna DB. Um alias novo exige cabecalho de origem comprovado,
teste positivo e teste negativo.

## Tabelas principais

### ssa_table

Armazena uma linha corrente por SSA. O smart upsert preserva valores existentes
quando o snapshot novo traz vazio e aplica o contrato de recencia documentado em
`docs/ARCH_DB_UPSERT.md`.

`data_planilha` e metadata ativa de snapshot. Nao e coluna legada nem alias de
campo de negocio.

### ssa_event_records

Armazena ocorrencias hierarquicas de desvio, reprogramacao e execucao parcial
que nao cabem em uma unica linha principal.

Colunas exigidas no schema:

- identidade: `numero_ssa`
- evento: `record_type`, `record_order`, `record_label`, `payload_json`
- proveniencia: `arquivo_origem`, `data_planilha`, `data_arquivo_origem`
- origem fisica: `source_sheet`, `source_row`

`data_planilha` e `data_arquivo_origem` aceitam `NULL` quando a origem nao
oferece timestamp confiavel. Identidade, tipo, ordem, label, payload, nome do
arquivo, folha e linha fisica sao `NOT NULL`.

A restricao unica usa
`(numero_ssa, record_type, record_order, payload_json)`. O reset de uma tabela
SSA valida colunas e executa um insert real sob SAVEPOINT antes de promover o
banco candidato.

## Colunas dinamicas e idiomas

O upsert pode adicionar cabecalhos nao canonicos como colunas dinamicas
sanitizadas. Os identificadores DB abaixo foram produzidos por imports EN reais
e permanecem campos independentes:

- `deviation_records`
- `situation_of_deviation`
- `partial_records`
- `situation_of_partial`

Eles nao sao apagados, ocultados como legados nem coalescidos automaticamente
com os campos PT. A grafia humana do cabecalho bruto so pode virar alias quando
o XLSX de origem estiver disponivel ou outra evidencia direta provar a forma
exata.

## Extracao e persistencia

1. O extractor valida e aplica mappings estritos.
2. Continuacoes hierarquicas sao capturadas antes do filtro de identidade.
3. Linhas sem identidade restantes geram `invalid_row_summary`.
4. Todo caller canonico bloqueia payload removido; os CLIs auxiliares tambem
   bloqueiam escrita SSA sem smart upsert.
5. O smart upsert persiste pai e eventos em uma transacao. Os callers canonicos
   passam `metrics_out` e exigem as contagens de insert, update e eventos.

`utils/robust_importer.py` permanece um utilitario para `read_report`, derivadas
e simulacao. Ele nao e o parser de escrita dos CLIs auxiliares de SSA.

## Migracao incremental

`scripts/migracao/migrar_para_unificado.py` adiciona colunas ausentes e cria
backup antes da migracao. Ele nao recupera eventos historicos removidos de
planilhas antigas.

Para recriacao completa, use o full rescan. Os utilitarios
`scripts/import_excel_file.py` e `scripts/migracao/backfill_reprocessar.py`
rejeitam `--reset-db` porque nao promovem um banco completo de forma atomica.

## Testes relacionados

- `tests/test_extracao.py`
- `tests/test_import_excel_file.py`
- `tests/test_backfill_script.py`
- `tests/test_upsert_behaviors.py`
- `tests/test_db_reset_and_upsert.py`

## Historical snapshot

As heuristicas de reheader, coalescencia e `ImportStats` documentadas em 2025
continuam pertencendo a `utils/robust_importer.py`. Elas nao representam o
pipeline canonico atual de escrita SSA.

<!-- DOC_SYNC_MAC: 2026-08-11 canonical schema and event records -->
