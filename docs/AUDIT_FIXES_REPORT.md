# Relatorio de Correcoes  -  Auditoria SSA Consulta Rapida

**Branch:** `fix/audit-surgical-fixes`. Codigo desta rodada publicado ate `1ef9edaf` nos tres destinos em 13/09/2026. A documentacao e versionada em commit posterior; obtenha o HEAD completo com `git rev-parse HEAD`. Base da implementacao: `ca542fb5`; base da auditoria historica: `dev` em `e62a85bf`.
**Historico anterior:** `e62a85bf..ca542fb5` contem 21 commits; o intervalo exclusivo `36dc3137..ca542fb5` tem 20. A reescrita anterior preservou 12 hashes e alterou 9, com arvores equivalentes. Esta rodada acrescentou quatro commits de codigo sem reescrever ancestrais.
**Validacao anterior informada:** 2924 passed, 9 skipped. Revisao independente: 83 aprovacoes focadas; py_compile/Ruff passaram; ty falhou (um erro novo no teste, outros diagnosticos fora do patch); Semgrep parcial por dois timeouts.
**Estado atual, 13/09/2026:** exportacao, F3/F4, N7/N8/N11, coordenacao de operacoes, tracebacks e feedback GUI corrigidos e commitados. Os quatro commits de codigo foram publicados nos tres destinos. Hooks de autoria instalados e ativos; CI versionada/publicada, sem execucao remota comprovada. Compilacao, Ruff e ty passaram nos 22 Python alterados/novos. Os 16 creditos antigos permanecem nas mensagens dos ancestrais; nao houve reescrita nesta rodada. A passagem completa para reteste esta em `VALIDATION_PLAN.md`.

Legenda de estado: **CORRIGIDO** (codigo commitado e publicado; a evidencia de validacao e discriminada por rodada) | **PARCIAL** | **NAO CORRIGIDO** (justificativa) | **NAO-BUG** (verificado, sem alteracao)


## Comparativo antes/depois e estado por pedido

A resposta anterior foi incompleta tanto no codigo como no relato. Esta tabela substitui o encerramento anterior; nao reutiliza um resultado historico como prova das mudancas atuais.

| Pedido | Antes, em ca542fb5 / primeira entrega | Depois, nos commits desta rodada | Estado |
|---|---|---|---|
| Preservar API Python | Duas funcoes existentes; proposta externa considerava exclusao | Funcoes JSON/CSV preservadas e TSV acrescentada, sem remover chamadas existentes | ENTREGUE |
| Preservar stdout JSON | CLI imprimia JSON; documentacao nao explicitava todos os contratos | stdout mantido, inclusive com flags; exemplos, erros e codigos de saida documentados | ENTREGUE |
| CLI JSON/CSV/TSV | Sem flags dedicadas | --report-json, --report-csv, --report-tsv combinaveis em sync/heal/maintenance | ENTREGUE |
| GUI JSON/CSV/TSV | Sem acao de exportacao | Menu Database exporta o resultado da sincronizacao concluida no banco atual, com dialogo e confirmacao | ENTREGUE |
| Protecao de arquivos | Primeira entrega nao cobria WAL real quando DB era symlink | Banco resolvido antes de formar -wal/-shm/-journal; fontes/destinos repetidos protegidos; gravacao por arquivo preserva destino anterior em erro | ENTREGUE |
| Relatorio correto apos dialogos | Primeira entrega verificava estado antes da ultima confirmacao | Revalidacao depois de TODOS os dialogos; invalidacao gera aviso e zero exportacoes | ENTREGUE |
| F3 | Coluna opcional ausente + dado inconsistente: primeira tentativa rejeitava, segunda aceitava | Mesmos bloqueios SQLite/schema/permissoes antes/depois do reparo; dado permitido gera aviso na primeira tentativa | ENTREGUE |
| F4 | Ressalvas ficavam no resultado interno/log; GUI apresentava sucesso sem detalhes | ImportOutcome real fornece avisos ao worker/controlador/dialogo. Resultado com ressalvas persiste, sem mudar A5 | ENTREGUE |
| N8 | Resultado tardio A podia apagar resultado pronto B | Closure e identidade por pedido; B e entregue uma vez mesmo quando A termina depois | ENTREGUE |
| N7: flag/timers | Flag incorreta em adiamento/forcado; timers parados com janela aberta | Adiamento restaura flag/menus; timers permanecem ativos; aceite/forcado mantem flag ativa | ENTREGUE |
| N7: preferencias | Primeira entrega ainda encerrava fila antes de decidir fechar; snapshots novos eram recusados | flush aguarda sem encerrar a fila; novo snapshot aceito depois de timeout e gravado ao liberar o escritor | ENTREGUE |
| N11 / F2 do item 5 | Prazo antigo reaproveitado em derivadas; primeira entrega falhava apos preferencias | Novo Qt/derivadas recebe prazo novo inclusive apos conjunto anterior vazio; mesma operacao conserva prazo | ENTREGUE |
| A7 / Z-A15 / Z-C1 / Z-C5 | Menus ativos e guardas apenas da propria operacao permitiam sobreposicao | Acoes conflitantes e entradas coordenadas entre carga, derivadas, rescan, SAM, vacuum e validacao de DB | ENTREGUE |
| Feedback de operacoes | Filtro podia esconder barra/status de derivadas; import/lista/erro de carga tinham informacao insuficiente | Filtros continuam utilizaveis sem apagar progresso; import informa quantidade; lista informa destino/linhas; erro marca tabela anterior | ENTREGUE nos casos especificados |
| C2 e guia de instalacao | Traceback nao sanitizado; guia anunciava abertura mesmo com retorno False | Texto/JSON de excecao legiveis em ASCII; status do guia depende do retorno real | ENTREGUE |
| Regra de autoria no repo | AGENTS.md era a unica prevencao acrescentada | AGENTS.md atualizado; verificador unico usado em commit-msg e pre-push, ambos instalados e ativos | ENTREGUE |
| Regra na CI GitHub/GitLab | Nenhuma verificacao de autoria nesses fluxos | Mesma verificacao incorporada aos arquivos de CI existentes em c49dbac7; usa HEAD real do PR/MR | PUBLICADA; EXECUCAO REMOTA NAO COMPROVADA |
| Bloqueio nativo de servidor | Recursos completos indisponiveis nos planos/tipos atuais | Limite confirmado; hooks locais e CI nao sao apresentados como substitutos equivalentes | NAO ATIVADO ONLINE |
| Corrigir mensagens antigas | 16 commits continham credito Devin apesar do autor/committer humanos | Diagnostico e proposta de reescrita discriminados; objetos/referencias publicados preservados | NAO REESCRITO |
| Documentacao no inicio/final | Contagens, caminho GitLab e estados divergentes; sem comparativo completo | Relatorio, laudo, backlog, guias e indices reconciliados; passagem completa e documentos desta rodada versionados | ENTREGUE |
| Reteste pesado por outros modelos | Solicitado fora da execucao cirurgica desta rodada | Texto completo em VALIDATION_PLAN.md: hashes, comandos, casos, resultados esperados e criterios; reteste pesado nao disparado | ADIADO CONFORME PEDIDO |

