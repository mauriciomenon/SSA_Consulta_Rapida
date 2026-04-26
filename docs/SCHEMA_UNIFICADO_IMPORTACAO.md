# Schema Unificado & Importacao Robusta

> Documento tecnico de referencia (2025-09) sobre a consolidacao de schema e as heuristicas do importador.

## 1. Objetivos da Unificacao
- Eliminar divergencia entre `schema.sql` (tabela `ssa_table`) e `schema_optimized.sql` (tabela `ssas`).
- Reduzir falhas de insercao causadas por colunas esperadas ausentes.
- Facilitar evolucao incremental (novas colunas adicionadas sem reconstrucao completa).
- Manter compatibilidade com codigo/consultas legadas (views `ssas`, `ssa_chamados`).

## 2. Arquivo Oficial
`config/schema_unified.sql` — superset consolidado. Principais caracteristicas:
- Tabela canonica: `ssa_table`.
- Views de compatibilidade: `ssas`, `ssa_chamados`.
- Colunas novas integradas: `numero_desvios`, `num_reprogramacoes`, `justificativa`, `total_tempo_tpe_executada`, `total_tempo_tex_executada`, etc.

## 3. Migracao Incremental
Script: `scripts/migracao/migrar_para_unificado.py`

### Funcionamento
1. Le definicao da tabela no `schema_unified.sql`.
2. Usa `PRAGMA table_info(ssa_table)` para listar colunas atuais.
3. Identifica colunas ausentes → `ALTER TABLE ADD COLUMN` (tipo heuristico: `INTEGER` se nome indica contador/semana/numero; caso contrario `TEXT`).
4. Gera backup em `data/ssas.db.backup_before_unified_<timestamp>`.
5. Log de colunas incluidas em `logs/migracao_unificado_<timestamp>.log`.

### Execucao
```
python scripts/migracao/migrar_para_unificado.py --db data/ssas.db
```

### Seguranca
- Nao remove colunas.
- Nao renomeia nem altera tipos existentes.
- Repetir o script quando quiser: se nao houver colunas faltantes, sai com mensagem “Nada a migrar.”

## 4. Novos Mapeamentos de Coluna (Aliases)
Arquivo: `config/column_mappings.json` (reforcado por defaults em `core/config_manager.py`).

| Cabecalho Planilha (exemplo)     | Coluna Canonica              |
|----------------------------------|------------------------------|
| Desvio                           | numero_desvios               |
| Justificativa sem APR            | justificativa                |
| Reprogramacoes                   | num_reprogramacoes           |
| Total Tempo TPE Executada        | total_tempo_tpe_executada    |
| (outros existentes)              | (mantidos)                   |

Adicao de novos aliases: basta editar `column_mappings.json` e (opcional) atualizar defaults. Recomenda-se rodar teste sintetico apos alterar.

## 5. Importador Robusto (`utils/robust_importer.py`)
### Problema Original
Algumas planilhas traziam o titulo (“SSAs com Desvio na Programacao”) como header unico → somente 1 coluna mapeada (`mapped_columns_count=1`) e falhas de insert (`no column named ...`).

### Heuristicas Introduzidas
1. **Header mesclado unico**: se todos os nomes de coluna sao iguais e ha >5 colunas, tenta reprocessar usando outras linhas como header.
2. **Revarredura multi‐linha**: testa linhas 0..9 como potenciais cabecalhos; escolhe a que produz maior numero de grupos canonicos (break antecipado se ≥5 grupos). 
3. **Fallback cabecalho a partir da primeira linha de dados**: quando apenas 1 coluna existe e a primeira linha apresenta variedade textual (≥3 strings validas), reinterpreta linha 0 como header real.
4. **Promocao explicita de `numero_ssa`**: se nenhum grupo canonico direto, procura aliases normalizados e forca inclusao.

### Resultado
- Planilha problematica passou de 1 para 35 colunas mapeadas.
- Insercoes param de falhar por colunas inexistentes derivadas de titulos de folha.

### Estatisticas Exportadas
Arquivo: `reports/last_import_stats.json`
Campos relevantes: `original_columns_count`, `mapped_columns_count`, `dropped_columns`, `merged_columns`, `invalid_numero_ssa_rows`, etc.

## 6. Variaveis de Ambiente
| Variavel            | Efeito                                                         |
|---------------------|----------------------------------------------------------------|
| `SSA_IMPORT_DEBUG`  | Ativa logs DEBUG detalhados no importador.                     |
| `SSA_CONFIG_DIR`    | Redireciona carregamento de JSONs de config (multi-env).       |
| `SSA_EXTRA_DIRS`    | Diretorios adicionais criados no bootstrap inicial.           |

## 7. Teste Sintetico de Novas Colunas
Arquivo: `tests/test_import_novas_colunas.py`
- Gera XLSX temporario com cabecalhos alias.
- Executa importador para validar mapeamentos → verifica que colunas canonicas aparecem.
- Insere em banco configurado com `schema_unified.sql` e checa persistencia de valores.

Execucao pontual:
```
pytest -q tests/test_import_novas_colunas.py
```

## 8. Fluxo Recomendado de Atualizacao
1. `git pull` / obter versao recente.
2. `python scripts/migracao/migrar_para_unificado.py --db data/ssas.db`
3. (Opcional) `pytest -q tests/test_import_novas_colunas.py`
4. Importar novas planilhas normalmente (CLI/GUI).

## 9. Backfill (Planejado)
Script futuro devera:
- Reprocessar diretorio `docs_entrada/` aplicando importador robusto.
- Usar smart upsert para adicionar valores de novas colunas onde antes estavam vazias.
- Gerar relatorio de quantos registros foram enriquecidos.

## 10. Boas Praticas Futuras
- Ao adicionar coluna: incluir no `schema_unified.sql` e criar migracao incremental (se desejar imediata) ou esperar proxima execucao do script.
- Para alias novo: atualizar `column_mappings.json`, rodar teste sintetico e commit.
- Monitore `mapped_columns_count`; se cair drasticamente em planilha nova, ativar `SSA_IMPORT_DEBUG=1` e inspecionar `reports/last_import_stats.json`.

## 11. Checklist de Manutencao Rapida
- [ ] Schema unificado versionado? (`config/schema_unified.sql`)
- [ ] Migracao executada recentemente? (logs em `logs/migracao_unificado_*.log`)
- [ ] Teste sintetico passando? (`pytest -q tests/test_import_novas_colunas.py`)
- [ ] Estatisticas recentes disponiveis? (`reports/last_import_stats.json`)
- [ ] Aliases alinhados? (`config/column_mappings.json` + defaults)

---
Documento mantido; alteracoes futuras relevantes devem atualizar tambem o README (secao Schema Unificado & Migracao).

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

