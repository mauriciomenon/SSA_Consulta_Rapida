# Relatorio de Correcoes  -  Auditoria SSA Consulta Rapida

## Leitura e escopo

As secoes datadas preservam o estado das respectivas rodadas, incluindo falhas
e limites. Seus pedidos de proxima atividade nao sao autorizacoes permanentes.
Para entregas de binarios, seguir [o procedimento de builds](BUILD_WINDOWS_ARM64_AMD64.md);
este historico nao acrescenta novos requisitos nem exige recompilar por docs.

**Branch:** `fix/audit-surgical-fixes`. A primeira entrega foi publicada nos tres destinos em `0beceb58` (codigo ate `1ef9edaf`), seguida da correcao de fixture em `39e7c16a`. A rodada K parte de `39e7c16a`; seu codigo foi publicado ate `0f239dac`, com documentacao em `c30f87da`. A rodada A-E da secao L parte de `c30f87da`; seu fechamento e registrado em L4. Obtenha o HEAD com `git rev-parse HEAD`. Base da implementacao: `ca542fb5`; base da auditoria historica: `dev` em `e62a85bf`.
**Historico anterior:** `e62a85bf..ca542fb5` contem 21 commits; o intervalo exclusivo `36dc3137..ca542fb5` tem 20. A reescrita anterior preservou 12 hashes e alterou 9, com arvores equivalentes. A primeira implementacao acrescentou quatro commits de codigo e um documental, sem reescrever ancestrais; `39e7c16a` ajustou a preparacao de um teste e a passagem.
**Validacao historica anterior a 0beceb58:** 2924 passed, 9 skipped. Revisao independente: 83 aprovacoes focadas; py_compile/Ruff passaram; ty falhou (um erro novo no teste, outros diagnosticos fora do patch); Semgrep parcial por dois timeouts.
**Resultado da rodada A-E:** cinco residuos corrigidos em seis arquivos de producao. Reteste completo em `5b75f8f8`: **2969 passed, 9 skipped, 34 warnings, 11 subtests passed em 706,03s**, retorno 0. A primeira execucao falhou em quatro variantes de uma fixture; a correcao e os dois resultados estao separados em L4.

**Resultado historico da rodada K, em 13/09/2026:** oito falhas de estado reproduzidas localmente e corrigidas em preferencias, SAM API, derivadas, reescaneamento, compactacao e banco alternativo; detalhes na secao K. Passaram 83 testes dos controladores e uma selecao de 47 casos, com sobreposicao. Suite completa aprovada: **2938 passed, 9 skipped, 34 warnings, 11 subtests passed em 701,80s**, no codigo de `0f239dac`. Os onze Python ficaram inalterados durante a execucao. Revisao CodeRabbit e complemento local detalhados em K3. Os placares de zcode/Devin e o ajuste de fixture pertencem a rodada anterior, preservada na secao J. Hooks ativos e CI versionada; as 16 mensagens antigas com credito proibido permanecem sem reescrita autorizada.

**Rodada A-E concluida:** os cinco residuos do levantamento posterior foram reproduzidos e receberam correcoes locais. Isso amplia a cobertura dos sites S1-S8; nao transforma a suite historica em aprovacao do diff atual. Antes/depois e evidencias em L; validacao integrada, commits e publicacao em L4.

**Rodada vigente CI/CD:** parte de `b9672334`, sem alterar codigo da aplicacao.
Corrige parser/diagnosticos dos gates, agenda GitLab em branches fix e torna a
suite completa bloqueante, com artefatos de diagnostico. O resumo e o estado
da PR estao na secao M. As referencias anteriores a GitLab manual e ausencia
de pipeline nesta branch descrevem os commits anteriores a esta rodada.

Legenda de estado: **IMPLEMENTADO** (correcao no codigo; validacao/publicacao discriminadas em L4) | **CORRIGIDO** (codigo commitado e publicado; a evidencia de validacao e discriminada por rodada) | **PARCIAL** | **NAO CORRIGIDO** (justificativa) | **NAO-BUG** (verificado, sem alteracao)


## Comparativo antes/depois e estado por pedido

Esta tabela registra pedidos e entregas historicas ate K. A rodada A-E possui comparativo proprio em L2; CI/CD e PR estao na secao M. As tabelas A-K preservam evidencias por revisao; suas expressoes "nesta rodada" referem-se a entrega historica descrita, sem aprovar alteracoes posteriores.

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
| Sites S1-S8: reteste e estabilizacao de estado | zcode informou suite reprovada em 0beceb58; ajuste de fixture publicado em 39e7c16a | Pedido posterior autorizou reproducao com modelo externo e fallback local. A chamada externa falhou; oito falhas reais receberam correcao e regressao focada | ENTREGUE: SUITE LOCAL APROVADA; ver K |
| Residuos A-E apos c30f87da | Levantamento apontou preparacao de rescan/filtro, termino do escritor, entrega de carga e finalizadores ainda expostos | Correcao localizada e reproducao discriminadas em L2-L3 | CORRIGIDO; VALIDADO em L4 |
| Teste de fechamento forcado | Timestamp vencido sem identidade da operacao; teste falhava | Preparacao registra o mesmo worker em _shutdown_pending_operations; aceitacao e desconexao continuam exigidas | CORRIGIDO E VALIDADO LOCALMENTE |

Evidencias de codigo: `gui/gui_ssa.py` (validacao/fechamento), `gui/ssa/gui_preferences_persistence.py` (fila), `gui/ssa/app_menus.py` e controladores (coordenacao), `armazenamento/database_integrity.py` (F3), `gui/workers/rescan_worker.py` e `gui/ssa/gui_rescan_lifecycle.py` (F4), `scripts/derivadas_cli.py`/`armazenamento/derivadas_sync.py` (exportacao), `scripts/validate_git_authorship.py` (regra executavel).


---

## A. Prioridade ALTA (auditoria original)

| # | Problema | Evidencia original | Correcao | Estado |
|---|---|---|---|---|
| A1 | `_other_db_validation_running` fica preso para sempre se `_work` lanca ou `start()` falha; sem timeout | `gui/gui_ssa.py` validacao de DB alternativo | Tratamentos e prazo de 120s preservados. Cada pedido agora possui resultado em closure propria; entregas atrasadas nao sobrescrevem o pedido atual (N8). | **CORRIGIDO** nesta rodada; ver mapa G |
| A2 | Rescan multi-batched promovia candidato contendo so o batch 1 sobre o DB primario | `gui/workers/rescan_worker.py` `force_import` so no batch 1 | `force_import=False` em todos os batches explicitos; restaurado no `finally` | **CORRIGIDO** (`9163348c`) |
| A3 | `actually_changed=False` no 1o full rescan (sem backup pre-existente)  -  GUI nao recarregava | `core/app_logic.py`, `core/import_database_rotation.py` | promocao reconhecida via `working_db_path == primary_db_path` | **CORRIGIDO** (`68b8f369`) |
| A4 | `SSA_DB_PATH` era lida pela interface mas ignorada pela importacao CLI | `main.py` defaults `data/ssas.db` | `db_path`/`table_name` propagados ao importer; `docs_dir` ancorado no runtime root | **CORRIGIDO** (`9b3f9be0`, `6c32dffd`) |
| A5 | Deadlock operacional: inconsistencia de DADOS (`situacao` fora do catalogo, duplicado) bloqueava justamente a reimportacao que a corrigia | `armazenamento/database_integrity.py`, gates em `app_logic.py` | Politica adotada: "inconsistencia de dados != corrupcao". SQLite, tabela, schema e permissoes continuam bloqueantes; qualidade de dados vira warning e permite reimport. A descricao antiga de disco sempre bloqueante estava incorreta: ha criterios condicionais diferentes entre preparo e promocao, detalhados em M10. Reparo conservador aplica os mesmos criterios estruturais antes e depois de adicionar colunas opcionais; dados inconsistentes permitidos continuam produzindo aviso (F3). | **CORRIGIDO** nesta rodada; ver mapa G |
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
| `worker.start()` restantes (prefs writer, launcher stderr pump, `qt_thread_shim`) | Inspecao anterior limitada ao inicio da thread; nao comprova seguranca de todo o ciclo. A rodada K confirmou falha de persistencia/flush no prefs writer e falha de construtor em derivadas. **vacuum NAO era inerte**, corrigido em N14 |
| `subprocess.Popen` (`system_integration.py:163`) | **NAO e morto**  -  alcancavel via guia de instalacao (`main_window_system_controller.open_local_path`  ->  `open_local_path_non_blocking`); claim anterior incorreto |
| `BEGIN`/`BEGIN IMMEDIATE` sem rollback (5 sites) | todos dentro de `get_db_connection`, que faz rollback em excecao e fecha no finally |
| `lock.acquire()` fora de `with` | nenhum |
| `os.environ`/`os.chdir` mutacao | nenhum em producao |
| `worker.wait()` bloqueante | bounded + fallback de retencao (`gui_workers.py:672`) |
| `setEnabled(False)` orfao | Inspecao historica limitada aos caminhos entao percorridos. O residual B confirmou UI de filtro ocupada apos falha de preparacao; corrigido e reproduzido na rodada L. Nao comprova cobertura de toda a classe de falha |
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

## H. Escopo e limites da primeira implementacao

- Os testes novos listados nos commits publicados sao evidencia historica, nao testes executados nesta implementacao.
- Os tres destinos estavam em ca542fb5 antes da implementacao e receberam os quatro commits ate 1ef9edaf por push normal. Nao houve reescrita nesta rodada. A simulacao ao final refere-se somente ao historico anterior e nao foi executada.
- Sem reescrita, as 16 mensagens de coautoria continuam presentes; autor humano correto nao remove essas mensagens.
- APIs Python e stdout JSON mantidos. Novas interfaces sao aditivas; CSV/TSV recusam ausencia de reconciliacao em vez de inventar contagens zero.
- Nenhuma exclusao de codigo por inventario AST. A7 e C2 foram corrigidos nesta complementacao; D7 recebeu as correcoes especificadas. C3, D1, D5 e o restante de D7 estao discriminados como nao alterados, sem alegacao de encerramento global.
- Suite completa, novos testes extensos, scans pesados, desempenho comparativo e plataformas nativas ficam para outros modelos, por pedido explicito do mantenedor.
- Laudo anterior: `docs/AUDIT_DECISION_REVIEW_ca542fb5.md`, referente ao commit publicado antes destas mudancas.


## I. Validacao e operacao da primeira implementacao

### I1. Verificacoes da primeira implementacao, anteriores aos retornos

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

Nenhum caso de teste novo foi criado. Tres arquivos de testes existentes receberam apenas ajuste de contrato/fixture: menu/status, temporizador enfileirado no controlador e assinatura do callback do filtro. Suite completa, scanners amplos e validacao multiplataforma nao foram executados pelo implementador nessa primeira rodada. Os retornos externos e o complemento estao discriminados na secao J.

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

Diff reproduzivel do codigo: `git diff ca542fb5..1ef9edaf`. Relatorio, laudo, backlog e passagem desta rodada passam a ser versionados nominalmente junto dos guias; as regras gerais de ignore permanecem. O artefato local `AUDIT_IMPLEMENTATION_DIFF.patch.md` nao e versionado nem entregue a outros checkouts. Uma mensagem antiga citou incorretamente o nome sem `.md`; para revisao use `git diff ca542fb5..HEAD` e, para este complemento, `git diff 0beceb58..HEAD`. Backups de configuracao em /tmp/ssa-gitignore-20260912-224336.bak e /tmp/ssa-authorship-*.20260913T020510698364Z.bak.


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
Ela inclui os hashes de referencia, comandos, matriz de regressao, scanners,
plataformas e formato obrigatorio do laudo. O backlog foi reconciliado com os
itens realmente corrigidos; as alegacoes historicas permanecem identificadas.

