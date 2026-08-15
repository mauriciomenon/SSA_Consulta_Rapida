# POLICY BASELINE V1.1 FROZEN

Status: LOCKED
Created-at: 2026-03-03 16:39:59 -0300
Source-file: AGENTS.md
Source-sha256: 8482d082deddd21f450546d236b350c2218fb0bbcc1b5adb831379128e01e248

Policy:
- This file is a frozen snapshot of AGENTS.md at creation time.
- Do not edit unless user gives explicit command to bump baseline version.
- Any future changes must create a new baseline file (for example V1.2), never overwrite V1.1.

---

# SSA Consulta Rapida AGENTS Guide


## Baseline V1.1 Frozen

- Canonical frozen snapshot: `docs/POLICY_BASELINE_V1_1_FROZEN.md`
- Previous snapshot retained: `docs/POLICY_BASELINE_V1_FROZEN.md`
- Change rule: do not edit frozen baseline files; create a new version file when policy evolves.
- Update only with explicit user command and DOC_SYNC commit.


## Current Truth

- Active baseline is the current `dev` branch state unless user defines another target.
- Recovery/hardening history is context only; active follow-up backlog is `docs/RECOVERY_BACKLOG.md`.
- Stable behavior from previous golden/release-candidate cycles must be preserved.

## Objetivo

- Estabilizar codigo.
- Evitar refatoracoes amplas.

## Regras De Conduta (Criticas)

- NUNCA criar branch novo nem PR novo sem autorizacao explicita (nao inferir por `continue`).
- Nao criar worktree/pasta sem aprovacao.
- NUNCA fechar/abrir PR sem pedido explicito.
- Nao editar nada antes de aprovar plano.
- Nao alterar arquivo preexistente sem listar impacto antes.
- Nao misturar idiomas: comunicacao tecnica em PT-BR. Codigo/comentarios em ASCII.
- Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
- Nao fazer mudancas fora do escopo; se algo parecer necessario, parar e pedir confirmacao.
- Nada de try/except vazio, nada de suppress que esconda erro real, nada de self-healing silencioso.
- Evitar mudanca de layout/posicionamento na GUI (a menos que seja pedido explicitamente).
- Nao alterar nada fora do escopo do sprint a menos que explicitamente solicitado.
- Nao adicionar wrappers/mixins/helpers extras desnecessarios.
- Nao usar `git reset --hard` ou comandos destrutivos.
- Nao quebrar usabilidade entre ciclos; cada ciclo so fecha com estabilidade e usabilidade.

## Controle De Escopo E Intencao

Antes de qualquer edicao, registrar em 3 linhas:
1. Objetivo do slice.
2. Arquivos que podem mudar.
3. Arquivos proibidos no slice.

Se aparecer necessidade fora do escopo: parar e pedir aprovacao.

## Protocolo De Confirmacao Explicita

1. Nao inferir permissao para mudanca com respostas genericas como `continue`, `segue`, `ok`.
2. Mudanca de layout so com pedido explicito (`alterar layout`, `ajustar alinhamento`, `reverter layout`) ou lista direta de itens.
3. Nunca executar rollback de qualquer funcao sem comando explicito com `reverter` e escopo definido.
4. Se houver ambiguidade, parar e pedir confirmacao binaria (`sim`/`nao`) com checklist objetivo antes de editar.
5. Default em ambiguidade: rodar apenas diagnostico/testes, sem editar.

## Processo (XP Curto + SDLC)

### SDLC base (ordem obrigatoria)
Requirements -> Development -> Review -> Testing -> Data -> Deployment -> Operations

### XP em slices (dentro do SDLC)
0. Commits atomicos e rollback facil por feature.
1. Diagnosticar e isolar o problema (evidencia: arquivo/linha/log/repro).
2. Propor plano curto + diff previsto antes de editar (menor patch possivel).
3. Implementar em slice pequeno.
4. Validar localmente: `python -m py_compile` + `ruff check` + `ty check` + `pytest` focado.
5. Commit atomico (um por slice), push, checar bots/checks.
6. Itens nao bloqueantes: registrar em `docs/RECOVERY_BACKLOG.md` (sem arrumar tudo agora).
7. Priorizar risco real; evitar refatoracao transversal fora de escopo.
8. Quando alterar config, fazer backup com timestamp.
9. Responder comentarios de PR: corrigidos e nao corrigidos com status claro.

