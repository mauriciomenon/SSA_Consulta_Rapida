# SSA Consulta Rapida AGENTS Guide

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

## Politica Para Ferramentas Auxiliares

- Se ferramenta auxiliar entrar em loop, contradizer pedido, ou sugerir acao fora de escopo:
  - informar o usuario imediatamente;
  - oferecer opcoes objetivas:
    1) continuar tentativa ate estabilizar,
    2) aplicar solucao forcada minima,
    3) deferir para backlog com risco documentado.

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
