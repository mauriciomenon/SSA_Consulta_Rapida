# Importacao de Planilhas SSA

## CURRENT TRUTH

O caminho canonico de escrita de SSA usa
`extracao.extractor.extract_data_from_excel`. Ele atende:

- `core/import_single_file.py`
- `scripts/import_excel_file.py`
- `scripts/migracao/backfill_reprocessar.py`

`utils/robust_importer.py` continua ativo, mas em outro contrato: `read_report`,
sincronizacao de derivadas e simulacao. Ele nao deve substituir o extractor nos
dois CLIs de SSA, pois o filtro historico de linhas sem identidade e a
deduplicacao por `numero_ssa` nao preservam continuacoes hierarquicas.

## Pipeline canonico

1. Valida limites do XLSX e localiza as folhas elegiveis.
2. Detecta o cabecalho e aplica `config/column_mappings.json`.
3. No mapping default, compara aliases apos `strip`; com `--mappings` explicito,
   compara somente o header e os aliases literais fornecidos, normalizando caixa,
   acentos e espacos. Nao cria sinonimos nem coalesce campos de negocio.
4. Em ambos os modos, rejeita aliases ambiguos apos normalizacao e alvos
   internos reservados.
5. Normaliza `numero_ssa` e valida as colunas obrigatorias.
6. Captura grupos hierarquicos antes do filtro de identidade.
7. Remove somente linhas restantes sem identidade e publica o resumo em
   `DataFrame.attrs["invalid_row_summary"]`.
8. Publica eventos em `DataFrame.attrs["ssa_event_records"]`.
9. Aplica metadata do arquivo fisico e executa smart upsert de pais e eventos na
   mesma transacao.

Nao existe forward-fill de `numero_ssa`. A associacao de uma continuacao depende
de evidencia estrutural do grupo. Formato nao reconhecido com payload e
rejeitado de forma fechada em todos os callers canonicos.

## Registros hierarquicos

Cada evento persistido contem:

- `numero_ssa`
- `record_type`, `record_order` e `record_label`
- `payload_json`
- `arquivo_origem`, `data_planilha` e `data_arquivo_origem`
- `source_sheet` e `source_row`

A chave de idempotencia inclui SSA, tipo, ordem e payload. Em empate de snapshot,
a origem recebe desempate deterministico. O CLI confirma
`ssa_event_records_processed == eventos capturados`; divergencia encerra a
importacao em erro.

## Identidade invalida

O extractor informa, entre outras contagens:

- `total_removed`
- `payload_removed`
- `hierarchical_rows_captured`
- `hierarchical_records_captured`

`payload_removed > 0` levanta `UNSAFE_INVALID_IDENTITY_PAYLOAD` no core antes de
metadata, validacao ou upsert; o orquestrador interrompe a rodada sem promocao ou
cache. `scripts/import_excel_file.py` retorna erro e o backfill marca o arquivo
como falha. Nos dois CLIs, um arquivo com linhas de entrada, mas nenhuma linha
aceita, tambem retorna falha, inclusive em dry-run. No core principal,
`ALL_ROWS_REJECTED` e registrado como rejeicao deterministica e o lote continua.

## Metadata e recencia

`arquivo_origem`, `data_planilha` e `data_arquivo_origem` sao derivados do
arquivo fisico. Valores com esses nomes dentro da planilha nao podem rebaixar a
recencia nem separar a proveniencia do pai e dos eventos.

## Variantes de idioma

Cabecalhos sem alias comprovado continuam como colunas dinamicas sanitizadas.
Isso evita inventar equivalencia de negocio. Os campos DB
`deviation_records`, `situation_of_deviation`, `partial_records` e
`situation_of_partial` permanecem independentes dos campos PT; conflitos sao
preservados, nao coalescidos.

`data_planilha` e metadata operacional separada. Ela nao e alias de campo de
desvio/parcial e nao e coluna legada.

## CLI de arquivo unico

Dry-run seguro:

```bash
uv run --python 3.13 scripts/import_excel_file.py \
  --file "docs_entrada/arquivo.xlsx" \
  --db data/ssas.db \
  --dry-run
```

Escrita SSA:

```bash
uv run --python 3.13 scripts/import_excel_file.py \
  --file "docs_entrada/arquivo.xlsx" \
  --db data/ssas.db \
  --table ssas \
  --smart-upsert
```

Contratos:

- `--dry-run` extrai e valida sem escrever
- tabela SSA exige `--smart-upsert`
- evento hierarquico exige `--smart-upsert`
- `--reset-db` e rejeitado antes de qualquer escrita
- `--mappings` aceita arquivo customizado, com validacao estrita

## Backfill

```bash
uv run --python 3.13 scripts/migracao/backfill_reprocessar.py \
  --dir docs_entrada \
  --db data/ssas.db \
  --pattern "*.xlsx" \
  --smart-upsert \
  --dry-run
```

Sem `--dry-run`, `--smart-upsert` e obrigatorio. `--reset-db` e rejeitado. Para
recriar o banco, use o full rescan, que trabalha com banco candidato e promocao
validada.

## Utilitario robust_importer

O utilitario antigo ainda oferece reheader, coalescencia, parsing de datas e
deduplicacao para seus consumidores especificos. Seu `ImportStats` continua
valido nesse caminho. Essas estatisticas nao descrevem o contrato do extractor
canonico e nao devem ser usadas para justificar descarte de linhas SSA.

## Testes de contrato

- `tests/test_extracao.py`
- `tests/test_import_excel_file.py`
- `tests/test_backfill_script.py`
- `tests/test_upsert_behaviors.py`
- `tests/test_db_reset_and_upsert.py`

<!-- DOC_SYNC_MAC: 2026-08-11 canonical hierarchy-safe import path -->
