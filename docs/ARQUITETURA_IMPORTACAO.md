# Arquitetura de Importacao (Baseline v4.47)

Este documento descreve a arquitetura ativa de importacao no baseline atual.

## Escopo

1. Fluxo de importacao de planilhas para SQLite.
2. Integracao com CLI e GUI sem import automatico no startup.
3. Politica de derivadas: somente full rescan ou acao manual.

## Componentes principais

- `core/app_logic.py`
  - orquestracao de importacao e full rescan.
- `extracao/extractor.py`
  - leitura, normalizacao e captura de registros hierarquicos.
- `armazenamento/database_upsert_logic.py`
  - persistencia e merge por `numero_ssa`.
- `armazenamento/database_validation.py`
  - validacoes de dados e regras de consistencia.
- `armazenamento/database_integrity.py`
  - verificacao de integridade e estrutura de schema.

## Fluxo canonico

1. Descoberta dos arquivos de entrada.
2. Extracao e normalizacao de colunas.
3. Captura de linhas hierarquicas em `ssa_event_records`, sem forward-fill.
4. Validacao de identidade, payload e regras de dados.
5. Persistencia atomica de pais e eventos no banco alvo.
6. Atualizacao de relatorios de importacao.
7. Em full rescan, sincronizacao de derivadas ao final.

## Discovery e ordenacao

1. Full rescan usa discovery com `include_processadas=True` por padrao.
2. Subpastas ignoradas seguem `import_settings` (default: ignora `nosurvivor`).
3. Importacao explicita (`explicit_files`) e resolvida com:
   - validacao de path dentro de `docs_dir`
   - dedupe de caminhos
   - ordenacao deterministica por `best_datetime_for_file` (mais antigo -> mais novo)
4. Objetivo da ordenacao: deixar o snapshot mais novo por ultimo para reduzir risco de regressao por ordem de entrada.

## Metadados de snapshot persistidos

Em cada arquivo importado, o pipeline garante as colunas:

1. `arquivo_origem` (nome do arquivo)
2. `data_arquivo_origem` (`YYYY-MM-DD HH:MM:SS`)
3. `data_planilha` (ISO `YYYY-MM-DDTHH:MM:SS`)

Fonte da data de arquivo:

1. parse no nome do arquivo quando reconhecido
2. fallback para metadata (`mtime`, depois `ctime`) quando nome e generico

Esses valores sao derivados do arquivo fisico e sobrescrevem colunas de
proveniencia eventualmente presentes no conteudo importado. Pais e eventos usam
o mesmo snapshot.

## Linhas hierarquicas

Relatorios de desvio, reprogramacao e execucao parcial podem representar um
mesmo SSA em varias linhas. O extractor:

1. prova o grupo pai/filho antes de associar uma linha sem `numero_ssa`
2. mantem no frame principal as linhas que ja possuem identidade; o extractor
   nao deduplica por SSA
3. transporta os registros do grupo em `DataFrame.attrs["ssa_event_records"]`

Os callers canonicos exigem que o smart upsert confirme a persistencia de todos
os eventos.

Linhas restantes sem identidade sao resumidas em
`DataFrame.attrs["invalid_row_summary"]`. Todo caller canonico bloqueia a escrita
quando `payload_removed > 0`. No core principal, o erro interrompe a rodada sem
promocao do candidato nem atualizacao de cache; assim, formato desconhecido nao
vira descarte silencioso.

## Regras de escrita por linha

Contrato resumido do upsert:

1. estados terminais (`STE`, `SCA`) no banco sao imutaveis
2. snapshot novo sem timestamp confiavel nao atualiza linha existente
3. snapshot mais antigo nao sobrescreve snapshot mais novo
4. `data_cadastro` fica como criterio auxiliar/tie-break

Referencia completa:

- `docs/ARCH_DB_UPSERT.md`

## Contratos operacionais

1. Startup sem import automatico.
2. Full rescan recria DB do zero por politica.
3. Sync de derivadas nao roda no incremental por padrao.
4. Falhas de importacao devem gerar log objetivo, sem suppress silencioso.
5. `scripts/import_excel_file.py` e `scripts/migracao/backfill_reprocessar.py`
   rejeitam `--reset-db`; recriacao segura pertence ao full rescan.
6. Escrita SSA nos dois utilitarios exige `--smart-upsert`; dry-run permanece
   somente leitura.

## CURRENT TRUTH

- Estado operacional e decisoes de ciclo:
  - `README.md`
  - `docs/README.md`

## HISTORICAL SNAPSHOT

O conteudo detalhado legado desta arquitetura nao e mais publicado no repositorio.

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->
