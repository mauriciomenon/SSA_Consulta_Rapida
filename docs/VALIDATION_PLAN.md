# Passagem para validacao completa da auditoria

Data: 2026-09-13. Branch: `fix/audit-surgical-fixes`.
Este documento e o texto de passagem para o proximo modelo. O pedido inicial
separava a implementacao do reteste pesado. O pedido posterior autorizou
reproducao e estabilizacao local caso a tentativa de modelo externo falhasse;
essa tentativa falhou. A rodada K executou a suite completa em `0f239dac`,
com documentacao publicada em `c30f87da`. A rodada vigente A-E parte de
`c30f87da`; seu fechamento esta na secao L4 do relatorio. A rodada posterior de CI/CD
parte de b9672334 e esta discriminada na secao M.
Reteste final em `5b75f8f8`: 2969 passed, 9 skipped, 34 warnings e 11 subtests
passed em 706,03s, retorno 0; 613 Python inalterados durante a execucao.
Scanners amplos e ensaios nativos continuam separados. Os comandos abaixo sao
trabalho da proxima rodada quando nao identificados como ja executados.

Atualizacao apos os retornos: zcode informou 2923 passed, 1 failed, 9 skipped
e 11 subtests no 0beceb58. A falha de preparacao do teste de fechamento forcado
foi reproduzida e ajustada em 39e7c16a; 27 testes locais passaram. A rodada
seguinte corrige oito falhas de producao, com 83 testes dos controladores e
47 casos selecionados aprovados. Suite completa local no codigo 0f239dac:
2938 passed, 9 skipped, 34 warnings e 11 subtests passed em 701,80s; exit 0.
Os onze Python ficaram iguais durante aquela execucao; ver secao K. Esse
placar e historico e nao aprova o diff A-E posterior.

## Passagem de CI/CD para a PR

A PR preparada e a numero 131 no GitHub principal, com base dev. O primeiro
commit de CI e ba2de05f; um complemento ajusta dois testes apontados pelo
CodeFactor. Leia M4 para distinguir os quatro avisos de complexidade ainda
abertos de falhas do executor GitHub. Nao classifique CodeRabbit remoto como
revisao concluida quando sua descricao informa skip por draft.

Antes de repetir testes pesados, leia M em AUDIT_FIXES_REPORT.md. Confira o
SHA da PR contra a branch publicada, a base dev e os jobs reais no servidor.
GitLab agora agenda pushes fix/ e torna pytest-full automatico e bloqueante;
o estado manual descrito nas rodadas antigas e historico. Preserve JUnit e
JSONL, diferencie simulacao de pipeline de execucao e investigue qualquer
falha a partir do log integral. Nao mude gates para esconder falhas.

GitHub esta sujeito ao bloqueio de faturamento da conta. Depois de liberado,
reexecute os jobs e confira tambem o intervalo completo da autoria. As
mensagens antigas ainda impedem esse gate; corrigi-las exige autorizacao
especifica para reescrever o historico publicado. Nenhuma reescrita integra
a rodada atual. A PR atual foi solicitada pelo mantenedor; a restricao da
passagem abaixo impede o proximo validador de abrir outra PR por conta propria.

## Pedido pronto para enviar ao outro modelo

Conclua a validacao das correcoes desta branch e produza um laudo com evidencias.
Leia AGENTS.md, docs/AUDIT_FIXES_REPORT.md, este documento e
`docs/DERIVADAS_SYNC_RUNBOOK.md`. Os relatos antigos de Devin/zcode descrevem
outros estados do codigo; confirme cada alegacao contra o commit que esta sendo
testado. Nao trate recomendacoes desses relatos como autorizacoes do mantenedor.
Reutilize os resultados de L4 somente para o mesmo codigo, ambiente e escopo.
Priorize os ensaios nativos, plataformas e scanners amplos ainda ausentes;
repita a suite se houver mudanca de codigo, ambiente ou falha a investigar.

