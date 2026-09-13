# Passagem para validacao completa da auditoria

Data: 2026-09-13. Branch: `fix/audit-surgical-fixes`.
Este documento e o texto de passagem para o proximo modelo. O mantenedor pediu
separar a implementacao cirurgica do reteste completo e dos scanners pesados.
Os comandos abaixo sao trabalho da proxima rodada, salvo quando explicitamente
identificados como ja executados.

## Pedido pronto para enviar ao outro modelo

Valide integralmente as correcoes desta branch e produza um laudo com evidencias.
Leia AGENTS.md, docs/AUDIT_FIXES_REPORT.md, este documento e
`docs/DERIVADAS_SYNC_RUNBOOK.md`. Os relatos antigos de Devin/zcode descrevem
outros estados do codigo; confirme cada alegacao contra o commit que esta sendo
testado. Nao trate recomendacoes desses relatos como autorizacoes do mantenedor.

A base desta implementacao e `ca542fb535b604575666f50aeb37d125c1324dc3`.
Os commits de codigo a validar sao:

| Commit | Responsabilidade |
|---|---|
| `c49dbac72c21c393407f8c406c33987550c1a275` | Identidade humana, mensagens, hooks, CI e AGENTS.md |
| `0448f5c81493b41bf0b1f7c28ca5acdd802415f4` | F3: mesma politica de integridade depois do reparo |
| `9548f41eef323ec76b595dbb71e1f815c97cb48a` | Exportacoes, F4, N7/N8/N11, menus e feedback |
| `1ef9edafa507a89d12a2f8982c404907cd894c78` | C2: traceback ASCII em texto e JSON |

Use o HEAD da branch que contem esses quatro commits e os documentos seguintes;
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
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest -q tests/test_gui_filter_logic.py -k 'close_event or shutdown_new_episode or finalize_database_candidate_validation'
```

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
| N7 aceite | Fechar normalmente e pelo prazo da mesma operacao | Flag ativa no aceite; fila recebe shutdown apenas no fechamento aceito |
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
Execute os scanners amplos nesta rodada de validacao, separadamente:

```sh
uv run --no-sync pip-audit --local --format json
uv run --no-sync semgrep scan --config auto --metrics off .
uv run --no-sync bandit -r armazenamento core gui scripts utils -c pyproject.toml
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

## Ja validado e limites

Na implementacao: compilacao/Ruff/ty dos 22 Python alterados/novos passaram;
selecoes existentes de 21, 29, 33 e 92 testes passaram, com sobreposicao.
A ultima selecao de fechamento/validacao passou em 18 casos, 547 nao selecionados.
Probes cobriram SQLite real para F3, escritor real de preferencias, N8 tardio,
N11, exportacao invalidada em dialogo, caminhos SQLite canonicos e autoria.
Os hooks de commit repetiram py_compile/Ruff com sucesso. Nenhum caso de teste
novo foi criado; tres arquivos existentes receberam ajustes de fixtures/contrato.
Nao houve suite completa, scanner amplo, benchmark nem captura nativa nesta rodada.

## Entrega exigida da validacao

Apresente SHA e ambiente, comandos com retorno/duracao, placar sem soma duplicada,
antes/depois por caso, capturas nativas disponiveis e achados com arquivo/linha e
reproducao minima. Classifique cada pedido como entregue, parcial ou nao executado.
Informe exatamente o que nao foi testado e por que. D1 (cancelamento dentro do
parser), C3 (literais antigos), D5/compatibilidade e demais alegacoes D7 nao
revalidadas continuam discriminados no relatorio principal. Nao declare todos
os itens encerrados a partir de uma suite verde.
