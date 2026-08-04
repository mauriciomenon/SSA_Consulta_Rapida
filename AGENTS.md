# SSA Consulta Rapida AGENTS Guide

## Baseline V1.1 Frozen

- Canonical frozen snapshot: `docs/POLICY_BASELINE_V1_1_FROZEN.md`
- Previous snapshot retained: `docs/POLICY_BASELINE_V1_FROZEN.md`
- Change rule: do not edit frozen baseline files; create a new version file when policy evolves.
- Update only with explicit user command and DOC_SYNC commit.

## Current Truth

- Active baseline is the current `dev` branch state unless user defines another target.
- Recovery/hardening history is context only; public operational docs must stay minimal.
- Stable behavior from previous golden/release-candidate cycles must be preserved.

## Isolamento Obrigatorio De Host

- No WSL, este repositorio so pode ser operado em `$HOME/gitlab_repo/ssa_consulta_rapida_pyqt6`, em filesystem Linux ext4.
- `$HOME/gitlab` e symlink para o Windows e e proibido para Git, `uv`, Python, build, teste, lint ou scanner POSIX.
- Qualquer caminho em `/mnt/*`, ferramenta `*.exe`, binario PE/MZ ou symlink resolvido para o Windows deve bloquear o harness antes do primeiro efeito colateral.
- Toda chamada POSIX ao guard deve encerrar o fluxo em falha (`ssa_native_guard_tools ... || exit $?`); e proibido executar a ferramenta em uma linha posterior sem short-circuit.
- O preflight de host e ferramentas deve ocorrer antes de `git status`, criacao de `.venv`, instalacao, limpeza, build ou teste.
- `.venv` nunca pode ser copiada ou compartilhada entre Windows, WSL, Linux ou macOS. Ambiente existente incompleto ou de outro host deve falhar; e proibido usar `uv venv --clear` como autorrecuperacao.
- Proibido executar `uv run`, `uv sync` ou `uv venv` diretamente antes do preflight. Aplicar `scripts/env/direnv_common.sh` ou usar entrypoint oficial que fixe `UV_PYTHON` e `UV_PROJECT_ENVIRONMENT`.
- Operacoes Linux sao publicadas pelo clone Linux. Depois do push, o clone Windows e atualizado com `git.exe pull --ff-only origin dev` executado no Windows nativo.
- Build e validacao Windows so podem ocorrer em `$env:USERPROFILE\gitlab\ssa_consulta_rapida_pyqt6`, por ferramentas Windows nativas e fora de sessao WSL.
- Ferramentas POSIX nunca podem chamar executaveis Windows, e ferramentas Windows nunca podem operar o clone Linux. Cada host usa seu clone, venv, Git e toolchain nativos.
- Orquestracao Windows + Debian e permitida somente pelo entrypoint dedicado, usando `wsl.exe` para entrar no clone Linux canonico; nunca mapear o clone Windows em `/mnt/*`.
- O mesmo isolamento se aplica ao repositorio C++ canonico `$HOME/gitlab_repo/ssa_consulta_rapida_cpp`.

## Dados Operacionais Fora Do Git

- O banco operacional Linux canonico fica em `$HOME/.ssaconsultarapida/data/ssas.db`; nunca versionar bancos ou copiar `.ssaconsultarapida` para dentro do Git.
- Os clones Linux mantem apenas a estrutura local necessaria de `data`, `docs_entrada` e `docs_saida`; arquivos grandes permanecem fora do controle de versao.
- Para o Python Linux, definir `SSA_DB_PATH=$HOME/.ssaconsultarapida/data/ssas.db` de forma explicita no comando de execucao.
- Antes de transportar o banco, fechar Python e C++, confirmar ausencia de WAL/SHM, gerar snapshot pela API de backup do SQLite, validar `quick_check` e comparar SHA-256.
- Nao executar Python e C++ como escritores simultaneos no mesmo banco sem teste explicito de concorrencia.

## Contrato De Build E Distribuicao Local

