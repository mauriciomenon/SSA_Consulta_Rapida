# Makefile utilitário

.PHONY: install-hooks secret-scan gitleaks-scan

install-hooks:
	bash scripts/install_hooks.sh

secret-scan:
	bash scripts/shell_doctor.sh --quick --secrets

# Executa gitleaks local (requer binário instalado)
# Instalar via: brew install gitleaks  (macOS) ou consultar releases
# Saída não-zero indica achados
# Usa config .gitleaks.toml se presente

gitleaks-scan:
	gitleaks detect --no-banner --redact --exit-code 1 || echo "(verifique acima; se override necessário, ajuste config)"
