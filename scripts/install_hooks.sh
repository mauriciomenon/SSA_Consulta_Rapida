#!/usr/bin/env bash
set -euo pipefail

authorship_only=0
case "${1:-}" in
  --authorship-only) authorship_only=1 ;;
  '') ;;
  *) echo 'Uso: scripts/install_hooks.sh [--authorship-only]' >&2; exit 2 ;;
esac

SCRIPT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_REPO_ROOT}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$SCRIPT_REPO_ROOT" || exit 1
ssa_native_guard_tools git mkdir cat chmod cmp || exit 1
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || { echo 'Execute dentro de um repo git'; exit 1; })"
if [[ "$(cd "$REPO_ROOT" && pwd -P)" != "$SCRIPT_REPO_ROOT" ]]; then
  echo '[install-hooks] Repo ativo difere do repo do script.' >&2
  exit 1
fi
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
install_failures=()

install_named_hook(){
  local hook_name="$1"
  local src="$HOOK_SRC_DIR/$hook_name"
  if [[ ! -f "$src" ]]; then
    echo "[install-hooks] ERRO: hook obrigatorio ausente: $hook_name" >&2
    missing_hooks+=("$hook_name")
    return 1
  fi
  local dst="$HOOK_DST_DIR/$hook_name"
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ ! -L "$dst" ]] && cmp -s "$src" "$dst"; then
      if [[ ! -x "$dst" ]]; then
        echo "[install-hooks] ERRO: hook identico sem permissao de execucao: $dst" >&2
        return 1
      fi
      echo "[install-hooks] Hook identico preservado: $hook_name"
      return 0
    fi
    echo "[install-hooks] ERRO: hook existente preservado; integrar manualmente: $dst" >&2
    return 1
  fi
  if ! (set -o noclobber; cat "$src" > "$dst"); then
    echo "[install-hooks] ERRO: falha ao copiar hook: $hook_name" >&2
    return 1
  fi
  if ! chmod +x "$HOOK_DST_DIR/$hook_name"; then
    echo "[install-hooks] ERRO: falha ao aplicar permissao no hook: $hook_name" >&2
    return 1
  fi
  echo "[install-hooks] Instalado hook $hook_name"
}

hook_names=(pre-commit commit-msg pre-push)
if [[ "$authorship_only" -eq 1 ]]; then
  hook_names=(commit-msg pre-push)
fi
for hook_name in "${hook_names[@]}"; do
  install_named_hook "$hook_name" || install_failures+=("$hook_name")
done

bootstrap_pre_commit(){
  local config_file="$REPO_ROOT/.pre-commit-config.yaml"
  if [[ ! -f "$config_file" ]]; then
    echo "[install-hooks] pre-commit config nao encontrada; bootstrap opcional ignorado."
    return 0
  fi

  if ! command -v pre-commit >/dev/null 2>&1; then
    echo "[install-hooks] AVISO: pre-commit nao esta no PATH; bootstrap opcional ignorado." >&2
    return 0
  fi

  echo "[install-hooks] Validando .pre-commit-config.yaml"
  if ! pre-commit validate-config; then
    echo "[install-hooks] ERRO: pre-commit validate-config falhou." >&2
    return 1
  fi

  echo "[install-hooks] Instalando ambientes do pre-commit"
  if ! pre-commit install-hooks; then
    echo "[install-hooks] ERRO: pre-commit install-hooks falhou." >&2
    return 1
  fi

  echo "[install-hooks] Bootstrap opcional do pre-commit concluido."
}

if [[ "$authorship_only" -eq 0 ]]; then
  bootstrap_pre_commit || install_failures+=("pre-commit-bootstrap")
fi

if [[ ${#missing_hooks[@]} -gt 0 ]]; then
  echo "[install-hooks] ERRO: hooks obrigatorios ausentes: ${missing_hooks[*]}" >&2
fi

if [[ ${#install_failures[@]} -gt 0 ]]; then
  echo "[install-hooks] ERRO: falha na instalacao dos hooks: ${install_failures[*]}" >&2
fi

if [[ ${#missing_hooks[@]} -gt 0 || ${#install_failures[@]} -gt 0 ]]; then
  exit 1
fi

echo "[install-hooks] Hooks instalados em: $HOOK_DST_DIR"

echo "[install-hooks] Concluido. Valide com probes sem criar commits no repositorio."
