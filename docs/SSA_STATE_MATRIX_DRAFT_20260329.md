# Matriz de Estados SSA (Draft para validacao)

## Objetivo

- Consolidar matriz de transicao de estados para decisao de update no banco.
- Base: codigos ativos do projeto + evidencia dos manuais.
- Status: DRAFT para validacao do usuario.

## Estados canonicos atuais

- Emissao/planejamento: `ASE`, `ADI`, `APG`, `APL`, `AAD`, `AAT`, `ACC`, `ACS`, `ADM`, `AIM`, `AIP`, `AMP`, `APV`, `ASI`, `ASO`
- Programacao/execucao: `SPG`, `SRP`, `SES`, `SEE`
- Aprovacao da execucao: `SAS`, `SAD`
- Cancelamento: `SCS`, `SCD`, `SCA`
- Terminal: `STE`

## Aliases historicos propostos

- `APR -> APG`
- `SPR -> SPG`
- `SCE -> SCA`
- `ALE -> AIP`
- `APM -> AMP`
- `ASL -> ASI`

## Arvore principal (visao operacional)

```text
ASE -> ADI -> APG
APG -> (AAD|AAT|ACC|ACS|ADM|AIM|AIP|AMP|APV|ASI|ASO|APL|SPG|SRP|SES)
(AAD|AAT|ACC|ACS|ADM|AIM|AIP|AMP|APV|ASI|ASO|APL) -> (SPG|SRP|SES)
(SPG|SRP|SES) -> SEE
SEE -> SAS -> SAD -> STE
qualquer estado nao terminal -> (SCS -> SCD -> SCA) ou direto SCA
STE e SCA: sem saida (imutaveis)
```

## Regras de transicao (draft)

1. Estado igual: permitido.
2. Estado terminal em DB (`STE`, `SCA`): bloquear update.
3. Transicao backward (regressao): bloquear.
4. Saltos forward por snapshot (ex.: `ADM -> STE`): permitido, pois snapshot pode nao conter todos os intermediarios.
5. Estados fora da matriz: registrar warning e tratar como nao confiavel para update.

## Pontos abertos para validacao humana

1. `SES`: ponte para `SEE` ou estado quase terminal no fluxo local.
2. `APL`: subestado de planejamento dentro de `APG` ou trilha separada.
3. Cancelamento com `SCS/SCD`: obrigatorio ou opcional.
4. Politica final para estado desconhecido em planilha: bloquear sempre ou permitir apenas insert.


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

