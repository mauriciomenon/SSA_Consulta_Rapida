#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_NAME=$(cat .python-version 2>/dev/null || true)
if [[ -z "${VENV_NAME:-}" ]]; then
  echo "[info] .python-version nao encontrado; usarei nome padrao ssa_consulta_rapida_py313"
  VENV_NAME="ssa_consulta_rapida_py313"
fi

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
  if [[ "${OSTYPE:-}" == darwin* ]]; then echo mac; return; fi
  if [[ -f /etc/debian_version ]]; then echo debian; return; fi
  uname_s=$(uname -s 2>/dev/null || echo unknown)
  case "$uname_s" in
    Linux) echo linux;;
    Darwin) echo mac;;
    *) echo linux;;
  esac
}

OS=$(detect_os)
echo "[info] OS detectado: $OS"

ensure_build_deps() {
  case "$OS" in
    debian)
      if have_cmd apt; then
        echo "[info] Instalando dependencias de build para pyenv (sudo pode ser solicitado)"
        sudo apt update -y
        sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
          libsqlite3-dev curl llvm tk-dev libncursesw5-dev xz-utils libffi-dev liblzma-dev ca-certificates
      fi
      ;;
    mac)
      if have_cmd brew; then
        echo "[info] Instalando ferramentas via Homebrew (pyenv, pyenv-virtualenv, direnv)"
        brew install pyenv pyenv-virtualenv direnv || true
      else
        echo "[aviso] Homebrew nao encontrado. Instale Homebrew ou pyenv manualmente: https://github.com/pyenv/pyenv"
      fi
      ;;
    *) ;;
  esac
}

ensure_pyenv() {
  if have_cmd pyenv; then
    echo "[ok] pyenv encontrado"
    return
  fi
  echo "[info] Instalando pyenv (metodo oficial)"
  # Instala o pyenv + plugins (pyenv-virtualenv) via instalador oficial
  curl -fsSL https://pyenv.run | bash
  export PATH="$HOME/.pyenv/bin:$PATH"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
}

ensure_direnv() {
  if have_cmd direnv; then
    echo "[ok] direnv encontrado"
  else
    case "$OS" in
      debian)
        if have_cmd apt; then
          echo "[info] Instalando direnv via apt (sudo pode ser solicitado)"
          sudo apt install -y direnv || true
        fi
        ;;
      mac)
        # já tentamos brew acima
        :
        ;;
      *) : ;;
    esac
  fi
}

init_pyenv_shell() {
  if have_cmd pyenv; then
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
  fi
}

create_virtualenv_if_missing() {
  if ! have_cmd pyenv; then
    echo "[aviso] pyenv nao disponivel; criando fallback .venv com python do sistema"
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -U pip
    python -m pip install -r requirements.txt
    echo "[ok] Ambiente .venv criado (fallback)."
    return
  fi

  if pyenv virtualenvs --bare | grep -qx "$VENV_NAME"; then
    echo "[ok] Virtualenv pyenv '$VENV_NAME' ja existe"
  else
    echo "[info] Criando virtualenv pyenv '$VENV_NAME'"
    # Descobre a ultima 3.13.x disponivel
    PY_VER=$(pyenv install -l | sed -n 's/^  \(3\.13\.[0-9]\+\)$/\1/p' | tail -1)
    if [[ -z "${PY_VER:-}" ]]; then
      echo "[erro] Nao foi possivel descobrir versao 3.13.x no pyenv. Verifique a instalacao do pyenv."
      exit 1
    fi
    pyenv install -s "$PY_VER"
    pyenv virtualenv "$PY_VER" "$VENV_NAME"
  fi

  # Ativa sem mexer em .python-version
  pyenv activate "$VENV_NAME"
  python -m pip install -U pip
  python -m pip install -r requirements.txt
}

configure_direnv_hint() {
  if have_cmd direnv; then
    echo "[dica] Rode 'direnv allow' na raiz do projeto para ativacao automatica."
  fi
}

echo "[1/4] Checando dependências de build"
ensure_build_deps
echo "[2/4] Checando/instalando pyenv"
ensure_pyenv || true
echo "[3/4] Inicializando shell do pyenv"
init_pyenv_shell
echo "[4/4] Checando direnv"
ensure_direnv || true

create_virtualenv_if_missing
configure_direnv_hint

echo "[ok] Ambiente pronto."