A base desta implementacao e `ca542fb535b604575666f50aeb37d125c1324dc3`.
Os commits de codigo a validar sao:

| Commit | Responsabilidade |
|---|---|
| `c49dbac72c21c393407f8c406c33987550c1a275` | Identidade humana, mensagens, hooks, CI e AGENTS.md |
| `0448f5c81493b41bf0b1f7c28ca5acdd802415f4` | F3: mesma politica de integridade depois do reparo |
| `9548f41eef323ec76b595dbb71e1f815c97cb48a` | Exportacoes, F4, N7/N8/N11, menus e feedback |
| `1ef9edafa507a89d12a2f8982c404907cd894c78` | C2: traceback ASCII em texto e JSON |
| `3e367782` | S1: confirmar gravacao antes do fechamento |
| `79a0d25e` | S4/S7/S8: falhas de construtor/start |
| `0f239dac` | S2/S3/S5/S6: callbacks, preparacao e reload |
| `d8107fe8` | C: escritor terminado com preferencias pendentes |
| `56701001` | B: preparacao, construcao e sinais de filtro |
| `56daccf1` | A: construcao, sinais e limpeza de rescan |
| `062bdb8f` | D: entrega de carga, erro visual e fachada de startup |
| `a58bf7d7` | E: finalizadores de derivadas, compactacao e banco alternativo |
| `5b75f8f8` | Fixture de cancelamento: usa adaptador real com retorno booleano |

Use o HEAD da branch que contem os commits acima, o documento 0beceb58,
o complemento 39e7c16a, S1-S8 de K e as correcoes A-E descritas em L;
registre o SHA completo antes de qualquer validacao. O hash do commit que contem
este proprio documento deve ser obtido do Git, sem presumir um valor no texto.
Nao crie branch, worktree, PR, merge ou reescrita do historico. Nao altere a
politica A5, nao remova APIs e nao use bancos, planilhas ou credenciais de
producao nos testes. Preserve alteracoes concorrentes. Apresente o plano antes
de executar; reproduza e relate falhas antes de propor qualquer novo patch.

## Preparacao e evidencia

Execute cada comando separadamente, guardando saida, erro, codigo de retorno,
duracao, versao da ferramenta, sistema operacional e arquitetura. Um timeout,
comando indisponivel, coleta vazia ou erro de ambiente nao conta como aprovacao.
Nao capture o retorno de `tail` ou `tee` como se fosse o retorno da ferramenta;
execute sem pipe ou preserve explicitamente o status do comando original.
Para comparar somente A-E use `git diff c30f87da..HEAD` apos os commits;
antes deles, use `git diff c30f87da` e registre que o conteudo ainda e local.
Para a implementacao anterior use `git diff 0beceb58..HEAD`; o arquivo local
AUDIT_IMPLEMENTATION_DIFF.patch.md nao e versionado nem necessario a revisao.

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git diff --stat ca542fb535b604575666f50aeb37d125c1324dc3..HEAD
git log --format=fuller ca542fb535b604575666f50aeb37d125c1324dc3..HEAD
uv --version
uv run --no-sync python --version
```

Use o ambiente existente. Se faltarem dependencias, confira o lock antes de
preparar o ambiente com `uv sync --frozen --extra dev`; nao atualize dependencias
nem substitua versoes para conseguir um resultado verde.

## Validacao estatica e suite completa

Compile os arquivos Python alterados desde a base usando a lista real do Git:

```sh
uv run --no-sync python - <<'PY'
import py_compile
import subprocess
from pathlib import Path

changed = subprocess.check_output([
    'git', 'diff', '--name-only', '--diff-filter=ACMR',
    'ca542fb535b604575666f50aeb37d125c1324dc3..HEAD', '--', '*.py',
], text=True).splitlines()
for filename in changed:
    if Path(filename).is_file():
        py_compile.compile(filename, doraise=True)
