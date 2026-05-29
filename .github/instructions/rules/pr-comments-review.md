---
applyTo: '**'
name: pr-comments-review-project
description: Review de comentarios do PR para SSA_Consulta_Rapida (BLOCO 0 + BLOCO 4)
version: 1.0
blocks: [BLOCO_0, BLOCO_4]
priority: project
---

# Review de Comentarios do PR - SSA_Consulta_Rapida

Este arquivo contem as regras especificas do projeto para review de comentarios do PR. As regras gerais compartilhadas ficam em `general-rules.md`; configuracoes globais da ferramenta podem complementar o contexto, mas nao fazem parte do contrato versionado.

## Contexto do Projeto

- Repositorio: SSA_Consulta_Rapida
- Branch de referencia: dev
- Objetivo: estabilizar codigo, evitar refatoracoes amplas

## Objetivo

Analisar comentarios ja existentes no PR e decidir, com evidencia, o status tecnico de cada um. Nao repetir opinioes. Nao concordar automaticamente com revisores anteriores. Validar tecnicamente cada comentario.

## Processo

### 1. Higiene Inicial

- `git status --short`
- `git branch --show-current`
- `gh pr view`
- `gh pr checks`
- listar comentarios do PR

### 2. Para Cada Comentario

1. identificar arquivo e linha
2. identificar a afirmacao tecnica
3. ler o arquivo inteiro
4. ler callsites
5. ler testes relacionados
6. verificar commits posteriores
7. verificar se ainda se aplica ao estado atual

## Status Possiveis

- CORRIGIDO: o problema foi resolvido com evidencia (commit hash, arquivo/linha)
- AINDA_BLOQUEANTE: o problema persiste e impede merge
- VALIDO_MAS_DEFERIDO: melhoria valida, mas fora do escopo atual
- FALSO_POSITIVO: comentario sem evidencia tecnica aplicavel ao contexto atual
- DECISAO_INTENCIONAL: comportamento mantido por politica aprovada

## Regras de Rigor

- nao assumir que comentario antigo ainda vale
- nao chamar de corrigido sem prova (commit hash, diff, arquivo/linha)
- nao chamar de falso positivo sem explicacao tecnica
- nao tratar melhoria como bloqueador

## Formato Para Cada Comentario

Para cada comentario analisado:
1. Comentario resumido em 1 linha
2. Status: CORRIGIDO/AINDA_BLOQUEANTE/VALIDO_MAS_DEFERIDO/FALSO_POSITIVO/DECISAO_INTENCIONAL
3. Evidencia: arquivo, linha, commit hash, diff ou explicacao tecnica
4. Impacto atual: qual o risco se nao for corrigido
5. Acao recomendada: o que fazer agora

## Politica de Resposta a Comentarios

- Todo comentario deve receber resposta
- Se corrigido: responder com commit hash e arquivo/linha
- Se nao corrigido agora: responder com motivo e status no PR/conversa
- Nao deixar comentario sem status

## Saida Final

1. Comentarios ainda bloqueantes (lista)
2. Comentarios corrigidos (lista com evidencia)
3. Comentarios validos mas deferidos (lista com motivo)
4. Comentarios falso positivo ou decisao intencional (lista com explicacao)
5. Resumo curto (situacao geral dos comentarios)

## Regras Especificas

- Verificar se commits posteriores ao comentario ja resolveram o problema
- Cruzar afirmacao do comentario com estado atual do codigo
- Se comentario menciona arquivo que foi removido, classificar como FALSO_POSITIVO
- Se comentario menciona comportamento que mudou intencionalmente, classificar como DECISAO_INTENCIONAL
