#!/usr/bin/env bash
set -euo pipefail

readonly TOKEN_CHARS='[A-Za-z0-9]'
readonly API_KEY_VALUE_MIN="${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}"
readonly PROVIDER_TOKEN_MIN="${API_KEY_VALUE_MIN}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}${TOKEN_CHARS}"
readonly TOKEN_START='(^|[^A-Za-z0-9])'
readonly TOKEN_END='([^A-Za-z0-9]|$)'
readonly DEFAULT_SENSITIVE_PATTERN="${TOKEN_START}(sk-${PROVIDER_TOKEN_MIN}${TOKEN_CHARS}*|hf_${PROVIDER_TOKEN_MIN}${TOKEN_CHARS}*|[A-Z_]+API_KEY=${API_KEY_VALUE_MIN}${TOKEN_CHARS}*)${TOKEN_END}"
readonly SENSITIVE_PATTERN="${SENSITIVE_PATTERN:-$DEFAULT_SENSITIVE_PATTERN}"
readonly HISTORY_MAX_COUNT="${SECRET_SCAN_HISTORY_MAX_COUNT:-200}"
readonly EXCLUDED_DIRS=(
  .git
  dist
  build
  logs
  __pycache__
  .pytest_cache
  .mypy_cache
  node_modules
)
readonly EXCLUDED_FILES=(
  '*.pyc'
  '*.so'
)

usage() {
  cat >&2 <<'EOF'
Usage: scan_secrets.sh <workspace|pr-diff|history> [base-ref]

Modes:
  workspace        Scan the checked-out workspace, excluding generated caches.
  pr-diff BASE_REF Scan added lines in the PR diff against BASE_REF.
  history          Advisory scan of recent Git history; never blocks.
EOF
}

validate_pattern() {
  local status
  set +e
  grep -E "$SENSITIVE_PATTERN" </dev/null >/dev/null
  status=$?
  set -e
  if (( status > 1 )); then
    echo '[ERROR] Invalid sensitive pattern' >&2
    return "$status"
  fi
  return 0
}

append_grep_excludes() {
  local item
  for item in "${EXCLUDED_DIRS[@]}"; do
    grep_args+=(--exclude-dir="$item")
  done
  for item in "${EXCLUDED_FILES[@]}"; do
    grep_args+=(--exclude="$item")
  done
}

append_git_pathspec_excludes() {
  local item
  for item in "${EXCLUDED_DIRS[@]}"; do
    pathspec_args+=(":(exclude)$item/**")
  done
  for item in "${EXCLUDED_FILES[@]}"; do
    pathspec_args+=(":(exclude)$item")
  done
}

scan_workspace() {
  echo '[INFO] Scanning workspace for sensitive patterns'
  validate_pattern

  local grep_args=(--binary-files=without-match)
  append_grep_excludes

  local pathspec_args=(-- .)
  append_git_pathspec_excludes

  local status
  set +e
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git grep --untracked -I -E -l "$SENSITIVE_PATTERN" "${pathspec_args[@]}"
  else
    grep -R -E -l "${grep_args[@]}" "$SENSITIVE_PATTERN" .
  fi
  status=$?
  set -e

  if (( status == 0 )); then
    echo '[ERROR] Sensitive patterns found'
    return 1
  fi
  if (( status > 1 )); then
    echo '[ERROR] Workspace scan failed' >&2
    return "$status"
  fi

  echo '[OK] No sensitive patterns detected'
}

scan_pr_diff() {
  local base_ref="${1:-}"
  if [[ -z "$base_ref" ]]; then
    echo '[ERROR] pr-diff mode requires a base ref' >&2
    return 2
  fi

  validate_pattern

  echo '[INFO] Scanning PR diff'
  git fetch --no-tags origin "$base_ref"

  local pathspec_args=(-- .)
  append_git_pathspec_excludes

  local added_lines
  added_lines="$(mktemp)"
  if ! git diff --unified=0 FETCH_HEAD...HEAD "${pathspec_args[@]}" \
    | awk '/^\+\+\+ (b\/|\/dev\/null)/ { next } /^\+/ { sub(/^\+/, ""); print }' \
    >"$added_lines"; then
    echo '[ERROR] PR diff scan failed' >&2
    rm -f "$added_lines"
    return 1
  fi

  if grep -E -q "$SENSITIVE_PATTERN" "$added_lines"; then
    echo '[ERROR] Possible secret in diff'
    echo '[INFO] Changed files in scanned diff:'
    git diff --name-only FETCH_HEAD...HEAD "${pathspec_args[@]}" | sed 's/^/[INFO] /'
    rm -f "$added_lines"
    return 1
  fi

  rm -f "$added_lines"
  echo '[OK] No sensitive patterns in diff'
}

scan_history() {
  echo '[INFO] Sampling recent commits'
  validate_pattern

  if git log --max-count="$HISTORY_MAX_COUNT" -E -G "$SENSITIVE_PATTERN" --format='%H' HEAD | grep -q .; then
    echo '[INFO] Historical pattern found in recent commits'
    echo '[INFO] Advisory only: current tree and PR diff scans are blocking'
    return 0
  fi

  echo '[OK] Recent history sample clean'
}

main() {
  local mode="${1:-}"
  case "$mode" in
    workspace)
      scan_workspace
      ;;
    pr-diff)
      scan_pr_diff "${2:-}"
      ;;
    history)
      scan_history
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage
      return 2
      ;;
  esac
}

main "$@"
