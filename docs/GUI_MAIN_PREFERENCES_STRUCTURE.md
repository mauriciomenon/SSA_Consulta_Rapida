# GUI Main Preferences Structure

Este documento descreve a estrutura canonica de preferencias da GUI principal e a hierarquia de decisao entre codigo, arquivo efetivo versionado, referencia canonica e runtime.

## Objetivo

1. manter nomes, ordem e larguras de colunas amarrados de forma simples
2. garantir que o arquivo efetivo de preferencias tenha a ultima palavra quando existir
3. evitar dependencia de um JSON fora do contrato versionado como unica fonte humana-legivel do contrato
4. preservar fallback seguro quando o arquivo local estiver ausente ou invalido, sempre a partir do codigo

## Arquivos envolvidos

1. contrato default em codigo:
   - `gui/gui_config.py`
2. arquivo versionado de referencia:
   - `config/gui_main_preferences.json.example`
3. arquivo efetivo da GUI em runtime:
   - `config/gui_main_preferences.json`
4. runtime da tabela:
   - `gui/ssa/gui_table.py`
   - `gui/simple_width_manager.py`

## Hierarquia de decisao

### 1. Codigo canonico

Em `gui/gui_config.py` ficam os contratos base:

1. `REQUIRED_DISPLAY_COLUMNS`
   - conjunto canonico definido pelo produto para colunas obrigatorias desta GUI
2. `DEFAULT_COLUMN_DISPLAY_NAMES`
   - labels curtos e amigaveis por nome interno
3. `COLUMN_HEADER_LABEL_VARIANTS`
   - matriz canonica `short/medium/long` para os headers adaptativos da GUI
4. `DEFAULT_COLUMN_WIDTHS`
   - mapa efetivo de runtime para a plataforma atual
   - resolvido a partir de `DEFAULT_COLUMN_WIDTHS_BY_PLATFORM`
5. `DEFAULT_COLUMN_WIDTHS_BY_PLATFORM`
   - mapas canonicos por SO:
     - `darwin`
     - `win32`
     - `linux`
6. `DEFAULT_GUI_MAIN_PREFERENCES`
   - composicao default de:
     - `display_columns`
     - `hidden_columns`
     - `column_display_names`
     - `column_widths`
     - `column_widths_by_platform`
     - `gui_settings`

### 2. Arquivo versionado de referencia

`config/gui_main_preferences.json.example` existe para:

1. documentar o padrao completo de forma legivel
2. servir como referencia para o usuario editar manualmente se quiser
3. permanecer igual ao que esta definido no codigo, ate mudanca explicita de produto
4. permitir auditoria de contrato sem depender apenas do arquivo efetivo de runtime

### 3. Arquivo efetivo de runtime

`config/gui_main_preferences.json` e o arquivo que a GUI usa em runtime.

Regras:

1. e um arquivo tracked e faz parte do contrato ativo do repo
2. pode ser sobrescrito por um caminho alternativo se o runtime mudar `SSA_CONFIG_DIR`
3. quando existir e estiver valido, prevalece sobre o default em codigo
4. quando estiver ausente, a GUI usa os defaults em memoria do codigo
5. quando trouxer `column_widths_by_platform`, o runtime escolhe primeiro o bloco da plataforma atual
6. quando nao trouxer `column_widths_by_platform`, o runtime cai em `column_widths` por compatibilidade
7. labels legados gerenciados e widths legados gerenciados sao migrados no merge quando ainda refletem o baseline canonico antigo
7. a fase antiga em que esse arquivo era tratado como local-only/skip-worktree e apenas historica, nao contrato atual

### 4. Runtime da tabela

Na renderizacao da tabela, a ordem de precedencia de largura deve ser:

1. largura persistida no arquivo de preferencias
2. largura calculada automaticamente em runtime
3. fallback seguro do codigo

Isso evita que o algoritmo automatico derrube uma largura explicitamente escolhida.

## Widths por plataforma

O contrato de larguras agora tem dois niveis:

