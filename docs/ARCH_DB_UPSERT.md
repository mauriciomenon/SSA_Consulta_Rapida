# ARCH DB UPSERT (v4.43)

Este arquivo e a referencia curta do contrato de update por `numero_ssa`.
Nao e apenas ponte legado.

## Fonte de runtime

1. `armazenamento/database_upsert_logic.py::_should_update_existing`
2. `armazenamento/database_optimized.py::_classify_upsert_rows` (reusa a regra canonica)

## Ordem real de decisao (update de linha ja existente)

1. Estado terminal no banco (`STE` ou `SCA`) bloqueia update.
2. Tenta resolver timestamp de snapshot usando, nesta ordem:
   - `data_planilha`
   - `data_arquivo_origem`
   - parse do nome em `arquivo_origem`
3. Se ha contexto de arquivo novo, mas sem timestamp confiavel: bloqueia update.
4. Se o registro existente tem timestamp de snapshot:
   - novo mais antigo: bloqueia
   - novo mais novo: atualiza
   - empate: segue para comparacao auxiliar
5. Comparacao auxiliar por `data_cadastro`:
   - novo maior: atualiza
   - novo menor: bloqueia
   - empate: tie-break por ranking de `situacao` (nao permite downgrade)
6. Sem datas parseaveis em ambos os lados: atualiza (merge defensivo).

## Merge de campos

Quando update e permitido:

1. valor novo vazio (`None`, `""`, nulo): preserva valor antigo
2. valor novo preenchido: sobrescreve

## Garantias operacionais atuais

1. `numero_ssa` permanece identificador textual canonico.
2. `STE`/`SCA` sao imutaveis para update.
3. Snapshot antigo nao deve sobrescrever snapshot mais novo quando timestamps existem.
4. Fluxo otimizado e fluxo principal usam a mesma funcao de decisao.

## Escopo fora deste contrato

1. Matriz completa de transicao de estados (draft): `docs/SSA_STATE_MATRIX_DRAFT_20260329.md`
2. Historico forense da mudanca de criterio: `docs/FORENSIC_UPDATE_CRITERIA_SSA_20260329.md`

<!-- DOC_SYNC_MAC: 2026-03-30 contract-aligned -->

