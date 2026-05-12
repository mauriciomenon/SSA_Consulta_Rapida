# SSA Environment Scripts

Scripts de bootstrap de ambiente Python com suporte multiplataforma (Windows, macOS, Linux).

## Estrutura

- **direnv_common.sh** - Bootstrap para Unix (Linux/macOS) via direnv ou source manual
- **direnv_common.ps1** - Bootstrap para Windows PowerShell via direnv
- **setup_env.sh** - Script auxiliar para setup inicial (Unix)
- **setup_env.ps1** - Script auxiliar para setup inicial (Windows)

## Como Funciona

### 1. Detecção de Versão Python
- Lê `.python-version` na raiz do repo (atualmente: **3.13.9**)
- Fallback para `SSA_PYTHON_STABLE_VERSION` (default: 3.13.7)
- Variante free-threaded usa `SSA_PYTHON_FT_VERSION` (default: 3.14-dev)

### 2. Estratégia de Ambiente (em ordem de precedência)
1. **pyenv + virtualenv** (preferido): Cria `ssa_consulta_stable_3_13_9`
2. **pyenv local** (se virtualenv indisponível): Usa `.python-version` via `pyenv local`
3. **venv local** (fallback): Cria `.venv` com Python do sistema

### 3. Variantes de Python
- **stable** (default): Versão estável de produção (3.13.9)
- **free-threaded**: Versão experimental nogil (3.14-dev)

Selecione via:
```bash
export SSA_PYTHON_VARIANT=free-threaded  # ou stable
# ou
export SSA_USE_FREE_THREADED=1
```

## Uso

### Com Direnv (recomendado)
```bash
cd /path/to/SSA_Consulta_Rapida
direnv allow
```

O `.envrc` na raiz automaticamente carrega `scripts/env/direnv_common.{sh,ps1}`.

### Sem Direnv

**Unix/macOS:**
```bash
source scripts/env/direnv_common.sh
ssa_env::apply manual
```

**Windows PowerShell:**
```powershell
. scripts\env\direnv_common.ps1
ssa_env_apply manual
```

## Variáveis de Ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `SSA_PYTHON_STABLE_VERSION` | Versão Python estável | Lê de `.python-version` ou 3.13.7 |
| `SSA_PYTHON_FT_VERSION` | Versão free-threaded | 3.14-dev |
| `SSA_PYTHON_VARIANT` | Variante a usar | stable |
| `SSA_USE_FREE_THREADED` | Atalho para free-threaded | 0 |
| `SSA_VENV_DIR_OVERRIDE` | Override do diretório venv | .venv |
| `SSA_SKIP_PYENV` | Pula pyenv, força venv local | 0 |
| `SSA_ENV_FALLBACK_PYTHON` | Python fallback se pyenv falhar | python3 |

## Troubleshooting

### pyenv shell está setando versão errada
Execute na sessão:
```powershell
Remove-Item Env:PYENV_VERSION -ErrorAction SilentlyContinue
pyenv shell --unset
```

### Forçar recriação do ambiente
```bash
# Remover ambiente pyenv
pyenv uninstall ssa_consulta_stable_3_13_9

# Remover venv local
rm -rf .venv

# Recarregar direnv
direnv reload
```

### Verificar configuração atual
```bash
echo $SSA_ENV_VARIANT          # stable ou free-threaded
echo $SSA_ENV_PY_VERSION       # 3.13.9 ou 3.14-dev
echo $SSA_ENV_SOURCE           # pyenv-virtualenv, pyenv-local, ou venv
python --version               # Versão ativa
```

## Integração com Requirements

Os scripts garantem que o Python está ativo antes de instalar dependências.

**Instalar dependências de desenvolvimento:**
```bash
uv sync --extra dev
```

Compatibilidade sem uv:
```bash
pip install -r requirements_dev.txt
```

**Instalar para plataforma específica:**
```bash
# Windows
pip install -r launchers/platforms/windows_amd64/requirements.txt

# macOS ARM64
pip install -r launchers/platforms/macos_arm64/requirements.txt

# Debian AMD64
pip install -r launchers/platforms/debian_amd64/requirements.txt
```

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

