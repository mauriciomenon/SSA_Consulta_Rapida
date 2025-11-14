# Plano de Modularizacao – Importador (Fase 2)

Objetivo: reduzir acoplamento e facilitar testes unitarios isolados do pipeline
`import_excel_robust`, permitindo reutilizacao de partes (ex.: limpeza de numero_ssa,
parsing de datas, coalescencia) em outros fluxos (CLI / GUI) sem duplicacao.

## Problemas Atuais
- Funcao monolitica com multiplas responsabilidades (IO Excel, mapeamento, coalescencia,
  normalizacao, parsing de datas, deduplicacao, estatisticas e persistencia de relatorio).
- Dificuldade para injetar politicas (ex.: regras alternativas de filtro) sem editar a funcao.
- Testes focam no output final; granularidade limitada (falta cobertura direcionada a cada etapa).

## Metas de Fase 2
1. Extrair etapas em funcoes puras / idempotentes.
2. Introduzir conteiner de contexto (dataclass) para acumular estatisticas incrementalmente.
3. Separar politica de deduplicacao e politica de filtragem em objetos ou funcoes plugaveis.
4. Preparar pontos de extensao para: auditoria, coleta de metricas de performance, e hooks.

## Proposta de Pacotes / Modulos
```
utils/importer/
  __init__.py
  reader.py               # Carrega Excel → DataFrame bruto
  header_mapping.py       # Canonicalizacao + construcao de grupos + promocao explicita
  coalesce.py             # Logica de coalescencia de colunas
  numero_ssa_clean.py     # Funcao limpa serie (wrapper atual + heuristicas de float)
  dates.py                # Parsing e normalizacao de colunas de data
  deduplicate.py          # Estrategia (default: ordena por data_cadastro desc, drop dup)
  filter_rows.py          # Filtros de invalidez (numero_ssa vazio, etc.)
  stats.py                # Dataclass ImportStats + merge incremental
  pipeline.py             # Orquestrador (substitui import_excel_robust), monta etapas
```

## Fluxo Proposto (Pipeline)
1. reader.read_excel(file_path) → df_raw
2. header_mapping.build(df_raw, mapping_json) → mapping_info (grupos, canonical_df_base, stats)
3. coalesce.apply(canonical_df_base, mapping_info) → df_mapped
4. numero_ssa_clean.clean(df_mapped) → df_ssa, stats.update
5. dates.parse_columns(df_ssa, DATE_CANDIDATES) → df_dates, stats.update
6. filter_rows.apply(df_dates, policy) → df_filtered, stats.update
7. deduplicate.apply(df_filtered) → df_dedup, stats.update
8. stats.finalize(df_dedup) → stats_dict
9. reports.persist(stats_dict)

Cada etapa retorna (df, stats) ou atualiza stats in-place. Orquestrador gerenciaria o early-return em caso de erro de IO.

## Politicas Plugaveis
- Numero SSA Policy: (strict) atual, futura (leniente para migracao) selecionavel por env (`SSA_NUMERO_SSA_POLICY=strict|legacy`).
- Deduplicate Policy: default vs. custom sort key (ex: prioridade de coluna alternativa se `data_cadastro` ausente).
- Filter Policy: remove vs. marca (flag nos stats e deixa linha para canais de diagnostico).

## Estatisticas Incrementais
`ImportStats` pode ganhar metodos:
```python
def record_header_mapping(self, original_cols, mapped_cols, merged): ...
def record_numero_ssa(self, total, invalid): ...
def record_dates(self, column, failures): ...
```
Permitindo validar em testes unitarios cada etapa isoladamente.

## Beneficios Esperados
- Aumento de cobertura unitaria sem dependencia de escrita/leitura de Excel para cada aspecto.
- Reducao de risco em futuras mudancas de normalizacao.
- Facilidade de ligar/alterar politica via env sem alterar corpo principal.

## Migracao Gradual
Fase 2 nao remove `import_excel_robust` imediatamente; ela passa a ser um thin wrapper que chama `pipeline.run(...)`. Tests existentes continuam verdes e novos testes de unidade surgem para modulos.

## Riscos / Mitigacoes
- Risco: Over-engineering para escopo atual. Mitigacao: limitar interface publica a `pipeline.run` e manter modulos focados (sem classe complexa).
- Risco: Duplicacao transitoria. Mitigacao: mover codigo copiando e depois remover blocos originais apos garantir paridade via testes.

## Proximos Passos (Implementacao)
1. Criar diretorio `utils/importer/` com `stats.py` (mover ImportStats), `numero_ssa_clean.py` (mover funcao adaptada), `dates.py` (extrair loop de datas).
2. Escrever testes unitarios curtos para cada modulo (ex.: `tests/importer/test_dates.py`).
3. Implementar `pipeline.py` e alterar `import_excel_robust` para delegar.
4. Deprecar gradualmente codigo inline removido do arquivo monolitico.
5. Atualizar documentacao (`GUIA_MODO_OPTIMIZED.md` / novo README de importador).

## Criterio de Conclusao Fase 2
- Todos os testes atuais + novos modulares passando.
- Reducao de complexidade cognitiva de `robust_importer.py` (>40% LOC movidos).
- Estatisticas invariantes comparado a versao pre-refator (snapshot de JSON igual salvo por fixture).

--
Documento criado em Fase 2 planejamento inicial.
