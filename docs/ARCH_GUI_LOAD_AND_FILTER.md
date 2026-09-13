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

Os retornos da SAM API tambem conferem a identidade do worker ativo antes de
alterar progresso, previa, decisao de importacao ou resultado. A identidade e
conferida novamente depois do dialogo de confirmacao. Um retorno antigo do
rescan pode concluir seu proprio dialogo, mas nao muda o status, recarrega dados
nem remove as referencias da operacao atual.

Falhas ao construir ou iniciar threads de derivadas, compactacao ou validacao
de outro banco encerram o estado da tentativa e liberam os controles. Na SAM
API, essa protecao inclui construcao, preparacao e conexao de sinais, permitindo
nova tentativa depois da falha. Se a SAM concluir e a recarga
falhar, o status orienta usar `Recarregar dados` e o log registra a falha.

Um fechamento adiado restaura o estado operacional da janela. A confirmacao de
preferencias distingue espera pendente de gravacao que falhou: fila vazia nao
comprova persistencia. A falha e informada no status e no log, e o adiamento
restaura `_is_shutting_down=False`. Novas preferencias podem ser enviadas;
somente uma nova gravacao bem-sucedida elimina o erro anterior. O prazo de
encerramento continua seguindo as operacoes ainda vivas.

## Referencias

- [Regras de carregamento e encerramento](GUI_ASYNC_LOADING_GUARDRAILS.md)
- [API e ciclo de vida dos workers](WORKERS_API_DOCUMENTATION.md)
- [Otimizacoes das abas de filtro](FILTER_TAB_OPTIMIZATIONS.md)
- [Regras gerais da GUI](GUI_PYQT6_REGRAS_GERAIS.md)
- [Exportacao do resultado de derivadas](DERIVADAS_SYNC_RUNBOOK.md)
- [Plano de validacao da auditoria](VALIDATION_PLAN.md)