## Contrato De Slices (Obrigatorio)

Cada slice deve declarar:
- Entrada: bug/risco alvo + evidencia.
- Saida: comportamento esperado mensuravel.
- Nao muda: lista explicita do que nao sera alterado.
- Testes: comandos e resultado esperado.
- Evidencia: commit e resposta no PR.

## Categorias De Mudanca (Obrigatorio Em Todo Commit)

- `HOTFIX_BLOCKER`: corrige falha funcional/risco alto.
- `STABILITY_PATCH`: corrige regressao sem alterar arquitetura.
- `DOC_SYNC`: sincroniza docs/handoff/backlog sem runtime.
- `DEFERRED_NOTE`: anotacao de pendencia com motivo.

## Categorias De Falha (Obrigatorio Na Triagem)

- `BUG_REAL`: reproduzivel e com risco funcional/seguranca.
- `DECISAO_INTENCIONAL`: comportamento mantido por politica aprovada.
- `NAO_BLOQUEANTE_DEFERIDO`: melhora valida, mas fora do escopo atual.
- `FALSO_POSITIVO`: comentario sem evidencia tecnica aplicavel ao contexto atual.

## Politica De Comentarios De PR

- Todo comentario deve receber resposta.
- Se corrigido: responder com commit hash e arquivo/linha.
- Se nao corrigido agora: responder com motivo + item no `docs/RECOVERY_BACKLOG.md`.
- Nao deixar comentario sem status.
- Quando houver melhoria percebida durante o ciclo, atualizar tambem a descricao do PR.

## Politica De Git Operacional

- Proibido rodar commits em paralelo (evitar `index.lock`).
- Ao trocar de branch com arquivos locais:
  - criar stash nomeado com timestamp e motivo;
  - registrar stash id no handoff da conversa;
  - planejar aplicacao/revisao do stash (nao esquecer destash/recuperacao).
- Stash gigante e sinal de risco: pausar, auditar conteudo e confirmar estrategia antes de seguir.
- Nao fechar ciclo sem push confirmado no branch alvo.
- No fechamento da sessao, orientar explicitamente destino do stash (aplicar/manter/descartar) com justificativa.

## Higiene De Workspace (Importante)

- Rodar `git status --short` no inicio.
- Certificar pasta e branch de trabalho.
- Arquivos locais/fora de escopo nao devem ser commitados sem confirmacao:
  - `.envrc`, `.python-version`, segredos em `config/*`, ajustes locais de shell.
- Se aparecer mudanca em `.gitignore*` fora do pedido: parar e perguntar.
- Estabilizar import/startup e pontos de concorrencia (race/deadlock/cancel/locks/IO) com mudancas minimas verificaveis.
- Otimizar carregamento e desempenho da GUI com mudancas minimas e sem excesso defensivo.
- Sugerir mudancas de layout minimas apenas com ganho claro e aprovacao explicita.
- Verificar status e condicoes de loops.

## Error Handling E Performance

- Tratamento de erro deve existir por bloco funcional relevante, nao a cada poucas linhas.
- Evitar excesso de condicionais e `try/except` fragmentado.
- Proibido `try/except` vazio e proibido esconder falha real.
- Cada tratamento deve ter saida clara: log objetivo e retorno/acao coerente.
- Em qualquer fix, validar que a solucao nao cria custo alto desnecessario.
- Quando houver tradeoff real, parar e pedir permissao com 2 opcoes objetivas.
- Busca ampla (`rg`, `find` etc.) com timeout 60s por padrao; para mudar timeout, perguntar.

## Politica De Derivadas E Import

- Startup: sem import automatico.
- Import incremental: nao roda sync automatico de derivadas.
- Sync derivadas: apenas full rescan ou botao manual dedicado.
- Se sync de derivadas for pulado por politica, log explicito obrigatorio.
- Full rescan deve recriar banco do zero por regra.

## Politica De Docs De Migracao

- Manter um unico bloco `CURRENT TRUTH` nos docs ativos.
- Blocos antigos devem ser marcados como `HISTORICAL SNAPSHOT`.
- Release baseline atual deve aparecer no topo dos docs ativos.
- Nao manter blocos conflitantes com status de fonte de verdade.