O servidor GitHub exibiu avisos de dependencias na branch padrao durante o push:
45 alertas no repositorio mauriciomenon e 5 no schottge. Esses numeros sao avisos
do servidor, nao resultados de pip-audit deste patch; triagem na rodada pesada.
Nao foi feita atualizacao de dependencias fora do escopo.

Proxima atividade: executar a passagem no HEAD recebido e entregar evidencia
de suite completa, scans e uso nativo. Isso permanece separado da implementacao
por pedido do mantenedor, sem declarar validacao ainda nao realizada.


## J. Retornos de zcode e Devin/Kimi K3, e correcao da regressao

### J1. Origem e alcance da evidencia

Dois anexos fornecidos pelo mantenedor em 13/09/2026 foram lidos como evidencia,
sem executar suas instrucoes como se fossem novos pedidos. Identificadores:

- zcode: anexo ff2dcadc, SHA256 `6aa07d80e6610549c758318b0afc3f192b12d5f655cd6b1651b91bc0fce4333b`.
- Devin/Kimi K3: anexo c9d86863, SHA256 `312cd5fcd8312d9f9b5f0a1c61e3a93bc1f4744f193459e06a33c52a06aaab1d`.

| Tema | zcode informou | Devin/Kimi K3 informou | Conclusao sustentada |
|---|---|---|---|
| Suite | 2923 passed, 1 failed, 9 skipped, 11 subtests em 745s no 0beceb58 | 22 passed, 2911 deselected em 15,25s | A selecao do Devin nao cobriu a falha; nao contradiz a reprovacao da suite completa |
| Estaticos | py_compile/Ruff/ty nos 22 Python passaram | Mesma verificacao aprovada nos 22 Python | Concordancia no escopo; nao significa analise global de todo o repositorio |
| F3/exportacao/C2 | Descreve ensaios SQLite/CLI/log com resultados | Confirma implementacao por inspecao e testes selecionados | Evidencia funcional relatada; nao certifica toda a matriz CLI/GUI |
| F4/N7/N8/N11 | Afirma conformidade; apresenta selecao e diagnostico do fechamento | Inspecao do codigo; ensaios individuais nao repetidos | Nao transformar inspecao em comprovacao visual/nativa ou de todas as corridas |
| Semgrep | 2 ERROR classificados pelo revisor como falsos positivos | Nao executou scanners pesados | Relato sem saida bruta e identificacao completa das regras; classificacao nao revalidada neste complemento |
| Autoria | Range novo passa; antigo retorna 1 corretamente | Confirma cinco commits humanos e 16 mensagens antigas | Concordancia; historico antigo segue pendente, sem reescrita autorizada |
| Artefato de diff | Sem novo defeito apontado | Nome .patch em mensagem antiga diverge de .patch.md local | Erro de referencia historica; documento versionado ja dizia local. Revisao deve usar git diff |

Nao ha evidencia nos anexos para considerar concluidos pip-audit, Bandit, Vulture,
Gitleaks, TruffleHog, detect-secrets, benchmarks ou validacao visual multiplataforma.
O comentario `nosec B608` citado no laudo, sozinho, nao demonstra que um achado
de outra ferramenta e falso positivo. Registrar regra, arquivo/linha e caminho
de dados antes de aceitar essa classificacao. Nenhuma regra foi suprimida aqui.

### J2. Defeito reproduzido e antes/depois

O teste `test_forced_close_disconnects_pending_workers` criava um worker ativo
e atribuia apenas um timestamp antigo a `_shutdown_started_at`. Desde N11,
`shutdown()` tambem compara a identidade das operacoes pendentes. Um conjunto
anterior vazio com um worker atual representa episodio novo e reinicia o prazo.
Portanto a falha nao era intermitente: a preparacao deixou de representar o
fechamento forcado da mesma operacao que o teste pretendia verificar.

Antes: `1 failed, 564 deselected in 0.69s`, exit 1, reproduzido diretamente
no 0beceb58 em `tests/test_gui_filter_logic.py:14705`.

Depois: acrescentada somente a linha
`self.window._shutdown_pending_operations = (worker,)` antes do timestamp.
As assercoes de aceitacao do evento e `worker.disconnected is True` permanecem.
O codigo de producao e a protecao do prazo novo foram preservados.

Validacao local do complemento:

- py_compile, Ruff e ty em `tests/test_gui_filter_logic.py`: exit 0.
- `QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py -k 'close or shutdown or other_database or candidate'`: **27 passed, 538 deselected in 22.31s**, exit 0.
- A selecao inclui o teste que falhava e `test_shutdown_new_episode_resets_force_deadline`.
- CodeRabbit CLI 0.7.6 autenticada revisou apenas o diff de uma linha no teste: review_completed, 0 issues. O parecer independente confirmou a identidade do mesmo episodio e a preservacao das duas assercoes.
- Nenhum teste novo criado, removido, marcado como skip ou relaxado. O caso usa um duble de worker; nao comprova sozinho callbacks apos destruicao Qt nativa. O ensaio anterior preferencias->worker nao foi apresentado como teste versionado.
- Suite completa nao repetida pelo implementador, conforme a divisao de trabalho
  pedida pelo mantenedor; nao inferir 2924 passed do ajuste de um caso.

### J3. Lacuna corrigida na passagem

O seletor anterior `close_event or shutdown_new_episode or
finalize_database_candidate_validation` nao inclui o nome
`test_forced_close_disconnects_pending_workers`. A selecao de 18 casos realmente
passou, mas nao sustentava cobertura completa do fechamento. O comando foi
alargado para close/shutdown/other_database/candidate, e os dois testes criticos
foram listados por node ID para evitar nova exclusao pelo nome.

A proxima validacao deve usar o HEAD que inclui este complemento. Exigir suite
completa nova e evidencias dos scanners ainda ausentes; manter resultados do
0beceb58 como historico reprovado. Os demais limites da secao I4 permanecem.


## K. Estabilizacao de estado apos 39e7c16a

### K1. Pedido, metodo e tentativa externa

Pedido do mantenedor: reproduzir falhas reais de estado, logica e chamadas
faliveis; tentar um modelo externo via CLI e executar localmente se falhasse.
A autorizacao anterior de corrigir, documentar, comitar e publicar foi mantida.
Nao houve mudanca de politica A5, remocao de API ou refatoracao transversal.

Foi usada a skill external-model-audit-coordinator com um pacote delimitado de
quatro controladores, sem credenciais, bancos, planilhas ou logs de producao.
A verificacao de saida do pacote encontrou zero itens sensiveis em um arquivo
com 65317 bytes; SHA256:
`f7fb07457abf442abf41e700bd5b95cafb2ad039c4a35a03e63e980f170db36d`.

Comando externo efetivamente executado:

```sh
pi --provider opencodex --model cursor/kimi-k3 --thinking high \
  --no-tools --no-session --no-extensions --no-skills \
  --no-prompt-templates --no-context-files --no-themes --no-approve \
  --mode json -p @packet.txt
```

Resultado: 14,39 segundos, processo com exit 0, mas quatro mensagens do modelo
com `stopReason=error` e `Connection error.`. Nenhum parecer valido. O exit 0
nao foi tratado como sucesso. A analise e as reproducoes seguintes sao locais;
nao sao achados atribuidos ao modelo externo.

### K2. Falhas reproduzidas e correcao aplicada

| Caso | Antes, reproduzido em 39e7c16a | Depois | Evidencia de regressao |
|---|---|---|---|
| S1, preferencias/N7 | Gravador aceitava snapshot, mas `flush()` retornava True mesmo com retorno False ou OSError na gravacao. Fechamento podia ser aceito sem persistencia confirmada | Guarda o resultado da ultima gravacao; `flush()` levanta OSError se ela falhou. Termino acorda aguardantes. Nova gravacao bem-sucedida limpa a falha. GUI informa erro, rejeita fechamento e restaura `_is_shutting_down=False` | `test_preferences_writer_reports_unexpected_failure`, `test_preferences_writer_flush_confirms_disk_write_and_later_recovery`, `test_close_event_waits_for_preferences_writer` parametrizado |
| S2, SAM API/callbacks | A parava, B iniciava e um sinal antigo de A mudava status; sucesso antigo ainda provocava reload. Reproducao: referencia B preservada, mas 1 reload indevido | Progresso, preview, pedido de confirmacao, sucesso e erro verificam identidade do worker. Decisao e revalidada depois do dialogo. `finished` antigo nao limpa B | `test_previous_worker_signals_do_not_change_current_operation`; confirma tambem que B continua entregando progresso e sucesso |
| S3, SAM API/inicializacao | Excecao em connect escapava e deixava referencia ativa. Construcao/reset/conexao ficavam fora do tratamento de start | Construcao, reset, registro, conexoes e partida usam o mesmo tratamento. Falha informa status, libera somente a referencia correspondente e permite nova tentativa | `test_refresh_setup_failure_allows_next_attempt`: construtor, reset, connect e start |
| S4, derivadas/inicializacao | Construtor da thread lancava; `state.running` permanecia True com nenhuma thread criada | Criacao e partida compartilham tratamento; `mark_finished()` libera o estado antes do finalizador restaurar a UI. Thread ainda viva permanece retida conforme contrato existente | `test_async_derivadas_start_failure_runs_finalize_to_restore_ui` parametrizado para construtor/start, verificando flag, referencia, lock e estado da UI |
| S5, reescaneamento/callbacks | Sucesso, erro e cancelamento antigos substituiam o status de B por mensagens de A. Nenhum reload indevido nesse caso, mas feedback da operacao atual ficava errado | Publicacao de status exige worker vigente. Dialogo antigo conserva seu encerramento; liberacao de referencias e carga continuam protegidas por identidade | `test_previous_rescan_signals_preserve_current_status_and_references`, incluindo sucesso/erro apos cancelamento e `finished` antigo |
| S6, SAM API/reload | Erro ao recarregar dados escapava do callback, com status ainda dizendo que estava carregando | Falha de reload e registrada e exibida com instrucao para Recarregar dados. Importacao concluida nao e repetida; referencia permanece ate termino nativo | `test_success_reports_reload_failure_without_losing_worker` |
| S7, compactacao/inicializacao | Construtor da thread lancava antes do try e deixava `_vacuum_analyze_running=True` | Criacao e registro entram no tratamento existente de start. Falha libera flag/referencia/menus, informa status e nao agenda polling | `test_database_thread_failure_releases_state_for_next_attempt`, combinacoes de compactacao com construtor/start |
| S8, banco alternativo/inicializacao | Mesmo padrao deixava `_other_db_validation_running=True` depois da falha de construtor | Tratamento existente cobre criacao e start. Estado liberado; nova tentativa recebe nova identidade de validacao | Mesmo teste parametrizado, combinacoes de banco alternativo com construtor/start |