Evidencias de codigo: `gui/gui_ssa.py` (validacao/fechamento), `gui/ssa/gui_preferences_persistence.py` (fila), `gui/ssa/app_menus.py` e controladores (coordenacao), `armazenamento/database_integrity.py` (F3), `gui/workers/rescan_worker.py` e `gui/ssa/gui_rescan_lifecycle.py` (F4), `scripts/derivadas_cli.py`/`armazenamento/derivadas_sync.py` (exportacao), `scripts/validate_git_authorship.py` (regra executavel).


---

## A. Prioridade ALTA (auditoria original)

| # | Problema | Evidencia original | Correcao | Estado |
|---|---|---|---|---|
| A1 | `_other_db_validation_running` fica preso para sempre se `_work` lanca ou `start()` falha; sem timeout | `gui/gui_ssa.py` validacao de DB alternativo | Tratamentos e prazo de 120s preservados. Cada pedido agora possui resultado em closure propria; entregas atrasadas nao sobrescrevem o pedido atual (N8). | **CORRIGIDO** nesta rodada; ver mapa G |
| A2 | Rescan multi-batched promovia candidato contendo so o batch 1 sobre o DB primario | `gui/workers/rescan_worker.py` `force_import` so no batch 1 | `force_import=False` em todos os batches explicitos; restaurado no `finally` | **CORRIGIDO** (`9163348c`) |
| A3 | `actually_changed=False` no 1o full rescan (sem backup pre-existente)  -  GUI nao recarregava | `core/app_logic.py`, `core/import_database_rotation.py` | promocao reconhecida via `working_db_path == primary_db_path` | **CORRIGIDO** (`68b8f369`) |
| A4 | `SSA_DB_PATH` era lida pela interface mas ignorada pela importacao CLI | `main.py` defaults `data/ssas.db` | `db_path`/`table_name` propagados ao importer; `docs_dir` ancorado no runtime root | **CORRIGIDO** (`9b3f9be0`, `6c32dffd`) |
| A5 | Deadlock operacional: inconsistencia de DADOS (`situacao` fora do catalogo, duplicado) bloqueava justamente a reimportacao que a corrigia | `armazenamento/database_integrity.py`, gates em `app_logic.py` | Politica adotada: "inconsistencia de dados != corrupcao". Estrutural (sqlite/tabela/schema/disco) continua bloqueante; qualidade de dados vira warning e permite reimport. Reparo conservador aplica os mesmos criterios estruturais antes e depois de adicionar colunas opcionais; dados inconsistentes permitidos continuam produzindo aviso (F3). | **CORRIGIDO** nesta rodada; ver mapa G |
| A6 | "Atualizar derivadas" concluia sem recarregar dados  -  contagens stale na tabela | `gui/ssa/derivadas_sync_controller.py` | sucesso dispara `load_data()` no padrao do commit `73251013` | **CORRIGIDO** (`de1be62c`) |
| A7 | Operacoes de dados podiam iniciar em paralelo; menus continuavam ativos | `app_menus.py`, controladores de carga/derivadas/rescan/SAM e validacao de DB | Predicado compartilhado protege entradas e acoes reais do menu. Checagem ocorre antes e depois de dialogos; acoes restauradas em termino/falha. Filtros e navegacao preservados. A classificacao anterior de guardas honestas estava incorreta. | **CORRIGIDO** nesta rodada |

## B. Prioridade MEDIA (auditoria original)

| # | Problema | Correcao | Estado |
|---|---|---|---|
| B1 | `force_wal_checkpoint` descartava o erro na 3a tentativa (perdia sinal "busy") | `import_database_rotation.py`  -  `last_error` preservado; so zera quando checkpoint completo | **CORRIGIDO** (`36dc3137`) |
| B2 | progress_bar/status disputados por derivadas x carga (barra infinita travada) | flag `_data_load_busy` + guardas bidirecionais | **CORRIGIDO** (`6e3e0315`) |
| B3 | Filtro clobberava busy state da carga (reabilitava botoes/escondia progress) | `set_idle`/`set_cleanup` consultam `_data_load_busy` | **CORRIGIDO** (`6e3e0315`) |
| B4 | `closeEvent`  ->  janela zumbi (worker pendurado = nunca fecha) | Prazo de 30s em tentativas repetidas, sem fechamento automatico. Nova operacao Qt ou thread de derivadas recebe prazo proprio (N11); flag e timers permanecem coerentes no adiamento/fechamento forcado (N7). | **CORRIGIDO** nesta rodada; ver mapa G |
| B5 | `launch_streamlit` usava `project_root` em vez de `active_runtime_root` | verificado: o parametro localiza `dev_env/streamlit_app.py` (codigo fonte) e `log_root` ja recebe o runtime root | **NAO-BUG** |
| B6 | Fallback GUI -> CLI sem checar interatividade (loop sem input em headless/SSH) | `_fallback_gui_to_cli()` so invoca CLI com `sys.stdin.isatty()`; senao `sys.exit(1)`; teste novo cobre o ramo | **CORRIGIDO** (`9b3f9be0`) |
| B7 | `logs/` criado no CWD em import-time; 5 modulos de producao com logger em nivel de modulo | `log_dir` relativo ancora em `SSA_RUNTIME_ROOT` (fallback: raiz do pacote); falha de escrita degrada para console em vez de ImportError | **CORRIGIDO** (`22ccae16`, `617b9d72`) |
| B8 | `worker.start()` sem try no data loader  -  busy state preso | try/except + rollback completo do estado | **CORRIGIDO** (`6e3e0315`) |
| B9 | "Sucesso fantasma": excecao fora da tupla de `run()` nao emitia `error_occurred` | catch-all em `data_loader_worker.py` emitindo `error_occurred` seguro | **CORRIGIDO** (`6e3e0315`) |
| B10 | `queued=True`/`staged=N` mesmo quando rescan ja ativo | `rescan_data()` retorna bool; callers usam o retorno real | **CORRIGIDO** (`6d6567c3`) |
| B11 | Reload pos-import falho deixava status de sucesso com dados stale | catch de falha de `load_data()`  ->  status "Use 'Recarregar Dados'" | **CORRIGIDO** (`6e3e0315`) |
| B12 | `api_button` ("Carregar XLSX") nunca desabilitado durante carga | incluido no grupo busy | **CORRIGIDO** (`6e3e0315`) |
| B13 | Salvar filtro alterava flags e conteudo sem aplicar | Flags restauradas em finally; conteudo restaurado por deepcopy em N13 | **CORRIGIDO** (`6e3e0315`, `ca542fb5`) |
| B14 | Contrato `result` divergente: `no_changes`/rejeicao-only retornavam True | `result=False` para `no_regular_import_candidates` e `deterministic_rejections_only`; consumidores roteiam para banners informativos | **CORRIGIDO** (`2db1b913`) |

