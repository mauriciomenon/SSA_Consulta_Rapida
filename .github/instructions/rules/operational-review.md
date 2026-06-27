---
applyTo: '**'
name: operational-review-project
description: Review guiada operacional para SSA_Consulta_Rapida (BLOCO 0 + BLOCO 3)
version: 1.0
blocks: [BLOCO_0, BLOCO_3]
priority: project
---

# Review Guiada Operacional - SSA_Consulta_Rapida

Este arquivo contem as regras especificas do projeto para review guiada operacional. As regras gerais compartilhadas ficam em `general-rules.md`; configuracoes globais da ferramenta podem complementar o contexto, mas nao fazem parte do contrato versionado.

## Contexto do Projeto

- Repositorio: SSA_Consulta_Rapida
- Branch de referencia: dev
- Objetivo: estabilizar codigo, evitar refatoracoes amplas

## Roteiro Operacional Estrito

Nao improvise a ordem. Siga exatamente o fluxo abaixo.

### FASE 1 - HIGIENE

Executar nesta ordem:
1. `git status --short`
2. `git branch --show-current`
3. `git remote -v`
4. `gh pr status` (se aplicavel)
5. `gh pr view` do PR atual (se necessario)

### FASE 2 - LEITURA DE CONTRATO

Ler nesta ordem:
1. AGENTS.md
2. README.md
3. docs/README.md
4. .github/instructions/scanner-code-review.instructions.md

### FASE 3 - LEITURA DO PR

Executar nesta ordem:
1. listar arquivos alterados
2. ler diff completo
3. ler cada arquivo alterado por inteiro
4. localizar callsites
5. localizar testes relacionados
6. ler comentarios do PR
7. ler checks do PR

### FASE 4 - TRIAGEM

Classificar cada suspeita como:
- BUG_REAL: reproduzivel e com risco funcional/seguranca
- DECISAO_INTENCIONAL: comportamento mantido por politica aprovada
- NAO_BLOQUEANTE_DEFERIDO: melhora valida, mas fora do escopo atual
- FALSO_POSITIVO: comentario sem evidencia tecnica aplicavel ao contexto atual

Atribuir severidade:
- P0: bloqueador critico
- P1: risco alto
- P2: risco medio
- P3: baixo risco

### FASE 5 - PRIORIZACAO TECNICA

Procurar primeiro (nesta ordem):
1. storage/write path
2. numero_ssa
3. derivadas
4. import/startup
5. nullable/readback
6. concorrencia/cancelamento/locks/IO
7. performance em caminho quente
8. regressao de contrato
9. lacuna de testes relevante

### FASE 6 - VALIDACAO

Executar nesta ordem:
1. `uv run --python 3.13 python -m py_compile`
2. `uv run --python 3.13 ruff check .`
3. `uv run --python 3.13 ty check`
4. `uv run --python 3.13 python -m pytest -q tests`
5. se necessario, pytest focado

### FASE 7 - SAIDA

1. Findings (lista de problemas com evidencia)
2. Duvidas e hipoteses (o que precisa de confirmacao)
3. Resumo curto

Se nao houver bloqueador: "nao encontrei findings bloqueantes"

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

## Regras Especificas do Review Operacional

- Seguir a ordem das fases exatamente
- Nao pular fases
- Nao improvisar ordem de leitura
- Documentar cada fase executada
- Se alguma fase falhar, documentar o motivo e prosseguir para a proxima