1. `column_widths_by_platform`
   - fonte preferencial quando existir
   - permite baseline diferente para:
     - `darwin`
     - `win32`
     - `linux`
2. `column_widths`
   - fallback de compatibilidade para configs antigos
   - continua sendo o mapa persistido efetivo que a GUI usa em runtime apos resolver a plataforma

Onde a deteccao do SO acontece:

1. `gui/gui_config.py::_normalize_platform_key(...)`
   - usa `sys.platform` quando nao recebe override
   - normaliza para `darwin`, `win32` ou `linux`
2. `gui/gui_config.py::_resolve_platform_column_widths(...)`
   - recebe os mapas por plataforma
   - escolhe o bloco da plataforma atual
3. `gui/gui_config.py::_merge_preferences(...)`
   - fecha `merged["column_widths"]` para o runtime

Leitura complementar obrigatoria:

1. `docs/COLUMN_WIDTHS_BY_PLATFORM.md`
   - detalha o algoritmo
   - mostra o Mermaid
   - lista os mapas atuais por plataforma

## O que mudou em termos de comportamento

1. se `config/gui_main_preferences.json` faltar ou o runtime estiver em outro `SSA_CONFIG_DIR`, o runtime cai para os defaults em memoria do codigo
2. se existir largura persistida valida para a coluna, ela ganha da largura calculada em runtime
3. o fallback local de largura da tabela foi amarrado ao contrato canonico de `gui/gui_config.py`, sem numeros paralelos soltos em `gui/ssa/gui_table.py`
4. o baseline automatico do `SimpleWidthManager` agora parte de `DEFAULT_COLUMN_WIDTHS`; o crescimento automatico so adiciona espaco por cima desse baseline, sem reabrir os numeros canonicos
   - esse `DEFAULT_COLUMN_WIDTHS` ja e o mapa resolvido para a plataforma atual
5. reorder de colunas por drag e alteracao de colunas visiveis passam a persistir no mesmo arquivo de preferencias, junto com `hidden_columns`
6. o contrato fica assim:
   - arquivo local tem a ultima palavra
   - o arquivo `.example` documenta o padrao e deve espelhar o codigo
   - codigo define o contrato base

## O que este desenho fez de forma diferente do plano estrutural maior

1. este trabalho nao mudou `REQUIRED_DISPLAY_COLUMNS`
2. este trabalho nao mudou `DEFAULT_COLUMN_WIDTHS`
   - mas o contrato atual passa a resolver esse mapa por plataforma antes do runtime
3. o slice 1 fechou primeiro a hierarquia de preferencias e a precedencia da largura salva
4. o slice 2 atacou apenas o desalinhamento remanescente do width manager automatico, fazendo-o partir do baseline canonico em vez de manter numeros paralelos
5. este ajuste corretivo remove a semantica errada que fazia o runtime usar o `.example` como seed
6. isso foi propositalmente menor do que a critica estrutural mais ampla feita aos commits do Copilot: o objetivo aqui foi corrigir a arquitetura minima sem reabrir a sua decisao de produto sobre ordem e tamanhos

## Schema logico do JSON

### `display_columns`

Lista ordenada das colunas visiveis por default.

Regras:

1. cada item deve ser uma chave interna de coluna
2. a ordem da lista e a ordem visual default
3. colunas ausentes podem ser completadas pelo merge quando fizerem parte do contrato canonico

### `hidden_columns`

Lista de colunas ocultas por default.

Regras:

1. nao deve duplicar itens de `display_columns`
2. serve para colunas conhecidas mas nao exibidas por default

### `column_display_names`

Mapa `nome_interno -> label visual`.

Regras:

1. a chave e o nome tecnico real da coluna
2. o valor e o texto curto ou amigavel visto na GUI
3. se uma chave conhecida faltar, o merge completa com fallback do contrato

### `display_mappings`

Espelho operacional de labels de exibicao.

Uso:

1. compatibilidade com fluxos antigos
2. inicializacao de aliases na GUI

Regra:

1. deve permanecer coerente com `column_display_names`

### `column_widths`

Mapa `nome_interno -> largura em pixels`.