Arquivos de producao: `gui/gui_ssa.py`, `gui/ssa/gui_preferences_persistence.py`,
`gui/ssa/pai_api_controller.py`, `gui/ssa/derivadas_sync_controller.py` e
`gui/ssa/gui_rescan_lifecycle.py`. As reproducoes usam gravador real em thread,
eventos de sincronizacao e dubles dos pontos faliveis; nao consultam SAM real
nem danificam arquivos reais para simular erros.

Referencias do codigo de `0f239dac` (as linhas podem mudar na rodada L):

| Caso | Ponto corrigido |
|---|---|
| S1 | `gui/ssa/gui_preferences_persistence.py:93` e `:109`; `gui/gui_ssa.py:5709` |
| S2 | `gui/ssa/pai_api_controller.py:349`, `:384`, `:399` e `:423` |
| S3 | `gui/ssa/pai_api_controller.py:209` |
| S4 | `gui/ssa/derivadas_sync_controller.py:327` |
| S5 | `gui/ssa/gui_rescan_lifecycle.py:48` |
| S6 | `gui/ssa/pai_api_controller.py:405` |
| S7 | `gui/gui_ssa.py:5029` |
| S8 | `gui/gui_ssa.py:5447` |

### K3. Validacao historica da rodada S1-S8

- py_compile, Ruff e ty: aprovados nos onze arquivos Python alterados.
- Quatro arquivos de testes dos controladores: **83 passed in 0.61s**.
- Selecao conjunta de fechamento, preferencias e concorrencia: **47 passed,
  602 deselected in 29.18s**. Inclui fechamento forcado e prazo por operacao.
- Nao somar esses dois placares: ha casos em comum.
- `tests/test_gui_menu_import_external.py`: **21 passed in 0.26s**, incluindo
  quatro combinacoes de construtor/start em compactacao e banco alternativo.
- Foram acrescentados casos de regressao nos arquivos existentes para omissoes
  confirmadas. Nenhum teste foi removido, desabilitado ou transformado em skip.
- A primeira execucao focada teve uma expectativa nova incorreta: o sucesso do
  rescan atual inicia carga e deve mostrar Carregando dados. A expectativa foi
  corrigida para exigir esse status e exatamente uma carga; producao preservada.
- CodeRabbit CLI 0.7.6 autenticada: review_completed, dez arquivos Python,
  0 issues. Revisao independente confirmou os contratos de identidade e flush.
- Os dois ajustes posteriores de construtor e seu teste tiveram revisao local
  independente, sem regressao concreta identificada. Nao fazem parte do parecer
  CodeRabbit anterior; a CLI nao permite limitar a chamada aos dois trechos.
- Ensaios adicionais em memoria: A retorna False com B pendente, B salva e o
  flush final confirma sucesso; A lanca com B pendente, a thread termina e
  flush(timeout=None) levanta OSError sem espera infinita. Shutdown confirma
  termino da thread, nao sucesso em disco; snapshot pendente nao e gravado
  automaticamente depois de uma excecao terminal.
- A primeira suite ampla foi interrompida deliberadamente com SIGINT para
  incorporar S7/S8; terminou com exit 134 durante a interrupcao, apos 477,07s.
  Esse resultado nao e aprovacao. A nova execucao registra hashes dos onze
  Python para verificar que o codigo permaneceu igual durante toda a suite.
- Suite completa final: **2938 passed, 9 skipped, 34 warnings, 11 subtests
  passed in 701.80s (0:11:41)**; exit 0. Tempo externo total: 703,73s.
- Comando: `QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q --durations=10`.
- Ambiente: macOS 27.0 arm64, Python 3.13.12, uv 0.12.13, pytest 9.1.1,
  PyQt/Qt 6.11.0. Hashes dos onze arquivos Python confirmados iguais do inicio
  ao fim; conteudo corresponde ao commit de codigo `0f239dac`.
- Os nove skips foram preservados. Os 34 avisos sao de grupos em regex (2)
  e inferencia de formato de datas (32), em arquivos fora deste patch.
  Nenhum aviso foi suprimido para obter o placar.
- A lista de duracoes inclui teste de lock de importacao (15,06s), substituicao
  de filtro antigo (10,11s) e cache apos mutacao (10,09s). Essas duracoes sao de
  testes; nao sao benchmark comparativo de CPU/RSS do aplicativo.
- Doze documentos passaram no verificador, sem problemas; links relativos
  existentes foram conferidos. Scanners amplos, SAM real e validacao visual
  nativa nao foram executados.

### K4. Commits por assunto

| Commit | Casos | Conteudo |
|---|---|---|
| `3e367782` | S1 | Confirmacao da gravacao e fechamento; regressoes de falha/recuperacao |
| `79a0d25e` | S4/S7/S8 | Construtor/start de derivadas, compactacao e banco alternativo |
| `0f239dac` | S2/S3/S5/S6 | Identidade de callbacks, preparacao e reload SAM, status de rescan |

Autoria e committer humanos preservados: Mauricio Menon, com o email ja
configurado no Git. Sem trailers ou credito de ferramentas. Os hooks locais
repetiram py_compile/Ruff nos commits. O verificador de autoria passou no range
novo desde 39e7c16a. Documentacao consolidada em commit posterior; obtenha
seu SHA pelo Git. Nenhum commit anterior foi reescrito.

### K5. Limites e proxima atividade

Os testes cobrem os estados reproduzidos, incluindo a tentativa seguinte; nao
provam ausencia de toda corrida possivel. Ainda faltam ensaios nativos com Qt,
CPU/RSS e plataformas Windows/Linux, alem dos scanners discriminados na passagem.
O prazo existente para fechamento forcado continua aplicavel; informar falha
na gravacao nao remove essa politica nem torna um disco indisponivel gravavel.
Cancelamento no meio do parser de planilha, inventario de APIs e historico Git
continuam com os estados declarados no backlog. O reteste completo registrado
em L4 pertence ao commit `5b75f8f8`; a suite de `0f239dac` e historica e o
diff A-E posterior exige a evidencia propria ja registrada em L4. Os limites
nativos, remotos e de durabilidade permanecem separados.


## L. Residuos A-E apos c30f87da

### L1. Escopo e leitura do levantamento

Base desta rodada: `c30f87da`, cujo codigo Python corresponde ao conjunto
S1-S8 validado em `0f239dac`. O anexo posterior e um levantamento externo;
suas sugestoes nao constituem uma nova autorizacao. O pedido do mantenedor
para reproduzir, estabilizar e corrigir as falhas de estado fornece o escopo.

Os sites S1-S8 estavam corrigidos nos caminhos testados. A expressao "genero
corrigido" nao demonstrava que todo construtor, preparacao, retorno de Qt ou
encerramento do projeto estava protegido. A-E sao residuos concretos em outros
pontos ou etapas desses fluxos. Foram preservadas API Python, stdout JSON,
exportacoes JSON/CSV/TSV, politica A5 e identidade humana nos procedimentos Git.
Nenhum `sys.excepthook` global foi acrescentado.

### L2. Antes/depois por residual

| Residual | Antes em c30f87da | Correcao e resultado observado | Estado |
|---|---|---|---|
| A, rescan/importacao | Construtor e preparacao fora do tratamento de partida. Falhas podiam deixar dialogo, worker ou registro da tentativa e escapar para o slot do menu | Construcao, preparacao, conexoes obrigatorias, registro e partida tratados no mesmo fluxo. Falha limpa os recursos da tentativa, informa erro e permite outra importacao; referencias alheias permanecem preservadas | CORRIGIDO; VALIDADO |
| B, filtro | Falha em token, construtor ou preparacao escapava com texto Filtrando, busca desabilitada e progresso visivel. Apenas `start()` estava protegido | Preparacao de termos, fonte, modo e colunas ocorre antes de busy. Token, construtor, sinais obrigatorios, retencao e partida usam tratamento unico. Erro cancela a tentativa anterior e passa por `on_filter_error`; nova requisicao entrega dados | CORRIGIDO; VALIDADO |
| C, preferencias | Thread terminava antes da escrita com `_pending` preenchido e `_write_failed=False`; `flush()` devolvia True pela flag de termino | Termino com preferencias pendentes registra falha. `flush()` levanta OSError; encerramento vazio legitimo continua True, e gravacao posterior bem-sucedida conserva a recuperacao prevista | CORRIGIDO; VALIDADO |
| D, entrega da carga | DataFrame malformado ou erro ao sincronizar controles escapava de `on_data_loaded`. A consulta ter terminado nao garantia aplicacao bem-sucedida na GUI | Entrega protegida e erro encaminhado a `on_load_error`. Antes de aplicar dados, tabela anterior preservada; depois da aplicacao, mensagem informa exibicao possivelmente incompleta e pede recarga. Retorno False da atualizacao visual tambem e tratado como falha. O encaminhamento preserva a fachada da janela, inclusive apresentacao no startup, modal, mascara do caminho e retencao | CORRIGIDO; VALIDADO |
| E, entrega de derivadas | Finalizador podia lancar no resultado, timeout ou tratamento de falha de partida; relatorio parcialmente aplicado podia continuar disponivel | Bloco local de entrega registra erro, invalida relatorio, restaura UI e retorna falha. Mantem referencia de thread ainda viva; nova tentativa conclui depois de seu termino | CORRIGIDO; VALIDADO |
| E, compactacao | Dialogo ou widget podia lancar durante finalizacao por timer | Finalizador protege aplicacao, informa erro e retorna `ok=False`. Polling aguarda termino nativo antes de liberar referencia e estado | CORRIGIDO; VALIDADO |
| E, banco alternativo | Falha de preparacao ocorria depois de mudar DB_PATH; dialogo falho mantinha busy. Recarga falha ainda retornava sucesso | Prepara/invalida estado antes de selecionar. Falha anterior preserva banco antigo; falha posterior conserva banco ja selecionado, relatorio anterior invalidado e instrucao de recarga. Estado liberado e retorno falso | CORRIGIDO; VALIDADO |

Referencias no codigo de `5b75f8f8` (producao igual a `a58bf7d7`):

| Residual | Implementacao | Regressao |
|---|---|---|
| A | `gui/ssa/gui_workers.py:1613`; `gui/ssa/gui_rescan_lifecycle.py:20` | `tests/test_gui_workers_rescan_data.py:240`; cancelamento tardio em `tests/test_import_outcome_isolation.py:211` |
| B | `gui/mixins/filter_gui_ssa_mixin.py:788` e `:844` | `tests/test_gui_filter_logic.py:14147` e `:14252` |
| C | `gui/ssa/gui_preferences_persistence.py:77` | `tests/test_gui_preferences_atomic_write.py:212` e `:229` |
| D | `gui/ssa/gui_workers.py:1335` e `:1398`; fachada em `gui/gui_ssa.py:2362` | `tests/test_contract_data_load_stale_guard.py:168`; startup em `tests/test_gui_filter_logic.py:14873` |
| E | `gui/ssa/derivadas_sync_controller.py:254`; `gui/gui_ssa.py:5058`, `:5255` e `:5303` | `tests/test_derivadas_sync_controller.py:102`; casos de finalizacao em `tests/test_gui_menu_import_external.py:860` |

### L3. Evidencia e limites das reproducoes

- B: reproducao na fixture real da GUI mostrou RuntimeError escapando em
  construtor/token/modo, texto Filtrando, busca desabilitada e progresso visivel.
  Selecao `initiate_filtering or filter_worker or filter_finished or filter_error
  or sync_filter`: **48 passed, 528 deselected em 30,26s**. Os testes abrangem
  sete etapas de inicializacao e quatro de preparacao, com nova entrega apos erro.
