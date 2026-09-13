# GUI Async Loading Guardrails

Este documento define as regras de segurança para o carregamento assíncrono da GUI (`load_data`) e para evitar regressões do tipo race condition, deadlock e inconsistência de estado.

## Atualizacao 2026-03-27

- `update_derivadas_from_sources()` e `load_other_database()` passaram a seguir a mesma diretriz: I/O e validacao fora do thread principal no runtime normal.
- Em testes (`PYTEST_CURRENT_TEST`), o caminho sincrono controlado continua permitido para manter a harness deterministica.

## Objetivos

- Garantir que apenas o carregamento mais recente atualize a UI.
- Evitar travamento da UI durante troca de workers de carga.
- Evitar callbacks tardios alterando botões/estado após uma nova requisição.
- Manter cleanup previsível no fechamento da janela.

## Invariantes de Concorrência

1. Cada chamada de `load_data()` gera um `request_id` monotônico.
2. `self._active_data_load_request_id` aponta para a requisição vigente.
3. `on_data_loaded`, `on_load_error` e `on_load_finished` ignoram eventos com `request_id` obsoleto.
4. Worker anterior é desconectado imediatamente quando uma nova carga começa.
5. Troca de worker em `load_data()` é não bloqueante (`wait_ms=0`) para não congelar a UI.
6. Worker lento/remanescente é mantido em `self._retired_data_loader_workers` até emitir `finished`.
7. `closeEvent` solicita cancelamento cooperativo e consulta os workers ativos sem esperas em serie. O fechamento pode ser adiado; o estado nativo determina quando cada worker terminou.
8. Hand-off de `filter_thread` também é não bloqueante (`wait_ms=0`) em requisições rápidas.
9. Worker de filtro lento/remanescente também é retido até `finished` em `self._retired_filter_workers`.
10. `load_data()` invalida e cancela o pipeline de filtro vigente antes de iniciar novo carregamento.
11. `load_data()` para o debounce de busca para evitar disparo tardio com dataset antigo.

## Regras de Estado da UI

- Início de carga:
  - `status_label = "Carregando dados..."`
  - `progress_bar` visível
  - `load_button` e `search_button` desabilitados

- Fim de carga vigente:
  - `progress_bar` oculta
  - `load_button` e `search_button` habilitados
  - `clear_filter_button` sincronizado por `_has_any_active_filters()`

- Evento obsoleto:
  - Não altera dataset, botões, texto de status ou paginação.

## Guardrails adicionais para outras operacoes pesadas

- Validacao de banco selecionado por arquivo:
  - nao consultar schema/tabela no thread principal do runtime normal;
  - entregar resultado de volta por timer/sinal, com guarda de estado de janela.
- Sync manual de derivadas:
  - nao usar `processEvents()` como substituto de background real;
  - runtime normal deve executar o bloco pesado fora da UI.

## Encerramento e operacoes concorrentes

- `closeEvent` define `_is_shutting_down` durante a tentativa e restaura `False`
  se o fechamento for adiado. Timers so param quando o fechamento e aceito.
- `shutdown()` aguarda a persistencia de preferencias com `flush(timeout=1.0)`;
  esse limite nao encerra o gravador nem impede novas preferencias. O gravador
  recebe `shutdown(timeout=0.0)` somente no fechamento aceito.
- O prazo de 30 segundos acompanha os objetos de operacoes pendentes, incluindo
  workers Qt e a thread de derivadas. Um conjunto novo, sem operacoes da
  tentativa anterior, reinicia o prazo. Uma nova tentativa apos o prazo pode
  aceitar o fechamento forcado da mesma operacao, com registro no log e retencao
  dos workers ainda vivos; nao significa que o trabalho terminou com sucesso.
- A validacao de banco guarda o resultado em cada requisicao e inclui
  `_request_id` na entrega. Timers e finalizadores antigos nao alteram o estado
  de uma selecao posterior, mesmo depois de timeout ou dialogos modais.
- Acoes que disputam o banco usam `database_operation_in_progress()` e
  `refresh_database_actions()`. As referencias das acoes reais e o botao da API
  sao atualizados no inicio, no erro e no termino nativo. Filtros nao escondem
  progresso e estado de carga ou sincronizacao ainda em andamento.
- O relatorio de derivadas e invalidado ao iniciar outra sincronizacao ou trocar
  de banco. Exportar exige validar o mesmo resultado novamente apos os dialogos.

## Anti-patterns proibidos

- Bloquear thread de UI com `wait()` em trocas normais de worker.
- Usar resultado assíncrono sem validação por `request_id`.
- Destruir worker potencialmente ativo sem retenção/release explícito.
- Repetir cleanup em múltiplos caminhos com lógica divergente.

## Fluxo de Filtro Assíncrono

- `initiate_filtering()`:
  - incrementa `request_id` de filtro
  - invalida requisições anteriores
  - troca worker anterior sem bloquear UI
- `on_filter_finished` / `on_filter_error`:
  - só processam evento se `request_id` for o ativo
- `on_filter_finished_cleanup`:
  - libera UI e encerra worker da requisição vigente
  - em evento obsoleto, faz cleanup apenas do worker stale

## Cobertura de Testes Mínima

- Resultado obsoleto ignorado (`on_data_loaded`).
- Erro obsoleto ignorado (`on_load_error`).
- Cleanup de `finished` obsoleto sem mexer em estado da requisição ativa.
- Substituição de worker anterior em `load_data`.
- Worker lento anterior mantido até `finished`.
- `closeEvent` limpa `data_loader_thread` e `filter_thread`.
- Requisições rápidas de filtro não bloqueiam UI na troca de worker.
- Worker de filtro lento é retido e liberado apenas em `finished`.

A matriz completa de reproducao, incluindo fechamento adiado, preferencias,
validacao de banco, menus e exportacao, esta no
[plano de validacao](VALIDATION_PLAN.md). As regras acima descrevem o contrato;
nao constituem evidencia de execucao da suite completa ou de teste visual nativo.

## Arquivos-chave

- `gui/gui_ssa.py`
  - `_cleanup_data_loader_worker`
  - `_retain_data_loader_worker_until_finished`
  - `load_data`
  - `on_data_loaded`
  - `on_load_error`
  - `on_load_finished`
  - `closeEvent`

- `tests/test_gui_filter_logic.py`
  - testes de corrida/sincronização para carga e filtro assíncronos.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

