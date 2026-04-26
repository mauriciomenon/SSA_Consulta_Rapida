# GUI State Contract Postmortem 2026-04-09

## Objetivo

Registrar as falhas de contrato que passaram sem serem vistas na GUI,
explicar a causa raiz tecnica, e deixar claro quais blindagens foram
aplicadas sem reabrir refatoracao ampla.

## Escopo

Este postmortem cobre a frente de:
1. busca geral da GUI
2. reorder, sort e resize do header
3. painel `Detalhes da SSA Selecionada`
4. persistencia de colunas/larguras em `gui_main_preferences`
5. fluxo de derivadas

Nao cobre:
1. mudanca de layout
2. `fuzzy`
3. refatoracao ampla de `display_current_page(...)`
4. backlog estrutural fora da GUI de tabela/detalhes

## Current Truth

Em 2026-04-09, os contratos mais perigosos desta frente ficaram assim:
1. a GUI e dona explicita das colunas da busca geral
2. reorder de coluna nao pode atualizar detalhes
3. sort de coluna nao pode atualizar detalhes
4. resize precisa persistir largura na coluna correta mesmo com reorder
5. reorder em schema parcial nao pode truncar o estado visivel persistido
6. derivadas devem:
   - aplicar filtro em `derivada_de`
   - mostrar as derivadas na lista
   - atualizar detalhes para a primeira derivada exibida
   - ao limpar, voltar a SSA origem via `_jump_to_ssa(...)`

## Falhas Que Passaram

### 1. Contrato escondido da busca geral

Falha:
1. a busca geral da GUI dependia de uma lista default escondida no core
2. colunas relevantes, como localizacao, ficaram fora do contrato real

Causa raiz:
1. contrato de produto enterrado em implementacao generica
2. GUI sem ownership explicito do proprio escopo de busca
3. docs sem fonte de verdade curta e direta

Blindagem aplicada:
1. a GUI passou a montar explicitamente `search_columns`
2. o contrato foi documentado em `docs/GUI_GENERAL_SEARCH_COLUMN_CONTRACT.md`
3. testes de contrato passaram a travar inclusoes/exclusoes relevantes

Commits:
1. `bf57520d73a93335715d71a63ec5783b9040ec28`

### 2. Reorder visual contaminando estado funcional

Falha:
1. reorder de coluna mexia no painel `Detalhes da SSA Selecionada`

Causa raiz:
1. `on_columns_changed(...)` e `_on_header_section_moved(...)` chamavam
   `display_current_page(...)`
2. esse metodo nao era apenas render de tabela; ele carregava detalhes junto
3. a suite validava reorder, mas nao a ausencia de efeito colateral em detalhes

Blindagem aplicada:
1. reorder passou a usar `display_current_page(..., update_details=False)`
2. testes passaram a verificar preservacao de:
   - `_details_current_ssa`
   - `details_text`
   - ausencia de refresh de detalhes no caminho

Commits:
1. `c45d9e4208d30cf25eea55cad8b75d326e0c3489`

### 3. Sort contaminando detalhes

Falha:
1. clicar no header para ordenar trocava detalhes da SSA exibida

Causa raiz:
1. `on_header_clicked(...)` ordenava `df_exibido`
2. depois chamava `display_current_page(current_page)` com detalhes ligados
3. o contrato entre sort e detalhes nao estava declarado em teste

Blindagem aplicada:
1. `sort` passou a usar `display_current_page(..., update_details=False)`
2. teste passou a travar:
   - ordenacao real do `df_exibido`
   - preservacao de detalhes
   - ausencia de `_update_details_from_series(...)`

Commits:
1. `3bc0d36f4e8f5ff01c0d0353ba81e85e2f9eba3d`

### 4. Resize persistindo largura na coluna errada

Falha:
1. em cenarios de reorder, largura podia ser persistida para a coluna errada

Causa raiz:
1. `resize` ainda usava mapeamento logico cru
2. sort e menu contextual ja tinham resolucao mais robusta
3. `resize` tinha ficado atras no mesmo contrato

