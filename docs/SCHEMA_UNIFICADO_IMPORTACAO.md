# Schema Unificado & Importação Robusta

> Documento técnico de referência (2025-09) sobre a consolidação de schema e as heurísticas do importador.

## 1. Objetivos da Unificação
- Eliminar divergência entre `schema.sql` (tabela `ssa_table`) e `schema_optimized.sql` (tabela `ssas`).
- Reduzir falhas de inserção causadas por colunas esperadas ausentes.
- Facilitar evolução incremental (novas colunas adicionadas sem reconstrução completa).
- Manter compatibilidade com código/consultas legadas (views `ssas`, `ssa_chamados`).

## 2. Arquivo Oficial
`config/schema_unified.sql` — superset consolidado. Principais características:
- Tabela canônica: `ssa_table`.
- Views de compatibilidade: `ssas`, `ssa_chamados`.
- Colunas novas integradas: `numero_desvios`, `num_reprogramacoes`, `justificativa`, `total_tempo_tpe_executada`, `total_tempo_tex_executada`, etc.

## 3. Migração Incremental
Script: `scripts/migracao/migrar_para_unificado.py`

### Funcionamento
1. Lê definição da tabela no `schema_unified.sql`.
2. Usa `PRAGMA table_info(ssa_table)` para listar colunas atuais.
3. Identifica colunas ausentes → `ALTER TABLE ADD COLUMN` (tipo heurístico: `INTEGER` se nome indica contador/semana/número; caso contrário `TEXT`).
4. Gera backup em `data/ssas.db.backup_before_unified_<timestamp>`.
5. Log de colunas incluídas em `logs/migracao_unificado_<timestamp>.log`.

### Execução
```
python scripts/migracao/migrar_para_unificado.py --db data/ssas.db
```

### Segurança
- Não remove colunas.
- Não renomeia nem altera tipos existentes.
- Repetir o script quando quiser: se não houver colunas faltantes, sai com mensagem “Nada a migrar.”

## 4. Novos Mapeamentos de Coluna (Aliases)
Arquivo: `config/column_mappings.json` (reforçado por defaults em `core/config_manager.py`).

| Cabeçalho Planilha (exemplo)     | Coluna Canônica              |
|----------------------------------|------------------------------|
| Desvio                           | numero_desvios               |
| Justificativa sem APR            | justificativa                |
| Reprogramações                   | num_reprogramacoes           |
| Total Tempo TPE Executada        | total_tempo_tpe_executada    |
| (outros existentes)              | (mantidos)                   |

Adição de novos aliases: basta editar `column_mappings.json` e (opcional) atualizar defaults. Recomenda-se rodar teste sintético após alterar.

## 5. Importador Robusto (`utils/robust_importer.py`)
### Problema Original
Algumas planilhas traziam o título (“SSAs com Desvio na Programação”) como header único → somente 1 coluna mapeada (`mapped_columns_count=1`) e falhas de insert (`no column named ...`).

### Heurísticas Introduzidas
1. **Header mesclado único**: se todos os nomes de coluna são iguais e há >5 colunas, tenta reprocessar usando outras linhas como header.
2. **Revarredura multi‑linha**: testa linhas 0..9 como potenciais cabeçalhos; escolhe a que produz maior número de grupos canônicos (break antecipado se ≥5 grupos). 
3. **Fallback cabeçalho a partir da primeira linha de dados**: quando apenas 1 coluna existe e a primeira linha apresenta variedade textual (≥3 strings válidas), reinterpreta linha 0 como header real.
4. **Promoção explícita de `numero_ssa`**: se nenhum grupo canônico direto, procura aliases normalizados e força inclusão.

### Resultado
- Planilha problemática passou de 1 para 35 colunas mapeadas.
- Inserções param de falhar por colunas inexistentes derivadas de títulos de folha.

### Estatísticas Exportadas
Arquivo: `reports/last_import_stats.json`
Campos relevantes: `original_columns_count`, `mapped_columns_count`, `dropped_columns`, `merged_columns`, `invalid_numero_ssa_rows`, etc.

## 6. Variáveis de Ambiente
| Variável            | Efeito                                                         |
|---------------------|----------------------------------------------------------------|
| `SSA_IMPORT_DEBUG`  | Ativa logs DEBUG detalhados no importador.                     |
| `SSA_CONFIG_DIR`    | Redireciona carregamento de JSONs de config (multi-env).       |
| `SSA_EXTRA_DIRS`    | Diretórios adicionais criados no bootstrap inicial.           |

## 7. Teste Sintético de Novas Colunas
Arquivo: `tests/test_import_novas_colunas.py`
- Gera XLSX temporário com cabeçalhos alias.
- Executa importador para validar mapeamentos → verifica que colunas canônicas aparecem.
- Insere em banco configurado com `schema_unified.sql` e checa persistência de valores.

Execução pontual:
```
pytest -q tests/test_import_novas_colunas.py
```

## 8. Fluxo Recomendado de Atualização
1. `git pull` / obter versão recente.
2. `python scripts/migracao/migrar_para_unificado.py --db data/ssas.db`
3. (Opcional) `pytest -q tests/test_import_novas_colunas.py`
4. Importar novas planilhas normalmente (CLI/GUI).

## 9. Backfill (Planejado)
Script futuro deverá:
- Reprocessar diretório `docs_entrada/` aplicando importador robusto.
- Usar smart upsert para adicionar valores de novas colunas onde antes estavam vazias.
- Gerar relatório de quantos registros foram enriquecidos.

## 10. Boas Práticas Futuras
- Ao adicionar coluna: incluir no `schema_unified.sql` e criar migração incremental (se desejar imediata) ou esperar próxima execução do script.
- Para alias novo: atualizar `column_mappings.json`, rodar teste sintético e commit.
- Monitore `mapped_columns_count`; se cair drasticamente em planilha nova, ativar `SSA_IMPORT_DEBUG=1` e inspecionar `reports/last_import_stats.json`.

## 11. Checklist de Manutenção Rápida
- [ ] Schema unificado versionado? (`config/schema_unified.sql`)
- [ ] Migração executada recentemente? (logs em `logs/migracao_unificado_*.log`)
- [ ] Teste sintético passando? (`pytest -q tests/test_import_novas_colunas.py`)
- [ ] Estatísticas recentes disponíveis? (`reports/last_import_stats.json`)
- [ ] Aliases alinhados? (`config/column_mappings.json` + defaults)

---
Documento mantido; alterações futuras relevantes devem atualizar também o README (seção Schema Unificado & Migração).
