# Correcoes Pontuais v3.10 – GUI (SSA_Consulta_Rapida)

Este documento descreve, de forma objetiva, as correcoes de GUI aplicadas cirurgicamente no arquivo `gui/gui_ssa.py`, conforme solicitado.

## Correcoes aplicadas
- Import de `QSizePolicy` no topo e remocao de imports locais dentro de metodos, eliminando `UnboundLocalError`.
- Filtro por coluna:
  - Pressionar Enter no campo (`QLineEdit`) aplica o filtro da propria coluna.
  - Botao “Limpar” da coluna limpa apenas o conteudo daquele filtro.
  - Nao reordena e nao reseta a paginacao; a pagina atual e preservada.
- Pesquisa geral:
  - Campo de busca ampliado (~25%) para facilitar digitacao.
- Resumo de filtros:
  - Adicionada uma linha abaixo da area de paginacao/filtros com o resumo: “Geral: ... | Colunas: ...”.
  - Inclui botao “Limpar todos os filtros” que limpa busca geral e filtros por coluna, preservando a pagina atual.

## Pontos tocados
- `gui/gui_ssa.py`:
  - Import: inclusao de `QFrame` e uso de `QSizePolicy` apenas via import de modulo (sem reimports locais).
  - Construcao do painel de filtros por coluna: ligacao de `returnPressed` e ajustes do “Limpar”.
  - Atualizacao de exibicao apos aplicar/limpar: preserva pagina atual e atualiza indicadores/resumo.
  - UI do resumo: criacao de `QFrame` + `QLabel` + botao (sem interferir no resto do layout).

## Nao alterado
- `main.py` e demais componentes fora do escopo da GUI nao foram modificados.
- Nao houve mudancas em regras de ordenacao originais do projeto, alem de preservar a pagina corrente em acoes de filtragem.

## Observacao sobre build/execucao
- Os launchers `.cmd` na raiz foram adicionados para facilitar a execucao direta (CLI e GUI) sem exigir ativacao manual da venv.
- O `build.py` foi reescrito para gerar executaveis (CLI/GUI) onefile com icone e empacotar ZIP de distribuicao.