## C. Classe Sanitizacao ASCII (achado "Cpia")

| # | Problema | Correcao | Estado |
|---|---|---|---|
| C1 | `sanitize_ascii_text` apagava caracteres (entrada `C\u00f3pia`, saida `Cpia`); log divergia do relatorio JSON | NFKD remove marcas combinantes: `C\u00f3pia` vira `Copia`; mensagens comuns ficam legiveis. Tracebacks tambem tratados em `1ef9edaf` (C2). | **CORRIGIDO** (`a677f4c7`) |
| C2 | Sanitizacao de `record.exc_text` acontecia antes de o texto existir | O filtro prepara o traceback e translitera; JSONFormatter reutiliza o texto preparado. Ensaio confirmou tipo, pilha e mensagem legivel nos dois formatos. | **CORRIGIDO** nesta rodada; sem refatoracao ampla |
| C3 | 149 literais nao-ASCII em producao: (a) aliases de coluna = dado real das planilhas; (b) textos CLI; (c) logs auto-mutilados; (d) fallbacks legados; (e) simbolos UI | categoria (c) resolvida por C1; (a)/(d)/(e) corretos por design; (b) textos CLI acentuados mantidos  -  conformidade plena nao aplicada | **PARCIAL** |

## D. Prioridade BAIXA (auditoria original)

| # | Problema | Estado |
|---|---|
| D1 | Cancelamento do RescanWorker so consultado entre arquivos (lento em Excel grande) | **NAO CORRIGIDO**  -  impacto baixo, granularidade exigiria hooks dentro do parser |
| D2 | `verify_ssl=False` em remote_itaipu | **NAO-BUG**  -  default `True`; opcao de diagnostico documentada |
| D3 | Fallback por basename no cache de arquivos  -  colisao entre diretorios com mesmo nome | **CORRIGIDO** (`77e45ac2`)  -  hit por basename legado obriga comparacao de hash; fast-path so para chave canonica |
| D4 | Modal "Nenhum dado carregado para filtrar" durante carga inicial | **CORRIGIDO** (`6e3e0315`)  -  guarda `_data_load_busy` antes do QMessageBox |
| D5 | `update_derivadas_button = None` permanente; `_open_url_in_browser` e `resolve_uv_version_text` mortos em producao | **NAO CORRIGIDO**  -  codigo morto cosmetico; remocao nao e fix de bug |
| D6 | `_use_optimized_mode` global sem lock | **NAO-BUG**  -  so alternado no caminho CLI de `main()` (set/reset em finally); GUI e CLI nao coexistem no processo |
| D7 | Grupo de pendencias de feedback/usabilidade do zcode | **PARCIAL**: corrigidos prompt antes da guarda, status de importacao explicita, retorno da exportacao de lista, aviso de tabela anterior apos erro e status do guia. Demais itens historicos nao foram revalidados individualmente; ver inventario residual. |

## E. Achados pos-review (zcode + varredura propria)

