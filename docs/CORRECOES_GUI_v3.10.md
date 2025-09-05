# Correções Pontuais v3.10 – GUI (SSA_Consulta_Rapida)

Este documento descreve, de forma objetiva, as correções de GUI aplicadas cirurgicamente no arquivo `gui/gui_ssa.py`, conforme solicitado.

## Correções aplicadas
- Import de `QSizePolicy` no topo e remoção de imports locais dentro de métodos, eliminando `UnboundLocalError`.
- Filtro por coluna:
  - Pressionar Enter no campo (`QLineEdit`) aplica o filtro da própria coluna.
  - Botão “Limpar” da coluna limpa apenas o conteúdo daquele filtro.
  - Não reordena e não reseta a paginação; a página atual é preservada.
- Pesquisa geral:
  - Campo de busca ampliado (~25%) para facilitar digitação.
- Resumo de filtros:
  - Adicionada uma linha abaixo da área de paginação/filtros com o resumo: “Geral: … | Colunas: …”.
  - Inclui botão “Limpar todos os filtros” que limpa busca geral e filtros por coluna, preservando a página atual.

## Pontos tocados
- `gui/gui_ssa.py`:
  - Import: inclusão de `QFrame` e uso de `QSizePolicy` apenas via import de módulo (sem reimports locais).
  - Construção do painel de filtros por coluna: ligação de `returnPressed` e ajustes do “Limpar”.
  - Atualização de exibição após aplicar/limpar: preserva página atual e atualiza indicadores/resumo.
  - UI do resumo: criação de `QFrame` + `QLabel` + botão (sem interferir no resto do layout).

## Não alterado
- `main.py` e demais componentes fora do escopo da GUI não foram modificados.
- Não houve mudanças em regras de ordenação originais do projeto, além de preservar a página corrente em ações de filtragem.

## Observação sobre build/execução
- Os launchers `.cmd` na raiz foram adicionados para facilitar a execução direta (CLI e GUI) sem exigir ativação manual da venv.
- O `build.py` foi reescrito para gerar executáveis (CLI/GUI) onefile com ícone e empacotar ZIP de distribuição.

