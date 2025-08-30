Ambiente Python Compartilhado (dev_env)

Objetivo: manter um ambiente Python consistente para o projeto sem impor a mesma versão/localmente, servindo de referência para quem ainda não tem nada configurado. A raiz do projeto permanece limpa; a ativação automática é feita via direnv/pyenv quando disponível.

Pontos‑chave
- Referência de ambiente: o arquivo `.python-version` contém o nome do virtualenv do pyenv: `ssa_consulta_rapida_py313`.
- Não impõe nada: se esse virtualenv não existir localmente, nada é ativado automaticamente. Se existir, direnv/pyenv ativa.
- `.envrc` local: inicializa pyenv e ativa o virtualenv correspondente se existir (arquivo está ignorado no git).
- Fallback: se preferir, use um `.venv` (venv padrão) sem pyenv.

Scripts
- `bootstrap.sh` (Linux/macOS): instala/checa pyenv, cria o virtualenv indicado por `.python-version` com a última versão 3.13.x disponível, instala dependências e configura direnv.
- `bootstrap.ps1` (Windows): instala/checa pyenv‑win, cria o virtualenv indicado e instala dependências. Mantém `.python-version` como referência (não sobrescreve).

Fluxo recomendado
1) Linux (Debian/Ubuntu) ou macOS:
   - Pré‑requisitos de compilação (pyenv):
     - Debian/Ubuntu: `sudo apt update && sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl llvm tk-dev libncursesw5-dev xz-utils libffi-dev liblzma-dev`.
     - macOS: instale Homebrew (se desejar) e depois `brew install pyenv pyenv-virtualenv direnv`.
   - Executar: `bash dev_env/bootstrap.sh`
   - Após rodar: se usar direnv, rode `direnv allow` na raiz do projeto.

2) Windows 10/11 (PowerShell):
   - Execute: `powershell -ExecutionPolicy Bypass -File dev_env/bootstrap.ps1`
   - Reabra o terminal após a instalação do pyenv‑win (se solicitado).

Ativação do ambiente
- Com direnv: ao entrar na pasta do projeto, o ambiente ativa automaticamente se o virtualenv existir. Use `direnv allow` na primeira vez.
- Sem direnv: ative manualmente com `pyenv activate ssa_consulta_rapida_py313` (quando já criado), ou `source .venv/bin/activate` (fallback).

Notas
- Este projeto usa `requirements.txt`. Após ativar o ambiente, rode: `pip install -U pip && pip install -r requirements.txt` (os scripts já fazem isso).
- Caso já tenha um ambiente preferido, ignore pyenv e use apenas um venv local próprio.

