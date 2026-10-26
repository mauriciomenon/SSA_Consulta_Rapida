# Release v4.52-rc1 (pre-release)

Pre-release de teste gerada do branch `rev` (o caminho oficial continua sendo o `main` via PR).
A janela "Sobre" destes pacotes informa "Build de teste (branch rev): nao e release oficial".
A ultima release oficial publicada segue sendo `v4.51`.

## Principais mudancas desde v4.51

- GUI: menu Arquivo > "Nova janela com a tela atual (copia temporaria)", ate 3 copias com as linhas da tela
  congeladas (filtrar, ordenar e abrir detalhes sem recarregar do banco; "Voltar ao estado congelado").
- GUI: "Salvar estado da tela..." e "Abrir estado salvo..." (filtros, ordenacao, colunas, pagina e SSA em foco;
  aviso quando o banco mudou desde o estado salvo).
- Busca com regex recusada mostra o motivo na GUI, CLI e Streamlit.
- Streamlit revisado (17 achados do BL-13): cache sem resultado velho, erro de leitura visivel, ano/semana de emissao
  como a GUI, "Tem derivadas" na base inteira, limites de data, avisos de valores ignorados, CSV com BOM, painel de
  fonte so em loopback, porta ocupada recusada.
- Windows ARM64: o "Sobre" avisa que a interface web nao esta disponivel (pyarrow sem pacote para a arquitetura).
- Builds: backend PyOxidizer removido (sem manutencao desde 2022 e preso no Python 3.10); ZIP combinado do Windows
  com a arquitetura no nome.

Lista completa: secao "4.52-rc1" do `CHANGELOG.md`.

Publicada em 2026-10-26: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.52-rc1 (GitLab aponta para os mesmos arquivos; tag v4.52-rc1 em 640ac328).

## Validacao

- Suite completa no commit da release: 3705 passed, 4 skipped.
- Revisao multimodelo (CodeRabbit, Codex, BitoReview): achados confirmados corrigidos antes da release.
- Cada pacote: smoke de CLI (Windows/macOS) ou de importacao (Debian) com sucesso; arquitetura conferida (PE 0x8664/0xAA64, Mach-O arm64, .deb amd64/arm64); SHA-256 igual na maquina de build e na copia.
- Nao feito nesta rodada: abertura da GUI em tela nos alvos (roteiro manual do REL-01).

## Assets (SHA-256)

| Asset | SHA-256 |
| --- | --- |
| SSA_Consulta_Rapida_v4.52_macos_arm64.dmg | e80a44d85ae6b25748c47268a372457a0dea4632a5143c747c261accf546ff61 |
| SSA_Consulta_Rapida_v4.52_windows_amd64.zip | 34fa20ceae9007f3d184fba98be7cc57875e3b9e80161f93e7291359925fad0b |
| SSA_Consulta_Rapida_v4.52_windows_arm64.zip | cf99e4849e037fd0c7b76d5320b2663e64f413ad65fdd15841073701d236be8d |
| SSA_Consulta_Rapida_v4.52_debian_amd64.deb | a1e850957b31f3e9f996161220494d8e1ee4ff999ba2878e91561cd7e032e106 |
| SSA_Consulta_Rapida_v4.52_debian_arm64.deb | 029c804cabb104b2d91dc41d019e6dfa62a92a00cbab36312a74e5c70da7ccb6 |