| # | Problema | Correcao | Estado |
|---|---|---|---|
| N1 | closeEvent com auto-retry `QTimer.singleShot(500, self.close)`  -  X acidental fechava a janela sozinho, sem cancelar | auto-retry removido; deadline 30s so vale para tentativas repetidas do usuario | **CORRIGIDO** (`9e6bce8e`) |
| N2 | `SSA_DB_PATH` fora do project_root: `ensure_path_is_allowed` recusaria o caminho no CLI | `extra_allowed_roots` propagado (espelhando `rescan_worker.py`); bug colateral encontrado: filtro por assinatura removia todos kwargs de callables com `**kwargs`  ->  agora `VAR_KEYWORD` desativa o filtro; teste novo cobre | **CORRIGIDO** (`6c32dffd`) |
| N3 | Mensagens de 16 commits ainda possuem `Co-Authored-By: Devin` | Autor/email humanos foram normalizados, mas o texto de coautoria permaneceu. A regra do mantenedor proibe esses creditos. Remocao em commits publicados exige reescrita autorizada especificamente. | **PARCIAL**: AGENTS.md e hooks ativos; CI publicada em c49dbac7; 16 mensagens antigas permanecem; regra nativa completa indisponivel nos planos atuais |
| N4 | `log_dir` ancorado na raiz do pacote  -  read-only em build PyInstaller | prefere `SSA_RUNTIME_ROOT`; teste novo cobre os dois ramos | **CORRIGIDO** (`617b9d72`) |
| N5 | **5 sites adicionais** de `worker.start()` desprotegido com estado persistente (mesma classe do B8): filter worker, adv options, list export, PAI API, derivadas sync | rollback cirurgico em cada um: limpa flag/worker registrado e reporta erro | **CORRIGIDO** (`b17fafcf`) |
| N6 | **5 sites** de `blockSignals(True)`  ->  chamada falivel  ->  `blockSignals(False)` sem `finally`  -  excecao deixava widget permanentemente mudo (input de filtro, paginator, tab bar de derivadas, spinbox de page size) | `try/finally` no padrao do `_blocked_widget_signals` existente | **CORRIGIDO** (`6882882f`) |
| N7 | **`_is_shutting_down` ficava True para sempre apos fechamento adiado**  -  `shutdown()` setava o flag, retornava False (workers ativos), janela continuava aberta mas o flag bloqueava silenciosamente filtros, carga de dados, PAI API, finalize de derivadas e refresh de adv options ate reiniciar | closeEvent centraliza a flag e os timers. Adiamento agora aguarda flush sem parar a fila de preferencias; novos snapshots continuam aceitos. O escritor so recebe shutdown ao aceitar o fechamento. Menus refletem a retomada. Testes existentes e ensaio com thread real confirmam o fluxo. | **CORRIGIDO** nesta rodada; ver mapa G |
| N8 | **[P1] Resultado de validacao de banco alternativo expirado selecionava o banco errado**  -  `_work` escrevia `_other_db_validation_pending_result` sem identidade do pedido; A expira (120s), usuario inicia B, resultado atrasado de A era consumido pelo poll de B e aplicava `DB_PATH = A` | Resultado local a cada chamada, com `_request_id` preservado ate o finalizador. Poll antigo termina sem tocar o estado do pedido atual; A atrasado nao substitui o resultado pronto de B. Ensaio com ordem B-completa/A-atrasada confirmou entrega unica de B. | **CORRIGIDO** nesta rodada; ver mapa G |
| N9 | **[P1] Callbacks tardios acessavam widgets destruidos apos fechamento forcado**  -  `WA_DeleteOnClose` destroi widgets ao aceitar; workers retidos continuavam emitindo para slots que acessam `self.*`/`window.*`  ->  `RuntimeError: wrapped C/C++ object deleted` (reproduzido pelo revisor e reproduzido na suite: `_on_ready` de adv options abortava o pytest) | dupla camada: (a) fechamento forcado desconecta sinais de todos os workers pendentes; (b) guarda `sip.isdeleted` nos slots que tocam a janela  -  `_connect_signal`/`_connect_filter_signal` ganharam `window=`, closures `_on_ready`/`_on_error`/`_on_finished` de adv options, partials do PAI API (`_finish_*`, `_release_worker`, `_run_auto_refresh_timeout`, progress/preview), `_on_error` de list export, callbacks de rescan (`on_finished_successfully`, `on_batch_completed`, `on_error`, `on_cancel_requested`), handlers do data loader | **CORRIGIDO** (`ca542fb5`) |
| N10 | **[P2] Gate de reparo liberava banco somente-leitura**  -  `repair_database_if_needed` retornava True para "so inconsistencia de dados" sem consultar `file_permissions_ok`; escrita real falhava depois com `attempt to write a readonly database` | permissao volta a ser bloqueante no reparo (antes do ramo de inconsistencias) e `file_permissions_ok` entrou no conjunto estrutural do gate de promocao; teste novo com report readonly+inconsistente | **CORRIGIDO** (`4ed62185`) |
| N11 | **`_shutdown_started_at` nunca era resetado**  -  X ignorado as 10h, operacao nova as 17h, X seguinte  ->  elapsed>30s  ->  fechamento forcado imediato no 1o clique do novo episodio | Comparacao inclui Qt e derivadas, com referencias retidas. Conjunto novo disjunto reinicia o prazo inclusive quando a tentativa anterior aguardava apenas preferencias e tinha conjunto vazio. Ensaios confirmaram prazo novo Qt/derivadas e fechamento da mesma operacao apos 31s. | **CORRIGIDO** nesta rodada; ver mapa G |
| N12 | **Residuo N5 (derivadas)**: rollback de `worker.start()` liberava estado logico mas deixava barra indeterminada, status "Atualizando derivadas" e botao desabilitado | falha de start passa por `finalize_result`, que restaura UI pelo mesmo caminho de uma falha em andamento; teste novo verifica finalize chamado | **CORRIGIDO** (`e7a94672`) |
| N13 | **Residuo B13**: `save_current` restaurava flags mas nao o conteudo de `_advanced_filters`  -  cancelar salvamento deixava filtro divergente ativo | `copy.deepcopy` do dict antes do `store_only` e restore no `finally`; teste de regressao | **CORRIGIDO** (`ca542fb5`) |
| N14 | **Vacuum**: `_vacuum_analyze_running=True` ficava preso se `thread.start()` falhasse  -  minha classificacao anterior ("threading.Thread novo e inerte") estava errada: CPython levanta `RuntimeError("can't start new thread")` em falha de recurso | try/except + rollback de flag/thread/status, mesmo padrao do worker de validacao | **CORRIGIDO** (`ca542fb5`) |
| N15 | **Wiring perdido**: `refresh_data_from_api` completo sem nenhum caller GUI | acao "Atualizar dados agora" adicionada ao menu SAM API (`_add_pai_api_menu`); teste de contrato de menu atualizado | **CORRIGIDO** (`ca542fb5`) |
| N16 | **ty**: 2 diagnosticos novos (inferencia de `roots` em `main.py`; `SimpleNamespace` vs `argparse.Namespace` no teste) | anotacao `list[str]` e `argparse.Namespace` | **CORRIGIDO** (`ca542fb5`) |

Erro adicional de ty em `_fake_apply` corrigido no teste existente com `patch.object(..., autospec=True, side_effect=...)`, substituindo a atribuicao direta de assinatura incompativel. O caso existente passou. ty passou nos 22 arquivos Python alterados/novos desta entrega; diagnosticos globais anteriores nao foram revalidados.

## F. Resultados anteriores de varreduras (escopo limitado)