## Politica Para Ferramentas Auxiliares

- Se ferramenta auxiliar entrar em loop, contradizer pedido, ou sugerir acao fora de escopo:
  - informar o usuario imediatamente;
  - oferecer opcoes objetivas:
    1) continuar tentativa ate estabilizar,
    2) aplicar solucao forcada minima,
    3) deferir para backlog com risco documentado.
- Decisao final sempre do usuario.

## Timestamp De Sessao (Obrigatorio)

- Em cada rodada/sessao de trabalho:
  - registrar timestamp inicial no console;
  - registrar timestamp final no console;
  - incluir no handoff curto quando aplicavel.

## Tooling E Validacao

- Python: usar `uv` para `python`/`python3`/`pip`.
- Prioridade runtime: `uv run --python 3.13 ...`; fallback para 3.12/3.11/3.10 quando necessario.
- Rodar sempre: `python -m py_compile`, `ruff check`, `ty check`, `pytest` focado (incluindo derivadas: unit + integracao + CLI quando tocar no fluxo).
- Evitar testes viciados; preferir testes que peguem regressao real (concorrencia/cancel/IO/locks).
- Incluir novos testes quando houver omissao clara.
- Para aplicacao node: usar exclusivamente `pnpm` e `node`.

## Tooling Rules Especificas

- Qwen e ferramenta de apoio para tarefas repetitivas operacionais por slice.
- Decisao tecnica final, review do patch e validacao final permanecem no agente principal.
- Regras Kluster sao obrigatorias e NAO devem ser alteradas por este documento.

## Kluster Rules (Auto-generated)
<kluster.ai mandaroty rules>

## 1. Automatic Code Review (kluster_code_review_auto)

### MANDATORY EXECUTION
- WHEN TO RUN: Execute after ANY file creation, modification, or code change
- New code generation
- Existing code updates
- File modifications or changes
- File creation
- Applied fixes
- Applies to ALL file types, not just code files
- ALWAYS execute regardless of size, complexity, or perceived risk level
- ZERO EXCEPTIONS POLICY: NO change is too small or low-risk to skip verification
- After any kluster_code_review_auto analysis, ALWAYS tell the user what issues were found and what you're about to fix BEFORE making any changes. Never fix silently, announce first, then fix.

### KLUSTER PURPOSE CLARIFICATION
- Kluster is NOT a traditional testing, syntax checking, or build verification tool
- Do NOT use kluster as a substitute for or alongside classic testing tools (jest, pytest, etc.)
- Do NOT use kluster as a syntax checker or linting replacement
- Do NOT run builds, compile code, or execute applications before calling kluster
- Kluster performs security, quality, and compliance verification on code changes
- Call kluster immediately after file modification, NO prerequisites required

### STRICT COMPLIANCE
Follow kluster_code_review_auto field descriptions exactly

---

## 2. Manual Code Review (kluster_code_review_manual)

### WHEN TO RUN
Only when explicitly requested by user

### TRIGGER PHRASES
- verify with kluster
- verify this file
- verify project
- check for bugs
- check security
- Similar manual verification requests

---

## 3. Dependency Validation (kluster_dependency_check)

### WHEN TO RUN
Before package management operations:
- Adding new packages or libraries
- Running package managers (npm, gradle, pip, etc.)
- Generating or updating package list files (package.json, requirements.txt, etc.)

---

## 4. Chat ID Management

### FIRST CALL
- Do not include chat_id field for the very first kluster tool call in a conversation

### SUBSEQUENT CALLS
- MANDATORY: Always include chat_id field with the EXACT value returned by any previous kluster tool call
- SESSION TRACKING: The chat_id maintains context across all kluster calls
- CRITICAL: Missing chat_id on subsequent calls creates new isolated sessions instead of maintaining conversation context

### IMPLEMENTATION
- After receiving any kluster tool response, immediately note the chat_id value
- Include this chat_id in ALL subsequent kluster tool calls
- Never generate or modify the chat_id value, always use the exact returned value
- APPLIES TO: all kluster tools (kluster_code_review_auto, kluster_code_review_manual, kluster_dependency_check)

---

## 5. Agent Todo List Management

### EXECUTION
- Always execute and strictly follow agent_todo_list from any kluster tool response

