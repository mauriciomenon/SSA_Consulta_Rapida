# Carregamento e filtros da GUI

O carregamento e a filtragem usam identificadores de requisicao para impedir
que resultados antigos substituam o estado de uma operacao mais recente.
A validacao de um banco escolhido em arquivo tambem conserva seu resultado por
requisicao; um retorno atrasado apos timeout nao publica nem apaga o resultado
da proxima selecao.

As acoes que disputam o banco compartilham o estado de ocupacao definido em
`gui/ssa/app_menus.py`. Importacao, rescan, troca de banco, atualizacao pela API,
sincronizacao de derivadas e manutencao consultam esse estado nos pontos de
entrada e apos dialogos. Acoes de menu e botao da API refletem o estado real da
operacao. Filtros e navegacao mantem seus controles proprios; seu retorno nao
apaga o progresso de uma carga ou sincronizacao ainda ativa.

Um fechamento adiado restaura o estado operacional da janela. Preferencias
continuam aceitando alteracoes ate o fechamento ser aceito, e o prazo de
encerramento acompanha as operacoes ainda vivas.

## Referencias

- [Regras de carregamento e encerramento](GUI_ASYNC_LOADING_GUARDRAILS.md)
- [API e ciclo de vida dos workers](WORKERS_API_DOCUMENTATION.md)
- [Otimizacoes das abas de filtro](FILTER_TAB_OPTIMIZATIONS.md)
- [Regras gerais da GUI](GUI_PYQT6_REGRAS_GERAIS.md)
- [Exportacao do resultado de derivadas](DERIVADAS_SYNC_RUNBOOK.md)
- [Plano de validacao da auditoria](VALIDATION_PLAN.md)
