#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || { echo 'Execute dentro de um repo git'; exit 1; })"
HOOK_SRC_DIR="$REPO_ROOT/scripts/git_hooks"
HOOK_DST_DIR="$REPO_ROOT/.git/hooks"

if [[ ! -d $HOOK_SRC_DIR ]]; then
  echo "[install-hooks] Diretorio $HOOK_SRC_DIR nao encontrado." >&2
  exit 1
fi

install_hook(){
  local src="$1"; local name
  name="$(basename "$src")"
  # Se arquivo se chamar pre-commit.* use nome base pre-commit
  if [[ $name == pre-commit* ]]; then
    cp "$src" "$HOOK_DST_DIR/pre-commit"
    chmod +x "$HOOK_DST_DIR/pre-commit"
    echo "[install-hooks] Instalado pre-commit a partir de $name"
  else
    # Nome igual
    cp "$src" "$HOOK_DST_DIR/$name"
    chmod +x "$HOOK_DST_DIR/$name"
    echo "[install-hooks] Instalado hook $name"
  fi
}

for f in "$HOOK_SRC_DIR"/*; do
  [[ -f $f ]] || continue
  install_hook "$f"
done

echo "[install-hooks] Concluido. Teste: git commit --allow-empty -m 'hook test'"
