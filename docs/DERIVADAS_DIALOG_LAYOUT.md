# Dialogo de Derivadas no Painel de Detalhes

## Objetivo

Registrar o contrato atual do dialogo de detalhes da SSA, com foco na area
de derivadas consolidada na mesma janela.

## Estrutura atual

O dialogo usa uma unica tela de conteudo, sem `QTabWidget` de aba unica.

A altura inicial do dialogo segue a altura atual da janela principal, limitada
ao tamanho util da tela ativa.

O layout principal usa um `QSplitter` vertical com tamanhos iniciais:

- area superior `Detalhes`: `560`
- area inferior `Derivadas`: `170`

A area inferior usa um `QSplitter` horizontal com tamanhos iniciais:

- texto de derivadas, a esquerda: `430`
- grafo e exportacao, a direita: `560`

Os dois splitters sao redimensionaveis pelo usuario.

Para tornar esse ajuste usavel na pratica, o handle dos splitters usa largura:

- `10`

## Grafo de derivadas

O grafo usa os seguintes tamanhos base:

- largura da caixa: `100`
- altura da caixa: `30`
- gap horizontal: `110`
- gap vertical: `60`
- margem externa: `8`

O no em destaque usa azul claro para preservar legibilidade com texto preto.

## Overflow e legibilidade

Quando o SVG fica maior que a area disponivel, ele e reduzido para caber no
painel atual.

Esse comportamento foi mantido por ser simples, estavel e aceitavel no estado
atual. Em casos extremos, a legibilidade pode cair. Refinamento futuro pode
adotar estrategia dedicada para overflow do grafo.

## Tela ativa

Antes de abrir, o dialogo e limitado ao tamanho util da tela ativa:

- respeita largura maxima disponivel
- respeita altura maxima disponivel
- ajusta o tamanho minimo efetivo para nao exceder a tela

Isso evita que a janela ultrapasse a geometria util da tela em setups com
multiplos monitores ou telas menores.

## Navegacao por links de derivadas

No bloco textual de derivadas, so recebem link as SSAs que existem nos dados
carregados no momento.

Se a SSA relacionada nao estiver disponivel no dataset atual, ela aparece como
texto normal, sem link.