Blindagem aplicada:
1. `resize` passou a reutilizar a mesma resolucao de coluna do header
2. regressao adicionada para:
   - reorder visual + resize
   - reorder persistido + reload + resize

Commits:
1. `5e581d6ef003e5c53d62fa0ef1a75edffc0c0cb1`

### 5. Reorder com schema parcial truncando estado visivel

Falha:
1. reorder com schema parcial podia derrubar colunas ainda validas do estado
   persistido

Causa raiz:
1. `_current_display_columns` refletia so o schema atual renderizado
2. o reorder podia sobrescrever `visible_columns` como se aquela lista parcial
   fosse a lista completa

Blindagem aplicada:
1. reorder passou a mesclar:
   - colunas presentes reordenadas
   - colunas ainda visiveis, mas ausentes do schema atual
2. teste de regressao passou a travar esse caso

Commits:
1. `048700c46a6d8d8af4303d8f147d1181566710d5`

### 6. Runtime config sendo sujo por teste/GUI

Falha:
1. `config/gui_main_preferences.json` tracked era alterado incidentalmente

Causa raiz:
1. persistencia real sendo acionada em contexto de teste/execucao
2. isolamento insuficiente entre runtime state e arquivo tracked
3. o efeito aparecia como newline, reorder de `hidden_columns`, ou ambos

Blindagem aplicada:
1. normalizacao do arquivo tracked
2. alinhamento da documentacao do contrato
3. restauracao automatica do arquivo ao final de slices quando o ruido reaparece
4. testes adicionais de saneamento e persistencia

Commits:
1. `f1b676c42baeff1d0b5ac9b153a7c0bcac31ac84`
2. `254f39bdb5ddced6cd5f858c3ca75a98441ebd96`

### 7. Contrato de derivadas sem trava forte

Falha:
1. o runtime fazia algo coerente, mas o contrato nao estava fechado em teste

Causa raiz:
1. faltava declarar o ciclo completo:
   - aplicar derivadas
   - atualizar lista
   - atualizar detalhes
   - limpar
   - voltar para a origem

Blindagem aplicada:
1. testes passaram a travar:
   - `_last_derivada_origem`
   - filtro ativo `derivada_de`
   - `df_exibido`
   - `_details_current_ssa`
   - chamada de `_jump_to_ssa(...)` no clear

Commits:
1. `21135ccfa91ac8a40760e66fb7926bd607af9782`

## Causa Raiz Sistematica

O padrao que deixou varias falhas passarem foi este:
1. acoes de apresentacao usavam um fluxo mais pesado do que precisavam
2. esse fluxo carregava responsabilidades semanticas junto
3. a suite perguntava "funciona?" em vez de "o que isto nao pode quebrar?"

O principal concentrador desta classe de risco continua sendo:
1. `display_current_page(...)`

Hoje ele concentra junto:
1. paginacao
2. schema visivel
3. render da tabela
4. sync do header
5. larguras
6. detalhes

Nao houve refatoracao ampla aqui por decisao de escopo.
O endurecimento foi feito nos call sites mais perigosos.

## Licoes Operacionais

1. acao visual nao pode, por default, usar fluxo que atualiza detalhes
2. teste de feature isolada nao substitui teste de ausencia de efeito colateral
3. contratos de UI precisam ser declarados em texto curto e em regressao real
4. config tracked de runtime exige higiene de teste explicita
5. docs vivos precisam andar junto com o runtime; doc stale mascara bug

## Blindagens Aplicadas Nesta Frente

1. GUI passou a ser dona explicita do contrato de busca geral
2. reorder preserva detalhes
3. sort preserva detalhes
4. resize persiste largura na coluna correta
5. reorder em schema parcial preserva colunas visiveis ausentes
6. derivadas ficaram travadas em contrato de navegacao
7. `gui_main_preferences` tracked foi normalizado e redocumentado

## Pendencia Estrutural Consciente

Ainda existe um debt arquitetural claro:
1. `display_current_page(...)` continua concentrando responsabilidades demais

Status atual:
1. risco agudo dos call sites principais foi reduzido
2. refatoracao transversal segue fora do escopo desta frente
3. qualquer ataque a esse ponto deve entrar em slice proprio, pequeno e medido