| Classe | Resultado |
|---|---|
| `worker.start()` restantes (prefs writer, launcher stderr pump, `qt_thread_shim`) | sem flag persistente relevante; **vacuum NAO era inerte**  -  corrigido em N14 |
| `subprocess.Popen` (`system_integration.py:163`) | **NAO e morto**  -  alcancavel via guia de instalacao (`main_window_system_controller.open_local_path`  ->  `open_local_path_non_blocking`); claim anterior incorreto |
| `BEGIN`/`BEGIN IMMEDIATE` sem rollback (5 sites) | todos dentro de `get_db_connection`, que faz rollback em excecao e fecha no finally |
| `lock.acquire()` fora de `with` | nenhum |
| `os.environ`/`os.chdir` mutacao | nenhum em producao |
| `worker.wait()` bloqueante | bounded + fallback de retencao (`gui_workers.py:672`) |
| `setEnabled(False)` orfao | todos restaurados por maquinas de estado (filter bar, rescan dialog, paginator) |
| `bare except`/`eval`/`exec`/`os.system`/`shell=True` | ausentes no codigo da aplicacao |
| Identificadores SQL | validados/escapados (`is_valid_identifier`, `_quote_identifier`) |
| `FilterCache` | deep copy + lock + limites de bytes |
| Claims do zcode "4 itens prioritarios faltando" | **falso positivo de escopo**  -  estavam nos commits da base do range revisado |

## F2. Alcance de funcoes e compatibilidade

Ausencia de consumidor interno nao comprova funcao removivel ou perda por refatoracao. Esta rodada mantem as APIs e acrescenta exportacao, conforme pedido do mantenedor.

| Familia | Situacao verificada |
|---|---|
| `refresh_data_from_api` | Acao manual ligada ao menu SAM API em N15. |
| `export_reconciliation_csv` / `export_report_json` | APIs preservadas; stdout JSON ja existe. Opcoes CLI/GUI JSON, CSV e TSV implementadas; export_reconciliation_tsv acrescentada. Ver runbook e secao I. |
| `utils/remote_itaipu.py` | Vivo: import dinamico no Streamlit, acessivel por --streamlit/--web. |
| `open_local_path_non_blocking` | Vivo: guia de instalacao e menus de pastas. Popen tem tratamento nos chamadores. |
| `utils/enhanced_importer.py` | Consumo identificado somente em testes; nao importado pelo Streamlit atual. |
| `clear_filter`, `normalize_numero_ssa*` de database.py | Compatibilidade explicita; preservar contratos. |
| Wrappers de largura/schema/datas, rotacao de banco, versao, cache_manager, file_metadata, reload_required | Parte usada por testes; sem consumidores internos de aplicacao para os membros inventariados. Nao excluir em bloco. |
| Helpers antigos de shutdown, wrappers de resize, `_start_derivadas_sync_ui_state` | Sem consumidor interno identificado; nenhuma remocao autorizada nesta rodada. |

## F3 e F4. Integridade e informacao ao usuario

- F3 corrigido em `0448f5c8`: o gate apos adicionar colunas opcionais exige database_accessible, table_exists, schema_valid, sqlite_integrity_ok e file_permissions_ok. Inconsistencias apenas de dados geram aviso e permitem reimportacao, conforme A5. Ensaio SQLite real confirmou primeira tentativa aceita, repeticao coerente e dados preservados.
- F4 corrigido em `9548f41e`: RescanWorker consome o integrity_report real do ImportOutcome, preserva avisos e issues nao bloqueantes e os entrega ao controlador GUI. O dialogo mantem resultado com ressalvas e detalhes; nao executa nova verificacao nem muda A5. Falha real continua sendo falha.

## G. Mapa commit  ->  itens

| Commit | Itens |
|---|---|
| `36dc3137` | B1 |
| `68b8f369` | A3 |
| `a677f4c7` | C1 |
| `de1be62c` | A1, A6 |
| `9163348c` | A2 |
| `e86fb90a` | A5 (reparo) |
| `2db1b913` | A5 (gates), B14 |
| `77e45ac2` | D3 |
| `6e3e0315` | B2, B3, B8, B9, B11, B12, B13, D4, A7 (parcial) |
| `6d6567c3` | B4 (deadline), B10 |
| `9b3f9be0` | A4, B6 |
| `22ccae16` | B7 (ancora pacote + degrade) |
| `6c32dffd` | N2 (+ fix VAR_KEYWORD) |
| `617b9d72` | N4 |
| `9e6bce8e` | N1, B4 (refinamento UX) |
| `b17fafcf` | N5 |
| `6882882f` | N6 |
| `e701bbf1` | N7 |
| `4ed62185` | N10 |
| `e7a94672` | N12 |
| `ca542fb5` | N8, N9, N11, N13, N14, N15, N16; residuos N8/N11 discriminados acima |
| `c49dbac7` | N3: verificador, hooks, CI e AGENTS.md; sem reescrever mensagens antigas |
| `0448f5c8` | F3 / A5: gate depois do reparo |
| `9548f41e` | F2 exportacoes/API, F4, N7/N8/N11, A7/Z-A15/Z-C1/Z-C5, cinco casos D7 |
| `1ef9edaf` | C2: traceback texto/JSON |

## H. Escopo e limites da rodada atual

- Os testes novos listados nos commits publicados sao evidencia historica, nao testes executados nesta implementacao.
- Os tres destinos estavam em ca542fb5 antes da implementacao e receberam os quatro commits ate 1ef9edaf por push normal. Nao houve reescrita nesta rodada. A simulacao ao final refere-se somente ao historico anterior e nao foi executada.
- Sem reescrita, as 16 mensagens de coautoria continuam presentes; autor humano correto nao remove essas mensagens.
- APIs Python e stdout JSON mantidos. Novas interfaces sao aditivas; CSV/TSV recusam ausencia de reconciliacao em vez de inventar contagens zero.
- Nenhuma exclusao de codigo por inventario AST. A7 e C2 foram corrigidos nesta complementacao; D7 recebeu as correcoes especificadas. C3, D1, D5 e o restante de D7 estao discriminados como nao alterados, sem alegacao de encerramento global.
- Suite completa, novos testes extensos, scans pesados, desempenho comparativo e plataformas nativas ficam para outros modelos, por pedido explicito do mantenedor.
- Laudo anterior: `docs/AUDIT_DECISION_REVIEW_ca542fb5.md`, referente ao commit publicado antes destas mudancas.