- C: `debounce_seconds=float("inf")` faz `Condition.wait()` levantar OverflowError
  antes da escrita, sem monkey-patch. Antes: accepted=True, terminated=True,
  pending preenchido, nenhuma escrita e flush=True. Depois: flush=OSError.
  Regressao antes do patch: **1 failed, 2 passed, 10 deselected**. Arquivo depois:
  **13 passed em 0,55s**. O gatilho e controlado e extremo; nao demonstra frequencia
  observada desse erro em producao. O defeito confirmado e a falsa confirmacao
  quando o escritor termina com uma preferencia aceita ainda pendente.
- D: reproducao com QTimer real em subprocesso isolado e DataFrame com duas
  colunas `numero_ssa`. Antes: processo encerrado por SIGABRT, retorno -6.
  Depois: retorno 0 e busy=False. Esse ensaio confirma o caminho Qt exercitado;
  nao equivale a inspecao visual nativa nem a cobertura multiplataforma.
- E: tres reproducoes de derivadas falharam antes do patch por excecao escapando
  em resultado, timeout e finalizacao de start_failed. Para GUI, os metodos do
  HEAD extraidos por AST confirmaram dialogo escapando, troca prematura de banco
  com relatorio antigo preservado e recarga falha retornando ok=True.
- E: **35 passed em 0,31s** nos arquivos `test_gui_menu_import_external.py` e
  `test_derivadas_sync_controller.py`, incluindo sete casos novos de falha e
  nova tentativa concluida. A referencia/busy permanecem enquanto a thread
  controlada esta viva. py_compile, Ruff e ty passaram nesses quatro Python.
- A/D: **57 passed em 0,31s** nos dois arquivos completos de rescan e contrato
  de carga. Seis falhas de inicializacao/conexao e quatro falhas de entrega
  verificam limpeza, aviso correto e nova tentativa concluida.
- D/fachada: **42 passed, 545 deselected em 15,60s**, retorno 0, na selecao
  de carga e callbacks obsoletos. Dois casos novos usam os metodos reais de
  SSAMainWindow para conferir apresentacao no startup antes/depois da aplicacao.
- C: py_compile, Ruff e ty passaram no modulo e no arquivo de testes.
- Nao somar selecoes sobrepostas. A verificacao integrada da rodada pertence
  a L4; os 2938 passed historicos nao validam as alteracoes A-E.

Revisao CodeRabbit CLI 0.7.6 sobre os seis arquivos GUI: um achado major
valido em D. Chamar diretamente o controlador de erro contornava a fachada da
janela e podia manter a janela inicial escondida. A correcao encaminha pelo
`window.on_load_error`, com `data_applied` keyword-only na fachada, preservando
apresentacao no startup, contexto do banco, modal e retencao. Foi acrescentada
regressao para esse caminho. Nao registrar esse parecer como zero achados; o
resultado final da regressao e da revisao integrada pertence a L4.

Scanners focados executados nesta rodada; nao representam
varredura ampla do repositorio/historico:

| Ferramenta | Escopo e resultado |
|---|---|
| Semgrep | p/python, 1066 regras, seis arquivos de producao, zero achados, retorno 0. A tentativa com config auto + metrics off falhou por incompatibilidade e nao conta como aprovacao |
| Bandit | Seis arquivos de producao, zero achados e zero erros |
| detect-secrets | Escopo focado, zero achados |
| TruffleHog | filesystem, no-verification, escopo focado, zero achados; nao executou verificacao online de credenciais |
| Gitleaks | Diff com redacao de valores, zero achados; nao e auditoria de todo o historico |
| Vulture | Limiar >=80, 18 imports nao usados; comparacao com c30f87da confirmou os mesmos 18, nenhum novo |
| pip-audit | --path .venv/lib/python3.13/site-packages: 47 entradas, 46 externas auditadas sem vulnerabilidades conhecidas; pacote local ssa-consulta-rapida 4.50.0 ignorado por nao estar no PyPI. A execucao default com 28 entradas auditou o ambiente da ferramenta e nao prova seguranca do aplicativo |
| ShellCheck | scripts/install_hooks.sh e hooks pre-push/commit-msg, retorno 0 |
| PSScriptAnalyzer | scripts/ recursivo, 59 avisos e zero erros; nenhum PowerShell alterado |

A validacao integrada tambem deve conferir os erros de preparacao/conexao de A,
retencao/liberacao dos registros, falha visual depois de dados aplicados em D,
retornos False e preservacao das operacoes seguintes. Comandos na passagem.

### L4. Fechamento da rodada A-E

A primeira execucao global sobre `a58bf7d7` terminou com **4 failed, 2965 passed,
9 skipped, 34 warnings, 11 subtests passed em 669,06s**, retorno 1; tempo de
parede 670,97s. Nenhum Python mudou durante a execucao. As quatro falhas eram
variantes do mesmo teste de cancelamento tardio: a fixture retornava None apos
conectar o sinal, em desacordo com o contrato booleano do adaptador.

A reproducao isolada confirmou as quatro falhas em 0,19s. `5b75f8f8` passa a
usar `_connect_signal` real nessa fixture, sem remover assercoes ou alterar
producao. Os arquivos de isolamento de resultado e rescan passaram juntos:
**68 passed em 0,30s**, com py_compile, Ruff e ty aprovados. O reteste global
abaixo e uma execucao separada; o primeiro resultado continua registrado como
falha.


| Registro | Resultado |
|---|---|
| Base | `c30f87da` |
| Validacao integrada, SHA/conteudo, comando, placar, duracao e retorno | `5b75f8f840072b806aadf17d1d0e6933500cb112`; `QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q --durations=10`: **2969 passed, 9 skipped, 34 warnings, 11 subtests passed em 706,03s**, retorno 0; parede 707,93s. Os 613 Python versionados ficaram inalterados. |
| Revisao do diff final | CodeRabbit 0.7.6: seis arquivos de producao, um major em D; encaminhamento pela fachada corrigido e validado por dois casos de startup. Revisao local do complemento, py_compile, Ruff e ty aprovados. |
| Commits por assunto e autoria conferida | `d8107fe8` C; `56701001` B; `56daccf1` A; `062bdb8f` D; `a58bf7d7` E; `5b75f8f8` fixture de cancelamento. Seis commits de codigo/testes e zero notas aprovados pelo verificador de autoria. |
| Publicacao e conferencia dos tres remotes/checks | Codigo/testes `5b75f8f8` publicado e conferido por `git ls-remote` nos dois GitHub e no GitLab. GitHub principal: statuses vazio e consulta de Actions limitada a PRs vazia; GitLab: pipelines vazio. A configuracao nao agenda CI por push nesta branch. Schottge: API retorna 404, publicacao SSH confirmada. Documentacao segue em commit proprio nesta branch. |

Os resultados historicos de K e a primeira execucao global com falha ficam
preservados. O placar aprovado acima pertence exclusivamente ao reteste final.
Ambiente: macOS 27.0 arm64, Python 3.13.12, PyQt/Qt 6.11.0, pytest 9.1.1.
Os artefatos desta rodada foram gerados em armazenamento temporario local:
`pytest-final-full.log`, `pytest-final-result.json`, `pytest-final-metadata.json`,
`pytest-final-source-hashes.json`, `final-static-checks.json` e
`scanners-results.json`. Este repositorio nao fornece uma copia desses arquivos.
O resumo acima e um registro historico; sem os originais, nao permite auditar
novamente o log integral ou os hashes. Nao presumir sua disponibilidade nem
apresentar esse resultado como validacao de outro commit.

### L5. Durabilidade e pendencias

`flush()` confirma o resultado informado pelo escritor e, no caminho normal,
a gravacao/substituicao do arquivo por `os.replace`. Isso nao garante durabilidade
absoluta contra queda de energia. `core/config_manager.py` ainda tolera OSError
no fsync do arquivo temporario e do diretorio, registrando em debug; no Windows,
o fsync do diretorio nao e executado. A rodada A-E nao mudou essa politica.
A afirmacao de que todas as falhas de fsync propagam estava incorreta.

A suite local esta aprovada em L4. Permanecem pendentes: scanners amplos,
uso visual nativo e capturas, SAM real, Windows/Linux e comparacoes CPU/RSS.
Cancelamento dentro do parser, inventario de APIs, mensagens Git historicas e
limitacoes de regras online continuam no backlog. Esses limites pertencem a
esta rodada historica. Ensaios adicionais dependem do escopo solicitado ou de
falha ou risco concreto; nao bloqueiam automaticamente uma entrega posterior.


## M. Correcao de CI/CD e preparacao da PR

Pedido: verificar e corrigir CI/CD, atualizar docs e preparar PR. Base local
`b96723349217499fe10470be52209ff9993ed93e`, branch existente
`fix/audit-surgical-fixes`, destino da PR `dev` no GitHub principal. A base
comum e `e62a85bf0f90e337def6fb2916651fe1e7364884`. Sem nova branch,
worktree, merge ou reescrita do historico.

### M1. Antes e depois

| Item | Antes | Depois | Estado |
|---|---|---|---|
| Aspas em GATES_ARGS | Falha de shlex ocorria em process substitution e era ignorada; gates/smoke ainda executavam | Parse sincrono com retorno conferido e tokens separados por NUL; erro sai com codigo 2 antes dos gates | CORRIGIDO |
| Argumentos vazios no macOS | Bash 3.2 com nounset abortava ao expandir array vazio | Expansao compativel preserva zero argumentos | CORRIGIDO |
| Diagnostico dos gates | stdout/stderr capturados nao apareciam; GitLab nao anexava JSONL | Log visivel e artefato JSONL em sucesso/falha por 14 dias | CORRIGIDO |
| Pipeline da branch fix | Push nesta branch nao agendava GitLab | Regra para push em fix/, evitando duplicacao quando ha MR | CORRIGIDO |
| Suite remota GitLab | pytest-full manual e allow_failure=true; pipeline verde podia omitir toda a suite | Suite automatica e bloqueante, timeout e relatorio JUnit | CORRIGIDO |
| Falha final do build Windows | Envio dos logs vinha antes da verificacao dos artefatos | Coleta vem no fim e cobre falhas posteriores ao build | CORRIGIDO |
| GitHub Actions | Jobs nem iniciavam por bloqueio de faturamento | Bloqueio confirmado na API; exige regularizacao da conta | BLOQUEADO NO SERVIDOR |
| Autoria no intervalo da PR | Mensagens antigas violam a regra vigente | Verificador preservado; a PR nao recebe excecao | BLOQUEADO PELO HISTORICO |

Backups timestamp das configuracoes e artefatos desta rodada ficam em
diretorio temporario local da execucao, sem copia fornecida neste repositorio.
O backup do shell tambem foi salvo em armazenamento temporario local.

### M2. Validacao local e do agendamento

- Reproducao inicial do shell: 3 falhas e 1 aprovado. A revisao encontrou
  perda de argumento vazio no primeiro patch; esse patch nao foi publicado.
  O parser final preserva argumentos vazios e LF com NUL em arquivo temporario,
  retorna 2 em parse invalido e remove o temporario em sucesso/falha.
- Validacao final: shell e tres arquivos quality_gates, 77 passed em 7,06s
  com Bash 3.2; contratos shell, 73 passed em 5,60s com Bash 5.3. Ha
  sobreposicao. Ambos shells executaram no macOS; Linux depende do job remoto.
  Regressoes ampliadas no arquivo existente, sem novo arquivo de teste.
