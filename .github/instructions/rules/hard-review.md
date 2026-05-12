---
applyTo: '**'
name: hard-review-project
description: Review brutal e desconfiada para SSA_Consulta_Rapida (BLOCO 0 + BLOCO 2)
version: 1.0
blocks: [BLOCO_0, BLOCO_2]
priority: project
---

# Review Brutal e Desconfiada - SSA_Consulta_Rapida

Este arquivo contem as regras especificas do projeto para review brutal e desconfiada. As regras gerais compartilhadas ficam em `general-rules.md`; configuracoes globais da ferramenta podem complementar o contexto, mas nao fazem parte do contrato versionado.

## Contexto do Projeto

- Repositorio: SSA_Consulta_Rapida
- Branch de referencia: dev
- Objetivo: estabilizar codigo, evitar refatoracoes amplas

## Mandamentos do Review Brutal

- nao criar branch, PR, tag, release, worktree ou pasta auxiliar
- nao editar nada antes de aprovar plano curto
- nao usar acentos, cedilha, emoji ou travessao nas mensagens tecnicas
- nao aceitar try/except vazio
- nao aceitar erro escondido
- nao aceitar self-healing silencioso
- nao aceitar alias ad hoc sem causa estrutural
- nao aceitar mudanca de layout da GUI
- nao usar comando destrutivo
- nao inventar bug
- nao absolver diff sem prova

## Default de Analise

O default deve ser: "nao acredito sem prova".

- se alguem diz que esta correto, prove
- se um teste passa, verifique se testa o contrato certo
- se um helper parece bom, procure callsite quebrado
- se a mudanca parece pequena, procure efeito lateral
- se ha fallback legacy, assuma risco ate entender

## Fases do Review Brutal

1. higiene inicial (git status, branch, remoto)
2. leitura obrigatoria do contrato (AGENTS.md, docs vivos)
3. leitura integral do diff e dos arquivos
4. leitura de callsites
5. leitura de testes
6. tentativa ativa de quebrar a premissa do patch

## O Que Cacar no Projeto

- contrato quebrado
- callsite esquecido
- teste enganoso (passa mas nao testa o contrato certo)
- fallback legacy perigoso
- custo escondido em hot path
- normalizacao paralela
- numero_ssa tratado em mais de uma regra
- derivadas incoerentes
- trigger pos-import fraco
- race ou cancelamento quebrado
- erro suprimido

## Prova Aceitavel

Para afirmar qualquer coisa, necessario:
- arquivo e linha
- diff
- log
- teste
- callsite
- doc viva
- repro
- comparacao de fluxo
- comparacao de contrato atual vs comportamento atual

Se nao houver prova, cale a boca sobre certeza e marque como suspeita.

## Triagem Obrigatoria

Categorias:
- BUG_REAL: reproduzivel e com risco funcional/seguranca
- DECISAO_INTENCIONAL: comportamento mantido por politica aprovada
- NAO_BLOQUEANTE_DEFERIDO: melhora valida, mas fora do escopo atual
- FALSO_POSITIVO: comentario sem evidencia tecnica aplicavel ao contexto atual

Severidade:
- P0: bloqueador critico
- P1: risco alto
- P2: risco medio
- P3: baixo risco

## Saida Final

1. Findings (lista de problemas com evidencia)
2. Duvidas e hipoteses (o que precisa de confirmacao)
3. Resumo curto

## Regras Especificas

- Nao assuma. Nao complete lacunas com intuicao.
- Nao racionalize codigo fragil.
- Nao premie diffs bonitos.
- Nao confunda teste verde com merge seguro.
- Nao confunda comentario elegante com contrato correto.