- Windows deve usar PowerShell nativo no clone `$env:USERPROFILE\gitlab\ssa_consulta_rapida_pyqt6`; nunca gerar release Windows pelo WSL ou pelo clone Linux.
- Comando canonico com banco atual: `.\release.ps1 -Target windows -Backend pyinstaller -IncludeRuntimeDb -Yes`.
- A entrega Windows deve gerar dois bundles PyInstaller `onedir` (CLI e GUI), ZIP portatil com pastas e instalador Inno. `onefile` e proibido.
- `_internal` pode conter somente runtime e dependencias. DB, XLS e XLSX sao proibidos dentro de `_internal`.
- Quando solicitado, cada bundle deve conter exatamente `data\ssas.db` ao lado do executavel. `docs_entrada`, `docs_saida`, `exportacao`, `config` e `data` permanecem pastas externas e gravaveis.
- Primeiro startup frozen copia o DB externo para `%APPDATA%\SSA_Consulta_Rapida\data\ssas.db` somente quando o destino nao existe; nunca sobrescrever DB do usuario.
- `SSA_RUNTIME_ROOT` pode selecionar outra pasta gravavel permitida, inclusive dentro do perfil do usuario. O runtime deve criar nela `data`, `docs_entrada`, `docs_saida`, `exportacao`, `reports` e `logs`.
- Saidas locais ficam em `launchers\dist\windows_amd64`, `builds\pyinstaller\windows_amd64`, `builds\packages\windows_amd64` e `dist_packages`. Nunca adicionar executaveis, ZIPs, instaladores ou bancos ao Git.
- Antes e depois do build, executar guardas nativas, testes de contrato, smoke funcional real do artefato e verificacao de hash do DB. Falha bloqueia entrega local.

## Objetivo

- Estabilizar codigo.
- Evitar refatoracoes amplas.
- Garantir que cada mudanca seja pequena, reversivel e validada.
- Manter comunicacao clara e documentada.
- Priorizar risco real e usabilidade.
- Evitar ciclos longos e iteracoes viciadas.
- Garantir que cada passo seja aprovado e compreendido antes de seguir.
- Correcao minima mais eficiente pode envolver reescrita de funcao, mudanca de algoritmo e ate mesmo extracao de funcao, desde que seja o patch mais curto e com menor impacto comprovado.


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
6. Itens nao bloqueantes: registrar na conversa ou no PR, sem publicar backlog interno no repositorio.
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
- Cada decisão de mudança deve ser documentada com evidências técnicas, impacto esperado e plano de rollback, mesmo que o rollback seja apenas a reversão do commit.
- Em caso de patch de performance, o agente deve incluir obrigatoriamente no report do slice:
  - tempo do fluxo alvo antes/depois
  - RSS antes/depois
  - caminho de execucao e quebra por subblocos quando houver hotspot
  - justificativa clara de que a solucao proposta é o patch mais curto e com menor impacto comprovado para resolver o problema identificado.
  - Apos qualquer patch funcional, o agente deve responder com report obrigatorio do slice antes de seguir.

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
- Se nao corrigido agora: responder com motivo e status no PR/conversa.
- Nao deixar comentario sem status.
- Quando houver melhoria percebida durante o ciclo, atualizar tambem a descricao do PR.

## Politica De Git Operacional

- Mapa canonico de remotos: `origin` = GitLab, `bitbucket` = Bitbucket, `gh` = GitHub.
- Neste projeto, o pedido explicito `commitar` autoriza criar o commit e publicar a branch nos dois remotos operacionais: `origin` e `bitbucket`.
- HTTP 403 ou conta suspensa no remote `gh` bloqueia somente GitHub; nao implica bloqueio de fetch, pull ou push em `origin`/`bitbucket`.
- Antes do push duplo, confirmar fast-forward nos dois remotos; nunca usar force push sem autorizacao explicita.
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
- Nao abrir novo slice funcional com arquivos locais modificados de slice anterior sem commit ou deferimento explicito.

## Error Handling E Performance