## I. Validacao e operacao do resultado atual

### I1. Verificacoes efetivamente executadas

- py_compile, Ruff e ty: 22 arquivos Python alterados/novos aprovados. Ultimos ajustes de polling/autoria rechecados separadamente, tambem aprovados.
- Preferencias/fechamento/validacao de DB: 21 testes existentes selecionados passaram (554 nao selecionados).
- Logs ASCII, guia e CLI de derivadas: 29 testes existentes passaram. Ensaio adicional de traceback confirmou tipo, pilha e mensagem legivel em texto e JSON.
- Controlador de derivadas, menu e persistencia: 33 testes existentes passaram apos os ultimos ajustes.
- Ultima selecao de fechamento/validacao: 18 passed, 547 deselected em 12,32s.
- Os quatro commits passaram pelos hooks py_compile/Ruff; o intervalo ca542fb5..1ef9edaf passou no verificador de autoria antes do push, e cada destino executou o pre-push com sucesso.
- Coordenacao GUI: ultima selecao do agente com 92 testes existentes passou; selecao ampliada anterior com 102 passou. Ha sobreposicao entre selecoes; nao somar como cobertura distinta.
- Ensaios N7/N11: thread real aceitou snapshot 2 apos flush expirado do snapshot 1; gravou [1,2]. Novo Qt/derivadas depois de preferencias recebeu prazo novo; primeiro X ignorado, mesma operacao aceita apos 31s.
- Ensaio N8: A expira, B conclui, A entrega atrasado; somente B e entregue com identidade atual.
- Exportacao: SQLite real/arquivos temporarios na primeira implementacao; revisao complementar confirmou caminhos canonicos de auxiliares e zero exportacao apos invalidacao no segundo dialogo.
- F3: ensaio SQLite real confirmou reparo + inconsistencias de dados na primeira tentativa, controles e repeticao coerente, com dados preservados.
- GUI Qt fora da tela: formatos/avisos e bloqueio/restauracao de acoes conferidos; navegacao/filtros preservados. Nao houve inspecao visual nativa completa ou captura de tela.
- Autoria: identidades humanas aceitas; autor/committer estranhos e mensagens proibidas recusados; hooks instalados exercitados por stdin; tags/notas, refs/replace, nota intermediaria removida, historico raso e Latin-1/CP1252 conferidos em repositorio temporario apagado ao final. Nenhuma ref/objeto do projeto real alterado nos probes.
- ShellCheck, YAML e verificacoes Python do mecanismo de autoria passaram. git diff --check passou.

Nenhum caso de teste novo foi criado. Tres arquivos de testes existentes receberam apenas ajuste de contrato/fixture: menu/status, temporizador enfileirado no controlador e assinatura do callback do filtro. Suite completa, scanners amplos e validacao multiplataforma continuam nao executados nesta rodada por orientacao do mantenedor.

### I2. Uso e limites dos relatorios

```sh
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync --report-json sync.json --report-csv sync.csv --report-tsv sync.tsv
```

JSON preserva o resultado completo. CSV/TSV representam a reconciliacao; na GUI, uma linha por fase db/sheets. Em heal/maintenance sem sincronizacao, CSV/TSV nao sao fabricados: stderr explica a ausencia e o comando retorna 1, com JSON preservado. As exportacoes sao tentadas independentemente; falha de arquivo nao desfaz a sincronizacao ja realizada.

CLI exige --overwrite-reports para substituir arquivo existente. GUI confirma substituicao. APIs mantem overwrite=True para chamadas antigas. Os destinos sao validados contra DB canonico, auxiliares SQLite e fontes. Cada arquivo e preparado em temporario; no modo sem sobrescrita, sua publicacao usa hard link e exige suporte do sistema de arquivos. Falha e explicita, sem sobrescrever o destino.

GUI: Database > Exportar relatorio de derivadas..., depois de concluir Atualizar derivadas no banco atual. Troca de banco, nova sincronizacao ou falha invalidam o resultado anterior. Exportar nao repete a sincronizacao. Mais detalhes em DERIVADAS_SYNC_RUNBOOK.md.

### I3. Autoria executavel e limites online

`commit-msg` verifica a identidade efetiva de autor e committer, inclusive overrides por ambiente/--author, e a mensagem. `pre-push` verifica os commits novos de cada atualizacao, tags anotadas e blobs de notas do historico enviado. A regra protege os tres destinos usados por este checkout; preserva o verificador anterior de tamanho.

Nomes humanos com/sem acento sao normalizados para conferencia, sem alterar configuracao. Emails humanos reconhecidos: mauriciomenon@users.noreply.github.com, 54405514+mauriciomenon@users.noreply.github.com e mauricio.menon@gmail.com. GIT_NO_REPLACE_OBJECTS impede inspecionar objeto substituto; historico raso nao e aceito como verificacao completa; encoding da mensagem e respeitado.

Instalacao realizada com `bash scripts/install_hooks.sh --authorship-only`. Os hooks Lefthook pre-commit/prepare-commit-msg e post-commit existente foram preservados byte a byte, com conferencia SHA256. O post-commit existente referencia um executavel Qoder ausente neste host; nao foram encontradas refs/notes no repositorio. Nenhum credito novo foi acrescentado.

Os arquivos de CI foram publicados em `c49dbac7`; nao ha execucao remota comprovada nesta rodada. Os gatilhos existentes foram preservados: GitHub push/PR para main/dev e manual; GitLab MR/default/manual. Nao cobrem todo push em qualquer ref. A CI depende de protecao obrigatoria para impedir integracao e nao recusa sozinho o recebimento de um push. Hooks locais sao contornaveis; regras por email conferem metadados, nao identidade criptografica.

| Destino correto | Estado observado na consulta | Bloqueio nativo solicitado |
|---|---|---|
| GitHub mauriciomenon/SSA_Consulta_Rapida | Publico pessoal; ruleset Copilot_review existente | Restricoes de metadados exigem Enterprise em organizacao |
| GitHub schottge-menon/ssa_consulta_rapida_pyqt6 | Privado pessoal; sem rulesets aplicaveis no estado consultado | Limites de plano/tipo; metadados exigem Enterprise em organizacao |
| GitLab mauricio.menon/ssa_consulta_rapida_pyqt6, projeto 84352011 | Namespace pessoal Free, Owner; push_rule retorna 404 | Push rules exigem Premium/Ultimate |

