# Importacao Robusta de Planilhas SSA

Este documento descreve o pipeline "a prova de bala" de ingestao de planilhas Excel (`.xlsx`) contendo registros de SSA.

## Objetivos Principais

- Aceitar variacoes de cabecalho (acentos, maiusculas, espacamento, quebras de linha, grafias alternativas).
- Colapsar sinonimos em um unico nome canonico usando `config/column_mappings.json`.
- Evitar duplicacao logica de colunas (coalescencia linha a linha quando multiplas colunas representam o mesmo campo).
- Normalizar `numero_ssa` e descartar linhas sem valor valido (opcional).
- Parsing resiliente de datas em varios formatos (ISO, dd/mm/yyyy, dd-mm-yyyy, serial Excel numerico).
- Deduplicar registros pelo mesmo `numero_ssa` mantendo o mais recente (maior `data_cadastro`).
- Evitar sobrescrever dados ja existentes com valores vazios durante upsert.
- Gerar estatisticas detalhadas para auditoria.

## Componentes Envolvidos

| Arquivo | Responsabilidade |
|---------|------------------|
| `utils/robust_importer.py` | Funcao `import_excel_robust` que implementa normalizacao e estatisticas. |
| `config/column_mappings.json` | Mapeamento de sinonimos para nomes canonicos. |
| `scripts/import_excel_file.py` | CLI para importacao (dry-run, reset, upsert inteligente). |
| `armazenamento/database.py` | Logica de insercao e upsert preservando dados. |
| `scripts/simulate_import_and_gui.py` | Integra import real + lotes sinteticos + teste de GUI offscreen. |

## Pipeline de Normalizacao

1. **Leitura**: `pandas.read_excel` abre a planilha original.
2. **Canonizacao de Cabecalhos**: para cada coluna:
   - Remove quebras de linha e multiplos espacos.
   - Normaliza acentuacao (NFKD) e converte para minusculas.
   - Consulta `column_mappings.json` para resolver sinonimo → canonico.
3. **Agrupamento de Colunas Semanticas**: colunas diferentes que apontam ao mesmo canonico sao agrupadas.
4. **Coalescencia**: valores linha-a-linha: primeira coluna do grupo prevalece; valores vazios sao preenchidos por colunas alternativas subsequentes.
5. **Normalizacao de `numero_ssa`**: digitos extraidos e validados (YYYY + 5 digitos). Linhas invalidas podem ser descartadas (opcao padrao).
6. **Parsing Resiliente de Datas**: cada coluna de data candidata e convertida tentando:
   - ISO direto (`YYYY-MM-DD...`) sem `dayfirst`.
   - Formato dia/mes/ano (`dayfirst=True`).
   - Tentativa final invertida (`dayfirst=False`).
   - Numeros inteiros / floats tratados como serial Excel (origem `1899-12-30`).
   - Resultado final em `YYYY-MM-DD HH:MM:SS` ou `None`.
7. **Deduplicacao**: se existir `numero_ssa`, ordena por `numero_ssa` e data (desc) e mantem a primeira (mais recente); contabiliza descartes.
8. **Estatisticas**: estrutura `ImportStats` registra linhas totais, linhas apos filtro, merges, falhas de data, duplicatas removidas, etc.

## Estrategia de Deduplicacao

- Chave: `numero_ssa`.
- Criterio de escolha: maior `data_cadastro` (datas nulas perdem para validas; entre nulas, mantem a primeira encontrada em ordem original).
- Beneficio: evita crescer indefinidamente com versoes multiplas da mesma SSA.

## Regra de Merge no Upsert

Arquivo: `armazenamento/database.py` funcao interna `_perform_upsert`.

Para cada `numero_ssa` ja existente:
- Se `_should_update_existing` aprova (regra de data: nova data >= existente ou casos de ausencia conforme definido), entao procede.
- Monta um registro mesclado coluna a coluna:
  - Se valor novo e vazio (`None`, NaN ou string branca) mantem o valor antigo.
  - Caso contrario substitui pelo novo.
- Esse merge evita perda involuntaria de campos preenchidos anteriormente quando a nova fonte traz colunas parciais.

## Interpretacao das Estatisticas (Exemplo)

```json
{
  "total_rows_in": 850,
  "total_rows_out": 820,
  "original_columns_count": 45,
  "mapped_columns_count": 38,
  "dropped_columns": [],
  "merged_columns": { "situacao": ["Situacao", "Status" ] },
  "date_parse_failures": { "data_cadastro": 12, "prazo_limite": 5 },
  "duplicate_rows_dropped": 18,
  "invalid_numero_ssa_rows": 12,
  "file_path": "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx"
}
```

Campo | Significado
------|------------
`total_rows_in` | Linhas lidas originalmente.
`total_rows_out` | Linhas apos descartes/deduplicacao.
`merged_columns` | Colunas sinonimas que foram coalescidas.
`date_parse_failures` | Contagem de celulas que nao puderam ser interpretadas como data (mantidas como `None`).
`duplicate_rows_dropped` | Quantos registros a mais com mesmo `numero_ssa` foram removidos.
`invalid_numero_ssa_rows` | Linhas descartadas por `numero_ssa` invalido.

## CLI de Importacao

Uso rapido:
```bash
python3 scripts/import_excel_file.py \
  --file "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx" \
  --db data/ssas.db \
  --table ssas \
  --reset-db --smart-upsert --verbose
```

- `--dry-run`: nao insere no banco, apenas exibe estatisticas.
- `--reset-db`: recria o banco antes de inserir (aplica `schema.sql`).
- `--smart-upsert`: habilita logica de preservacao + deduplicacao incremental.

## Integracao com Simulacao GUI

`simulate_import_and_gui.py` aceita `--excel` e `--import-real-once`:
- Importa a planilha real antes de gerar lotes sinteticos.
- Permite aquecer o banco e testar carregamento + filtragem na GUI.

## Boas Praticas & Extensoes Futuras

- Adicionar testes unitarios fabricando cenarios: sinonimos multiplos, datas malformadas, numeros seriais.
- Gerar relatorio CSV de estatisticas historicas de import para auditoria.
- Implementar verificacao opcional de colisao sem atualizacao (ex.: logar quando `_should_update_existing` recusa update).
- Suporte a multiplos arquivos por lote (concat + pipeline unico).
- Flag para permitir sobrescrever com vazio (politica inversa) em casos de limpeza intencional.

## Limitacoes Atuais

- Datas sem ano explicito nao sao inferidas.
- Campos textuais muito longos nao sao truncados no import (apenas no schema/DB se houver restricao posterior).
- Nao ha ainda validacao cruzada entre campos (ex.: consistencia de semanas versus data).

## Resumo

O pipeline garante ingestao resiliente e idempotente, reduzindo riscos de perda de dados e minimizando ruido causado por variacoes de planilhas fornecidas por diferentes setores.

---
_Manter este documento atualizado sempre que a semantica de importacao ou upsert for alterada._

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

