# Indicios Importacao - Sessao 2026-03-05

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
