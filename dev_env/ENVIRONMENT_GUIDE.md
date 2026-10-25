# Guia de Ambiente SSA (direnv + pyenv)

Este documento complementa o `README.md` do diretorio `dev_env` e descreve em detalhe como o fluxo unificado de ambiente funciona nas diferentes plataformas.

## 1. Estrutura de arquivos
- `dev_env/bootstrap.sh` / `dev_env/bootstrap.ps1`: scripts opcionais para instalar pyenv/direnv e criar os virtualenvs antecipadamente.
- `.envrc`: ponto de entrada do direnv. Monitora `scripts/env/direnv_common.sh`.
- `scripts/env/direnv_common.sh`: nucleo compartilhado. Resolve a variante (`stable` ou `free-threaded`), provisiona pyenv ou `.venv` e exporta PATH/variaveis.
- `dev_env/activate_repo.sh` / `dev_env/activate_env.sh`: wrappers POSIX para quem nao usa direnv.
- `dev_env/activate_repo.ps1` / `dev_env/activate_env.ps1`: wrappers PowerShell (pyenv-win ou `.venv`, sem uv).

## 2. Processo de ativacao
1. Ao entrar na pasta (ou ao executar um dos wrappers) o script chama `ssa_env::apply`.
2. `ssa_env::apply` determina a variante desejada seguindo a prioridade:
   1. argumento passado ao wrapper;
   2. variaveis `SSA_PYTHON_VARIANT` ou `SSA_USE_FREE_THREADED`;
   3. padr?o `stable` (produ??o).
3. Linux/macOS: com `uv` no PATH (e sem `SSA_SKIP_UV=1`), cria ou reaproveita `.venv` (`.venv_ft` na variante livre) com `uv venv --python <versao>` e para aqui.
4. Sem uv, se `pyenv` e `pyenv-virtualenv` estiverem presentes:
   - Garante que a versao (`3.13.12` ou `3.14-dev`) esteja instalada.
   - Cria/ativa o virtualenv `ssa_consulta_{variant}_{versao}`.
5. Se pyenv nao estiver disponivel:
   - Cria `.venv` ou `.venv_ft` por meio de `python -m venv`.
   - Mostra aviso quando a variante livre de GIL cair no fallback.
6. Exporta `PYTHONUTF8=1` e `PYTHONDONTWRITEBYTECODE=1` e adiciona `scripts/` e `scripts_manutencao/` ao PATH.
7. Um log `[env] python ...` informa a versao e a origem (`uv-venv`, `pyenv-virtualenv`, `pyenv-local`, `venv`).

## 3. Variantes disponiveis
- **stable** (padrao): `SSA_PYTHON_STABLE_VERSION` (default `3.13.12`); um `.python-version` local, se existir, tem precedencia (o repositorio nao traz esse arquivo).
- **free-threaded**: usa `SSA_PYTHON_FT_VERSION` (default `3.14-dev`) para builds `--disable-gil`.

Para trocar manualmente:
```bash
# POSIX
env SSA_PYTHON_VARIANT=free-threaded direnv reload
source dev_env/activate_repo.sh  # respeita a env var acima
```
```powershell
# PowerShell
$env:SSA_PYTHON_VARIANT = 'free-threaded'
. .\dev_env\activate_repo.ps1
```

## 4. Diagnostico rapido
- `direnv status`: confirma se o hook foi carregado.
- `pyenv version` / `pyenv virtualenvs`: lista versoes disponiveis.
- `echo $SSA_ENV_SOURCE` (bash) ou `$env:SSA_ENV_SOURCE` (PowerShell): mostra investimento atual.
- `pyenv install --list | grep 3.14`: verifica se a build `3.14-dev` esta disponivel no mirror local.

## 5. Boas praticas
- Sempre rodar `direnv allow` ap?s alterar `.envrc` ou `scripts/env/direnv_common.sh`.
- Em Windows, considere adicionar `. .\dev_env\activate_repo.ps1` ao perfil para ativacao automatica.
- Instale dependencias com `uv sync --frozen`; o runtime sem ferramentas usa `uv sync --frozen --no-dev`. Ativacao nao instala pip.
- Ao testar builds free-threaded, valide se alguma dependencia nativa suporta o binario `--disable-gil`.

## 6. Restauro manual
Se o ambiente corromper:
1. Remova o virtualenv: `pyenv virtualenv-delete ssa_consulta_stable_3.13.12` (ajuste a versao).
2. Reentre na pasta ou rode `. dev_env/activate_repo.sh` / `. .\dev_env\activate_repo.ps1` para recriar.
3. Se necessario, exclua `.venv` ou `.venv_ft` e repita o passo anterior.

Com isso, o setup permanece previsivel em Windows, WSL Debian e macOS.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
