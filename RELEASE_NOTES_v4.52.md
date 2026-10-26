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

Lista completa: secao "Unreleased" do `CHANGELOG.md`.

## Assets

Preenchido na publicacao (um pacote por alvo e `SHA256SUMS.txt`).