print(f'Compilacao concluida: {len(changed)} arquivos.')
PY
uv run --no-sync ruff check .
uv run --no-sync ty check
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q
uv run --no-sync python scripts/check_docs.py --fail-on-issues --paths AGENTS.md docs/VALIDATION_PLAN.md docs/AUDIT_FIXES_REPORT.md docs/DERIVADAS_SYNC_RUNBOOK.md
```

A suite completa deve produzir um placar novo. Os 2924 passed/9 skipped relatados
antes desta implementacao nao comprovam o HEAD atual. Nao some subconjuntos que
se sobrepoem como se fossem casos distintos. Para diagnostico focado:

```sh
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_derivadas_cli.py tests/test_derivadas_sync_controller.py tests/test_derivadas_sync_job.py tests/test_database_verification.py tests/test_rescan_worker_advanced.py tests/test_rescan_worker_cleanup.py tests/test_rescan_progress_dialog.py tests/test_gui_preferences_atomic_write.py tests/test_filter_ui_state.py tests/test_ascii_logging_filter.py tests/test_gui_menu_import_external.py
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py -k 'close or shutdown or other_database or candidate'
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py::TestGUIFilterLogic::test_forced_close_disconnects_pending_workers tests/test_gui_filter_logic.py::TestGUIFilterLogic::test_shutdown_new_episode_resets_force_deadline
```

O seletor antigo com `close_event` excluia `forced_close_disconnects_pending_workers`.
Os node IDs acima garantem verificar a desconexao apos o prazo da mesma operacao
e o reinicio do prazo para uma operacao diferente. Nao remover um caso para
conseguir suite verde.

## Casos obrigatorios e resultado esperado

| Caso | Preparacao/acao | Resultado exigido |
|---|---|---|
| CLI antiga | sync/heal/maintenance sem flags novas | Mesmo contrato de stdout JSON e codigos anteriores |
| Tres formatos | Solicitar JSON, CSV e TSV juntos | JSON completo; CSV/TSV com cabecalho e reconciliacao real; stdout parseavel |
| Sem reconciliacao | heal/maintenance que nao precisam sincronizar | JSON preservado; CSV/TSV nao inventam zeros; stderr e retorno 1 |
| Erro em um destino | Falhar uma gravacao depois da operacao | Demais exportacoes tentadas; stdout preservado; banco nao revertido |
| Sobrescrita | Destino existente, sem/com flag | Recusa sem flag; substituicao completa com autorizacao; conteudo antigo preservado se serializacao falhar |
| Corrida de destino | Arquivo surge entre validacao e publicacao sem overwrite | Arquivo concorrente preservado; falha explicita |
| Caminhos protegidos | DB, WAL/SHM/journal, planilhas, symlink e hard link | Nenhum arquivo de entrada sobrescrito; DB canonico protege seus auxiliares |
| Destinos invalidos | Repetidos, pasta inexistente, diretorio, sem permissao, espacos | Erro claro; nenhuma operacao iniciada quando a prevalidacao falha |
| Sistema sem hard link | Exportar sem overwrite em volume sem suporte | Falha clara; nao substituir destino nem aceitar gravacao parcial |
| API Python | Chamadas antigas JSON/CSV e nova TSV | API preservada; overwrite=True continua padrao apenas na chamada direta |
| GUI formatos | Sincronizar e exportar em cada formato | JSON completo; CSV/TSV uma linha por fase db/sheets; sem repetir sync |
| GUI dialogos | Cancelar, completar extensao, recusar sobrescrita | Sem arquivo indevido e sem efeito na sincronizacao |
| GUI resultado invalido | Trocar banco ou iniciar sync durante qualquer dialogo, inclusive segunda confirmacao | Aviso e zero exportacoes do relatorio invalidado |
| F3 | Coluna opcional ausente + duplicata/status inconsistente | Primeira tentativa aceita com aviso; segunda coerente; dados preservados |
| F3 bloqueios | Falhar acesso/tabela/schema/SQLite/permissao isoladamente | Falha continua bloqueante antes e depois de reparar |
| F4 | ImportOutcome com ressalvas nao bloqueantes | Worker transmite report real; dialogo/status preservam ressalvas depois de concluir/recarregar |
| F4 falha | Importacao ou recarga falha | Erro continua visivel, sem mensagem de sucesso fabricada |
| N8 | A expira, B conclui, A entrega depois | Apenas B aplicado uma vez; resultado pronto de B nao apagado |
| N7 flag/timers | X durante worker, fechamento adiado | Flag restaurada, timers vivos, filtros e conclusoes continuam funcionando |
| N7 preferencias | Escrita 1 bloqueada, flush expira, salvar 2, liberar escrita | Fila aceita 2 e grava [1,2]; nao inicia segundo escritor concorrente |
| N7 aceite | Fechar normalmente e pelo prazo da mesma operacao; no teste forcado, registrar o mesmo worker como operacao anterior | Flag ativa no aceite, sinais desconectados; fila recebe shutdown apenas no fechamento aceito |
| N11 Qt/derivadas | Operacao A termina, B nova; primeiro X em B | Prazo novo, incluindo transicao de preferencias para Qt/derivadas |
| N11 mesma operacao | Repetir X durante mesma operacao apos 30s | Politica de fechamento forcado existente mantida, sem auto-retry |
| Menus | Carga/rescan/derivadas/SAM/vacuum/validacao ativos; tentar outro caminho | Acoes conflitantes bloqueadas e restauradas em sucesso, erro e falha de start |
| Corrida no dialogo | Iniciar operacao concorrente enquanto dialogo esta aberto | Nova guarda impede iniciar operacao conflitante apos o dialogo |
| Progresso | Usar filtro/navegacao durante derivadas | Progresso e status nao somem; navegacao permitida preservada |
| Callback antigo | Poll/finished da operacao anterior chega durante uma nova | Nao desbloqueia nem finaliza a operacao nova |
| Feedback | Importar lista, exportar lista, falhar carga, falhar abertura de guia | Quantidade/destino visiveis; dados antigos identificados; sem falso sucesso |
| C2 | Excecao com caracteres acentuados, handlers texto e JSON | Tipo, pilha e mensagem legivel preservados; sem caracteres apagados |

## Autoria, hooks e CI

```sh
uv run --no-sync python scripts/validate_git_authorship.py range ca542fb535b604575666f50aeb37d125c1324dc3 HEAD
shellcheck scripts/install_hooks.sh scripts/git_hooks/pre-push scripts/git_hooks/commit-msg
```

Em repositorio descartavel, sem modificar refs do projeto, confira identidade
efetiva por ambiente/--author, autores e committers estranhos, mensagens com
credito proibido, tagger, tags anotadas, notas intermediarias removidas no mesmo
push, refs/replace, historico raso e mensagens Latin-1/CP1252. Verifique instalacao
idempotente e preservacao de hooks preexistentes. Valide PR com head real e MR
com a base correta, sem atribuir autoria ao merge sintetico de CI.

Ha 16 mensagens antigas com credito proibido em `e62a85bf..ca542fb5`. Validar
`dev..HEAD` deve acusa-las. Isso e passivo conhecido, nao motivo para enfraquecer
a regra. Remover essas mensagens exige reescrita especificamente autorizada e
muda tambem hashes dos descendentes; esta passagem nao autoriza essa operacao.

Os hooks sao contornaveis. CI roda depois do push e somente nos eventos
configurados; o push simples desta branch nao aciona minimal-ci nem o pipeline
GitLab sem um evento adicional aplicavel. Nao afirmar que existe bloqueio nativo
universal. Consulte os checks do SHA testado; nao dispare novos jobs pesados
apenas para substituir a validacao local sem registrar escopo e custo.

## Scanners e plataformas

Confira primeiro a disponibilidade e a sintaxe pela ajuda das versoes instaladas.
Execute os scanners amplos nesta rodada de validacao, separadamente. O caminho
de pip-audit deve ser o site-packages da .venv do aplicativo, nao o ambiente
que instalou a ferramenta. O comando abaixo resolve esse caminho no shell
POSIX; no PowerShell obtenha o mesmo valor de sysconfig e passe-o a --path.
Semgrep usa p/python com metrics off: config auto e metrics off sao
incompativeis na versao encontrada.

```sh
uv run --no-sync pip-audit --path "$(uv run --no-sync python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" --format json
uv run --no-sync semgrep scan --config p/python --metrics off .
uv run --no-sync bandit -r armazenamento core gui scripts utils
uv run --no-sync vulture armazenamento core gui scripts utils
uv run --no-sync detect-secrets scan --all-files
gitleaks dir . --redact --exit-code 1 --no-banner
trufflehog git "file://$PWD" --no-update --only-verified --json
```

Use o uv para ferramentas Python; registre indisponibilidade em vez de instalar
ou atualizar pacotes silenciosamente. Preserve baseline e configuracoes existentes.
Nao divulgue valores de segredos encontrados; relatorios compartilhados devem
conter localizacao e classificacao com valores ocultos. Analise ShellCheck dos
scripts afetados e PSScriptAnalyzer nos scripts PowerShell pertinentes a validacao
Windows. Nenhum PowerShell foi alterado nesta implementacao.

Separe achado novo, preexistente, falso positivo comprovado, falha de ferramenta
e timeout. Ausencia de caller detectada por Vulture/AST nao autoriza remover API.

Em macOS arm64, Windows 11 amd64/arm64, Debian e Arch/Artix amd64/arm64, registre
quais plataformas foram realmente acessiveis. Inspecione a GUI nativa com
capturas: menus, formatos, ressalvas, redimensionamento, fechamento adiado e
retomada. Qt offscreen nao substitui essa evidencia. Meca CPU/RSS e tempo nos
fluxos alterados com os mesmos dados, separando carga inicial de repeticoes.
Nao invente comparacao de desempenho se nao houver base executada equivalente.

## Contratos S1-S8, introduzidos apos 39e7c16a

Casos de regressao foram acrescentados aos arquivos existentes apenas para as
falhas reproduzidas. Executar todos os controladores e a selecao de fechamento:

```sh
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_pai_api_controller.py tests/test_gui_preferences_atomic_write.py tests/test_derivadas_sync_controller.py tests/test_gui_workers_rescan_data.py
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py -k 'close or shutdown or other_database or candidate'
```

Conferir os contratos abaixo, incluindo a tentativa seguinte:

| Cenario | Resultado exigido |
|---|---|
| Preferencias: escrita retorna False ou lanca | `flush` levanta OSError; fechar informa erro e restaura flag. `shutdown` sozinho so confirma termino da thread |
| Preferencias: A falha, B ainda pendente | Espera curta retorna False enquanto B trabalha; B bem-sucedida permite flush True. Excecao terminal nao pode deixar espera infinita |
| SAM: A termina, B inicia, chegam sinais de A | Status, confirmacao, carga e referencia de B permanecem intactos; B ainda entrega resultados |
| SAM: construtor/reset/connect/start falha | Retorno False, status de falha, nenhuma referencia indevida; proxima tentativa inicia |
| SAM: sucesso seguido de reload falho | Erro de recarga visivel; nao reimportar nem perder referencia antes de finished |
| Derivadas: construtor/start falha | running=False, lock liberado e UI restaurada pelo finalizador |
| Compactacao/banco alternativo: construtor/start falha | Flag/referencia liberadas, erro informado, nenhum polling iniciado e nova tentativa aceita |
| Rescan: sucesso/erro/cancelamento/finished antigos | Dialogo antigo pode concluir; status, carga e referencias atuais permanecem |

Evidencia historica de `0f239dac`: 83 casos dos controladores aprovados em 0,61s; selecao conjunta
de fechamento/concorrencia com 47 passed, 602 deselected em 29,18s. Nao somar
placares sobrepostos. py_compile/Ruff/ty passaram nos onze Python alterados; os 21 testes do
menu/importacao passaram, incluindo quatro casos de construtor/start.
CodeRabbit CLI 0.7.6: review_completed, dez arquivos, 0 issues. O complemento
de construtores teve revisao local independente. A suite completa passou com
2938 passed, 9 skipped, 34 warnings e 11 subtests passed em 701,80s, exit 0,
no conteudo de 0f239dac. Executada em macOS arm64/Python 3.13.12/Qt 6.11.0,
com offscreen. A chamada Pi/Kimi falhou e nao forneceu parecer; exit 0 da CLI
com mensagens de erro do modelo nao representa aprovacao.

## Evidencia das rodadas anteriores e limites

Retornos externos do 0beceb58: suite reprovada informada pelo zcode; selecao de
22 aprovada pelo Devin. Complemento local: uma linha na preparacao do teste,
py_compile/Ruff/ty aprovados e 27 passed, 538 deselected em 22,31s.
Esses resultados nao constituem nova execucao da suite completa. O Semgrep
externo informou dois ERROR classificados como falsos positivos; obter a saida
bruta e validar a justificativa antes de encerrar essa analise. Os outros
scanners amplos nao possuem resultado nos anexos recebidos.


Na implementacao: compilacao/Ruff/ty dos 22 Python alterados/novos passaram;
selecoes existentes de 21, 29, 33 e 92 testes passaram, com sobreposicao.
A ultima selecao de fechamento/validacao passou em 18 casos, 547 nao selecionados.
Probes cobriram SQLite real para F3, escritor real de preferencias, N8 tardio,
N11, exportacao invalidada em dialogo, caminhos SQLite canonicos e autoria.
Os hooks de commit repetiram py_compile/Ruff com sucesso. Nenhum caso de teste
novo foi criado; tres arquivos existentes receberam ajustes de fixtures/contrato.
Nao houve suite completa, scanner amplo, benchmark nem captura nativa nesta rodada.

## Rodada A-E, base c30f87da

Leia o antes/depois e a evidencia da secao L do relatorio. Nao reaproveite o
placar historico de 2938 passed. Registre a revisao efetivamente executada e
confirme que o codigo ficou estavel durante a verificacao.

```sh
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_workers_rescan_data.py tests/test_contract_data_load_stale_guard.py tests/test_gui_preferences_atomic_write.py tests/test_derivadas_sync_controller.py tests/test_gui_menu_import_external.py
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py -k 'initiate_filtering or filter_worker or filter_finished or filter_error or sync_filter or on_data_loaded or on_load_error or other_database or candidate or vacuum or derivadas'
```

Verifique a coleta antes da execucao se novos nomes de casos forem adicionados.
A suite completa e os scanners usam os comandos das secoes anteriores; se forem
executados pelo implementador, registre o resultado em L4 e mantenha nesta
passagem apenas as verificacoes que realmente restarem.

| Residual | Evidencia exigida |
|---|---|
| A | Falha no construtor, preparacao, sinais obrigatorios e partida de rescan; dialogo, referencia e registro liberados; nenhuma alteracao de outra operacao; nova tentativa conclui |
| B | Token/construtor/sinais/retencao/start e termos/fonte/modo/colunas; busca e progresso coerentes apos erro; cancelamento da tentativa antiga e entrega da nova |
| C | Termino antes da escrita com preferencia pendente gera OSError em flush; encerramento vazio continua True e gravacao bem-sucedida posterior limpa erro |
| D | DataFrame com colunas numero_ssa duplicadas por QTimer real em subprocesso; nenhuma excecao escapa, busy libera e proxima carga conclui. Falha anterior conserva tabela; posterior informa exibicao incompleta; retorno False de refresh nao vira sucesso. Encaminhamento pela fachada precisa mostrar a janela no startup e preservar contexto/modal/retencao |
| E | Finalizador de derivadas falha em entrega/timeout/start_failed; relatorio invalidado, thread viva retida, UI recuperada. Vacuum/banco esperam termino nativo. Falha antes de selecionar preserva banco anterior; falha posterior conserva banco novo com orientacao de recarga; tentativa seguinte conclui |

O ensaio Qt de D registrado nesta rodada passou de SIGABRT (-6) para retorno 0
com busy=False. Execute qualquer caso que possa abortar em subprocesso isolado,
sem bancos/configuracoes de producao e sem instalar excepthook global para
mascarar o erro. Offscreen, callbacks controlados e janela nativa sao evidencias
diferentes. Nao declarar validacao visual por um subprocesso que apenas terminou.

C usa `debounce_seconds=float("inf")` como falha controlada da espera. Nao tratar
o teste extremo como medida da probabilidade em producao. `flush()` confirma
escritor/replace; OSError no fsync temporario/diretorio ainda e tolerado em
`core/config_manager.py`. A politica nao foi alterada e durabilidade absoluta
nao foi demonstrada.

### Scanners ja executados no escopo A-E

Semgrep p/python passou com 1066 regras sobre seis arquivos; Bandit,
detect-secrets, TruffleHog filesystem sem verificacao online e Gitleaks no diff
nao encontraram achados nesse escopo. Vulture informou 18 imports nao usados,
todos presentes na base c30f87da. ShellCheck passou nos hooks/instalador;
PSScriptAnalyzer scripts/ informou 59 avisos e zero erros. Esses resultados
nao aprovam uma varredura de todo o repositorio/historico.

pip-audit executado com --path da .venv examinou 46 dependencias externas sem
vulnerabilidades conhecidas; das 47 entradas, o pacote local 4.50.0 nao esta
no PyPI e foi ignorado. A execucao default auditava 28 entradas do ambiente da
ferramenta e nao deve ser citada como prova das dependencias do aplicativo.

CodeRabbit 0.7.6 encontrou um major em D: erro contornava a fachada responsavel
por mostrar a janela no startup. Foi corrigido o encaminhamento e acrescentada
regressao. Conferir resultado integrado em L4; nao converter o parecer em
"zero achados" depois de aplicar a correcao.

### Primeira execucao global e correcao da fixture

A suite em a58bf7d7 terminou com 4 failed, 2965 passed, 9 skipped, 34 warnings
e 11 subtests passed em 669,06s; retorno 1. As quatro falhas eram variantes de
`test_late_cancel_after_success_reloads_committed_changes`: a fixture conectava
o sinal, mas retornava None, em desacordo com a confirmacao booleana agora
exigida pelo ciclo de vida. Reproducao focada: quatro falhas em 0,19s.

5b75f8f8 troca essa fixture por `_connect_signal`, o adaptador real. Nenhuma
assercao foi removida, nenhum caso foi ignorado e nenhum arquivo de producao
mudou. `test_import_outcome_isolation.py` e `test_gui_workers_rescan_data.py`
passaram juntos: 68 passed em 0,30s. O resultado do reteste global e registrado
separadamente em L4; nao renomear a execucao inicial como aprovada.

## Entrega exigida da validacao

Apresente SHA e ambiente, comandos com retorno/duracao, placar sem soma duplicada,
antes/depois por caso, capturas nativas disponiveis e achados com arquivo/linha e
reproducao minima. Classifique cada pedido como entregue, parcial ou nao executado.
Informe exatamente o que nao foi testado e por que. D1 (cancelamento dentro do
parser), C3 (literais antigos), D5/compatibilidade e demais alegacoes D7 nao
revalidadas continuam discriminados no relatorio principal. Nao declare todos
os itens encerrados a partir de uma suite verde.
