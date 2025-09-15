# Importação Robusta de Planilhas SSA

Este documento descreve o pipeline "à prova de bala" de ingestão de planilhas Excel (`.xlsx`) contendo registros de SSA.

## Objetivos Principais

- Aceitar variações de cabeçalho (acentos, maiúsculas, espaçamento, quebras de linha, grafias alternativas).
- Colapsar sinônimos em um único nome canônico usando `config/column_mappings.json`.
- Evitar duplicação lógica de colunas (coalescência linha a linha quando múltiplas colunas representam o mesmo campo).
- Normalizar `numero_ssa` e descartar linhas sem valor válido (opcional).
- Parsing resiliente de datas em vários formatos (ISO, dd/mm/yyyy, dd-mm-yyyy, serial Excel numérico).
- Deduplicar registros pelo mesmo `numero_ssa` mantendo o mais recente (maior `data_cadastro`).
- Evitar sobrescrever dados já existentes com valores vazios durante upsert.
- Gerar estatísticas detalhadas para auditoria.

## Componentes Envolvidos

| Arquivo | Responsabilidade |
|---------|------------------|
| `utils/robust_importer.py` | Função `import_excel_robust` que implementa normalização e estatísticas. |
| `config/column_mappings.json` | Mapeamento de sinônimos para nomes canônicos. |
| `scripts/import_excel_file.py` | CLI para importação (dry-run, reset, upsert inteligente). |
| `armazenamento/database.py` | Lógica de inserção e upsert preservando dados. |
| `scripts/simulate_import_and_gui.py` | Integra import real + lotes sintéticos + teste de GUI offscreen. |

## Pipeline de Normalização

1. **Leitura**: `pandas.read_excel` abre a planilha original.
2. **Canonização de Cabeçalhos**: para cada coluna:
   - Remove quebras de linha e múltiplos espaços.
   - Normaliza acentuação (NFKD) e converte para minúsculas.
   - Consulta `column_mappings.json` para resolver sinônimo → canônico.
3. **Agrupamento de Colunas Semânticas**: colunas diferentes que apontam ao mesmo canônico são agrupadas.
4. **Coalescência**: valores linha-a-linha: primeira coluna do grupo prevalece; valores vazios são preenchidos por colunas alternativas subsequentes.
5. **Normalização de `numero_ssa`**: dígitos extraídos e validados (YYYY + 5 dígitos). Linhas inválidas podem ser descartadas (opção padrão).
6. **Parsing Resiliente de Datas**: cada coluna de data candidata é convertida tentando:
   - ISO direto (`YYYY-MM-DD...`) sem `dayfirst`.
   - Formato dia/mês/ano (`dayfirst=True`).
   - Tentativa final invertida (`dayfirst=False`).
   - Números inteiros / floats tratados como serial Excel (origem `1899-12-30`).
   - Resultado final em `YYYY-MM-DD HH:MM:SS` ou `None`.
7. **Deduplicação**: se existir `numero_ssa`, ordena por `numero_ssa` e data (desc) e mantém a primeira (mais recente); contabiliza descartes.
8. **Estatísticas**: estrutura `ImportStats` registra linhas totais, linhas após filtro, merges, falhas de data, duplicatas removidas, etc.

## Estratégia de Deduplicação

- Chave: `numero_ssa`.
- Critério de escolha: maior `data_cadastro` (datas nulas perdem para válidas; entre nulas, mantém a primeira encontrada em ordem original).
- Benefício: evita crescer indefinidamente com versões múltiplas da mesma SSA.

## Regra de Merge no Upsert

Arquivo: `armazenamento/database.py` função interna `_perform_upsert`.

Para cada `numero_ssa` já existente:
- Se `_should_update_existing` aprova (regra de data: nova data >= existente ou casos de ausência conforme definido), então procede.
- Monta um registro mesclado coluna a coluna:
  - Se valor novo é vazio (`None`, NaN ou string branca) mantém o valor antigo.
  - Caso contrário substitui pelo novo.
- Esse merge evita perda involuntária de campos preenchidos anteriormente quando a nova fonte traz colunas parciais.

## Interpretação das Estatísticas (Exemplo)

```json
{
  "total_rows_in": 850,
  "total_rows_out": 820,
  "original_columns_count": 45,
  "mapped_columns_count": 38,
  "dropped_columns": [],
  "merged_columns": { "situacao": ["Situação", "Status" ] },
  "date_parse_failures": { "data_cadastro": 12, "prazo_limite": 5 },
  "duplicate_rows_dropped": 18,
  "invalid_numero_ssa_rows": 12,
  "file_path": "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx"
}
```

Campo | Significado
------|------------
`total_rows_in` | Linhas lidas originalmente.
`total_rows_out` | Linhas após descartes/deduplicação.
`merged_columns` | Colunas sinônimas que foram coalescidas.
`date_parse_failures` | Contagem de células que não puderam ser interpretadas como data (mantidas como `None`).
`duplicate_rows_dropped` | Quantos registros a mais com mesmo `numero_ssa` foram removidos.
`invalid_numero_ssa_rows` | Linhas descartadas por `numero_ssa` inválido.

## CLI de Importação

Uso rápido:
```bash
python3 scripts/import_excel_file.py \
  --file "docs_entrada/Consulta SSA - 10-09-2025_0307PM (1).xlsx" \
  --db data/ssas.db \
  --table ssas \
  --reset-db --smart-upsert --verbose
```

- `--dry-run`: não insere no banco, apenas exibe estatísticas.
- `--reset-db`: recria o banco antes de inserir (aplica `schema.sql`).
- `--smart-upsert`: habilita lógica de preservação + deduplicação incremental.

## Integração com Simulação GUI

`simulate_import_and_gui.py` aceita `--excel` e `--import-real-once`:
- Importa a planilha real antes de gerar lotes sintéticos.
- Permite aquecer o banco e testar carregamento + filtragem na GUI.

## Boas Práticas & Extensões Futuras

- Adicionar testes unitários fabricando cenários: sinônimos múltiplos, datas malformadas, números seriais.
- Gerar relatório CSV de estatísticas históricas de import para auditoria.
- Implementar verificação opcional de colisão sem atualização (ex.: logar quando `_should_update_existing` recusa update).
- Suporte a múltiplos arquivos por lote (concat + pipeline único).
- Flag para permitir sobrescrever com vazio (política inversa) em casos de limpeza intencional.

## Limitações Atuais

- Datas sem ano explícito não são inferidas.
- Campos textuais muito longos não são truncados no import (apenas no schema/DB se houver restrição posterior).
- Não há ainda validação cruzada entre campos (ex.: consistência de semanas versus data).

## Resumo

O pipeline garante ingestão resiliente e idempotente, reduzindo riscos de perda de dados e minimizando ruído causado por variações de planilhas fornecidas por diferentes setores.

---
_Manter este documento atualizado sempre que a semântica de importação ou upsert for alterada._