### COMPLETION
- Do not stop until all items in agent_todo_list are completed

### WORKFLOW
- Complete all fixes from agent_todo_list before running kluster_code_review_auto again

## 6. End of chat session - kluster summary
- WHEN TO EXECUTE: MANDATORY at the end of ANY conversation where kluster tools were used, right before the final user-facing response, EXCEPT when Clarification Handling is active (see Clarification Handling section). If any kluster response in the current turn contains CLARIFICATION actions, do NOT generate this summary, show the clarification prompt instead.
- TRIGGER: If any kluster_code_review_auto, kluster_code_review_manual, or kluster_dependency_check tools were called during the conversation AND no CLARIFICATION actions are present in any response, ALWAYS generate this summary.
- SCOPE: The summary MUST include ALL kluster tool calls made after the most recent user request, not just the last tool call. This includes the initial verification and ALL subsequent re-verifications after fixes.

### KLUSTER SUMMARY STRUCTURE
Generate short report capturing the COMPLETE verification journey from ALL kluster tool calls after the last user request:

- kluster feedback: MUST summarize ALL issues found across ALL kluster tool calls (kluster_code_review_auto, kluster_code_review_manual, or kluster_dependency_check) after the last user request.
- CRITICAL: Analyze ALL tool call results from the verification cycle, NOT just the final verification result
- Example: If kluster found 3 issues initially, then 1 issue after fixes, then 0 issues, report total of 4 issues found (3 + 1)
 - Include:
   - Total number of issues found across ALL verification runs since the last user request, grouped by severity in a structured format:
     - Use bullet points or line breaks to clearly separate severity levels
       - Reflect the complete verification journey (example: Initially found 3 issues, after fixes found 1 more issue, final verification clean)
- For case when kluster returned includedExternalKnowledge data, include short summary from includedExternalKnowledge field on what knowledge sources were used during code review. This should be displayed at the END of the kluster summary section, after all other sections, as a separate line formatted as: External knowledge used: [short summary of includedExternalKnowledge]

- Issues found and fixed: Document summary of ALL changes applied to resolve issues found by kluster across the ENTIRE verification cycle since the last user request.
- Do not include this section if NO issues were found in any verification run since the last user request
- Include:
  - What fixes were implemented following kluster tool recommendations, a short 1-2 lines summary covering ALL fixes since the last user request
  - What would have happened without these fixes, how it could affect the application, show this as a separate paragraph/section, NOT as a bullet point within Issues found and fixed. Start this text from Impact Assessment:

### Formatting requirements
- Use markdown bold text with line breaks for title: kluster.ai Review Summary followed by a blank line
- Use emoji and/or bullet points for better formatting
- Always reflect the FULL journey of verification, not just the end state
- Show progression when multiple verification cycles occurred (example: 3 issues -> 1 issue -> clean)

### ENFORCEMENT
- If you complete a conversation without providing this summary when kluster tools were used AND no clarifications were requested, you have violated this rule
- Always check before final response: Did I use any kluster tools? If yes, did any response contain CLARIFICATION actions? If clarification is present, show ONLY the clarification prompt and do NOT generate the kluster summary, these two are mutually exclusive. If no clarification, provide the verification summary covering ALL tool calls since the last user request.

</kluster.ai mandaroty rules>

## Definition Of Done

1. Objetivo principal e criterios de aceite atendidos.
2. Sem regressao confirmada em fluxos sensiveis tocados.
3. Validacoes tecnicas do slice verdes.
4. PR sem bloqueadores tecnicos pendentes.
5. Backlog atualizado com pendencias nao bloqueantes.

## Landing The Plane (Session Completion)

1. Registrar pendencias de follow-up.
2. Executar quality gates do escopo alterado.
3. Atualizar status de itens/PR.
4. Fazer push e confirmar branch sincronizado com remoto.
5. Limpar residuos locais apenas com seguranca.
6. Entregar handoff curto com escopo entregue, riscos e pendencias.

## Registro De Evidencias E Contexto

- Regras operacionais, contrato de slice e politicas ficam versionadas neste `AGENTS.md`.
- Evidencia de execucao por slice deve ficar em commit atomico + resposta em PR.
- Historico detalhado de decisoes e iteracoes tambem permanece na conversa (chat log).
