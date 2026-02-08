# GUI Async Loading Guardrails

Este documento define as regras de segurança para o carregamento assíncrono da GUI (`load_data`) e para evitar regressões do tipo race condition, deadlock e inconsistência de estado.

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
7. `closeEvent` usa cleanup bloqueante controlado (`wait_ms=3000`) para reduzir risco de `QThread` ativo no encerramento.

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

## Anti-patterns proibidos

- Bloquear thread de UI com `wait()` em trocas normais de worker.
- Usar resultado assíncrono sem validação por `request_id`.
- Destruir worker potencialmente ativo sem retenção/release explícito.
- Repetir cleanup em múltiplos caminhos com lógica divergente.

## Cobertura de Testes Mínima

- Resultado obsoleto ignorado (`on_data_loaded`).
- Erro obsoleto ignorado (`on_load_error`).
- Cleanup de `finished` obsoleto sem mexer em estado da requisição ativa.
- Substituição de worker anterior em `load_data`.
- Worker lento anterior mantido até `finished`.
- `closeEvent` limpa `data_loader_thread` e `filter_thread`.

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
