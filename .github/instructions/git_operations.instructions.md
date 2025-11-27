---
applyTo: '**'
description: Instrucoes para operacoes Git usando GitKraken MCP
---

# Operacoes Git com GitKraken MCP

## PREFERENCIA

**Sempre que possivel, use GitKraken MCP ao inves de comandos git manuais no terminal.**

Vantagens:
- Melhor integracao com o workflow
- Menos erros de digitacao
- Output estruturado
- Suporte a operacoes complexas

## Ferramentas Disponiveis

### Staging e Commits

```
git_add_or_commit
- action: "add" ou "commit"
- directory: diretorio do repo
- files: array de arquivos (opcional)
- message: mensagem de commit (para action=commit)
```

**Exemplo de uso:**
```
Fazer commit de alteracoes:
1. git_add_or_commit(action="add", files=["arquivo.py"])
2. git_add_or_commit(action="commit", message="feat: nova funcionalidade")
```

### Historico e Diffs

```
git_log - Ver historico de commits
git_diff - Ver diferencas entre commits/branches
```

### Branches

```
git_branch - Listar ou criar branches
git_switch - Trocar de branch
git_restore - Restaurar arquivos
```

### Pull Requests

```
git_create_pull_request - Criar novo PR
git_get_pull_requests - Listar PRs
git_get_pull_request_comments - Comentarios de PR
git_get_issue - Detalhes de issue
```

### Worktrees

```
git_worktree - Gerenciar worktrees
```

## Fluxo de Trabalho Recomendado

### Para commits simples:
```
1. Editar arquivo(s)
2. codacy_cli_analyze nos arquivos
3. Corrigir issues se houver
4. git_add_or_commit(action="add", files=[...])
5. git_add_or_commit(action="commit", message="...")
```

### Para criar feature branch:
```
1. git_branch para criar nova branch
2. git_switch para trocar para ela
3. Fazer alteracoes
4. Commits
5. git_create_pull_request quando pronto
```

### Para revisar historico:
```
1. git_log para ver commits recentes
2. git_diff para ver alteracoes especificas
```

## Convencoes de Commit (Conventional Commits)

Use prefixos padronizados:

| Prefixo | Uso |
|---------|-----|
| `feat:` | Nova funcionalidade |
| `fix:` | Correcao de bug |
| `docs:` | Documentacao |
| `style:` | Formatacao (sem mudanca de codigo) |
| `refactor:` | Refatoracao |
| `test:` | Testes |
| `chore:` | Manutencao |
| `perf:` | Performance |
| `ci:` | CI/CD |

**Exemplos:**
- `feat: adicionar filtro por data na GUI`
- `fix: corrigir erro de encoding no Excel`
- `docs: atualizar README com instrucoes de build`
- `refactor: extrair logica de validacao para utils`

## Quando NAO usar GitKraken

- Resolucao de conflitos complexos (usar IDE)
- Rebase interativo (usar terminal)
- Operacoes destrutivas (force push) - **SEMPRE perguntar primeiro**