- Tratamento de erro deve existir por bloco funcional relevante, nao a cada poucas linhas.
- Evitar excesso de condicionais e `try/except` fragmentado.
- Proibido `try/except` vazio e proibido esconder falha real.
- Cada tratamento deve ter saida clara: log objetivo e retorno/acao coerente.
- Em qualquer fix, validar que a solucao nao cria custo alto desnecessario.
- Quando houver tradeoff real, parar e pedir permissao com 2 opcoes objetivas.
- Busca ampla (`rg`, `find` etc.) com timeout 120s por padrao; para mudar timeout, perguntar.
- Levantamento tecnico obrigatorio deve conter ownership de memoria, copias materiais, caches e contrato funcional antes de patch de performance.

## Politica De Docs De Migracao

- Manter um unico bloco `CURRENT TRUTH` nos docs ativos.
- Blocos antigos devem ser marcados como `HISTORICAL SNAPSHOT`.
- Release baseline atual deve aparecer no topo dos docs ativos.
- Nao manter blocos conflitantes com status de fonte de verdade.
- Nao misturar DOC_SYNC com STABILITY_PATCH no mesmo commit.
- Toda alteracao local validada e ainda nao commitada deve ser registrada imediatamente nos docs vivos.
- 

## Politica Para Ferramentas Auxiliares

- Cada mudança deve ser validada com testes focados e ferramentas de análise antes de ser considerada completa, e cada teste deve ser projetado para pegar regressões reais, não apenas verificar que o código não quebre.
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
- Para aplicacao node: usar exclusivamente `pnpm` e quando inevitavel `bun` e `node`.
- 

## Politica De Timeout De Reviews

- Busca ampla continua com `timeout 120s` por padrao.
- Para ferramentas de review e scanner com latencia externa, usar orcamento maior:
  - `clawpatch`: ate `180s` de execucao aberta e mais `60s` de espera/poll em background antes de considerar retry ou bloqueio.
  - `coderabbit`: ate `180s` de execucao aberta e mais `60s` de espera/poll em background antes de considerar retry ou bloqueio.
  - `snyk`: ate `180s` de execucao aberta e mais `60s` de espera/poll em background antes de considerar retry ou bloqueio.
  - `semgrep`: ate `240s` de execucao aberta e mais `60s` de espera/poll em background antes de considerar retry ou bloqueio.
  - `bandit`: ate `240s` de execucao aberta e mais `60s` de espera/poll em background antes de considerar retry ou bloqueio.
  - quando o problema parecer timeout e nao falha deterministica, insistir com pelo menos uma nova rodada calibrada antes de concluir bloqueio.
- Durante a espera em background, o agente deve comecar outra atividade util do mesmo slice sempre que houver trabalho nao sobreposto.
- Timeout de review nunca autoriza marcar verificacao como limpa; se a ferramenta nao concluiu, declarar bloqueio e escopo exato.

## Checklist De Ciclo Maior

- Em todo ciclo maior, manter checklist visivel nas atualizacoes ao usuario com estes estados:
  1. diagnostico atual
  2. slice em execucao
  3. validacao local
  4. review externo (`clawpatch`/`coderabbit`/`semgrep`/`snyk`)
  5. commit
  6. push
  7. backlog/deferidos
- Ao trocar de slice, informar explicitamente:
  - o que fechou no slice anterior;
  - o que continua aberto no ciclo maior;
  - o proximo passo imediato.
- Se houver multiplos commits dentro do mesmo ciclo maior, resumir sempre o placar atual do trabalho antes de seguir.

## Tooling Rules Especificas

- Qwen, clawpatch, coderabbit e scanners sao ferramentas auxiliares; decisao tecnica final, review do patch e validacao final permanecem no agente principal.


## Politicas Aprovadas Em Runtime E Performance GUI

- Toda referencia a commit deve incluir `hash completo + data/hora + titulo`.
- Quando houver relacao tecnica com historico, incluir tambem arquivo, funcao e link clicavel quando possivel.
- Todo diagnostico de performance GUI deve incluir obrigatoriamente:
  - smoke real
  - tempo do fluxo alvo
  - RSS antes/depois
  - caminho de execucao
  - quebra por subblocos reais quando houver hotspot
