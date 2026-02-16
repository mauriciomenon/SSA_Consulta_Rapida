# AGENTS Handoff For Next Cycle

This handoff is ready to reuse in the next conversation.

## Estado atual

- Merge concluido do trabalho de recovery/hardening.
- Registro de backlog criado em `/Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md`.
- Fluxo final ficou com checks tecnicos estaveis e ajustes defensivos aplicados sem mexer em layout da GUI.
- PR #30 (codex/import-review) aceito; proxima etapa: refatoracao de `gui/gui_ssa.py` com foco em separar responsabilidades sem alterar layout.

## O que foi feito (resumo)

- Hardening de concorrencia e estado em fluxo async/filtros/workers.
- Correcoes pontuais em wrappers de teste com timeout/kill/cleanup mais robustos.
- Ajustes de testes para isolamento e regressao.
- Correcoes pequenas de qualidade em tipos e comportamento defensivo.
- Commits atomicos, com validacao a cada lote.

## Como foi feito (metodo)

- Ciclos curtos: diagnostico -> patch minimo -> validacao -> commit atomico -> push.
- Validacao tecnica por lote:
  - `py_compile`
  - `ruff`
  - `pytest` focado + suites sensiveis
- Recheque de PR/reviews/checks apos cada push.
- Sem refatoracao ampla fora de escopo.
- Sem mudanca de posicao de botoes/layout.

## Regras de execucao para o novo ciclo

1. Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: `py_compile`, `ruff`, `pytest` focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito.
6. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
7. Manter backlog de follow-up em `/Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md`.

## Objetivo do novo ciclo

- Manter o mesmo cuidado, com foco na refatoracao de `gui/gui_ssa.py` (SSAMainWindow) para reduzir acoplamento.
- Preservar layout e comportamento da GUI; refatoracao deve ser estrutural, nao visual.
- Fazer levantamento detalhado antes de mover metodos para novos modulos.

## Texto pronto para abrir a nova conversa

```text
Contexto: branch de recovery foi mergeada; manter mesma disciplina de qualidade.

Regras de execucao:
1. Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
2. Commits atomicos e rollback facil por feature.
3. Sempre validar antes de push: py_compile, ruff, pytest focado.
4. Priorizar correcoes de risco real; evitar refatoracao transversal fora de escopo.
5. Nao alterar layout/posicao de elementos GUI sem pedido explicito.
6. Revisar bots/checks no PR e tratar apenas o que for bloqueante agora.
7. Manter backlog de follow-up em /Users/menon/git/SSA_Consulta_Rapida/docs/RECOVERY_BACKLOG.md.

Objetivo do novo ciclo: manter o mesmo cuidado, mas com foco funcional novo.
Objetivo atual: refatorar gui/gui_ssa.py sem mudar layout, com levantamento detalhado antes.
```
