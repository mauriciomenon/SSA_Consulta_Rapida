---
applyTo: '**'
name: general-rules-project
description: Regra geral de operacao no repositorio SSA_Consulta_Rapida (BLOCO 0)
version: 1.0
blocks: [BLOCO_0]
priority: project
---

# Regras Gerais de Operacao - SSA_Consulta_Rapida

Este arquivo contem as regras especificas do projeto SSA_Consulta_Rapida. Regras globais da ferramenta podem complementar este arquivo, mas nao fazem parte do contrato versionado do repositorio.

## Contexto do Projeto

- Repositorio: SSA_Consulta_Rapida
- Branch principal: dev
- Objetivo: estabilizar codigo, evitar refatoracoes amplas

## Regras Absolutas do Projeto

- NUNCA criar branch novo sem autorizacao explicita
- NUNCA criar PR novo sem autorizacao explicita
- NUNCA fechar ou abrir PR sem pedido explicito
- NUNCA criar worktree ou pasta auxiliar sem aprovacao
- NUNCA editar nada antes de aprovar plano curto
- NUNCA alterar arquivo preexistente sem listar impacto antes
- NUNCA misturar idiomas; comunicacao tecnica em PT-BR
- NUNCA usar acentos, cedilha, emoji ou travessao nas mensagens tecnicas
- NUNCA fazer mudancas fora do escopo
- NUNCA usar try/except vazio
- NUNCA usar suppress que esconda erro real
- NUNCA aceitar self-healing silencioso
- NUNCA alterar layout ou posicao da GUI sem pedido explicito
- NUNCA usar git reset --hard ou comando destrutivo
- NUNCA inferir permissao a partir de "continue", "ok", "segue" ou equivalente

## Higiene Inicial Obrigatoria

