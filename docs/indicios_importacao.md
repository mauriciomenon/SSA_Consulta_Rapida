# Indicios Importacao - Sessao 2026-03-05

## Historical Snapshot Notice

Este arquivo preserva evidencias de sessoes historicas de importacao.
Branches `codex/...` e comandos abaixo sao contexto da epoca, nao instrucao operacional atual.

Fonte ativa atual:
1. `README.md`
2. `docs/ARQUITETURA_IMPORTACAO.md`
3. `docs/TROUBLESHOOTING_IMPORTACAO.md`

## Sessao 2026-03-09 - full rescan real end-to-end (pacote unico)

### Escopo executado
- Branch: `codex/sprint-importacao-grave-fixes-20260305`
- Inicio: `2026-03-09 01:08:50 -0300`
- Fim: `2026-03-09 04:38:31 -0300`
- Comando: `uv run --python 3.13 python main.py --force-rescan --log-level INFO`
- Backup criado antes do rescan:
  - `data/db_backups/ssas.db.pre_full_rescan_20260309_010934.db`
- Log runtime:
  - `logs/full_rescan_runtime_20260309_010934.log`
- Report principal da rodada:
  - `logs/import_run_20260309_010936_830587.json`

### Resultado consolidado
- Status import: `updated` (`result=true`)
- Arquivos candidatos: `431`
- Arquivos sucesso: `431`
- Arquivos erro: `0`
- XLS legado ignorado por politica: `135`
- Linhas extraidas: `497162`
- Linhas removidas por identidade invalida: `2763`
- Linhas prontas para insert: `497162`
- Linhas inseridas: `497162`

### Tempo e performance
- `duration_seconds` total do run: `12522.179s` (inclui tempo no prompt CLI apos concluir import)
- Tempo efetivo do pipeline de arquivos (`run_file_processing_seconds`): `1251.979s` (~20.9 min)
- Somatorios por fase (novos campos em `durations`):
  - `sum_file_extraction_seconds`: `225.817s`
  - `sum_file_validation_seconds`: `294.541s`
  - `sum_file_insert_seconds`: `717.991s`

Observacao critica de medicao:
- O total `12522s` ficou inflado por execucao via `main.py` em modo nao interativo.
- Apos concluir a importacao, o CLI entrou no loop de input e encerrou por `EOF`.
- Para benchmark puro de importacao, usar execucao direta de `run_importer_logic(...)` sem loop interativo.

### Gargalos observados (insert por arquivo)
Top arquivos por `insert_seconds` nesta rodada:
1. `Consulta SSA - 15-12-2025_0105PM (1).xlsx`: `34.411s`
2. `Consulta SSA - 18-12-2025_0452PM.xlsx`: `17.790s`
3. `Todas as SSAs - 18-08-2022_1144AM.xlsx`: `16.914s`
4. `Consulta SSA - 20-02-2026_1118AM (1).xlsx`: `13.604s`
5. `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`: `13.110s`

Fonte:
- `logs/full_rescan_top_insert_20260309_063007.csv`

### Gargalos por familia de planilha (insert agregado)
Top familias por `insert_seconds`:
1. `Consulta SSA`: `450.954s` (`168` arquivos)
2. `SSAs Executadas`: `150.935s` (`102` arquivos)
3. `Todas as SSAs`: `70.972s` (`28` arquivos)

Fonte:
- `logs/full_rescan_family_insert_20260309_063007.csv`

### Remocoes por identidade invalida
Top arquivos por `rows_removed_invalid_identity`:
1. `SSAscomReprogramações_07-01-2026_0225PM.xlsx`: `1778`
2. `SSAs Pendentes com Execução Parcial_02-02-2026_1141AM.xlsx`: `323`
3. `SSAs Pendentes com Execução Parcial_10-09-2025_0317PM.xlsx`: `261`

Fonte:
- `logs/full_rescan_top_invalid_20260309_063007.csv`

### Saude do DB apos rodada
- `integrity_check`: `ok`
- `rows_total`: `76426`
- `distinct_numero_ssa`: `76426`
- `duplicate_numero_ssa`: `0`
- `rows_sem_data_cadastro`: `662`
- `column_count`: `82`
- `id_column_exists`: `true`
- `nan_columns`: `[]`