Fontes oficiais: [GitHub, metadados](https://docs.github.com/en/enterprise-cloud%40latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions), [GitLab, push rules](https://docs.gitlab.com/user/project/repository/push_rules/), [Git, hooks](https://git-scm.com/docs/githooks).

Nenhum plano foi comprado, repositorio transferido, protecao online alterada ou DCO exigido. O bloqueio nativo completo permanece nao entregue nos planos atuais. A CI e os hooks sao medidas concretas adicionais, com alcance discriminado.

### I4. O que permanece sem alteracao

- Mensagens de 16 commits publicados ainda contem credito Devin. Autor e committer desses commits sao humanos. Corrigir mensagens exige novos hashes e atualizacao coordenada dos tres destinos; nao e uma mudanca de configuracao de identidade.
- Codigo e CI foram commitados e publicados. Execucao remota de CI nao foi comprovada; o push simples desta branch nao aciona os fluxos minimal-ci/GitLab preservados. Estado final de documentos e workspace deve ser conferido pelo HEAD da entrega, nao pelo antigo ca542fb5.
- D1/BAI-1: granularidade de cancelamento no parser continua entre arquivos. Nao foi implementado cancelamento dentro da leitura de uma planilha.
- C3/ASC-3: aliases/dados e literais antigos nao foram transliterados em massa. Contratos de entrada e APIs foram preservados.
- D5 e inventario F2: nenhuma exclusao em bloco de funcoes publicas, wrappers ou compatibilidade. Ausencia de caller interno nao prova que a API deva ser removida.
- D7: foram corrigidos os cinco casos especificados na matriz. Demais alegacoes da tabela mestre original nao foram revalidadas individualmente; nao estao declaradas corrigidas nem verificadas seguras.
- Suite completa, novos testes dedicados, scans pesados, benchmarks e verificacao nativa em Windows/Linux/macOS ficam para os outros modelos. Nao foram disparados automaticamente.

### I5. Proposta concreta para mensagens publicadas

Escopo historico simulado: somente os 21 commits `e62a85bf..ca542fb5` da branch fix/audit-surgical-fixes. Agora ha descendentes novos; uma eventual execucao autorizada precisaria incluir esses descendentes no mapa de hashes. Remover exclusivamente as linhas de credito/coautoria Devin nas 16 mensagens afetadas; preservar autor/committer humanos, datas, conteudo das arvores, ordem e topologia. Os descendentes tambem mudariam de hash. Preservar os novos commits de implementacao e documentos, e conferir arvores/hash por commit. A simulacao antiga nao e um plano pronto para forcar a ponta atual.

Destinos a atualizar individualmente: mauriciomenon/SSA_Consulta_Rapida, schottge-menon/ssa_consulta_rapida_pyqt6 e mauricio.menon/ssa_consulta_rapida_pyqt6. Conferir o SHA remoto imediatamente antes e usar force-with-lease por destino. Nao alterar dev/main, criar PR/branch ou aplicar merge. Esta proposta nao foi executada.

| Commit com mensagem afetada | Assunto preservado |
|---|---|
| `36dc3137` | fix(core): Preserva erro de checkpoint WAL na ultima tentativa |
| `68b8f369` | fix(core): Reconhece promocao de candidato sem backup pre-existente |
| `a677f4c7` | fix(log): Translitera acentos no filtro ASCII em vez de deletar |
| `de1be62c` | fix(gui): Destrava validacao de banco alternativo e recarrega derivadas |
| `9163348c` | fix(gui): Impede modo full-rescan em importacao explicita batelada |
| `e86fb90a` | fix(db): Reparo nao bloqueia reimportacao por inconsistencia de dados |
| `2db1b913` | fix(core): Separa gate estrutural e unifica contrato result |
| `77e45ac2` | fix(cache): Hit por basename legado nao usa fast-path sem hash |
| `6e3e0315` | fix(gui): Coordena carga de dados com filtros, derivadas e rescan |
| `6d6567c3` | fix(gui): Deadline de shutdown e queued honesto no import |
| `9b3f9be0` | fix(main): Propaga caminho do banco e restringe fallback CLI a tty |
| `22ccae16` | fix(log): log_dir ancorado no pacote e degradacao para console |
| `6c32dffd` | Propaga extra_allowed_roots para SSA_DB_PATH externo no CLI |
| `617b9d72` | Ancora log_dir relativo no SSA_RUNTIME_ROOT |
| `9e6bce8e` | Remove auto-fechamento agendado no closeEvent |
| `b17fafcf` | Adiciona rollback em worker.start() com estado persistente |

Diff reproduzivel do codigo: `git diff ca542fb5..1ef9edaf`. Relatorio, laudo, backlog e passagem desta rodada passam a ser versionados nominalmente junto dos guias; as regras gerais de ignore permanecem. O artefato local `AUDIT_IMPLEMENTATION_DIFF.patch.md` e apenas uma copia de consulta e nao substitui o diff Git. Backups de configuracao em /tmp/ssa-gitignore-20260912-224336.bak e /tmp/ssa-authorship-*.20260913T020510698364Z.bak.


### I6. Antes/depois dos hashes propostos, somente simulacao

Simulacao anterior aos quatro commits desta rodada: hashes calculados com git hash-object SEM -w. A simulacao nao gravou objetos nem refs; os commits de implementacao foram criados posteriormente por git commit normal. Autor, committer, datas, arvores e mensagens restantes preservados; somente 32 linhas de credito removidas de 16 mensagens, mais os pais atualizados dos descendentes. Os commits posteriores nao integram esta simulacao.

| Hash publicado | Hash proposto | Arvore preservada | Linhas de credito removidas |
|---|---|---|---|
| `36dc3137bf55c8a2574a7f1437ef4d904d9fd269` | `3219f3f8b375e00c0317ad6ee11304c1a42db13a` | `28d2138748ec7b95cf194bc42f6c8137a408bdac` | 2 |
| `68b8f36934089b934baf6461d398a983e18436a8` | `b90330b297b173d47a36a5eefd8e5805aa50386f` | `38c8a6960ad014243c8debe296ec985719c84e18` | 2 |
| `a677f4c7fbfc4032e989f1154e6892afbe4235fe` | `21640d3062a6e1309d9e97a2550ea9c5536029bc` | `70471b02c1bfc66a4ba9ba9a5ecbc03757ffc9b1` | 2 |
| `de1be62c039dbe2fbf3d9b00785061221e0ea3da` | `58cbf0511b6520deccdbf4114077be510c80cf03` | `93fdb34f1de29def925922d1334339193f4f79d1` | 2 |
| `9163348cecb41a99138a8f4d4afcc91d0acd7184` | `3a6b2c475be859cf14874df7eb4ffb24afcb029c` | `a5b667a9a4f8b30cda3d60bc3dfa768ae80b56e7` | 2 |
| `e86fb90a2d0d4d67eb4b118f53be6cfe86e83279` | `78dce9964267b0e393425fa0093feaa5aa151cad` | `85804829e14bf3808dc21933dda3b4cd03d09f2b` | 2 |
| `2db1b9131314a50070a5f2a2a06f715a18ec99bc` | `237f48b39dfc6cc00001cee3d41cf2343369fac0` | `1104324248918041466c3bd60cab8de98027a987` | 2 |
| `77e45ac269e0029e3984128ecc6d61a2df1ed48e` | `d263f069ab57cf00a8abd1295f3d1bf017d44ea4` | `20600ed7c3b469d3bfe91102a6044a901cd017e6` | 2 |
| `6e3e03154d08717047dd05981ccb761b94613e95` | `a28c182cd7c0bef4571532f488ec5fdfe2bf5478` | `0b083f3278a7e7090f03a0de2921c70b0ecb9f9d` | 2 |
| `6d6567c3fc8ff8835458a73ff80c7c8232ceab13` | `72c8777b623b7572ad661d67b3f11344554f7205` | `369765c39f98dab58f389574f27dcb61e3e96164` | 2 |
| `9b3f9be07eaf8b64645834b0163e07e0564b7775` | `27fd9d3ed0fe492697a0d38e9fb45afba0dbe434` | `fd1243b0bfc58e75ab7a6f53387e537f386f6ddf` | 2 |
| `22ccae16d9c3049ec8cd35b505592119ab0e4fc8` | `896965c143a290421c1e02ea88c41ff77832f16f` | `6afa361fb7ee475e7a5df014cbbb8ee2f417980f` | 2 |
| `6c32dffd2c1190cc5ef103117ee32781bd48ad37` | `a1a259992c77926d44f1144dcaf051bf5c608d3f` | `988d6614b9d88a71b34a61684d49085d537bea7a` | 2 |
| `617b9d72195476cf7bb5aac5be5940f1b44cf2e9` | `c2dbc0b66623d894fad0771e1eefc6dc94a6ed51` | `92e5f0a13a94d69cb8157052900558cd78fe798b` | 2 |
| `9e6bce8ef51c5ee846ce72e1af435fe4d51961f6` | `991ca3398ff997f18f5a6dd7e5a24d42b852f75e` | `1dea903e7882f8da3f9384be53ab82fc1ce7b33a` | 2 |
| `b17fafcffc72d1090f8ef0c3e29bdfbfe415a696` | `177102697db886c617dc36205e62823c99d2b39a` | `d0f0eb699ac2ad37153acc601dcc3baa95bbfeb6` | 2 |
| `6882882fd697cfd1a678ebd7bfbcea45713ec41d` | `d684e5bb9eaf32471b706f28cdb5138d071e58db` | `08f5ae7a903faa517778dedcf8747f9ada38c2fd` | 0 |
| `e701bbf1be95ca978672eff89f1142305e2168c0` | `0c3f4ce01f3fbbf3d77fe0a6da9d77da4a55b72a` | `2077a15733daa6ad9ef18e9f1f36a047f4ef5339` | 0 |
| `4ed62185d54f6315c103a528e9fb6a5232266e50` | `3f7c303ebf3ca5068c96bc332c804e48d334e544` | `0f5d4b6e6f53cdecbe1bf41ce1e3ec03a3c56e42` | 0 |
| `e7a9467296ba56975ac8ed291ddbe7ecd0898ef2` | `1a6831e290b5d14e9d5bb1b98cc750ca0ef0248c` | `f9a1b312359d8ee6cdd3eaefc19cb6b135b9770c` | 0 |
| `ca542fb535b604575666f50aeb37d125c1324dc3` | `172e11bb7ae32261c2edcb95231930c420ca76af` | `b6a60abff864c08da9e5b46e99f95082d94023ba` | 0 |

Ponta que a simulacao antiga produziria: `172e11bb7ae32261c2edcb95231930c420ca76af`, correspondente apenas a `ca542fb5` reescrito. Nao representa o codigo novo nem a ponta atual. Nenhuma reescrita foi realizada; novos commits foram publicados por push normal. Continua necessaria autorizacao especifica para alterar mensagens antigas e reescrever seus descendentes.


### I7. Entrega e proxima atividade

Codigo publicado nos tres destinos por push normal ate 1ef9edaf. A identidade
dos novos commits e Mauricio Menon <mauriciomenon@users.noreply.github.com>,
sem credito de ferramentas. Nao houve branch nova, PR, merge nem reescrita.

A passagem executavel para o outro modelo esta em [VALIDATION_PLAN.md](VALIDATION_PLAN.md).
Ela inclui os quatro hashes completos, comandos, matriz de regressao, scanners,
plataformas e formato obrigatorio do laudo. O backlog foi reconciliado com os
itens realmente corrigidos; as alegacoes historicas permanecem identificadas.

O servidor GitHub exibiu avisos de dependencias na branch padrao durante o push:
45 alertas no repositorio mauriciomenon e 5 no schottge. Esses numeros sao avisos
do servidor, nao resultados de pip-audit deste patch; triagem na rodada pesada.
Nao foi feita atualizacao de dependencias fora do escopo.

Proxima atividade: executar a passagem no HEAD recebido e entregar evidencia
de suite completa, scans e uso nativo. Isso permanece separado da implementacao
por pedido do mantenedor, sem declarar validacao ainda nao realizada.