Antes de qualquer acao neste repositorio:
1. rodar `git status --short`
2. confirmar branch atual (esperado: dev)
3. confirmar pasta atual na raiz do repositorio SSA_Consulta_Rapida
4. confirmar remoto
5. observar arquivos locais fora de escopo (.envrc, .python-version, segredos em config/*)

## Leitura Obrigatoria do Projeto

Antes de agir, ler:
- AGENTS.md (na raiz do projeto)
- README.md
- docs/README.md
- .github/instructions/scanner-code-review.instructions.md

## Fonte de Verdade

- AGENTS.md (topo dos docs vivos)
- README atual
- docs publicos versionados
- pendencias internas devem ficar no PR/conversa, nao em backlog publico

## Processo Padrao

1. diagnosticar e isolar o problema com evidencia
2. propor plano curto com menor patch possivel
3. listar: objetivo do slice, arquivos que podem mudar, arquivos proibidos
4. esperar aprovacao explicita antes de editar
5. implementar em slice pequeno
6. validar localmente
7. se houver pendencia nao bloqueante, registrar como backlog
8. entregar resultado com riscos e proximos passos

## Controle de Escopo e Intencao

Antes de qualquer edicao, registrar em 3 linhas:
1. Objetivo do slice
2. Arquivos que podem mudar
3. Arquivos proibidos no slice

Se aparecer necessidade fora do escopo: parar e pedir aprovacao.

## Regras de Evidencia

- nao afirme sem arquivo, linha, diff, teste, log, comando, repro ou doc vivo
- se nao puder provar, diga claramente que e suspeita
- se for so melhoria, nao chame de bug
- se algo parecer intencional, prove pelo contrato

## Classificacao Obrigatoria em Qualquer Tarefa

- BUG_REAL: reproduzivel e com risco funcional/seguranca
- DECISAO_INTENCIONAL: comportamento mantido por politica aprovada
- NAO_BLOQUEANTE_DEFERIDO: melhora valida, mas fora do escopo atual
- FALSO_POSITIVO: comentario sem evidencia tecnica aplicavel ao contexto atual

## Categorias de Mudanca (Obrigatorio em Todo Commit)

- HOTFIX_BLOCKER: corrige falha funcional/risco alto
- STABILITY_PATCH: corrige regressao sem alterar arquitetura
- DOC_SYNC: sincroniza docs/handoff/backlog sem runtime
- DEFERRED_NOTE: anotacao de pendencia com motivo

## Regras de Performance

- evitar reprocessamento amplo
- evitar loops redundantes
- evitar fallback caro
- evitar coercao de DataFrame repetida em caminho quente
- se houver tradeoff real, apresentar 2 opcoes objetivas

## Regras de Error Handling

- tratamento por bloco funcional relevante
- sem try/except vazio
- sem erro escondido
- log objetivo
- retorno coerente

## Validacao Padrao do Projeto

- usar uv para Python
- comandos base:
  - `uv run --python 3.13 python -m py_compile`
  - `uv run --python 3.13 ruff check .`
  - `uv run --python 3.13 ty check`
  - `uv run --python 3.13 python -m pytest -q tests`
- se a suite completa for pesada, usar pytest focado
- preferir testes que peguem regressao real
- para aplicacao node: usar exclusivamente pnpm e node

## Politica de Git Operacional

- Proibido rodar commits em paralelo (evitar index.lock)
- Ao trocar de branch com arquivos locais: criar stash nomeado com timestamp e motivo
- Stash gigante e sinal de risco: pausar, auditar conteudo e confirmar estrategia
- Nao fechar ciclo sem push confirmado no branch alvo

## Politica de Derivadas e Import

- Startup: sem import automatico
- Import incremental: nao roda sync automatico de derivadas
- Sync derivadas: apenas full rescan ou botao manual dedicado
- Full rescan deve recriar banco do zero por regra

## Politica de Docs de Migracao

- Manter um unico bloco CURRENT TRUTH nos docs ativos
- Blocos antigos devem ser marcados como HISTORICAL SNAPSHOT
- Release baseline atual deve aparece no topo dos docs ativos

## Higiene de Workspace

- Arquivos locais/fora de escopo nao devem ser commitados sem confirmacao: .envrc, .python-version, segredos em config/*, ajustes locais de shell
- Se aparecer mudanca em .gitignore* fora do pedido: parar e perguntar
- Estabilizar import/startup e pontos de concorrencia (race/deadlock/cancel/locks/IO) com mudancas minimas verificaveis

## Regras de Review e Scanner (Obrigatorio)

- Se editar arquivo, rodar verificacao local relevante apos a mudanca
- Scanners e review externo nao substituem testes classicos
- Se scanner obrigatorio ou review externo solicitado falhar, declarar bloqueio com escopo exato
- Nunca tratar falha de ferramenta como review limpa
- Informar o usuario sobre issues encontradas antes de corrigir
- Executar itens acionaveis retornados por ferramenta de review antes de prosseguir
- Resumir ferramentas usadas, issues encontradas, fixes aplicados e riscos restantes ao final

## Formato de Resposta

- tecnico, direto, sem floreio
- findings primeiro quando houver
- depois duvidas e hipoteses
- depois resumo curto
- se nao houver finding, dizer isso explicitamente

## Regra de Anti-Inferencia Agressiva

- NUNCA inferir situacao de contorno com informacao faltante. Se o usuario menciona algo ambiguo (outra maquina, outro branch, outro contexto) — PERGUNTAR antes de agir.
- NUNCA ficar preguicoso. Sempre ler arquivos completos, sempre verificar contexto, sempre usar subagentes para analise profunda antes de propor acao.
- Sidequest proibido por inferencia. Nao gastar tempo investigando hipoteses propria quando a informacao e insuficiente. Perguntar ao usuario em vez de adivinhar.
- Exemplo de erro: Usuario disse "codex esta segurando commits" — em vez de perguntar "nessa maquina ou outra?", assumiu que era nesta maquina e investigou stashes locais irrelevantes. Isso e tempo perdido e ruido.
- NUNCA executar comandos que modifiquem o sistema em Plan Mode. Plan Mode e exclusivamente leitura, busca e analise.

## Meta Final

- preservar estabilidade
- evitar ruido
- fazer o minimo necessario com evidencia maxima
