#!/usr/bin/env bash
# shell_doctor.sh - Diagnóstico e recomendações para ambiente zsh + direnv
# Objetivo: Detectar problemas de completions (compinit), diretórios fpath faltando,
# múltiplas invocações de compinit, secretes em histórico / repo, variáveis expostas,
# zcompdump corrompido e oferecer ações sugeridas.
# Saída: Humana (default) ou JSON (--json). Exit codes: 0=OK,1=Achados,2=Erro script.

set -o pipefail
SCRIPT_NAME="shell_doctor.sh"
VERSION="0.1.0"
ISSUES=()
ACTIONS=()
WARNINGS=()
INFO_MSGS=()
JSON_MODE=0
CHECK_HISTORY=0
CHECK_SECRETS=0
MODE_QUICK=0
MODE_FULL=0
SELF_TEST=0
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ZDOTDIR_REAL="${ZDOTDIR:-$HOME}"
ZSHRC_FILE="$ZDOTDIR_REAL/.zshrc"
ZCOMPDUMP_FILE="$ZDOTDIR_REAL/.zcompdump"

# Padrões de segredos simples (não exaustivo)
SECRET_REGEXPS=(
  'sk-[A-Za-z0-9]{8,}'
  'hf_[A-Za-z0-9]{8,}'
  'api[_-]?key'
  'API_KEY'
  'ANTHROPIC_API_KEY'
  'GEMINI_API_KEY'
  'OPENROUTER_API_KEY'
  'GROQ_API_KEY'
  'MISTRAL_API_KEY'
  'COHERE_API_KEY'
  'DEEPSEEK_API_KEY'
  'TOGETHER_API_KEY'
  'FIRECRAWL_API_KEY'
)

COLOR_RESET='\033[0m'
COLOR_RED='\033[31m'
COLOR_YELLOW='\033[33m'
COLOR_GREEN='\033[32m'
COLOR_CYAN='\033[36m'

log_info(){ INFO_MSGS+=("$1"); [[ $JSON_MODE -eq 0 ]] && echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $1"; }
log_warn(){ WARNINGS+=("$1"); [[ $JSON_MODE -eq 0 ]] && echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"; }
log_issue(){ ISSUES+=("$1"); [[ $JSON_MODE -eq 0 ]] && echo -e "${COLOR_RED}[ISSUE]${COLOR_RESET} $1"; }
log_action(){ ACTIONS+=("$1"); [[ $JSON_MODE -eq 0 ]] && echo -e "${COLOR_GREEN}[ACTION]${COLOR_RESET} $1"; }

abort(){ echo "Script error: $1" >&2; exit 2; }

usage(){ cat <<EOF
$SCRIPT_NAME v$VERSION
Uso: $SCRIPT_NAME [opções]
  --quick          Executa subconjunto rápido (compinit, fpath, zcompdump)
  --full           Executa todos os testes (inclui --secrets e --all-history sugerido)
  --secrets        Procura segredos em repo (grep) e variáveis no ambiente atual
  --all-history    Analisa historico Git completo do repo
  --json           Saída em JSON
  --self-test      Roda testes internos de sanidade do script
  -h|--help        Esta ajuda

Exit codes: 0=nenhum problema importante, 1=achados relevantes, 2=erro interno
EOF
}

parse_args(){
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quick) MODE_QUICK=1 ; shift ;;
      --full) MODE_FULL=1 ; CHECK_SECRETS=1 ; CHECK_HISTORY=1 ; shift ;;
      --secrets) CHECK_SECRETS=1 ; shift ;;
      --all-history) CHECK_HISTORY=1 ; shift ;;
      --json) JSON_MODE=1 ; shift ;;
      --self-test) SELF_TEST=1 ; shift ;;
      -h|--help) usage; exit 0 ;;
      *) abort "Opção desconhecida: $1" ;;
    esac
  done
  if [[ $JSON_MODE -eq 1 ]] && ! command -v jq >/dev/null 2>&1; then
    abort "jq required for --json"
  fi
  if [[ $MODE_QUICK -eq 0 && $MODE_FULL -eq 0 && $CHECK_SECRETS -eq 0 && $CHECK_HISTORY -eq 0 && $SELF_TEST -eq 0 ]]; then
    MODE_QUICK=1
  fi
}