- Revisao CodeRabbit concluida: perda de argumento corrigida; recomendacao
  de adicionar RTK nao corresponde a requisito executavel e foi descartada.
  O complemento teve revisao focada; nenhum wrapper de ferramenta foi incluido.
- Contratos Windows/entrypoints/artefatos: 60 passed em 8,47s.
- py_compile, Ruff e ty do teste alterado, ShellCheck e actionlint aprovados.
  yamllint retorna 0 com avisos de comprimento de linha, sem erros de sintaxe.
  Parser PowerShell e PSScriptAnalyzer: tres passos inline, zero problemas.
- CI Lint remoto, dry_run com ref fix/audit-surgical-fixes: valid=true,
  errors=[], warnings=[]; quatro jobs on_success e allow_failure=false.
  A simulacao valida configuracao/agendamento; nao executa comandos dos jobs.
- Wrapper real, com `.venv/bin/python`: tres gates ok, smoke 1 passed e
  2985 deselected, retorno final 0 em 2,67s. A tentativa inicial do comando
  local resolveu o symlink para o Python base e falhou por pandas/pytest
  ausentes; corrigido somente o comando de validacao, sem instalar pacotes.
  `quality-gates-local.log` preserva essa falha de ambiente e
  `quality-gates-final.log` preserva a execucao correta.
- Suite completa da aplicacao: manter como evidencia historica os 2969 passed
  de `5b75f8f8` em L4. Nao apresentar esse resultado como reteste deste patch.

### M3. Evidencias anteriores e bloqueios de integracao

GitLab pipeline 2842491246, no dev e62a85bf: gates e scanner aprovados, mas
pytest-full permaneceu manual e allow_failure=true. Esse verde nao inclui
execucao da suite completa.

GitHub runs 34667652301, 34667652285 e 34667652262: os sete jobs falhos
possuem zero etapas e anotacao "The job was not started because your account
is locked due to a billing issue.". O limite da conta nao e falha de YAML.

O comando `uv run --no-sync python scripts/validate_git_authorship.py range
origin/dev HEAD` retorna 1 no primeiro commit antigo rejeitado:
`22ccae16d9c3049ec8cd35b505592119ab0e4fc8`. As 16 mensagens antigas
continuam como pendencia historica. Mudar essas mensagens altera hashes e
exige autorizacao especifica; nenhum gate foi afrouxado.

O segundo GitHub aceita Git SSH, mas a conta autenticada no gh nao consegue
consultar esse repositorio via API. Publicacao SSH e execucao de CI sao fatos
diferentes. Novos resultados de publicacao/PR serao registrados abaixo.


### M4. Publicacao, PR e verificacoes externas

Commit de CI `ba2de05fa4786ed556e57aa6e840550c701ff3cd`: autor e committer
Mauricio Menon, email humano configurado. Hook e verificador aprovaram o novo
intervalo; push e `git ls-remote` confirmaram o mesmo SHA nos tres remotes.

