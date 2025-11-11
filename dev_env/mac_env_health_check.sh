#!/usr/bin/env bash
set -u
fail=0
sect(){ printf '\n== %s ==\n' "$1"; }

sect "Sistema"
(sw_vers || true) 2>&1
uname -m

sect "Xcode / CLT"
if xcode-select -p &>/dev/null; then
  echo "OK: $(xcode-select -p)"
else
  echo "FALTA: Command Line Tools (xcode-select --install)"; fail=1
fi

sect "Homebrew"
if command -v brew >/dev/null; then
  brew --version | head -1
  echo "doctor (resumo):"
  brew doctor 2>&1 | sed -n '1,6p'
else
  echo "MISSING: Homebrew"; fail=1
fi

sect "PATH"
echo "$PATH" | tr ':' '\n' | sed -n '1,15p'

sect "Node / npm / npx"
command -v node >/dev/null && node -v || echo "MISSING node"
command -v npm  >/dev/null && npm -v  || echo "MISSING npm"
command -v npx  >/dev/null && npx -v  || echo "MISSING npx"

sect "Python / Pyenv"
command -v python >/dev/null && python -V || echo "MISSING python"
command -v pyenv  >/dev/null && pyenv versions || echo "pyenv não configurado"

sect "Virtualenv .venv"
[ -d .venv ] && .venv/bin/python -V || echo "Sem .venv (ok se usa pyenv direto)"

sect "gitleaks / mcp"
command -v gitleaks >/dev/null && gitleaks version || echo "MISSING gitleaks"
command -v mcp >/dev/null && mcp --version || echo "MISSING mcp"

sect "Hooks"
if [ -f .git/hooks/pre-commit ]; then
  grep -q SECRET .git/hooks/pre-commit && echo "Hook pre-commit ativo (secret scan)" || echo "Hook pre-commit presente (sem marker)"
else
  echo "MISSING hook pre-commit"
fi

sect "compinit linhas"
grep -c compinit ~/.zshrc || echo "Não acessível"

sect "Resumo"
if [ $fail -eq 0 ]; then
  echo "STATUS: OK (sem falhas críticas registradas aqui)"
else
  echo "STATUS: FALHAS ($fail) — revise itens MISSING"
fi