Leitura tecnica:
- Sem drift de schema detectado nesta rodada (sem colunas `nan*`, coluna `id` presente).
- Integridade estrutural e deduplicacao de `numero_ssa` permaneceram estaveis.

### Warnings relevantes no runtime log
- Aviso esperado de politica ativa: `135` arquivos `.xls` legados ignorados.
- Warnings de remocao de registros invalidos concentrados em:
  - `SSAscomReprogramações_*`
  - `SSAs Pendentes com Execução Parcial_*`
  - `SSAs com Desvio na Programação_*`
- Warnings de duplicidade exata no export em 2 arquivos `Todas as SSAs` (2 linhas cada).

### Comparativo de referencia (baseline anterior de sucesso)
- Baseline usado: `logs/import_run_20260308_164411_546107.json`
- Delta principal:
  - candidatos/sucessos/linhas: equivalentes
  - `ignored_legacy_excel_count`: `0 -> 135` (politica agora explicitamente contabilizada)
  - baseline antigo nao tinha bloco `durations`, entao comparacao de fases ficou disponivel apenas na rodada atual

Artefatos comparativos gerados:
- `logs/full_rescan_summary_20260309_063007.json`
- `logs/full_rescan_summary_20260309_063007.csv`
- `logs/full_rescan_family_insert_20260309_063007.csv`
- `logs/full_rescan_top_insert_20260309_063007.csv`
- `logs/full_rescan_top_invalid_20260309_063007.csv`

## Escopo
- Objetivo: testar importacao do zero, medir tempo, confiabilidade, perdas e saude do DB.
- Branch: `codex/sprint-importacao-grave-fixes-20260305`.
- Inicio: `2026-03-05 13:26:54 -0300`.
- Fim parcial desta coleta: `2026-03-05 14:12:23 -0300`.

## Procedimento Executado
1. Preflight git/branch com workspace limpo.
2. Backup manual do DB atual:
   - origem: `data/ssas.db`
   - destino: `data/db_backups/ssas.db.pre_manual_rescan_20260305_132803.db`
3. Full rescan iniciado via `run_importer_logic(force_import=True)` com log em:
   - `logs/full_rescan_20260305_132813.log`
4. Passada de retomada executada via `run_importer_logic(force_import=False)`:
   - `logs/rescan_resume_20260305_140405.log`
5. Smoke GUI:
   - script: abrir `SSAMainWindow`, aguardar 5s, sair
   - log: `logs/gui_smoke_20260305_140702.log`

## Resultado de Tempo/Estabilidade
- Full rescan (forcado) ficou ativo por pelo menos `2104s` (35m04s) ate o ultimo timestamp de log.
- Execucao longa terminou sem linha final `RESULT` no terminal (encerramento anomalo do processo de shell).
- Passada de retomada (`force_import=False`) retornou em `0.648s` com `ok=False`.
- Observacao operacional:
  - Sem barra de progresso por arquivo no modo usado.
  - Fluxo longo dificultou confirmar fim limpo da rodada.

## Evidencias Quantitativas do Log de Full Rescan
Fonte: `logs/full_rescan_20260305_132813.log`

- linhas no log: `570`
- arquivos com `missing_data_cadastro`: `138`
- total de linhas removidas por `missing_data_cadastro`: `2171`
- total de linhas removidas por "sem numero_ssa e sem descricao": `2393`
- arquivos pulados por falta de coluna obrigatoria apos normalizacao: `2`
- avisos de duplicidade de `numero_ssa`: `2` arquivos, `4` linhas no total

Top 10 arquivos por perda em `missing_data_cadastro`:
1. `Todas as SSAs - 14-07-2022_1010AM - Copia.xlsx`: 159
2. `Todas as SSAs - 18-08-2022_1144AM.xlsx`: 155
3. `Consulta SSA - 02-03-2026_0540PM.xlsx`: 57
4. `Consulta SSA - 15-12-2025_0105PM (1).xlsx`: 54
5. `Consulta SSA - 20-02-2026_1132AM (1).xlsx`: 53
6. `Consulta SSA - 28-10-2025_1203PM.xlsx`: 53
7. `Todas as SSAs - 29-08-2025_0423PM.xlsx`: 51
8. `Consulta SSA - 10-11-2025_0759AM.xlsx`: 50
9. `Consulta SSA - 18-12-2025_0452PM.xlsx`: 50
10. `Consulta SSA - 22-07-2025_0237PM.xlsx`: 47

