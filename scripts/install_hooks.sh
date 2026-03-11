#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || { echo 'Execute dentro de um repo git'; exit 1; })"
HOOK_SRC_DIR="$REPO_ROOT/scripts/git_hooks"
HOOK_DST_DIR="$(git rev-parse --git-path hooks 2>/dev/null || true)"

if [[ ! -d $HOOK_SRC_DIR ]]; then
  echo "[install-hooks] Diretorio $HOOK_SRC_DIR nao encontrado." >&2
  exit 1
fi

if [[ -z "${HOOK_DST_DIR:-}" ]]; then
  echo "[install-hooks] Nao foi possivel resolver diretorio de hooks via git." >&2
  exit 1
fi

mkdir -p "$HOOK_DST_DIR"
missing_hooks=()

install_named_hook(){
  local hook_name="$1"
  local src="$HOOK_SRC_DIR/$hook_name"
  if [[ ! -f "$src" ]]; then
    echo "[install-hooks] ERRO: hook obrigatorio ausente: $hook_name" >&2
    missing_hooks+=("$hook_name")
    return 1
  fi
  cp "$src" "$HOOK_DST_DIR/$hook_name"
  chmod +x "$HOOK_DST_DIR/$hook_name"
  echo "[install-hooks] Instalado hook $hook_name"
}

install_named_hook "pre-commit" || true
install_named_hook "pre-push" || true

if [[ ${#missing_hooks[@]} -gt 0 ]]; then
  echo "[install-hooks] ERRO: hooks obrigatorios ausentes: ${missing_hooks[*]}" >&2
  exit 1
fi

echo "[install-hooks] Hooks instalados em: $HOOK_DST_DIR"

echo "[install-hooks] Concluido. Teste: git commit --allow-empty -m 'hook test'"
