#!/usr/bin/env bash
# Setup inicial do ambiente Python para SSA_Consulta_Rapida (Unix/macOS)
# Garante que pyenv está instalado e configura o ambiente

set -euo pipefail

VARIANT="${SSA_PYTHON_VARIANT:-stable}"
SKIP_PYENV="${SSA_SKIP_PYENV:-0}"
FORCE="${FORCE:-0}"
ALLOW_REMOTE_PYENV_INSTALL="${SSA_ALLOW_REMOTE_PYENV_INSTALL:-0}"
PYENV_INSTALLER_SHA256="${SSA_PYENV_INSTALLER_SHA256:-}"
CONFIRM_REMOVE_PYENV="${SSA_CONFIRM_REMOVE_PYENV:-0}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
# shellcheck disable=SC1091
source "${repo_root}/scripts/env/native_host_guard.sh"
ssa_native_guard_repo "$repo_root" || exit 1
ssa_native_guard_tools uv || exit 1
ssa_native_guard_venv "$repo_root/.venv" || exit 1
ssa_native_guard_venv "$repo_root/.venv_ft" || exit 1

env_log() {
    printf '\033[36m[setup]\033[0m %s\n' "$*"
}

test_pyenv_installed() {
    command -v pyenv >/dev/null 2>&1
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

install_pyenv_from_verified_installer() {
    local installer_path actual_hash expected_hash

    if [[ "$ALLOW_REMOTE_PYENV_INSTALL" != "1" ]]; then
        env_log "Remote pyenv install disabled."
        env_log "Install pyenv manually or set SSA_ALLOW_REMOTE_PYENV_INSTALL=1 with SSA_PYENV_INSTALLER_SHA256."
        return 1
    fi
    if [[ -z "$PYENV_INSTALLER_SHA256" ]]; then
        env_log "SSA_PYENV_INSTALLER_SHA256 is required for remote pyenv install."
        env_log "Manual install: download https://pyenv.run, verify it, then run with bash."
        return 1
    fi

    if ! installer_path="$(mktemp "${TMPDIR:-/tmp}/pyenv-installer.XXXXXX")"; then
        env_log "Failed to create temporary file for pyenv installer."
        return 1
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://pyenv.run -o "$installer_path"
    elif command -v wget >/dev/null 2>&1; then
        wget -q https://pyenv.run -O "$installer_path"
    else
        env_log "curl or wget is required to download pyenv installer."
        rm -f "$installer_path"
        return 1
    fi

    actual_hash="$(sha256_file "$installer_path" | tr '[:upper:]' '[:lower:]')"
    expected_hash="$(printf '%s' "$PYENV_INSTALLER_SHA256" | tr '[:upper:]' '[:lower:]')"
    if [[ "$actual_hash" != "$expected_hash" ]]; then
        env_log "pyenv installer SHA256 mismatch. expected=$expected_hash actual=$actual_hash"
        rm -f "$installer_path"
        return 1
    fi
    if ! bash "$installer_path"; then
        rm -f "$installer_path"
        return 1
    fi
    rm -f "$installer_path"
}

install_pyenv() {
    env_log "pyenv not found. Preparing install..."
    
    if [[ -d "$HOME/.pyenv" ]]; then
        if [[ "$FORCE" == "1" ]]; then
            if [[ "$CONFIRM_REMOVE_PYENV" != "1" ]]; then
                env_log "FORCE=1 requires SSA_CONFIRM_REMOVE_PYENV=1 before removing $HOME/.pyenv"
                return 1
            fi
            env_log "Removing existing pyenv directory..."
            rm -rf "$HOME/.pyenv"
        else
            env_log "pyenv já existe em $HOME/.pyenv mas não está no PATH"
            env_log "Execute com FORCE=1 para reinstalar ou adicione ao PATH manualmente"
            return 1
        fi
    fi
    
    if ! install_pyenv_from_verified_installer; then
        env_log "pyenv install was not completed."
        return 1
    fi
    
    # Adicionar ao PATH da sessão atual
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    
    env_log "pyenv instalado! Adicione ao seu ~/.bashrc ou ~/.zshrc:"
    env_log '  export PYENV_ROOT="$HOME/.pyenv"'
    env_log '  export PATH="$PYENV_ROOT/bin:$PATH"'
    env_log '  eval "$(pyenv init -)"'
    return 0
}

# Main
env_log "Verificando ambiente Python..."

if [[ "$SKIP_PYENV" != "1" ]]; then
    if ! test_pyenv_installed; then
        if ! install_pyenv; then
            env_log "Falha ao instalar pyenv. Continue manualmente ou use SSA_SKIP_PYENV=1"
            exit 1
        fi
    else
        env_log "pyenv encontrado: $(pyenv --version)"
    fi
fi

# Determinar versão
python_version_file="$repo_root/.python-version"

if [[ -f "$python_version_file" ]]; then
    IFS= read -r python_version < "$python_version_file"
    python_version="${python_version%$'\r'}"
    env_log "Versão Python no .python-version: $python_version"
else
    python_version="${SSA_PYTHON_STABLE_VERSION:-3.13.12}"
    env_log ".python-version ausente; criando com $python_version"
    env_log "Override: set SSA_PYTHON_STABLE_VERSION before running this setup."
    echo "$python_version" > "$python_version_file"
fi

if [[ "$VARIANT" == "free-threaded" ]]; then
    python_version="${SSA_PYTHON_FT_VERSION:-3.14-dev}"
    env_log "Variante free-threaded: usando $python_version"
fi

# Instalar Python via pyenv se necessário
if [[ "$SKIP_PYENV" != "1" ]] && test_pyenv_installed; then
    if ! pyenv versions --bare 2>/dev/null | grep -Fx "$python_version" >/dev/null; then
        env_log "Instalando Python $python_version via pyenv..."
        if ! pyenv install "$python_version"; then
            env_log "Erro ao instalar Python $python_version"
            exit 1
        fi
    else
        env_log "Python $python_version já instalado"
    fi
    
    # Configurar versão local
    cd "$repo_root"
    pyenv local "$python_version"
    env_log "Configurado pyenv local para $python_version"
fi

# Verificar Python ativo
if command -v python >/dev/null 2>&1; then
    active_python=$(python --version 2>&1)
    env_log "Python ativo: $active_python"
elif command -v python3 >/dev/null 2>&1; then
    active_python=$(python3 --version 2>&1)
    env_log "Python ativo: $active_python"
else
    env_log "Nenhum Python encontrado! Instale manualmente ou use pyenv."
    exit 1
fi

# Instalar dependências
env_log ""
read -p "Instalar dependências agora? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    req_file="$repo_root/requirements_dev.txt"
    if [[ -f "$req_file" ]]; then
        env_log "Instalando dependências de desenvolvimento..."
        pip install -r "$req_file"
    else
        env_log "requirements_dev.txt não encontrado"
    fi
fi

env_log ""
env_log "Setup concluído!"
env_log "Para ativar o ambiente:"
env_log "  - Com direnv: direnv allow"
env_log "  - Manual: source scripts/env/direnv_common.sh && ssa_env::apply manual"
