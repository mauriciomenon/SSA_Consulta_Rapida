#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || { echo 'Execute dentro de um repo git'; exit 1; })"
HOOK_SRC_DIR="$REPO_ROOT/scripts/git_hooks"
HOOK_DST_DIR="$REPO_ROOT/.git/hooks"

if [[ ! -d $HOOK_SRC_DIR ]]; then
  echo "[install-hooks] Diretorio $HOOK_SRC_DIR nao encontrado." >&2
  exit 1
fi

install_named_hook(){
  local hook_name="$1"
  local src="$HOOK_SRC_DIR/$hook_name"
  if [[ ! -f "$src" ]]; then
    echo "[install-hooks] Hook ausente: $hook_name (pulado)"
    return 0
  fi
  cp "$src" "$HOOK_DST_DIR/$hook_name"
  chmod +x "$HOOK_DST_DIR/$hook_name"
  echo "[install-hooks] Instalado hook $hook_name"
}

install_named_hook "pre-commit"
install_named_hook "pre-push"

# Garante hook path padrao no repositorio local para nao cair em caminho quebrado.
git config --local core.hooksPath ".git/hooks"
echo "[install-hooks] core.hooksPath definido para .git/hooks"

echo "[install-hooks] Concluido. Teste: git commit --allow-empty -m 'hook test'"
