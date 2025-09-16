#!/usr/bin/env bash
# pre-commit.secret-scan.sh - Bloqueia commits que contenham padrões de segredos em STAGED changes.
# Instalação manual:
#   cp scripts/git_hooks/pre-commit.secret-scan.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
# Opcional: export GIT_HOOKS_VERBOSE=1 para ver detalhes.

set -euo pipefail

PATTERNS=(
  'sk-[A-Za-z0-9]{8,}'
  'hf_[A-Za-z0-9]{8,}'
  'ANTHROPIC_API_KEY=' 'GEMINI_API_KEY=' 'GROQ_API_KEY=' 'COHERE_API_KEY=' 'MISTRAL_API_KEY=' 'TOGETHER_API_KEY=' 'DEEPSEEK_API_KEY=' 'OPENROUTER_API_KEY=' 'FIRECRAWL_API_KEY='
  '[A-Z0-9_]*API_KEY='
)

err(){ echo "[secret-scan][BLOCK] $1" >&2; }
info(){ [[ ${GIT_HOOKS_VERBOSE:-0} -eq 1 ]] && echo "[secret-scan] $1" >&2; }

# Coleta diff staged (apenas adições)
DIFF=$(git diff --cached --unified=0 --no-color || true)
[[ -z $DIFF ]] && exit 0

# Remover linhas removidas e metadados, manter apenas linhas adicionadas começando com '+'
ADDED=$(echo "$DIFF" | grep -E '^\+' | grep -vE '^\+\+\+' || true)
[[ -z $ADDED ]] && exit 0

FOUND=0
for pat in "${PATTERNS[@]}"; do
  if echo "$ADDED" | grep -E -q "$pat"; then
    err "Padrão sensível detectado (regex): $pat"
    FOUND=1
  else
    info "OK: $pat"
  fi
done

if [[ $FOUND -eq 1 ]]; then
  cat <<'EOT' >&2
================ BLOQUEADO ================
Possível segredo detectado no conteúdo staged.
Ações sugeridas:
 1. Remover/mascarar o valor.
 2. Usar variáveis de ambiente (.envrc, keychain) em vez de hardcode.
 3. Se já comitado antes: rotacionar a chave após corrigir.
Override emergencial (NÃO RECOMENDADO): GIT_ALLOW_INSECURE_COMMIT=1 git commit ...
==========================================
EOT
  [[ ${GIT_ALLOW_INSECURE_COMMIT:-0} -eq 1 ]] && {
    echo "[secret-scan] Override GIT_ALLOW_INSECURE_COMMIT=1 ativo – commit permitido (inseguro)." >&2
    exit 0
  }
  exit 1
fi

exit 0