Uso:

1. representa a largura persistida da GUI
2. quando o arquivo local estiver presente, e o mapa efetivo de runtime depois de resolver a plataforma e aplicar fallbacks

Regra:

1. valores devem ser positivos
2. a tabela aplica clamp de seguranca em runtime

### `gui_settings`

Configuracoes gerais da GUI.

Exemplos:

1. `page_size`
2. `debounce_delay`
3. `theme`
4. `enable_column_sorting`
5. `table_cell_alignment`

Valores aceitos para `table_cell_alignment`:

1. `left`
2. `center`
3. `right`

Regra atual:

1. o runtime usa `right` por default
2. valores invalidos voltam para `right`
3. o slice atual altera apenas o alinhamento das celulas da tabela
4. o valor tambem pode ser alterado pelo menu `Opcoes -> Alinhamento da tabela`
5. se houver expansao futura para dialogo, toolbar ou outra superficie maior, isso deve entrar em slice proprio em `gui/gui_ssa.py`, sem misturar com o contrato base de preferencias

### `required_display_columns`

Snapshot serializado do contrato canonico de colunas obrigatorias.

Uso:

1. auditoria
2. merge defensivo

## Fluxo de carga

### Caso 1: arquivo efetivo existe e esta valido

1. a GUI le `config/gui_main_preferences.json` pelo caminho resolvido
2. valida integridade minima
3. faz merge defensivo com os defaults
4. detecta a plataforma atual
5. resolve `column_widths_by_platform[plataforma]` quando existir
6. carrega o resultado final em `GUI_MAIN_PREFERENCES`

### Caso 2: arquivo efetivo nao existe

1. a GUI resolve o caminho efetivo
2. usa os defaults em memoria do codigo
3. detecta a plataforma atual e resolve o bloco correto de widths
4. se `auto_create=True`, cria o arquivo local a partir desses defaults

### Caso 3: arquivo efetivo esta invalido

1. loga erro objetivo
2. nao tenta remendo chave-a-chave nem recuperacao silenciosa
3. cai nos defaults em memoria do codigo
4. detecta a plataforma atual e resolve o bloco correto de widths
5. se `auto_create=True`, o arquivo local pode ser recriado a partir desses defaults

## Caminho resolvido por ambiente

O arquivo efetivo respeita `SSA_CONFIG_DIR`.

Isso permite:

1. runtime em pastas alternativas
2. testes isolados
3. empacotamento com raiz de config redirecionada

O arquivo `.example` continua vindo do repo, mas nao participa do runtime.

## Amarracao entre nome, ordem e largura

### Nome interno

Exemplo:

1. `grau_prioridade_emissao`
2. `descricao_execucao`

Esse nome e a chave unica usada em:

1. `display_columns`
2. `hidden_columns`
3. `column_display_names`
4. `column_widths`

### Ordem

1. a ordem visual default nasce em `display_columns`
2. o drag manual pode persistir nova ordem no arquivo local
3. alteracoes de hide/show tambem passam a atualizar `display_columns` e `hidden_columns`

### Label

1. `column_display_names` continua sendo a fonte base de alias do runtime
2. `display_mappings` continua espelhando esses aliases por compatibilidade
3. `COLUMN_HEADER_LABEL_VARIANTS` define os tres niveis canonicos (`short`, `medium`, `long`) da GUI
4. se o runtime carregar alias customizado diferente do short canonico, a GUI preserva esse alias sem expandi-lo

### Largura

1. nasce em `column_widths`
2. pode ser recalculada automaticamente para colunas sem largura persistida aplicavel
3. o runtime nunca deve passar por cima de largura persistida valida
4. quando existir `column_widths_by_platform`, o baseline do runtime nasce do bloco da plataforma atual antes de fechar `column_widths`

## Algoritmo real de exibicao de texto na GUI

### Header da tabela

1. o header da GUI nasce de aliases canonicos em `column_display_names` / `display_mappings`
2. a GUI principal agora aplica uma segunda passada adaptativa no header usando `COLUMN_HEADER_LABEL_VARIANTS`
3. cada coluna da GUI tem exatamente tres slots:
   - `short`
   - `medium`
   - `long`
