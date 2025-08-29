# SSA Consulta Rápida v3.0.1

Tag: v3.0.1

Foco: manutenção do pipeline e previsibilidade. Nenhuma mudança funcional.

Principais pontos:
- Linter ESLint (SARIF): agora roda e envia resultados somente quando há arquivos JS/TS e configuração ESLint no repo; corrige comando multiline para geração garantida do arquivo `eslint-results.sarif` quando aplicável.
- Linter PSScriptAnalyzer (SARIF): agora roda e envia resultados somente quando existem arquivos PowerShell (`.ps1/.psm1/.psd1`); usa caminho POSIX e inclui passo de skip com mensagem clara.
- Code Scanning: removido workflow de CodeQL avançado que conflita com o Default Setup do GitHub (evita erro "CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled").

Notas:
- Mantidos todos os recursos do 3.0.0: filtro “5 opções” (CLI/GUI), modo padrão configurável (`-c`), GUI com instância única, 67 testes.
- Sem mudanças em APIs/CLI.

Como atualizar (se necessário):
1) Atualize sua cópia local para apontar para a tag v3.0.1.
2) Não há migração de dados nem alterações de configuração.

Links:
- Tag: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v3.0.1
- Notas do 3.0.0: docs_saida/RELEASE_v3.0.0.md