Arquivos pulados por `Missing required columns after normalization: ['data_cadastro']`:
1. `SSAs Pendentes de Aprovação na Emissão_15-08-2025_0411PM.xlsx`
2. `SSAs Pendentes de Aprovação na Emissão_02-02-2026_1141AM.xlsx`

## Saude do DB (Apos Rodada)
Comparacao entre:
- DB atual: `data/ssas.db`
- backup pre-rescan: `data/db_backups/ssas.db.pre_manual_rescan_20260305_132803.db`

DB atual:
- `integrity_check=ok`
- linhas: `73999`
- `distinct_numero_ssa=73999`
- duplicados por `numero_ssa`: `0`
- `rows_sem_data_cadastro=0`
- `num_reprogramacoes` textual: `0`
- `num_reprogramacoes like Reprogramacao#`: `0`

Delta atual - backup:
- linhas: `+3045`
- origens distintas: `+38` (72 -> 110)
- `num_reprogramacoes` preenchido: `+25922`
- `total_de_reprogramacoes` preenchido: `+2888`

## Achado Critico de Schema Drift
Comparacao de schema em `ssa_table`:
- backup: `82` colunas, com `id` presente
- atual: `73` colunas, `id` ausente

Colunas faltantes no DB atual:
- `id`
- `sn_extra`
- `numero_ssa_relacionada_1`
- `numero_ssa_relacionada_2`
- `numero_ssa_relacionada_3`
- `setor_emissor_relacionado_1`
- `setor_emissor_relacionado_2`
- `setor_executor_relacionado_1`
- `setor_executor_relacionado_2`
- `situacao_relacionada_1`
- `situacao_relacionada_2`
- `relacao`

Colunas espurias no DB atual:
- `nan`
- `nan_1`
- `nan_2`

Indicio de causa no codigo:
- `armazenamento/database_upsert_logic.py` usa `to_sql(... if_exists='replace')` quando tabela nao existe.
- Em full rescan, se a primeira escrita criar tabela por DataFrame, schema canonico pode ser perdido.

## Achado Critico de Regra de Descarte
Regra atual de validacao trata `data_cadastro` como erro critico por linha:
- fonte: `armazenamento/database_validation.py` (`missing_data_cadastro` com severidade `error`)
- em `core/app_logic.py`, linhas com `data_cadastro` ausente sao removidas antes de inserir.

Ponto adicional:
- para os dois arquivos pulados de "Pendentes de Aprovacao na Emissao", a coluna `Emitida Em` existe no header, mas vem 100% vazia.
- como o extrator remove colunas totalmente vazias antes da normalizacao (`dropna(axis=1, how='all')`), `data_cadastro` deixa de existir no DataFrame.
- isso impede fallback de data por outras colunas (`desde`, etc.) e resulta em skip completo do arquivo.

## Verificacao GUI
- Smoke GUI passou:
  - `exit_code=0`
  - `GUI_SMOKE_EXIT=0`
  - arquivo: `logs/gui_smoke_20260305_140702.log`

## Ferramentas Auxiliares (Laudo Externo)
- `qwen` e `glm_coding` disponiveis no PATH.
- Tentativas one-shot nesta rodada encerraram por timeout (`exit 124`) sem retorno util.

## Conclusao Tecnica da Rodada
1. O fluxo atual de full rescan segue com risco alto de schema drift (perda de `id` e colunas canonicas).
2. A regra de descarte por `missing_data_cadastro` remove volume alto de linhas.
3. Ha pelo menos um caso de skip total de arquivo onde existe dado temporal em colunas alternativas, mas o fluxo nao consegue aproveitar.
4. O DB atual ficou consistente para leitura (`integrity_check=ok`), mas com schema divergente do canonico.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

