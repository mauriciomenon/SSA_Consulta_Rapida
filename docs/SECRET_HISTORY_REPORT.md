# Relatório de Limpeza de Segredos

Data de geração: (gerar manualmente quando atualizar)

## Escopo
Este relatório documenta:
- Padrões sensíveis mapeados (sk-, hf_, *_API_KEY)
- Método de substituição (`git filter-repo --replace-text replacements.txt`)
- Verificações pós-rewrite

## Padrões Monitorados
```
sk-[A-Za-z0-9]{8,}
hf_[A-Za-z0-9]{8,}
(ANTHROPIC_API_KEY|GEMINI_API_KEY|GROQ_API_KEY|COHERE_API_KEY|MISTRAL_API_KEY|TOGETHER_API_KEY|DEEPSEEK_API_KEY|OPENROUTER_API_KEY|FIRECRAWL_API_KEY)=
[A-Z0-9_]*API_KEY=
```

## Procedimento Executado
1. Tag de segurança criada: `pre-filter-repo-YYYYMMDD-HHMMSS`.
2. Arquivo `replacements.txt` adicionado com regex de substituição.
3. Execução: `git filter-repo --replace-text replacements.txt`.
4. Verificação working tree: grep sem ocorrências dos padrões.
5. Verificação histórica: loop por `git rev-list --all` sem matches.
6. Adicionados mecanismos preventivos: hook pre-commit e workflow CI.

## Resultados
- Working tree: LIMPO
- Histórico reescrito: sem padrões detectados nos critérios aplicados.
- CI configurado para bloquear regressões futuras.

## Recomendações Contínuas
- Rotacionar chaves imediatamente após qualquer suspeita de exposição.
- Evitar inserir tokens diretos em `.vscode/settings.json` ou arquivos de config versionados.
- Usar `.envrc` + direnv ou solução de secret manager (ex.: 1Password CLI, Bitwarden, Keychain) para injeção local.
- Executar `./scripts/shell_doctor.sh --full` mensalmente.

## Auditorias Futuras
Adicionar (opcional) ferramentas mais robustas:
- trufflehog
- gitleaks
- detect-secrets

Integração possível: combinar relatórios JSON em `reports/security/`.

---
Documento inicial – atualize conforme novos padrões ou incidentes.

## Apêndice A – Limitações da Recuperação Exata (Pós Filter-Repo)

Após a execução de `git filter-repo`, não permanecem refs de backup (`.git/refs/filter-repo/*`) nem tags datadas anteriores além da(s) tag(s) `pre-filter-repo-*` criada(s) manualmente. Como nenhum snapshot explícito dos blobs anteriores foi preservado em refs internas, a re-extração literal dos tokens originais agora não é mais possível apenas com o estado atual do repositório.

Resumo:
- Padrões confirmados antes do rewrite: `sk-...`, `hf_...`, `FIRECRAWL_API_KEY=...` em `.vscode/settings.json`.
- Conteúdo exato foi substituído pelas strings `SK_REDACTED`, `HF_REDACTED`, `REDACTED_VALUE` conforme `replacements.txt`.
- Sem refs residuais → sem possibilidade de reconstruir os valores originais localmente.

Se um backup (clone antigo, fork ou mirror remoto) ainda existir em outra máquina/servidor, os tokens podem continuar expostos ali. Ações recomendadas:
1. Enumerar forks privados/públicos (se houver) e solicitar atualização / deleção.
2. Garantir que TODAS as chaves envolvidas foram rotacionadas (mesmo que não se recorde do uso). Priorizar as com prefixo `sk-` e tokens Hugging Face (`hf_`).
3. Monitorar logs de uso anômalo nos provedores (se disponível) nas 72h subsequentes à rotação.

## Apêndice B – Como Proceder com Outros Repositórios

1. Rodar varredura rápida:
	```bash
	git rev-list --all | while read c; do git --no-pager grep -E 'sk-|hf_|API_KEY' $c >/dev/null && echo "hit $c"; done
	```
2. Se houver hits, criar `replacements.txt` específico e repetir processo de limpeza.
3. Antes de reescrever histórico, sempre gerar:
	```bash
	git tag pre-filter-repo-$(date +%Y%m%d-%H%M%S)
	git bundle create backup_before_clean.bundle --all
	```
4. Após limpeza, instalar hook + ativar CI (copiar `scripts/git_hooks` e `.gitleaks.toml`).

## Apêndice C – Checklist de Rotação de Segredos

- [ ] Identificar provedores usados (OpenRouter/OpenAI, Hugging Face, Firecrawl, etc.)
- [ ] Criar novas chaves
- [ ] Atualizar `.envrc` / secret manager
- [ ] Revogar chaves antigas
- [ ] Verificar logs de acesso anômalo
- [ ] Registrar data/hora da rotação em um changelog interno

---