self_test(){
  log_info "Rodando self-test interno";
  # Teste rápido das funções de log
  log_issue "ISSUE_TEST"
  log_warn "WARN_TEST"
  log_action "ACTION_TEST"
  log_info "INFO_TEST"
  # Testar regex compilação com grep -E -q se possível
  for r in "${SECRET_REGEXPS[@]}"; do
    echo "fake sk-ABCD1234 token" | grep -E -q "$r" && { log_info "Regex '$r' operante"; break; }
  done
  log_action "Self-test concluído"
}

check_compinit_mul(){
  local count
  count=$(grep -Ec '^[^#]*compinit' "$ZSHRC_FILE" 2>/dev/null || true)
  if [[ -z $count ]]; then
    log_warn "Não foi possível determinar compinit no $ZSHRC_FILE"
    return
  fi
  if [[ $count -gt 1 ]]; then
    log_issue "Foram encontradas $count invocações de compinit (ideal = 1)"
    log_action "Remover duplicadas e manter bloco único com cache seguro";
  else
    log_info "Número de compinit OK ($count)"
  fi
}

check_fpath(){
  local missing=()
  # Capturar fpath atual dentro de subshell zsh se possível
  if command -v zsh >/dev/null 2>&1; then
    local zsh_out
    zsh_out=$(zsh -lc 'print -l $fpath' 2>/dev/null || true)
    while IFS= read -r line; do
      [[ -z $line ]] && continue
      if [[ ! -d $line ]]; then
        missing+=("$line")
      fi
    done <<<"$zsh_out"
  else
    log_warn "zsh não disponível no PATH para inspecionar fpath"
    return
  fi
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_issue "Diretórios fpath inexistentes: ${missing[*]}"
    log_action "Remover caminhos inválidos do fpath (editar .zshrc / plugins)"
  else
    log_info "Todos diretórios de fpath existem"
  fi
}

check_zcompdump(){
  if [[ -f $ZCOMPDUMP_FILE ]]; then
    if file "$ZCOMPDUMP_FILE" 2>/dev/null | grep -qi 'text'; then
      local age stat_mtime
      stat_mtime=$(stat -f %m "$ZCOMPDUMP_FILE" 2>/dev/null || stat -c %Y "$ZCOMPDUMP_FILE" 2>/dev/null || true)
      case "$stat_mtime" in
        ''|*[!0-9]*)
          log_warn "Nao foi possivel determinar idade do .zcompdump"
          return
          ;;
      esac
      age=$(( ( $(date +%s) - stat_mtime ) / 86400 ))
      if [[ $age -gt 30 ]]; then
        log_warn "Arquivo .zcompdump tem ${age}d; regenerar pode melhorar desempenho"
        log_action "Remover $ZCOMPDUMP_FILE e abrir nova sessão para recriar"
      else
        log_info ".zcompdump idade aceitável (${age}d)"
      fi
    else
      log_issue ".zcompdump não parece texto; possivelmente corrompido"
      log_action "Remover e regenerar com novo compinit"
    fi
  else
    log_warn "Sem .zcompdump (será criado no próximo compinit)"
  fi
}

check_repo_secrets(){
  [[ $CHECK_SECRETS -eq 1 ]] || return
  log_info "Procurando padrões de segredo no repo (grep)"
  local joined
  joined=$(printf '%s|' "${SECRET_REGEXPS[@]}")
  joined=${joined%|}
  local matches
  # Diretórios excluídos adicionais para reduzir ruído / binários grandes:
  #  - launchers (contém builds e bundles PyQt)
  #  - dist / build artefacts
  #  - logs (possível ruído, pode conter dados sensíveis; mantenha se quiser inspecionar)
  matches=$(grep -REl \
    --exclude-dir='.*cache' \
    --exclude-dir='.git' \
    --exclude-dir='launchers' \
    --exclude-dir='dist' \
    --exclude-dir='build' \
    --exclude-dir='logs' \
    -E "$joined" "$REPO_ROOT" 2>/dev/null || true)
  if [[ -n $matches ]]; then
    log_issue "Possíveis segredos encontrados em arquivos versionados (dirs principais filtrados)"
    log_action "Avaliar cada ocorrência; revogar / rotacionar chaves se reais"
    [[ $JSON_MODE -eq 0 ]] && printf '%s\n' "$matches"
  else
    log_info "Nenhum padrão de segredo encontrado em texto claro nos arquivos escaneados (com exclusões)"
  fi
}

