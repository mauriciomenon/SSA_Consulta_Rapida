#!/usr/bin/env bash
# SECRET SCAN HOOK MARKER
set -euo pipefail

TOKEN_REGEXES=(
  'sk-[A-Za-z0-9]{24,}'
  'hf_[A-Za-z0-9]{24,}'
)

ALLOW_VALUES=(
  ""
  "REDACTED"
  "CHANGE_ME"
  "TODO"
  "<PLACEHOLDER>"
  "PLACEHOLDER"
)

MIN_LEN=12

err(){ echo "[secret-scan][BLOCK] $1" >&2; }
info(){ [[ ${GIT_HOOKS_VERBOSE:-0} -eq 1 ]] && echo "[secret-scan] $1" >&2; }

DIFF=$(git diff --cached --unified=0 --no-color --text || true)
[[ -z $DIFF ]] && exit 0

ADDED=$(echo "$DIFF" | grep -E '^\+' | grep -vE '^\+\+\+' | grep -vE '^\+Binary files ' || true)
[[ -z $ADDED ]] && exit 0
ADDED_STRIPPED=$(echo "$ADDED" | sed 's/^+//')

FOUND=0

# 1) Tokens diretos
for rgx in "${TOKEN_REGEXES[@]}"; do
  if echo "$ADDED_STRIPPED" | grep -E -q "$rgx"; then
    err "Token suspeito: $rgx"
    FOUND=1
  else
    info "OK token: $rgx"
  fi
done

# 2) Linhas com API_KEY=
echo "$ADDED_STRIPPED" | grep -E '\b[A-Z0-9_]*API_KEY[[:space:]]*=' | while IFS= read -r line; do
  [[ -z "${line// }" ]] && continue
  raw_key="${line%%=*}"
  key=$(echo "$raw_key" | tr -d '"' | tr -d "'" | tr -d '[:space:]')
  if [[ ! "$key" =~ ^[A-Z0-9_]+$ ]]; then
    info "Ignorando linha sem chave válida: $line"
    continue
  fi
  val_part="${line#*=}"
  val_part="$(echo "$val_part" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
  val_clean="$(echo "$val_part" | sed -E "s/^['\"]//; s/['\"]$//")"
  val_clean="${val_clean//$'\r'/}"

  # Allow vazio / placeholders
  for av in "${ALLOW_VALUES[@]}"; do
    if [[ "$val_clean" == "$av" ]]; then
      info "PLACEHOLDER permitido: $line"
      continue 2
    fi
  done

  # Se vazio após trim
  [[ -z "$val_clean" ]] && { info "Vazio permitido: $line"; continue; }

  # Curto demais => permitir
  (( ${#val_clean} < MIN_LEN )) && { info "Curto permitido: $line"; continue; }

  err "Valor potencial de API_KEY (redacted)"
  FOUND=1
done

if [[ $FOUND -eq 1 ]]; then
  cat <<'EOT' >&2
================ BLOQUEADO ================
Possível segredo real.
Use placeholders (REDACTED / CHANGE_ME) ou .envrc.
Override (risco):
  GIT_ALLOW_INSECURE_COMMIT=1 git commit ...
===========================================
EOT
  [[ ${GIT_ALLOW_INSECURE_COMMIT:-0} -eq 1 ]] || exit 1
  echo "[secret-scan] Override inseguro aceito." >&2
fi

exit 0
