# Ambiente Python Compartilhado (dev_env)

Este diretorio descreve o fluxo por host nativo. Windows 11 usa PowerShell; Linux e macOS usam bash/zsh em clones e venvs proprios, sem abandonar o fallback em `.venv` quando o pyenv nao estiver instalado. Nao compartilhar checkout ou venv entre Windows e WSL/Linux; WSL fica restrito ao CodeRabbit em clone Linux proprio.

## Visao geral
- `.envrc` inicializa tudo: tenta pyenv + pyenv-virtualenv, garante a versao estavel (`3.13.12`, lida de `.python-version` se existir) e ativa o virtualenv `ssa_consulta_stable_<versao>`.
- A variante "free-threaded" usa `SSA_PYTHON_VARIANT=free-threaded` (ou `SSA_USE_FREE_THREADED=1`) e provisiona `3.14-dev` por padrao (`SSA_PYTHON_FT_VERSION` pode ajustar).
- Sem pyenv, o fluxo cria `.venv` (ou `.venv_ft` para a variante livre do GIL) com `python -m venv` e ativa automaticamente.
- O PATH recebe `scripts/` e `scripts_manutencao/`, alem de exportar `PYTHONUTF8=1` e `PYTHONDONTWRITEBYTECODE=1`.

## Como ativar
### Linux/macOS (bash/zsh)
1. Instale `direnv` e `pyenv`.
2. Na raiz do repositorio: `direnv allow` (apenas quando `.envrc` mudar).
3. Ao entrar na pasta, o prompt mostra `[env] python ...` com a versao ativa.

Sem direnv, rode `source ./activate_repo.sh` (pode definir `SSA_PYTHON_VARIANT=free-threaded` antes). O wrapper `activate_env.sh` apenas chama o mesmo helper.

### Windows 11 (PowerShell)
- Adicione ao profile: `. .\activate_repo.ps1` (ou use `scripts/append_profile_snippet.ps1`).
- Escolha de variante: `. .\activate_repo.ps1 -Variant free-threaded` ou via `SSA_PYTHON_VARIANT`.
- `activate_env.ps1` continua disponivel e delega para `activate_repo.ps1`.

### Variantes suportadas
- **stable** (padrao): usa `SSA_PYTHON_STABLE_VERSION` (default 3.13.12 ou o valor de `.python-version`).
- **free-threaded**: liga o build 3.14 `--disable-gil`. Ajuste com `SSA_PYTHON_FT_VERSION` se for usar outro rotulo do pyenv.

## Notas praticas
- A primeira carga pode rodar `pyenv install <versao>`; sem internet o fluxo cai no `.venv` local e avisa no log.
- Preferimos `pyenv virtualenv`. Caso apenas `pyenv` basico exista, usamos `pyenv shell <versao>`.
- As mensagens `[env]` indicam se o modo ativo eh `pyenv-virtualenv`, `pyenv` puro ou `venv`.
- Para sair, use `deactivate` (venv) ou `pyenv deactivate`.

## Bootstrap opcional
`dev_env/bootstrap.sh` e `dev_env/bootstrap.ps1` continuam uteis para instalar pyenv/direnv e criar antecipadamente os virtualenvs `ssa_consulta_stable_*` e `ssa_consulta_free-threaded_*`. O novo `.envrc` tambem cria tudo sob demanda, entao esses scripts sao opcionais.


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