check_commit_history(){
  [[ $CHECK_HISTORY -eq 1 ]] || return
  if ! command -v git >/dev/null; then
    log_warn "git não disponível; pulando análise de histórico"
    return
  fi
  log_info "Escaneando commits anteriores por padrões de segredos (pode demorar)"
  local joined shas
  joined=$(printf '%s|' "${SECRET_REGEXPS[@]}")
  joined=${joined%|}
  shas=$(git log --all --format='%H' -E -G "$joined" 2>/dev/null | sort -u || true)
  if [[ -n $shas ]]; then
    log_issue "Padrao sensivel presente em commits: $(echo "$shas" | tr '\n' ' ')"
    log_action "Considerar git filter-repo para remover segredos antigos (apos ROTACIONAR)"
  fi
}

check_env_vars(){
  [[ $CHECK_SECRETS -eq 1 ]] || return
  log_info "Verificando variáveis de ambiente exportadas com nomes sensíveis"
  local suspect=()
  while IFS='=' read -r name _value; do
    case "$name" in
      *KEY*|*TOKEN*|*SECRET*|*API*) ;;
      *) continue ;;
    esac
    suspect+=("${name}")
  done < <(env)
  if [[ ${#suspect[@]} -gt 0 ]]; then
    log_warn "Variáveis sensíveis ativas: ${suspect[*]} (verifique origem)"
  else
    log_info "Sem variáveis sensíveis aparentes (names)";
  fi
}

summarize(){
  local issue_count=${#ISSUES[@]}
  if [[ $JSON_MODE -eq 1 ]]; then
    jq -n \
      --arg version "$VERSION" \
      --arg script "$SCRIPT_NAME" \
      --argjson issues "$(printf '%s\n' "${ISSUES[@]}" | jq -R . | jq -s .)" \
      --argjson warnings "$(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .)" \
      --argjson actions "$(printf '%s\n' "${ACTIONS[@]}" | jq -R . | jq -s .)" \
      --argjson info "$(printf '%s\n' "${INFO_MSGS[@]}" | jq -R . | jq -s .)" \
      '{script:$script,version:$version,info:$info,warnings:$warnings,issues:$issues,actions:$actions}'
  else
    echo
    echo "================ RESUMO ================"
    echo "Script: $SCRIPT_NAME v$VERSION"
    echo "Issues: $issue_count | Warnings: ${#WARNINGS[@]}"
    if [[ $issue_count -gt 0 ]]; then
      echo "-- Issues --"; printf ' * %s\n' "${ISSUES[@]}"
      echo "-- Ações Sugeridas --"; printf ' + %s\n' "${ACTIONS[@]}"
    fi
  fi
  [[ $issue_count -gt 0 || ${#WARNINGS[@]} -gt 0 ]] && return 1 || return 0
}

main(){
  parse_args "$@"
  [[ $SELF_TEST -eq 1 ]] && { self_test; summarize; exit $?; }
  log_info "Repo root: $REPO_ROOT"
  log_info "ZDOTDIR efetivo: $ZDOTDIR_REAL"
  log_info ".zshrc alvo: $ZSHRC_FILE"

  check_compinit_mul
  check_fpath
  check_zcompdump
  if [[ $MODE_FULL -eq 1 ]]; then
    check_repo_secrets
    check_commit_history
    check_env_vars
  else
    [[ $CHECK_SECRETS -eq 1 ]] && { check_repo_secrets; check_env_vars; }
    [[ $CHECK_HISTORY -eq 1 ]] && check_commit_history
  fi
  summarize
}

main "$@"
