# Qwen Code Delegation Config

Objetivo
- Delegar lotes mecanicos para Qwen Code 3.5 com baixo custo de token/tempo.
- Manter validacao final e decisao tecnica no agente principal.

Ferramenta
- Binario: `/opt/homebrew/bin/qwen`
- Modelo padrao: `qwen3-coder-plus`
- Modo recomendado: one-shot com prompt curto e formato de saida fixo.

Setup minimo
1. Confirmar binario:
   - `command -v qwen`
2. Teste de vida do modelo:
   - `qwen -m qwen3-coder-plus "Responda apenas: OK QWEN"`
3. Rodar no root do repo:
   - `cd /Users/menon/git/SSA_Consulta_Rapida`

Contrato operacional (obrigatorio)
1. Patch minimo por item.
2. Nao fazer refatoracao ampla.
3. Nao alterar layout GUI sem pedido explicito.
4. Nao usar suppress vazio nem try/except sem tratamento real.
5. Para cada item: acao minima, teste focado, criterio de aceite.
6. Saida curta, em PT-BR tecnico ASCII.
7. Sem instalar dependencia nova sem aprovacao.
8. Nao tocar arquivos fora do lote.
9. Em caso de ambiguidade: retornar opcao A/B com impacto.
10. Entregar checklist por ID antes de sugerir codigo.
11. Regra permanente: usar Qwen em todo slice para tarefas repetitivas aplicaveis (checks e triagem curta).
12. A ausencia de uso do Qwen em tarefa repetitiva aplicavel deve ser tratada como desvio de processo.

Template de prompt (delegacao por lote)
```
Contexto: repo SSA_Consulta_Rapida.
Regras: patch minimo, sem refatoracao ampla, sem mudanca de layout sem pedido,
sem suppress vazio, sem try/except excessivo.
Lote: <IDs> do docs/PENDING_ACTION_MATRIX.md.
Formato de resposta (uma linha por ID):
ID | acao minima | teste focado | criterio de aceite
Maximo de linhas: <N>.
PT-BR tecnico ASCII.
```

Fluxo padrao de execucao
1. Qwen gera checklist por ID (quando houver lote de pendencias).
2. Agente principal implementa ou adapta patch.
3. Qwen executa checks repetitivos do slice (quando aplicavel):
   - `ruff check` (arquivos tocados)
   - `ty check` (arquivos tocados)
   - `pytest` focado no lote
4. Agente principal executa validacao independente final:
   - `python -m py_compile` (arquivos tocados)
   - confirmacao final de `ruff`/`ty`/`pytest`
5. Verificacao kluster apos cada alteracao.
6. Commit atomico por slice.

Regras de validacao final (responsabilidade do agente principal)
1. Confirmar que o patch respeita escopo do lote.
2. Confirmar que nao houve regressao de comportamento fora do lote.
3. Confirmar que todos os gates locais passaram.
4. Confirmar que kluster final do slice esta clean ou com pendencia documentada.
5. Documentar no `docs/RECOVERY_BACKLOG.md` e handoff quando aplicavel.

Metricas de eficiencia (guia)
- Preferir prompts curtos e estruturados para reduzir latencia.
- Preferir lotes de 5 a 10 itens relacionados.
- Evitar pedir para o qwen escrever texto longo; usar saida tabular curta.

Observacao
- Qwen e delegado de execucao assistida.
- A decisao tecnica final, validacao, e responsabilidade de merge permanecem no agente principal.

Arquivos de regra (fonte oficial)
- Regra global de processo: `/Users/menon/git/SSA_Consulta_Rapida/AGENTS.md`
- Regra detalhada de uso do Qwen: `/Users/menon/git/SSA_Consulta_Rapida/docs/QWEN_CODE_DELEGATION_CONFIG.md`
