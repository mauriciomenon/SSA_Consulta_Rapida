#!/usr/bin/env bash
# Setup inicial do ambiente Python para SSA_Consulta_Rapida (Unix/macOS)
# Garante que pyenv está instalado e configura o ambiente

set -euo pipefail

VARIANT="${SSA_PYTHON_VARIANT:-stable}"
SKIP_PYENV="${SSA_SKIP_PYENV:-0}"
FORCE="${FORCE:-0}"

env_log() {
    printf '\033[36m[setup]\033[0m %s\n' "$*"
}

test_pyenv_installed() {
    command -v pyenv >/dev/null 2>&1
}

install_pyenv() {
    env_log "pyenv não encontrado. Instalando..."
    
    if [[ -d "$HOME/.pyenv" ]]; then
        if [[ "$FORCE" == "1" ]]; then
            env_log "Removendo instalação existente..."
            rm -rf "$HOME/.pyenv"
        else
            env_log "pyenv já existe em $HOME/.pyenv mas não está no PATH"
            env_log "Execute com FORCE=1 para reinstalar ou adicione ao PATH manualmente"
            return 1
        fi
    fi
    
    # Instalar via pyenv-installer
    if command -v curl >/dev/null 2>&1; then
        curl https://pyenv.run | bash
    elif command -v wget >/dev/null 2>&1; then
        wget -O- https://pyenv.run | bash
    else
        env_log "curl ou wget necessário para instalar pyenv"
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
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_version_file="$repo_root/.python-version"

if [[ -f "$python_version_file" ]]; then
    python_version=$(cat "$python_version_file" | tr -d '\r' | tr -d '\n')
    env_log "Versão Python no .python-version: $python_version"
else
    python_version="3.13.9"
    env_log "Criando .python-version com $python_version"
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
