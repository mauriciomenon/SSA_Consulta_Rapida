# GUI Main Preferences Structure

Este documento descreve a estrutura canonica de preferencias da GUI principal e a hierarquia de decisao entre codigo, template versionado, arquivo local e runtime.

## Objetivo

1. manter nomes, ordem e larguras de colunas amarrados de forma simples
2. garantir que o arquivo de preferencias local tenha a ultima palavra quando existir
3. evitar dependencia de JSON local ignorado como unica fonte humana-legivel do contrato
4. preservar fallback seguro quando o arquivo local estiver ausente ou invalido

## Arquivos envolvidos

1. contrato default em codigo:
   - `gui/gui_config.py`
2. template versionado do padrao:
   - `config/gui_main_preferences.json.example`
3. arquivo local efetivo da GUI:
   - `config/gui_main_preferences.json`
   - ignorado pelo Git por politica operacional
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
3. `DEFAULT_COLUMN_WIDTHS`
   - larguras default persistidas
4. `DEFAULT_GUI_MAIN_PREFERENCES`
   - composicao default de:
     - `display_columns`
     - `hidden_columns`
     - `column_display_names`
     - `column_widths`
     - `gui_settings`

### 2. Template versionado

`config/gui_main_preferences.json.example` existe para:

1. documentar o padrao completo de forma legivel
2. servir como seed para criar o arquivo local real quando ele nao existir
3. permitir auditoria de contrato sem depender do arquivo ignorado do usuario

### 3. Arquivo local efetivo

`config/gui_main_preferences.json` e o arquivo que a GUI usa em runtime.

Regras:

1. pode divergir localmente por gosto do usuario
2. nao deve ser usado como unica fonte de release
3. quando existir e estiver valido, prevalece sobre o default em codigo
4. quando estiver ausente, a GUI usa o template versionado como seed/fallback

### 4. Runtime da tabela

Na renderizacao da tabela, a ordem de precedencia de largura deve ser:

1. largura persistida no arquivo de preferencias
2. largura calculada automaticamente em runtime
3. fallback seguro do codigo

Isso evita que o algoritmo automatico derrube uma largura explicitamente escolhida.

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
2. e a ultima palavra para colunas conhecidas quando o arquivo local estiver presente

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

### `required_display_columns`

Snapshot serializado do contrato canonico de colunas obrigatorias.

Uso:

1. auditoria
2. merge defensivo

## Fluxo de carga

### Caso 1: arquivo local existe e esta valido

1. a GUI le `config/gui_main_preferences.json` pelo caminho resolvido
2. valida integridade minima
3. faz merge defensivo com os defaults
4. carrega o resultado em `GUI_MAIN_PREFERENCES`

### Caso 2: arquivo local nao existe

1. a GUI resolve o caminho local efetivo
2. usa `config/gui_main_preferences.json.example` como seed
3. se `auto_create=True`, cria o arquivo local a partir desse template
4. se o template falhar, cai no hard default em memoria

### Caso 3: arquivo local esta invalido

1. loga erro objetivo
2. nao tenta remendo chave-a-chave nem recuperacao silenciosa
3. cai no template versionado
4. se `auto_create=True`, o arquivo local pode ser recriado a partir do template
5. se o template tambem falhar, cai no hard default em memoria

## Caminho resolvido por ambiente

O arquivo local efetivo respeita `SSA_CONFIG_DIR`.

Isso permite:

1. runtime em pastas alternativas
2. testes isolados
3. empacotamento com raiz de config redirecionada

O template versionado continua vindo do repo.

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

### Label

1. nasce de `column_display_names`
2. propaga para `display_mappings`
3. e consumido pela GUI na construcao dos headers

### Largura

1. nasce em `column_widths`
2. pode ser recalculada automaticamente para colunas sem largura persistida aplicavel
3. o runtime nunca deve passar por cima de largura persistida valida

## O que este desenho evita

1. helper paliativo escondido em runtime
2. depender de JSON ignorado sem template versionado
3. largura automatica derrotando escolha explicita do usuario
4. perda de rastreabilidade sobre nome, ordem e tamanho

## Limite intencional deste slice

Este slice nao reescreve a logica completa do `SimpleWidthManager`.

O tema que continua aberto para avaliacao separada e:

1. alinhar o baseline de largura dinamica com os mesmos numeros canonicos de `DEFAULT_COLUMN_WIDTHS`
2. decidir ate onde a tabela deve ser responsiva por calculo automatico versus estatica por preferencia persistida
