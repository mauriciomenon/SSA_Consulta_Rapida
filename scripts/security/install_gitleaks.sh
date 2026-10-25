#!/usr/bin/env bash
# Instala o gitleaks fixado (versao e SHA-256) para os jobs de pytest do CI (BL-38 achado 6).
# Sem ele os testes de tests/test_gitlab_secret_scan.py pulavam em todo CI.
# Mesma versao da imagem do job secret-scan do .gitlab-ci.yml; release oficial de 2026-03-21,
# OSV sem aviso. A release nao publica assinatura nem atestado: a garantia e o SHA-256 abaixo,
# igual ao gitleaks_8.30.1_checksums.txt oficial e ao digest do GitHub.
# Uso: bash scripts/security/install_gitleaks.sh <pasta_destino>   (so Linux x86_64)
set -euo pipefail

GITLEAKS_VERSION="8.30.1"
GITLEAKS_LINUX_X64_SHA256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"

dest="${1:?uso: install_gitleaks.sh <pasta_destino>}"
if [[ "$(uname -s)-$(uname -m)" != "Linux-x86_64" ]]; then
  printf 'install_gitleaks: so Linux x86_64 (CI); host atual: %s-%s\n' "$(uname -s)" "$(uname -m)" >&2
  exit 2
fi

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
archive="${work}/gitleaks.tar.gz"
curl -fsSL --retry 3 -o "$archive" \
  "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
printf '%s  %s\n' "$GITLEAKS_LINUX_X64_SHA256" "$archive" | sha256sum -c -
mkdir -p "$dest"
tar -xzf "$archive" -C "$dest" gitleaks
"${dest}/gitleaks" version