- Nenhum slice de GUI pode ser fechado so com teste verde.
- Sempre usar `update_plan` quando houver plano.
- Usar subagentes quando houver subtarefas independentes reais e sem risco de conflito.
- Em investigacao de lentidao GUI, o padrao obrigatorio e quebrar o fluxo real em subblocos de runtime antes de propor patch.
- O fluxo de teste GUI deve incluir, quando aplicavel:
  - abertura real da janela
  - cliques reais
  - troca de abas
  - aplicacao de filtros
  - validacao de detalhes
  - verificacao visual basica de posicionamento e texto
- Se a medicao ou o smoke nao foram feitos, isso deve ser declarado como bloqueio.
- Proibido criar funcao, helper, mixin, wrapper, alias ou camada nova apenas para remendar comportamento existente, salvo aprovacao explicita do usuario.
- Nova funcao so entra se for:
  - nova funcionalidade
  - substituicao clara de funcionalidade anterior
  - extracao estrutural explicitamente aprovada
- Em codigo ja localizado, a preferencia padrao e corrigir o fluxo existente, nao adicionar nova camada.
- Se o raciocinio de "patch minimo" comecar a degenerar em costura local em cima de costura local, o agente deve parar, declarar isso explicitamente e pedir nova aprovacao antes de editar.

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

## Regras novas devido a erros acumulados
- Proibido introduzir alias, sinonimo, normalizacao semantica ou mapeamento de termo de negocio na busca superior sem aprovacao explicita do usuario e sem listar:
origem da regra, arquivo onde ela fica, testes de regressao;
- Proibido corrigir repro real com termo especifico do negocio por meio de tabela ad hoc de aliases se a causa estrutural nao estiver provada.
- Qualquer alteracao em parser, normalizacao, alias ou sinonimos da busca deve vir acompanhada de diff previsto lista completa dos termos afetados,
- justificativa de produto e teste de contrato positivo e negativo
- Se existir infraestrutura antiga de alias, fallback, simplificacao ou regra herdada, ela deve ser exposta ao usuario antes de ser reutilizada em fix novo.
- Teste de estabilidade que verifica "nao trava" nao substitui teste de contrato funcional do resultado esperado.
- Textos de ajuda, tooltip e placeholder sao parte do contrato. Se o comportamento mudar, eles devem ser revisados no mesmo slice.
- Timeout de ferramenta de review nao autoriza esconder o risco nem prosseguir como se a verificacao estivesse limpa; o bloqueio deve ser declarado com escopo exato.

## Regra De Entrega De Binarios E Instaladores

Antes de publicar qualquer binario, instalador, DMG, DEB, ZIP ou asset de release:

1. Validar fluxo funcional real no artefato gerado, nao apenas startup, `--help` ou `--version`.
2. Para importacao XLSX, o smoke deve:
   - gerar ou usar XLSX real;
   - executar o entrypoint/CLI empacotado;
   - usar runtime isolado e gravavel;
   - validar linha esperada no SQLite;
   - falhar com exit code nao-zero se havia arquivo candidato e nada foi gravado.
3. Nenhum smoke pode tratar timeout como sucesso.
4. Nenhum erro de release pode terminar apenas como mensagem generica; deve haver stdout/stderr/log com causa objetiva.
5. Build frozen deve provar que nao escreve em bundle read-only e nao depende de caminho relativo do repo.
6. Instalador/DMG nao pode reutilizar artefato stale de versao anterior.
7. Teste que valida apenas abertura do processo nao cobre entrega de producao.
8. Falha em smoke funcional bloqueia upload/tag/release.
9. Qualquer excecao usada como fallback deve registrar causa clara; proibido `pass`, `suppress` ou fallback silencioso em fluxo de entrega.


## Review Rules

### 1. Automatic Code Review

- WHEN TO RUN: execute after ANY file creation, modification, or code change.
- Applies to all file types, not just code files.
- Zero exceptions: no change is too small to skip verification.
- Preferred tool order, adjusted to scope and availability:
  1. `clawpatch` for local diff, staged diff, or file review.
  2. `coderabbit` for PR/external review when a PR exists and the tool is authenticated.
  3. `semgrep`, `bandit`, `detect-secrets`, `gitleaks`, `trufflehog`, `pip-audit`, `snyk`, and other local scanners matching the touched surface.
