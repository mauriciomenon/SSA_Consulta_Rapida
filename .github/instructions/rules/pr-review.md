---
applyTo: '**'
name: pr-review-project
description: Review completa de PR para SSA_Consulta_Rapida (BLOCO 0 + BLOCO 1)
version: 1.0
blocks: [BLOCO_0, BLOCO_1]
priority: project
---

# Review Completa de PR - SSA_Consulta_Rapida

Este arquivo contem as regras especificas do projeto para review completa de PR. As regras gerais compartilhadas ficam em `general-rules.md`; configuracoes globais da ferramenta podem complementar o contexto, mas nao fazem parte do contrato versionado.

## Contexto Geral do PR

- Repositorio: SSA_Consulta_Rapida
- Branch de referencia: dev
- Objetivo principal: estabilizar codigo e evitar refatoracoes amplas
- Identificar baseline atual antes de iniciar review

## Como Ler o PR

1. ler o diff completo
2. listar arquivos alterados
3. ler cada arquivo alterado por inteiro
4. ler callsites
5. ler testes relacionados
6. ler checks e comentarios do PR
7. cruzar com docs vivos (AGENTS.md, README, docs/*)

## Triagem Obrigatoria

Categorias:
- BUG_REAL: reproduzivel e com risco funcional/seguranca
- DECISAO_INTENCIONAL: comportamento mantido por politica aprovada
- NAO_BLOQUEANTE_DEFERIDO: melhora valida, mas fora do escopo atual
- FALSO_POSITIVO: comentario sem evidencia tecnica aplicavel ao contexto atual

Severidade:
- P0: bloqueador critico, impede merge
- P1: risco alto, deve ser corrigido antes do merge
- P2: risco medio, pode ser deferido com nota
- P3: baixo risco, informativo

## O Que Priorizar no Projeto

1. integridade de dados
2. write path
3. import/startup
4. numero_ssa
5. derivadas
6. nullable/readback
7. concorrencia/cancelamento/locks/IO
8. performance em caminho quente
9. regressao de contrato

## Formato Obrigatorio de Finding

Para cada problema encontrado:
- Severidade: P0/P1/P2/P3
- Categoria: BUG_REAL/DECISAO_INTENCIONAL/NAO_BLOQUEANTE_DEFERIDO/FALSO_POSITIVO
- Arquivo e linha
- Evidencia
- Comportamento atual
- Impacto
- Justificativa tecnica
- Status de merge

## Regras Especificas do Review

- NUNCA criar branch, PR, worktree ou pasta auxiliar
- NUNCA editar nada antes de aprovar plano curto
- NUNCA alterar arquivo preexistente sem listar impacto antes
- NUNCA aceitar try/except vazio
- NUNCA aceitar suppress que esconda falha real
- NUNCA aceitar self-healing silencioso
- NUNCA aceitar alias ad hoc sem causa estrutural provada
- NUNCA aceitar mudanca de layout da GUI sem pedido explicito

## Saida Final do Review

1. Findings (lista de problemas encontrados com formato obrigatorio)
2. Duvidas e hipoteses (o que precisa de confirmacao)
3. Resumo curto (situacao geral do PR)

Se nao houver findings bloqueantes, escrever: "nao encontrei findings bloqueantes"

## Validacao no Review

Executar sempre apos analise do diff:
- `uv run --python 3.13 python -m py_compile`
- `uv run --python 3.13 ruff check .`
- `uv run --python 3.13 ty check`
- `uv run --python 3.13 python -m pytest -q tests`
- se necessario, pytest focado
