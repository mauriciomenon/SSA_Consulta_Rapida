# Plano de Modularização – Importador (Fase 2)

Objetivo: reduzir acoplamento e facilitar testes unitários isolados do pipeline
`import_excel_robust`, permitindo reutilização de partes (ex.: limpeza de numero_ssa,
parsing de datas, coalescência) em outros fluxos (CLI / GUI) sem duplicação.

## Problemas Atuais
- Função monolítica com múltiplas responsabilidades (IO Excel, mapeamento, coalescência,
  normalização, parsing de datas, deduplicação, estatísticas e persistência de relatório).
- Dificuldade para injetar políticas (ex.: regras alternativas de filtro) sem editar a função.
- Testes focam no output final; granularidade limitada (falta cobertura direcionada a cada etapa).

## Metas de Fase 2
1. Extrair etapas em funções puras / idempotentes.
2. Introduzir contêiner de contexto (dataclass) para acumular estatísticas incrementalmente.
3. Separar política de deduplicação e política de filtragem em objetos ou funções plugáveis.
4. Preparar pontos de extensão para: auditoria, coleta de métricas de performance, e hooks.

## Proposta de Pacotes / Módulos
```
utils/importer/
  __init__.py
  reader.py               # Carrega Excel → DataFrame bruto
  header_mapping.py       # Canonicalização + construção de grupos + promoção explicita
  coalesce.py             # Lógica de coalescência de colunas
  numero_ssa_clean.py     # Função limpa série (wrapper atual + heurísticas de float)
  dates.py                # Parsing e normalização de colunas de data
  deduplicate.py          # Estratégia (default: ordena por data_cadastro desc, drop dup)
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

## Políticas Plugáveis
- Numero SSA Policy: (strict) atual, futura (leniente para migração) selecionável por env (`SSA_NUMERO_SSA_POLICY=strict|legacy`).
- Deduplicate Policy: default vs. custom sort key (ex: prioridade de coluna alternativa se `data_cadastro` ausente).
- Filter Policy: remove vs. marca (flag nos stats e deixa linha para canais de diagnóstico).

## Estatísticas Incrementais
`ImportStats` pode ganhar métodos:
```python
def record_header_mapping(self, original_cols, mapped_cols, merged): ...
def record_numero_ssa(self, total, invalid): ...
def record_dates(self, column, failures): ...
```
Permitindo validar em testes unitários cada etapa isoladamente.

## Benefícios Esperados
- Aumento de cobertura unitária sem dependência de escrita/leitura de Excel para cada aspecto.
- Redução de risco em futuras mudanças de normalização.
- Facilidade de ligar/alterar política via env sem alterar corpo principal.

## Migração Gradual
Fase 2 não remove `import_excel_robust` imediatamente; ela passa a ser um thin wrapper que chama `pipeline.run(...)`. Tests existentes continuam verdes e novos testes de unidade surgem para módulos.

## Riscos / Mitigações
- Risco: Over-engineering para escopo atual. Mitigação: limitar interface pública a `pipeline.run` e manter módulos focados (sem classe complexa).
- Risco: Duplicação transitória. Mitigação: mover código copiando e depois remover blocos originais após garantir paridade via testes.

## Próximos Passos (Implementação)
1. Criar diretório `utils/importer/` com `stats.py` (mover ImportStats), `numero_ssa_clean.py` (mover função adaptada), `dates.py` (extrair loop de datas).
2. Escrever testes unitários curtos para cada módulo (ex.: `tests/importer/test_dates.py`).
3. Implementar `pipeline.py` e alterar `import_excel_robust` para delegar.
4. Deprecar gradualmente código inline removido do arquivo monolítico.
5. Atualizar documentação (`GUIA_MODO_OPTIMIZED.md` / novo README de importador).

## Critério de Conclusão Fase 2
- Todos os testes atuais + novos modulares passando.
- Redução de complexidade cognitiva de `robust_importer.py` (>40% LOC movidos).
- Estatísticas invariantes comparado à versão pré-refator (snapshot de JSON igual salvo por fixture).

--
Documento criado em Fase 2 planejamento inicial.