- Review tools do not replace syntax checks, lint, type checks, tests, builds, or real smoke validation.
- After any review tool reports issues, tell the user what was found and what will be fixed before editing again.
- If a review tool is missing, not authenticated, or times out, declare the exact blocker and continue with equivalent available gates when safe.

### 2. Manual Code Review

- Run manual review only when explicitly requested by the user.
- Trigger phrases include: `review`, `verify this file`, `verify project`, `check for bugs`, `check security`, and similar requests.
- Manual review findings must lead with bugs, risks, regressions, and missing tests, ordered by severity and tied to file/line evidence.

### 3. Dependency Validation

- Run dependency validation before package management operations:
  - Adding packages or libraries.
  - Running package managers.
  - Generating or updating package list files.
- Prefer `pip-audit`, `snyk`, lockfile review, and package-manager native audit tools that match the stack.

### 4. Tool Action Items

- Always execute and strictly follow actionable todo items returned by review tools when they are in scope and technically valid.
- If a tool suggests work outside scope, architecture churn, rollback, or ambiguous behavior, stop and ask the user before editing.
- Complete accepted tool action items before running the same review gate again.

### 5. End Of Session Review Summary

- If review tools were used after the most recent user request, include a short final review summary.
- The summary must cover all review runs in the current cycle, not only the last one.
- Include total issues found by severity, fixes applied, unresolved blockers, and external knowledge used when a tool reports it.
- If a tool was blocked or timed out, report it as blocked; never mark that gate clean.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

## Ferramentas Locais Disponiveis

- `uv tool`: `semgrep`, `bandit`, `ruff`, `pylama`, `pylint`, `mypy`, `pytype`, `pydocstyle`, `vulture`, `xenon`, `ggshield`, `sourcery-cli`, `pip-audit`, `detect-secrets`, `safety`, `checkov`
- `brew`: `gitleaks`, `trufflehog`, `trivy`, `grype`, `sonar-scanner`, `kube-bench`, `kics`, `talisman`, `cppcheck`, `flawfinder`, `cbmc`, `shellcheck`, `bashate`, `golangci-lint`, `gosec`, `govulncheck`, `staticcheck`, `snyk-cli`,`vulture`, `lacework-cli`, 
- `cargo`: `cargo-audit`, `cargo-deny`
- `pnpm -g`: `eslint`, `@biomejs/biome`, `oxlint`, `jscpd`, `@socketsecurity/cli`
- repo-local: DeepSec can live under `.deepsec/`; keep that directory ignored and rerun it with `pnpm deepsec scan`, `pnpm deepsec process`, and `pnpm deepsec export --format md-dir --out ./findings` from inside `.deepsec/`.

### Binarios E Mapeamentos

- Ferramentas extras podem ser indicadas para instalacao pelo agente, e instaladas apos aprovacao do usuario.
- `sourcery-cli` costuma expor o binario `sourcery`
- `@biomejs/biome` expõe o binario `biome`
- `@socketsecurity/cli` expõe o binario `socket`
- `snyk-cli` expõe o binario `snyk`
- `lacework-cli` expõe o binario `lacework`

### Receitas Locais Uteis

- `pip-audit` com `uv.lock` sem depender de venv temporaria do host:
  - `uv export --locked --format requirements.txt --no-emit-project --output-file /tmp/ssa_uv_export_requirements_no_project.txt`
  - `pip-audit -r /tmp/ssa_uv_export_requirements_no_project.txt --require-hashes --disable-pip --progress-spinner off -f json`


## Politica De Derivadas E Import

- Startup: sem import automatico.
- Import incremental: nao roda sync automatico de derivadas.
- Sync derivadas: apenas full rescan ou botao manual dedicado.
- Se sync de derivadas for pulado por politica, log explicito obrigatorio.
- Full rescan deve recriar banco do zero por regra.