4. a escolha runtime tenta `long -> medium -> short` com base na largura real da coluna ja aplicada
5. o calculo reserva espaco para o prefixo `[f] ` e para margem lateral, evitando encavalamento visual
6. se nenhuma variante couber, a GUI usa `short`
7. se uma coluna tiver filtro visual ativo, o header recebe o prefixo `[f] `
8. se o runtime estiver usando alias customizado diferente do short canonico, a GUI respeita esse alias e nao tenta expandi-lo

Consequencia:

1. colunas compactas continuam compactas quando `medium` e `long` repetem o mesmo rotulo
2. colunas largas conseguem crescer sem alterar `DEFAULT_COLUMN_WIDTHS`
   - ou `DEFAULT_COLUMN_WIDTHS_BY_PLATFORM` no nivel canonico
3. o comportamento adaptativo depende da largura final da coluna, nao do schema sozinho

### Celulas da tabela

1. o valor da celula e formatado por `utils/formatting.py`
2. quebras de linha sao substituidas por espaco antes de criar o `QTableWidgetItem`
3. nao existe truncamento manual com `...` nas celulas da tabela principal
4. o corte visual atual vem da largura da coluna e do desenho do Qt em linha unica

### Painel de detalhes

1. o painel de detalhes e o lugar de leitura longa do conteudo
2. ele complementa a tabela, que continua otimizada para leitura compacta

### Onde ha truncamento explicito com `...`

1. nomes de filtros persistentes
2. nao nas celulas da tabela principal

## Algoritmo real de largura na GUI

### Ordem de precedencia

1. largura persistida em `config/gui_main_preferences.json`
2. largura automatica calculada em runtime
3. largura carregada do merge de `GUI_MAIN_PREFERENCES`
4. fallback canonico de `DEFAULT_COLUMN_WIDTHS`
   - resolvido por plataforma antes do runtime

### Recalculo automatico

1. so acontece quando muda o conjunto/ordem de colunas
2. ou quando o viewport muda materialmente
3. se todas as colunas atuais ja tiverem largura persistida valida, resize puro de viewport nao deve derrubar essas larguras

### Crescimento automatico

1. o baseline parte de `DEFAULT_COLUMN_WIDTHS`
   - isto e, do mapa ja resolvido para a plataforma atual
2. o espaco extra automatico e distribuido apenas para colunas expansivas
3. hoje isso se aplica principalmente a `descricao_ssa`, `descricao_execucao` e `solicitante`

## GUI x CLI

1. a GUI usa `gui_main_preferences.json`, aliases de exibicao e `SimpleWidthManager`
2. a CLI nao usa esse contrato de labels/visibilidade da GUI
3. a CLI interativa principal continua com formatacao textual propria, `display_map`, `short_labels`, `fixed_widths` e alternancia `short/full`
4. o caminho principal da CLI interativa continua:
   - `main.py -> interface/cli.py -> interface/table_printer.py`
5. `core/handler_base.py` existe como renderer paralelo, mas nao foi confirmado como callsite ativo do caminho principal da CLI interativa
6. qualquer tentativa de convergir GUI e CLI deve ser tratada como novo slice, nao como efeito colateral desta frente

## O que este desenho evita

1. helper paliativo escondido em runtime
2. depender de JSON ignorado sem referencia versionada
3. largura automatica derrotando escolha explicita do usuario
4. perda de rastreabilidade sobre nome, ordem e tamanho
5. assimetria entre reorder persistido e hide/show nao persistido

## Limite intencional deste slice

Este slice nao reescreve a logica completa do `SimpleWidthManager`.

O tema que continua aberto para avaliacao separada e:

1. decidir ate onde colunas expansivas como `descricao_ssa`, `descricao_execucao` e `solicitante` devem crescer automaticamente por perfil de viewport
2. decidir se o baseline canonico de `gui/gui_config.py` ainda precisa revisao numerica de produto