[PR 131](https://github.com/mauriciomenon/SSA_Consulta_Rapida/pull/131)
aberta em draft, `fix/audit-surgical-fixes` para `dev`, sem conflitos no
momento da consulta. Draft nao significa pronta para merge: os bloqueios
abaixo continuam discriminados. A descricao inclui a auditoria completa e o
texto de passagem, alem deste patch de CI.

A primeira pipeline automatica da branch,
[2844932382](https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines/2844932382),
executou o commit ba2de05f: autoria aprovada e quality-gates aprovado em 65s.
O trace de pytest-full confirma execucao automatica com timeout e JUnit.
O complemento de testes/documentos posterior tem pipeline propria; conferir
SHA e resultado em
[pipelines desta branch](https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines?ref=fix%2Faudit-surgical-fixes).
Este registro de agendamento nao substitui o placar final da suite.

Na PR, os runs GitHub 34774710005 (minimal-ci), 34774709999 (Secret Scan),
34774710012 (CodeQL) e 34774710017 (Dependency review) falharam antes de
executar seus oito jobs por bloqueio de faturamento. Confirmado nas anotacoes
individuais. Nao foi alterado o YAML para esconder esse bloqueio.

CodeRabbit no servidor informou `Review skipped: draft pull request`; seu
status verde nao e uma revisao adicional. A revisao CLI de M2 foi executada.
O resultado de autoria do push GitLab valida somente o novo intervalo; a PR
completa continua rejeitando as 16 mensagens antigas.

O CodeFactor anotou oito ocorrencias na PR. Complemento apos a abertura:

| Ocorrencia | Tratamento | Validacao/limite |
|---|---|---|
| B108, tres caminhos em teste de resultado antigo de banco | Caminhos fixos /tmp substituidos pela fixture tmp_path; isolamento por caso e portabilidade | Teste de resultado antigo aprovado |
| B110, limpeza dos handlers em teste de logging | Removido except/pass; falha de close agora falha o teste | Dois testes de logging aprovados |
| Complex Method, on_load_error | Mantido nesta rodada | Cresceu de 65 para 83 linhas na auditoria; fluxo de erro/carga estabilizado, sem falha funcional nova demonstrada |
| Complex Method, _poll_delivery de derivadas | Mantido nesta rodada | De 41 para 48 linhas; guardas de timeout, identidade e fechamento precisam ser preservadas |
| Complex Method, load_other_database | Mantido nesta rodada | De 63 para 114 linhas; envolve dialogo, validacao asincrona e nova tentativa |
| Complex Method, validate_updates | Mantido nesta rodada | Funcao nova de 45 linhas verifica refs, commits, tags e notas; dividir sem revisao pode perder cobertura da politica |

Contagem de linhas e inventario AST, nao a metrica interna do CodeFactor.
O complemento altera somente dois testes; tres casos passaram em 1,19s,
com py_compile, Ruff e ty aprovados. Nenhum aviso de complexidade foi
suprimido e nenhum limiar de aprovacao foi reduzido. O CodeFactor passou no
complemento `7015e6fd`, mantendo quatro anotacoes de complexidade nao
bloqueantes. Esses itens permanecem como divida de manutencao.
Reavaliar em slice de refatoracao com contratos de erro, concorrencia e autoria
preservados; nao remover guardas apenas para reduzir a contagem.

O SHA que contem este complemento deve ser obtido do Git; a evidencia remota
final e vinculada ao SHA na descricao da PR e nos artefatos desta rodada.
Build Windows, ensaios visuais nativos e scanners amplos da passagem nao foram
executados aqui. Nao houve merge, reescrita nem alteracao de regras do servidor.


### M5. Estado do complemento 7015e6fd

O complemento `7015e6fd5c185cfc10c96b1bf99e00d6d8704c5b` foi publicado e
conferido por `git ls-remote` nos tres destinos. A pipeline do primeiro complemento e
[pipeline 2844937862](https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines/2844937862).
A anterior 2844932382 foi cancelada automaticamente apos o push: autoria e
gates passaram, pytest foi interrompido e secret-scan nao executou. Nao ha
placar completo a reutilizar daquela primeira tentativa.

CodeFactor no complemento: success, quatro anotacoes Complex Method e zero
anotacoes B108/B110. GitGuardian informou 40 commits examinados sem segredos.
Snyk, Socket e DeepScan tambem reportaram sucesso no escopo informado por
cada integracao; ausencia de mudanca em manifests nao equivale a auditoria
completa das dependencias. CodeRabbit/Aikido remotos omitiram analise por draft.

GitHub Actions no complemento: runs 34775012629, 34775012635, 34775012625 e
34775012621 encerraram com o mesmo bloqueio de faturamento. As oito anotacoes
confirmam que os jobs nao iniciaram. `gh pr checks --required` nao reportou
checks obrigatorios para esta PR. Portanto, CI falha e regra de servidor
impedindo merge nao sao equivalentes; a PR segue draft e nao foi integrada.

Novos commits humanos aprovados pelo verificador: dois no intervalo
b9672334..7015e6fd. A validacao do intervalo completo da PR continua rejeitada
pelas mensagens antigas; nao foi reescrito nem dispensado nenhum commit.
Logs e respostas de API desta rodada estao no diretorio de artefatos de M1;
a descricao da PR registra o resultado remoto por SHA.


### M6. DeepSource e complemento da limpeza de testes

O [DeepSource no 7015e6fd](https://app.deepsource.com/gh/mauriciomenon/SSA_Consulta_Rapida/run/b4ade804-0df7-4946-97a8-1d8635393188/python/)
terminou com status failure e nota C. A interface publica informa 746
ocorrencias marcadas como introduzidas, 622 resolvidas e 22 classificadas como
criticas. O proprio servico alerta que a branch pai nao tem PR propria e que
a analise de base pode incluir ocorrencias de branches anteriores. Nao ha
fundamento para declarar 746 novos bugs desta correcao de CI.

Duas ocorrencias criticas foram conferidas: `_get_canonical_available_columns`
(gui/gui_ssa.py:1817) ja verifica isinstance(cached, list) antes de iterar;
`copy_cell_value` (gui/gui_ssa.py:4313) verifica callable antes de chamar.
Ambas as funcoes sao identicas a dev/e62a85bf por comparacao AST. Outros
exemplos visiveis classificam next() de relogios controlados em testes como
risco critico. A triagem das 746 ocorrencias nao foi realizada nem dispensada.
Primeiro conferir a base de comparacao e separar alertas de teste, problemas
preexistentes e regressao; nao aplicar supressoes em massa.

A politica preexistente em `.github/CODE_QUALITY.md` trata DeepSource/Snyk como
sinais consultivos, sem mudar para isso a politica do servidor nesta rodada.
O status failure e real, mas nao equivale a job de testes falho nem a um check
obrigatorio de merge. Seu resultado permanece visivel e consta da passagem.

A revisao adicional da limpeza de logging reproduziu um problema no primeiro
complemento: se o primeiro close lancasse, sobrava um handler e o segundo
nao era fechado. O helper final tenta fechar todos, limpa o cache do logger e
propaga RuntimeError com todas as falhas e a primeira causa encadeada. Nenhum
erro fica em except/pass; os dois call sites compartilham a mesma limpeza.

Prova controlada com tres handlers, dois falhando: zero handlers restantes,
tres tentativas de close, cache vazio e as duas falhas presentes no erro.
Dois testes existentes de logging passaram em 0,05s; compile, Ruff e ty
aprovados. A prova esta em `cleanup-failure-probe.json` nos artefatos de M1.
O complemento `53e748b8` nao altera codigo da aplicacao nem configuracao de CI.


### M7. Falha Linux reproduzida e correcao do teste de cabecalho

A pipeline 2844937862 terminou com falha real de assercao, retorno 1, sem
atingir o timeout global. Placar no 7015e6fd: 2943 passed, 1 failed, 42 skipped,
34 warnings e 11 subtests passed, em 1737,34s; job em 1782,99s. JUnit publicado
com 2986 casos. Autoria e quality-gates passaram; secret-scan foi pulado pela
falha na etapa verify, portanto nao foi aprovado nessa pipeline.

O teste `test_executor_filter_refresh_rebuilds_table_through_pipeline` passou
pelas duas verificacoes de 50 linhas e falhou ao buscar o cabecalho visual
"Set. Exec". A GUI adapta esse texto conforme largura e fonte. Reproducao
local com o fluxo real: largura 26 gera "[f] Exec.", largura 240 gera
"[f] Set. Exec."; ambos conservam 50 linhas e somente IEE3. A busca antiga
falha no primeiro caso. Evidencia: `adaptive-header-before.json` em M1.

Antes: o helper de teste deduzia a coluna pelo titulo abreviado. Depois:
consulta o indice canonico setor_executor em `_current_display_columns`,
o mapa usado pela renderizacao. Removido o helper de busca textual. O caso
existente foi parametrizado com as duas larguras; as assercoes dos valores
visiveis e da quantidade de linhas continuam obrigatorias. Nenhum caminho da
aplicacao, fonte, abreviacao ou limite de desempenho foi modificado.

Validacao local: 43 testes de marcador/renderizacao passaram em 4,50s;
py_compile, Ruff e ty aprovados. Os 15 testes anteriores passaram isolados
antes da correcao, demonstrando por que o contexto visual precisa ser
controlado. A prova com coluna estreita reproduziu a falha antes do patch.

O job agora usa `run_tests.sh full` e `--durations=20`: publica os nomes dos
testes durante a execucao e os maiores tempos no resumo, mantendo captura de
saida, JUnit, 45s por teste, limite global de 30 minutos e falhas bloqueantes.
Correcao em 03b55d37; CI Lint remoto aprovou os quatro jobs bloqueantes,
sem erros ou avisos. A nova execucao remota deve ser conferida pelo SHA
publicado na PR 131; o placar falho acima permanece como evidencia e nao
aprova o complemento.


### M8. Runner local de pytest no Bash 3.2

Reproducao adicional: `PYTEST_ADDOPTS='' uv run --no-sync /bin/bash
scripts/run_tests.sh quiet` abortava com `pytest_extra_opts[@]: unbound
variable`, retorno 1, antes de iniciar pytest. O wrapper tambem serializava
opcoes por linha e as repassava em argv, embora pytest ja leia PYTEST_ADDOPTS;
isso duplicava opcoes e nao preservava corretamente tokens vazios ou LF.

Depois: o wrapper valida somente a sintaxe com shlex para preservar retorno 2
em aspas invalidas. Pytest recebe a variavel integral pelo ambiente, uma vez,
sem array adicional, serializacao ou novo helper. A precedencia e a nativa do
pytest: opcoes explicitas do modo escolhido prevalecem sobre as do ambiente.
Falhas de sintaxe continuam encerrando antes de executar a suite.

Contratos existentes ajustados: aspas, variavel vazia, espacos, token vazio,
LF e sintaxe invalida. 19 casos focados passaram no Bash 3.2 em 2,48s e os
mesmos 19 no Bash 5.3 em 2,69s. Wrapper real no Bash 3.2 executou oito casos
selecionados por PYTEST_ADDOPTS, em 1,09s; argv contem somente o comando base,
sem duplicar a selecao. ShellCheck, py_compile, Ruff, ty e diff-check passaram.
Logs: `/tmp/ssa-run-tests-bash53-20260913-161145.log` e
`/tmp/ssa-run-tests-real-bash32-20260913-161145.log`.

A pipeline 2844986660 corresponde ao complemento anterior 0abedeb1. Autoria
e gates passaram; sua execucao parcial nao aprova o runner posterior. A PR
131 identifica o HEAD publicado e a pipeline que valida o complemento final.


### M9. Scanners locais do diff de CI

Ferramentas executadas nos quatro Python alterados entre b9672334 e o
complemento do runner; scanners de segredos nos 14 arquivos entao alterados.
Nao e uma nova auditoria de todo o codigo ou historico. Nenhuma regra foi
suprimida, nenhuma dependencia foi atualizada e nenhum segredo foi validado
contra um servico externo. Saidas e hashes em focused-scanners-summary.json,
no diretorio de M1.

| Ferramenta | Escopo e resultado | Limite |
|---|---|---|
| pip-audit 2.10.1 | 13 dependencias de runtime exportadas do uv.lock frozen; retorno 0, zero vulnerabilidades conhecidas, zero dependencias ignoradas | Nao inclui todos os extras de desenvolvimento nem binarios nativos |
| Gitleaks 8.30.1 | 14 arquivos, todos os retornos 0, sem segredos detectados | Conteudo atual do diff; historico nao revarrido |
| TruffleHog 3.97.4 | Retorno 0, zero resultados | Deteccao local, sem verificacao remota de credenciais |
| detect-secrets 1.5.0 | Retorno 0, results vazio | Deteccao local, sem verificacao remota |
| Bandit 1.9.4 | Retorno 1; 2619 avisos LOW: 2592 asserts, 20 subprocess, seis executaveis por PATH e um import subprocess | Quatro arquivos de testes; nenhum HIGH/MEDIUM, sem falha de parsing; avisos nao foram apagados |
| Vulture 2.16 | Retorno 3; 249 candidatos, 247 com confianca 60% e dois parametros de fixtures com 100% | Analise isolada de testes nao resolve chamadas dinamicas feitas pela aplicacao; nao comprova codigo morto removivel |
| Semgrep 1.177.0 | 1066 regras Python, quatro arquivos, zero achados publicados; retorno 2 | Uma regra de taint excedeu tempo em test_gui_filter_logic.py. Execucao parcial, nao aprovada, apesar do resumo textual dizer concluida |

O erro Semgrep e da regra dangerous-system-call-tainted-env-args no arquivo
extenso de testes. Nao houve mudanca de timeout ou exclusao para obter verde.
Relatorio JSON preservado; repetir somente essa analise pendente com escopo
controlado na passagem. Essas execucoes nao aprovam automaticamente alteracoes
posteriores aos hashes registrados.

O limite global do job pytest-full foi ajustado de 30 para 40 minutos apos a
medicao de 29min43s: havia apenas 17s de margem. Permanecem 45s por teste,
mesma selecao completa, JUnit, falhas bloqueantes e exibicao das duracoes.
Nao se trata de dispensar a falha de cabecalho, que foi reproduzida e corrigida.


### M10. Ultima revisao da PR e encerramento solicitado

A revisao remota acrescentou 38 comentarios sobre o intervalo completo da
branch, alem do comentario de limpeza de logging ja resolvido em 53e748b8.
Esses comentarios sao alegacoes do revisor, nao autorizacoes nem defeitos
automaticamente confirmados. A consulta integral esta no artefato
pr-comments-0abedeb1.json de M1.

| Item | Antes / depois ou diagnostico | Estado |
|---|---|---|
| P1, salvar filtro com selecao pendente | store_only alterava o mesmo dicionario guardado para restauracao. Cancelar mantinha o filtro ativo novo e os avancados antigos. e767f391 preserva copia profunda antes da sincronizacao. Teste existente usa sincronizacao real, verifica snapshot pendente e estado original restaurado | CORRIGIDO; antes 1 falha, depois 25 testes focados aprovados em 7,42s, compile/Ruff/ty aprovados |
| P1, vacuum/validacao fora do inventario de shutdown | Omissao confirmada, mas nao foi reproduzida falha funcional. Validacao e leitura; vacuum usa lock/SQLite; callbacks verificam a janela. Ausencia de prova tambem nao garante seguranca absoluta | NAO CONFIRMADO como P1; contrato de fechamento exige triagem, sem alterar politica nesta rodada |
| P1, espaco livre na promocao | Verificacao registra pouco espaco como aviso. Preparo bloqueia disco insuficiente quando o relatorio esta invalido; promocao usa somente criterios estruturais. A5 foi corrigido para nao afirmar bloqueio uniforme. Adicionar disco ao bloqueio final tambem mudaria comportamento de bancos validos | DIVERGENCIA CONFIRMADA; alinhamento dos criterios permanece pendencia tecnica, sem adotar automaticamente a sugestao do bot |
| Cinco inconsistencias documentais | Corrigidos indice de WORKERS_API_DOCUMENTATION, lista completa de marcadores, abertura do HTML so apos geracao bem-sucedida, eventos reais de CI em VALIDATION_PLAN e cabecalho versionado/atualizado do RECOVERY_BACKLOG | CORRIGIDO |
| Outros 30 comentarios da revisao ampla | Incluem cobertura, importacao, reparo, exportacao, hooks, logging e estados de GUI. Nao houve triagem integral nem aplicacao automatica das sugestoes | PENDENTE; nao declarar a revisao integral aprovada |

A sugestao remota de liberar uma base Git ausente nao foi adotada: contraria
a politica explicita de autoria. A PR continua em rascunho, sem merge.

O mantenedor pediu para pular o teste Linux e encerrar o consumo adicional.
A suite da pipeline 2844986660 foi cancelada por esse pedido; o complemento
final nao recebe aprovacao Linux nesta rodada. A configuracao automatica da
CI permanece publicada para uso futuro, mas o teste Linux da publicacao final
tambem deve ser cancelado. Nao confundir cancelamento solicitado com sucesso.

Validacoes pesadas e novas varreduras encerradas. A proxima atividade tecnica
e tratar o backlog da revisao ampla em escopo proprio; regularizacao da conta
GitHub e autorizacao especifica para reescrita continuam pendencias separadas.


## N. Falha de importacao no build empacotado Windows (path safety em derivadas)

### N1. Incidente e evidencia

Importacao pelo executavel PyInstaller no Windows 11 falhou na fase de
derivadas apos gravar dados parciais. Log do usuario (`erro import.txt`,
14/09/2026): 42 arquivos estagiados, 31 processados, 20.706 SSAs atualizadas e
56 inseridas; banco cresceu de 99.538 para 99.594 linhas; erro final
`sync derivadas database: 'C:\Users\menon\Downloads\Telegram Desktop\ssas.db'
fora das bases permitidas (...)`, status `derivadas_sync_error` /
`blocking_derivadas_sync_error` e aviso explicito `O banco recebeu alteracoes
parciais`.

### N2. Cadeia causal confirmada no codigo

1. `gui/workers/rescan_worker.py` (~linhas 479-496) monta
   `extra_allowed_roots = [project_root, db_parent]` e chama
   `run_importer_logic(extra_allowed_roots=tuple(...))`. O banco externo e
   legitimamente permitido nesta camada.
2. `core/app_logic.py:1923` recebe `extra_allowed_roots` e o repassa a
   `_initialize_import_run_context` (:1950), que valida `docs_dir`, `data_dir`
   e `db_path` com essas raizes. A fase regular de importacao grava no banco
   externo com sucesso.
3. `core/app_logic.py:2163` chama `_run_optional_derivadas_sync` sem repassar
   as raizes; `:1175` chama `_run_derivadas_sync_phase` tambem sem elas.
4. `armazenamento/derivadas_sync.py:1558-1564` revalida `db_path` via
   `ensure_path_is_allowed` somente com as raizes globais
   (`utils/path_safety.py`), que nao incluem o diretorio do banco externo.
5. `PathSafetyError` (subclasse de `ValueError`, `path_safety.py:20`) e
   capturada pelo `except (OSError, RuntimeError, ..., ValueError,
   sqlite3.Error)` de `app_logic.py:1235`, vira `derivadas_sync_blocking_error`
   e retorna `False` em `app_logic.py:2213-2217`.

A mesma revalidacao isolada existe em `_normalize_sheet_file_path`
(`derivadas_sync.py:228-234`), `_open_derivadas_read_connection`
(:159-166, usado por `scan_derivadas_consistency` :1929 e `get_sync_stats`
:1811), `self_heal_derivadas` (:2036), `run_derivadas_maintenance` (:2078) e
`armazenamento/derivadas_schema.py` (:440, :484, :526). O fluxo manual da GUI
(`gui/ssa/derivadas_sync_job.py` -> `sync_derivadas_fn`) e a CLI
`scripts/derivadas_cli.py` tem a mesma lacuna para `--db` externo.

Defeito arquitetural: o contexto de politica de caminho nao e propagado
pelo pipeline; cada camada revalida contra raizes globais. Em desenvolvimento
o banco fica dentro do projeto e o bug e invisivel; ele so aparece no pacote
com banco em diretorio arbitrario do usuario.

### N3. Reproducao controlada (macOS, sem alterar o repo)

Em `/tmp/ssa_repro`, com banco vazio fora das raizes permitidas:

- `ensure_path_is_allowed('/tmp/ssa_repro/ext/ssas.db',
  purpose='sync derivadas database')` -> `PathSafetyError` com a mesma
  mensagem do log do usuario.
- Mesma chamada com `extra_allowed_roots=('/tmp/ssa_repro/ext',)` -> aceito.
- `inspect.signature(sync_derivadas)` confirma ausencia de parametro
  `extra_allowed_roots`.

### N4. Implementacao exata (entregue na branch devin_review)

Objetivo: propagar as mesmas raizes explicitas por toda a cadeia, sem
enfraquecer `ensure_path_is_allowed` nem ampliar `ALLOWED_ROOTS` global.

`armazenamento/derivadas_sync.py`:

- `_normalize_sheet_file_path(value)` -> acrescentar
  `extra_allowed_roots: Iterable[str | os.PathLike] | None = None` e repassar
  a `ensure_path_is_allowed(..., extra_allowed_roots=extra_allowed_roots)`.
- `_open_derivadas_read_connection(db_path)` -> idem.
- `sync_derivadas(...)` -> acrescentar keyword-only `extra_allowed_roots=None`;
  repassar a `_normalize_sheet_file_path` (:1540, :1545) e a
  `ensure_path_is_allowed` do `db_path` (:1559).
- `get_sync_stats(db_path)`, `scan_derivadas_consistency(db_path)` -> idem,
  repassando a `_open_derivadas_read_connection`.
- `self_heal_derivadas(...)` -> idem, repassando as duas chamadas de
  `scan_derivadas_consistency` (:2052, :2069) e a `sync_derivadas` (:2056).
- `run_derivadas_maintenance(...)` -> idem, repassando a
  `_open_derivadas_read_connection` (:2090), `scan_derivadas_consistency`
  (:2129) e `self_heal_derivadas` (:2165).

`armazenamento/derivadas_schema.py`:

- `ensure_derivadas_schema` (:440), `scan_derivadas_schema_readiness_from_path`
  (:484) e `scan_derivadas_read_schema_readiness_from_path` (:526) -> mesmo
  parametro opcional repassado a `ensure_path_is_allowed`.

`core/app_logic.py`:

- `_run_derivadas_sync_phase` (:485) -> parametro `extra_allowed_roots=None`;
  incluir em `sync_kwargs` (:503) e repassar a
  `scan_derivadas_consistency(db_path=db_path,
  extra_allowed_roots=extra_allowed_roots)` (:620).
- `_run_optional_derivadas_sync` (:1145) -> mesmo parametro repassado a
  `_run_derivadas_sync_phase` (:1175).
- `run_importer_logic` -> no call site :2163, passar
  `extra_allowed_roots=extra_allowed_roots`.

`gui/ssa/derivadas_sync_job.py` e `gui/gui_ssa.py`:

- `execute_derivadas_sync_job` -> parametro `extra_allowed_roots=None`
  repassado a `sync_derivadas_fn` e `scan_derivadas_consistency_fn`.
- `gui_ssa.py:_execute_derivadas_sync_job` (:5239) -> passar
  `extra_allowed_roots=[str(Path(db_path).resolve().parent)]`, replicando o
  padrao ja usado em `rescan_worker.py` para `db_parent`.

`scripts/derivadas_cli.py`:

- Nos handlers que recebem `--db`, passar
  `extra_allowed_roots=[str(Path(args.db).resolve().parent)]`. O banco
  nomeado pelo operador auto-autoriza seu diretorio; planilhas e destinos de
  relatorio continuam validados. Alternativa documentada: exigir
  `SSA_EXTRA_ALLOWED_PATHS`, mantida como opcao, nao como obrigatoria.

Compatibilidade: todos os parametros novos sao opcionais com default `None`;
assinaturas e contratos publicos preservados.

Estado: implementado em `devin_review`. Adicionalmente, `run_importer_logic`
ganhou pre-flight que valida `working_db_path` e cada
`derivadas_sheet_files` com as mesmas raizes antes de qualquer escrita,
fechando a janela de mutacao parcial para falhas de caminho (item N5.1).
Excecao na entrada invalida aborta como `ImporterError` com
`PathSafetyError` como causa, antes de `_import_single_file`.

### N5. Segundo defeito: mutacao parcial antes da fase de derivadas

O log prova que 31 arquivos foram gravados no banco primario antes do
bloqueio. O retorno `False` nao desfaz essas escritas; o mecanismo de
candidato/promocao so existe no full-rescan. Duas medidas:

1. Fail-fast (barata, entregue): `run_importer_logic` executa
   `ensure_path_is_allowed` em `working_db_path` e em cada planilha de
   derivadas antes do processamento, com as mesmas `extra_allowed_roots`.
   Caminho invalido agora aborta antes de qualquer linha gravada.
2. Decisao de consistencia (separada, PENDENTE): para falhas de derivadas
   nao relacionadas a caminho, decidir entre (a) aceitar progresso parcial
   com status/report honesto e caminho de retry (ja existe
   `db_only_derivadas_sync`), ou (b) estender o fluxo candidato/promocao ao
   rescan comum, promovendo so apos sync+consistencia. A opcao (b) e a mais
   segura, porem estrutural; nao implementar junto do hotfix N4 sem pedido
   proprio.

### N6. Cobertura de testes adicionada e executada

Novos casos (todos aprovados):

- `tests/test_derivadas_sync.py` (4): db externo exige raiz explicita;
  scan/stats/heal/maintenance propagam raizes; planilha externa segue a
  mesma politica.
- `tests/test_derivadas_schema.py` (1): `ensure_derivadas_schema` e os dois
  `scan_*_from_path` respeitam `extra_allowed_roots`.
- `tests/test_derivadas_sync_job.py` (1): `execute_derivadas_sync_job`
  repassa as raizes a `sync_derivadas_fn` e `scan_derivadas_consistency_fn`.
- `tests/test_import_derivadas_trigger.py` (2): `run_importer_logic` com db
  externo + raizes executa a fase de derivadas e propaga as raizes;
  planilha externa sem raiz aborta em pre-flight antes de qualquer
  `_import_single_file` (zero escritas).

Resultado registrado: 177 testes focados + 100 (workers/menu/queries) + 79
(filtros/derivadas GUI) aprovados em macOS arm64 offscreen; ruff e ty sem
achados nos arquivos alterados; dois stubs antigos de
`ensure_path_is_allowed` em testes foram alargados com `**_kwargs`. Suite
completa, scanners e validacao nativa Windows nao executados nesta rodada.

### N7. Origem e limite da evidencia

O mecanismo `extra_allowed_roots` existe desde antes da rodada de build
Windows; a sessao Codex de 10/09/2026 leu esses simbolos mas nao introduziu
a propagacao. O defeito so se manifesta com banco fora das raizes padrao,
cenario que a validacao do pacote nao exercitava. Correcao implementada em
`devin_review`; validacao do pacote Windows com banco externo continua
pendente (ver BUILD_WINDOWS_ARM64_AMD64.md).

## O. Correcao dos achados remanescentes da auditoria read-only (rodada 2026-09-15)

A auditoria read-only original listou seis achados (1 alta, 2 medias,
3 baixas). Esta rodada corrigiu cinco deles em `devin_review`; o sexto
permanece como decisao pendente por envolver empacotamento.

### O1. ALTA - `--streamlit` encerrava o servidor ao sair de `main()`

- `interface/streamlit_launcher.py`: nova funcao `wait_for_streamlit()`,
  que bloqueia em `process.wait()` sobre o processo Streamlit mais recente.
  Em `KeyboardInterrupt` retorna; a limpeza `atexit` existente encerra o
  filho na saida do interpretador. `launch_streamlit()` segue nao
  bloqueante (contrato preservado, testes existentes intactos).
- `main.py::_launch_interface`: apos lancamento bem-sucedido chama
  `wait_for_streamlit()`, entao o processo-pai permanece vivo enquanto o
  servidor estiver ativo e CTRL+C passa a funcionar como anunciado.

### O2. MEDIA - `logs/` crescia sem limite

- `core/import_run_report.py`: `_prune_import_run_reports()` descarta os
  `import_run_*.json` mais antigos (por mtime), retendo os 50 mais
  recentes a cada nova gravacao. Falhas de poda sao ignoradas (OSError),
  nunca bloqueiam o relatorio.
- `interface/streamlit_launcher.py`: `streamlit.log` acima de 5 MiB e
  rotacionado para `streamlit.log.1` (backup unico) antes da abertura.

### O3. MEDIA - `utils/fallback/emergency_import.py` apagava o banco real

- Removido o `os.remove(db_path)` silencioso. Banco existente agora aborta
  com mensagem, a menos que `--force` seja passado; com `--force` o banco
  e arquivado como `ssas.db.bak-<timestamp>` em vez de apagado. Novo
  argumento `--db` permite escolher o caminho de destino. O banner
  explicita que o script insere dados de TESTE.

### O4. BAIXA - `_parse_cache` e `results_stack` sem limite na CLI

- `interface/cli.py`: `_parse_cache` virou `OrderedDict` com evicao FIFO
  em 256 entradas. `results_stack` passa por `_push_result_state()` nos
  tres pontos de push (filtro, `ord`, `ordn`), com teto de 100 niveis; ao
  estourar, descarta o item mais antigo apos a base (indice 0 preservado
  para os comandos de reset). `_print_cache` ja tinha teto proprio
  (limpa aos 20) e nao foi alterado.

### O5. BAIXA - `except Exception` mascarando falhas

- `utils/remote_itaipu.py::map_to_dataframe`: restrito a
  `(ImportError, ValueError, TypeError, AttributeError)` com `logger.debug`
  da causa.
- `utils/path_safety.py::_is_within`: restrito a
  `(OSError, RuntimeError, ValueError)`, cobrindo `resolve()` e
  `relative_to()` sem engolir excecoes inesperadas.

### O6. BAIXA - `sys.path.insert` em runtime - PENDENTE

Nao alterado: `main.py` e `interface/cli.py` dependem dele no modo
desenvolvimento e em cenarios de launcher nao empacotado. Remover exige
garantir `pip install -e .` ou `PYTHONPATH` em todos os entry points;
decisao de empacotamento, nao de corretude. Registrado como backlog.

### O7. Validacao executada nesta rodada

- `pytest`: test_main_streamlit_launcher, test_cli_loop_filter_rounds,
  test_cli_config_preserve_session, test_path_safety (53), mais
  test_import_run_report (27) e demais modulos test_cli_* (38) - todos
  aprovados em macOS arm64.
- Verificacoes manuais: emergency_import (cria/recusa/arquiva),
  rotacao de streamlit.log, `wait_for_streamlit` com fake process, prune
  de relatorios (60 -> 50 mais recentes), `map_to_dataframe`.
- `py_compile` e `ruff check` limpos em todos os arquivos alterados.
- Nao executado: suite completa, scanners, validacao no pacote Windows.

### O8. Revisao externa (rodada 2) - codex e bitoreview sobre o diff

Revisao externa executada sobre `dev..devin_review` apos os testes de borda
da rodada 1. Resultado: 2 defeitos reais introduzidos/encontrados foram
corrigidos; demais apontamentos eram cosmeticos ou falsos positivos.

- **[P1] `emergency_import --force` perdia commits do WAL**
  (`utils/fallback/emergency_import.py`): renomear apenas `ssas.db`
  deixava `ssas.db-wal`/`-shm` orfaos — commits pendentes se perdiam e o
  WAL antigo poderia ser aplicado sobre o banco recriado. Corrigido: o
  trio (`db`, `-wal`, `-shm`) e arquivado junto. Reproduzido com WAL
  aberto: backup resultante abre com os dados preservados.
- **[P2] `extra_allowed_roots` como `Iterable` esgotavel**
  (`armazenamento/derivadas_sync.py`, `core/app_logic.py`,
  `gui/ssa/derivadas_sync_job.py`): gerador passado pelo chamador era
  consumido na primeira validacao e as seguintes recebiam o iterador
  esgotado, rejeitando caminhos autorizados. Corrigido materializando em
  `tuple(...)` nos pontos de entrada com multiplas validacoes:
  `sync_derivadas`, `self_heal_derivadas`, `run_derivadas_maintenance`,
  `execute_derivadas_sync_job` e `run_importer_logic`. Funcoes de uso
  unico (scan/stats/pass-through) nao precisam.
- **[LOW] bitoreview**: aplicados `entry: Tuple[pd.DataFrame, List[str]]`
  em `_push_result_state` e aviso impresso quando a rotacao de
  `streamlit.log` falha por erro real (FileNotFoundError segue esperado).
  Nao aplicados (falsos positivos/cosmeticos): appends pos-`clear()` na
  results_stack (profundidade 1, helper seria no-op), docstring do
  parametro no job, nome de helper no CLI.
- Bug de borda proprio encontrado na rodada 1: dois `--force` no mesmo
  segundo colidiam no `.bak-<timestamp>`; timestamp agora inclui
  microssegundos.

**Suite completa** executada nesta rodada: **2777 passaram, 1 falhou** —
`test_code_quality_documents_dynamic_dependency_submission_status`, que e
**falha pre-existente em `dev`** (o teste exige frase em ingles e o
`.github/CODE_QUALITY.md` esta em portugues desde antes do branch;
conteudo identico nos dois branches). Nao corrigida por estar fora do
escopo; requer decisao sobre qual lado do contrato prevalece.

### O9. Revisao externa (rodada 3) - fatiada por codigo e modelo

Ciclo de estabilizacao com revisores externos **fatiados** (cada modelo
revisou uma fatia de codigo, nao o diff inteiro) e propostas de correcao
revisadas antes da implementacao. Ferramentas: codex (fatia derivadas +
revisao de propostas), omp (fatia CLI + revisao da proposta P-C), hermes
(ciclo de vida streamlit + arquivamento WAL), bitoreview (diff completo).
claude/kimi/pi/opencode falharam por autenticacao/conexao/modelo
deprecado — sem achados.

Achados confirmados e corrigidos nesta rodada:

- **[MEDIA] `x <termo>` reaplicava o termo removido apos `ord`/`ordn`**
  (`interface/cli.py`, pre-existente): `ord` empilha `(df_ordenado,
  mesmos_termos)`; o atalho LIFO usava `stack[-2]` como base, que ja
  estava filtrada pelo termo removido — o filtro "removido" seguia
  aplicado em silencio. Corrigido com a variante V3 revisada pelo omp:
  `x` pousa na entrada mais recente cujos termos == `remaining` (e loop
  de pop no caso vazio). Reproducao local dos 9 cenarios que a variante
  V1 falhava: 9/9 corretos apos V3.
- **[MEDIA] ordem de arquivamento do WAL ainda insegura** (hermes):
  o loop `("", "-wal", "-shm")` renomeava o `.db` primeiro; um kill no
  meio deixava WAL orfao a ser reaplicado sobre o banco novo. Corrigido
  para `("-wal", "-shm", "")` — WAL orfao sem `.db` e inocuo. Verificado
  com conexao WAL aberta e commit pendente.
- **[BAIXA] filho streamlit orfao em SIGTERM** (hermes): `SIGTERM` nao
  executa `atexit`, logo o filho ficava segurando `:8501`. Corrigido com
  handler em `wait_for_streamlit` que termina o filho e sai 143; falha
  ao registrar o handler e tolerada (ex.: thread nao-principal).
- **[BAIXA] `--db '~/ssas.db'` rejeitado** (codex): `_db_extra_roots`
  fazia `resolve()` sem `expanduser()`, gerando raiz literal `~`.
  Corrigido em `scripts/derivadas_cli.py` e no call site de
  `gui/gui_ssa.py`; docstring tambem corrigida (a raiz do `--db` cobre
  planilhas sob o mesmo diretorio — mesmo criterio do rescan_worker).
- **[BAIXA] candidato orfao em falha de pre-flight** (revisao propria,
  ressalvas do codex aplicadas): em `force_import`, o candidato era
  criado antes do pre-flight e sobrava no disco quando ele falhava.
  Corrigido removendo `candidate±wal±shm` **somente se criado nesta
  rodada** (guard `candidate_preexisting`, pois o prepare reutiliza
  arquivo existente no path), com log em falhas de remocao e `raise`
  preservando `PathSafetyError` → `ImporterError`.

Proposta **adiada por decisao de escopo** (veredito codex: flawed):
autorizar caminhos digitados na UI Streamlit (`dev_env/streamlit_app.py`).
A correcao parcial seria incompleta — `get_filtered_data` e
`import_files_to_database` revalidam sem raizes — e o perfil de
confianca de caminho digitado em UI web difere do CLI local. Registrado
como limitacao conhecida para a rodada futura de paths externos.

**Validacao desta rodada**: 167 testes focados aprovados; reproducoes
manuais dos 9 cenarios de `x`/`ord`, do trio WAL, do handler SIGTERM
(exit 143, filho terminado), de `expanduser` e do cleanup do candidato;
`ruff` e `ty` limpos nos arquivos alterados.

### O10. Verificacao por subagente (Fusion) - ressalvas enderecadas

Revisao estatica independente sobre o estado do branch: veredito
APROVADO-COM-RESSALVAS, sem bloqueantes. Follow-ups aplicados:

- **`x <termo ausente>` imprimia "Removido" sem remover nada** —
  corrigido: verifica presenca do termo antes de processar e informa
  "nao esta no filtro atual".
- **`x` re-aplicava termos com modo `contains` ignorando
  `filter_mode_default` do usuario** (pre-existente) — corrigido em
  `_handle_remove_filter` e no refresh de filtros padrao: os termos
  restantes sao parseados com `parse_search_terms(..., default_mode)`
  antes de `filter_dataframe`. Dois testes ajustados para o contrato
  novo (termos parseados preservam `raw`).
- **Janela SIGTERM Popen→wait** — o handler `_terminate_children_and_exit`
  (termina todos os processos rastreados, exit 143) agora e instalado em
  `launch_streamlit`, fechando a janela em que o filho ficava orfao.
- **Sidecars `-wal`/`-shm` orfaos sem `.db`** — deixados por versoes
  antigas que so removiam o `.db`; seriam re-aplicados quando o banco
  novo ativasse `journal_mode=WAL`. Corrigido: sao arquivados como
  `.bak` mesmo sem `--force` (renomear preserva; nada e apagado).
  Falhas de `os.replace` agora abortam com contexto do arquivo que
  falhou — o estado resultante (arquivamento parcial, nada recriado)
  e seguro.
- **Materializacao defensiva** — `tuple(extra_allowed_roots)` tambem em
  `_run_derivadas_sync_phase` e `_initialize_import_run_context`
  (pontos multi-uso que hoje sempre recebem tuple, mas esgotariam um
  gerador silenciosamente).
- **Mensagem de `x` ao recuar para base com filtro inicial** — coberto
  por commit anterior: distingue "pertence ao filtro base", "Filtro
  atual: ..." e "Nenhum filtro restante".

Decisoes registradas (nao aplicadas, por escopo):

- Candidato criado em `_prepare_working_database_for_import` que falha
  DEPOIS da criacao (ex.: integrity check) nao passa pelo cleanup do
  pre-flight — mantido como evidencia diagnostica, mesmo criterio do
  codigo existente para cancelamento.
- `except Exception` remanescentes em `utils/remote_itaipu.py` sao de
  loops de retry (semantica "tentar de novo qualquer erro"), mantidos.
- `dev_env/streamlit_app.py` com paths digitados continua limitacao
  conhecida (ver O9).

### O11. Mudanca de comportamento aprovada: copia de banco externo

Solicitado pelo usuario: o banco selecionado em "Carregar outro banco"
passa a ser **copiado para `data/`** em vez de usado in-place.

- `gui/ssa/database_operations.py::copy_database_into_data_dir`:
  snapshot consistente via backup API do SQLite com origem `mode=ro`
  (captura commits pendentes no WAL sem alterar a origem). Destino
  existente e arquivado como `.bak-<ts>` (ordem wal/shm/db). Origem ja
  dentro de `data/` e no-op. Falha na copia remove o destino parcial.
- `gui/gui_ssa.py::_finalize_database_candidate_validation`: `DB_PATH`
  passa a apontar para a copia em `data/`; falha de copia aborta a
  selecao com `reason="copy_failed"`. A copia so ocorre apos
  `_get_derivadas_sync_state` (preparacao sem efeito colateral primeiro).
- `dev_env/build/release_windows.ps1`: prompt interativo
  "Incluir data\ssas.db no pacote? [s/N]" quando `-IncludeRuntimeDb`
  nao foi passado; default N. `-Yes` (nao-interativo) mantem o default.
- `sys.path.insert` em `interface/cli.py` e `core/app_logic.py` agora
  condicional (`if project_root not in sys.path`), mesmo padrao do
  `streamlit_app.py`. Remocao completa segue pendente (empacotamento).
- `.github/CODE_QUALITY.md`: frase canonica em ingles restaurada,
  corrigindo a falha pre-existente do contrato de documentacao
  (teste `test_code_quality_documents_dynamic_dependency_submission_status`).

**Validacao O11**: 8 testes novos em `tests/test_database_operations.py`
(copia, WAL pendente, arquivo destino, origem dentro de data/, fonte
nao-sqlite, origem ausente) + 8 variacoes manuais de caminho (espacos/
acentos, `~`, symlink, auto-selecao, colisao com trio wal/shm, data/
inexistente, caminho relativo). 4 testes de GUI atualizados para o
contrato novo (DB_PATH aponta para a copia); a copia e stubada neles —
o comportamento real e coberto pelos testes de unidade do modulo.
Parse do ps1 verificado com pwsh.

**Ordem temporal**: a suite completa (2997 passaram, 9 skipped, 0
falhas, ~762s) rodou sobre o estado pos-O10, **antes** das mudancas
de O11. O11 foi validado pelos testes focados acima; reexecucao da
suite completa fica para o fechamento da rodada.
