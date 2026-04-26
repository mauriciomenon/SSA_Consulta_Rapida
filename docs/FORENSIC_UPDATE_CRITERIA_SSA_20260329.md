# Forensic - Criterio de Update SSA (2026-03-29)

## Escopo

- Documento forense sobre a regressao de criterio de update de SSA.
- Foco: separar regra de validacao de registro vs regra de update de estado.
- Sem alteracao de runtime neste arquivo.

## Resumo executivo

1. O algoritmo antigo (2025-08) priorizava recencia de snapshot de arquivo.
2. No refactor de 2025-09, o nucleo de decisao mudou para comparacao por `data_cadastro`.
3. Nos hotfixes de 2026-03, entrou trava global de `STE` no topo e depois guard de data de arquivo.
4. Resultado atual: criterio principal voltou a depender de contexto de snapshot, com `data_cadastro` apenas auxiliar.

## Linha do tempo com evidencia

### 2025-08-08 - commit 2d76d68d

- Introduz smart upsert com metadados de arquivo (`data_arquivo_origem`, `versao_dados`).
- Decisao de update usa `should_update_ssa(existing_file_date, file_datetime_iso)`.

### 2025-08-12 - commit 6d672ff2

- Mantem criterio principal por data de arquivo.
- Em empate/ausencia de data de arquivo, usa tie-break por estado via:
  - `STATE_ORDER`
  - `STATE_RANK`
  - `_state_rank(new_state) > _state_rank(existing_state)`

### 2025-09-15 - commits cdbde826 / ea22291f

- Entra `armazenamento/database_upsert_logic.py::_should_update_existing`.
- Nucleo passa a comparar `existing_date/new_date` de `data_cadastro`.
- Retorno central: `n_val >= e_val`.
- Criterio por snapshot deixa de ser o eixo principal no nucleo.

### 2026-03-27 - commit a34a54b3

- Reforco de tie-break por `situacao` no empate de data.

### 2026-03-28 - commit 3b41233a

- Entra gate global de `STE` no topo de `_should_update_existing`:
  - se existente `STE` e novo nao `STE`, bloqueia.
- Reacoplado guard de data de arquivo no nucleo.

### 2026-03-28 - commit 905d6d14

- Persistencia de `data_arquivo_origem` no fluxo de import.

## Regra atual (estado do codigo em 2026-03-30)

Arquivo: `armazenamento/database_upsert_logic.py`

Ordem atual de decisao:

1. Estado existente `STE` ou `SCA`: bloqueia update.
2. Guard por data de arquivo (quando ambas datas existem).
3. Se arquivo novo tem contexto mas nao tem timestamp confiavel: bloqueia update.
4. Comparacao por `data_cadastro` (`>=`) com tie-break de `situacao` no empate.

## Distincao correta de dominio

### Validacao de registro (qualidade)

- `numero_ssa` canonico e valido.
- `situacao` em dominio esperado.
- `data_cadastro` parseavel (quando obrigatoria para o caso).
- Duplicidade e consistencia estrutural.

### Decisao de update (versionamento)

- Deve ser dirigida por recencia de snapshot + regras de transicao de estado.
- `data_cadastro` pode ser auxiliar (tie-break), nao motor principal.
- Regra de `STE` deve ser regra de transicao especifica, nao eixo global do algoritmo.

## Ordem usual de estados (evidencia de manual)

Fonte: `Procedimentos do SMA-SMP.pdf` (extracao textual local em 2026-03-29).

Sequencia usual identificada no manual:

1. Emissao/aprovacao:
   - `ASE` -> `ADI` (ou fluxo de um nivel conforme rotina local).
2. Aguardando/planejamento:
   - estados de espera como `AAD`, `AAT`, `ACC`, `ACS`, `ADM`, `AIM`, `APV`, `ASO`.
3. Execucao:
   - `SEE`.
4. Pos-execucao/aprovacao da execucao:
   - `SAS` -> `SAD`.
5. Fechamento:
   - `STE`.
6. Cancelamento:
   - `SCA` (e referencias legadas `SCE` em trechos historicos do manual).

Evidencias pontuais extraidas:

- Pagina 15: SSA numerada assume `ASE`, depois aprovacao leva para `ADI`.
- Pagina 51/52: conclusao da execucao gera `SAS`, depois `SAD`, depois `STE`.
- Pagina 61: rotina de cancelamento usa `SCA`.
- Pagina 82: tabela consolidada de situacoes inclui `ASE`, `ADI`, estados de espera, `SEE`, `SAS`, `SAD`, `SCA`, `STE`.

Observacao:

- Isso confirma que existe ordem usual operacional de estados.
- Logo, regra de update deve respeitar transicao de estado (maquina de estados), e nao depender de `data_cadastro` como motor principal.

## Riscos observados

1. Quando `data_cadastro` vira eixo principal, pode sobrescrever estado com semantica errada para historico de status.
2. Gate global de `STE` no topo protege um caso real, mas distorce prioridade geral.
3. Testes focados em helper/unit podem passar sem travar contrato E2E de update por snapshot+estado.

## Contrato de correcao sugerido (sem nova tabela)

1. Criterio principal de update:
   - recencia de snapshot (data no nome do arquivo; fallback mtime para nome generico).
2. Criterio secundario:
   - matriz de transicao de estado (ordem usual + transicoes permitidas).
3. Criterio auxiliar:
   - `data_cadastro` apenas para desempate entre transicoes validas.
4. `STE`:
   - tratado dentro da matriz de transicao, nao como gate global dominante.

## Hotfix funcional aplicado no ciclo (2026-03-29)

Escopo minimo para reduzir regressao imediata enquanto a matriz final e validada:

1. Nova coluna `data_planilha` (ISO) no schema e no fluxo de import.
2. `data_planilha` preenchida por:
   - data do nome do arquivo quando parseavel;
   - fallback metadata (`mtime/ctime`) quando nome for generico.
3. Regra de escrita para estados terminais:
   - se estado existente no DB for `STE` ou `SCA`, update bloqueado.
4. Quando houver contexto de arquivo, mas sem timestamp confiavel:
   - update bloqueado (arquivo pode inserir novos registros, mas nao sobrescrever existentes).

Status:

1. item aplicado em runtime
2. cobertura de regressao existe em testes focados de upsert/import

Referencia da matriz draft para validacao:

- `docs/SSA_STATE_MATRIX_DRAFT_20260329.md`

## Situacao dos demais manuais enviados

Arquivos:

- `C:\\Users\\mauri\\Downloads\\g04.pdf`
- `C:\\Users\\mauri\\Downloads\\g05.pdf`

Resultado tecnico em 2026-03-29:

- ambos sem camada de texto extraivel por parser PDF (paginas escaneadas/imagem).
- para extrair esses dois com referencia de pagina/linha, e necessario OCR.

Tentativas ja feitas:

- Adobe Acrobat MCP: falha de autenticacao (`Token exchange failed`).
- Extracao local com `pypdf`: `pages_with_text = 0` em `g05.pdf`.

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->

