# SSA Consulta Rapida

Aplicacao para importar planilhas de SSAs para um banco SQLite local e
consultar, filtrar e exportar os dados, com tres interfaces: terminal (CLI),
desktop (PyQt6) e web (Streamlit).

## Versao

Versao do codigo nesta candidata local: **4.51**. A ultima release publicada e **v4.50**. As fontes centrais sao `VERSION`, `config/version.json` e os metadados do pacote.

[Notas da candidata](RELEASE_NOTES_v4.51.md)

A documentacao operacional detalhada fica em `docs/`; apenas os guias
exigidos por testes e empacotamento sao versionados.

## Execucao

Use um checkout e ambiente Python nativos do sistema operacional. Nao compartilhe a pasta `.venv` entre sistemas.

No macOS ou Linux, execute a partir da raiz do repositorio:

```bash
bash -c 'source scripts/env/direnv_common.sh &&
ssa_env::apply &&
ssa_native_guard_tools uv &&
uv run --no-sync main.py --gui'
```

Interfaces e opcoes principais:

```bash
uv run --no-sync python main.py              # interface de terminal
uv run --no-sync python main.py --gui        # desktop PyQt6
uv run --no-sync python main.py --streamlit  # web local (127.0.0.1)
uv run --no-sync python main.py --force-rescan   # reimporta ignorando cache
uv run --no-sync python main.py --reset-db       # recria o banco do zero
uv run --no-sync python main.py --help           # todas as opcoes
```

No Windows, use PowerShell e o ambiente nativo descrito no [guia de ambiente](dev_env/ENVIRONMENT_GUIDE.md).

### Variaveis de ambiente

Nenhuma e obrigatoria. Flags booleanas ligam com `1`, `true`, `yes` ou `on`.

| Variavel | Efeito | Padrao |
|---|---|---|
| `SSA_DB_PATH` | Banco SQLite usado pela CLI, GUI e manutencao | `data/ssas.db` da raiz (do runtime, no pacote) |
| `SSA_RUNTIME_ROOT` | Raiz de dados, logs e `docs_saida` | raiz do codigo; no pacote, pasta do usuario |
| `SSA_CONFIG_DIR` | Pasta de configuracao (valor invalido gera aviso e cai no padrao) | `config/` da raiz do codigo |
| `SSA_TABLE_NAME` | Tabela consultada pela CLI (a GUI usa sempre `ssa_table`) | `ssa_table` |
| `SSA_NON_INTERACTIVE` | Flag: sem prompts nem paginacao (CLI) e sem confirmacao de limpeza (GUI) | desligada |
| `SSA_CACHE_MAX_MB` / `SSA_CACHE_MAX_TOTAL_MB` | Limite por item / total do cache de filtros (GUI e web); `0` = sem limite | 16 / 16 |
| `SSA_SCRAP_REPORT_ROOT` | Pasta do `scrap_report` (SAM API, GUI e script) | - |
| `SSA_ALLOW_SIBLING_SCRAP_REPORT` | Flag: procurar o `scrap_report` na pasta irma do projeto | ligada |
| `SSA_SCRAP_REPORT_RUNNER` | Executor do `scrap_report` (`uv` ou `pythonpath`), GUI e script | `uv` |
| `PAI_API_DEFAULT_SECRET_SERVICE` | Nome do servico no keyring para a credencial do SAM API | `scrap_report.sam` |
| `SSA_TSM_DEBUG` | Flag (macOS): nao filtra as mensagens TSM/Qt do stderr | desligada |
| `NO_COLOR` | Saida da CLI sem cores | - |

Uso interno: os launchers do pacote definem `SSA_RUNTIME_ROOT`, `SSA_CONFIG_DIR`, `SSA_DB_PATH` (sobrescrevem o valor herdado), `SSA_BUNDLED_ROOT` e `SSA_EXTRA_ALLOWED_PATHS`; `SSA_SMOKE_TEST` e do smoke de build e `SSA_SYNC_FILTER` dos testes da GUI. A interface web le tambem `SSA_DOCS_DIR`, `SSA_STREAMLIT_API_TIMEOUT_SECONDS`, `SSA_STREAMLIT_LARGE_PAGE_GUARD`, `SSA_STREAMLIT_UI_STATE_FILE`, `ITAIPU_BASE_PENDING` e `ITAIPU_BASE_DETAIL`.

Sem suporte (ainda lidas, remocao prevista; nao defina): `SSA_ALLOWED_COLUMNS`, `SSA_UPSERT_SHORT_CIRCUIT_POLICY`, `SSA_ENABLE_COMPLEMENTARY`, `SSA_STATUS_ORDER`, `SSA_DESC_COLUMNS`, `SSA_TERMINAL_STATUSES`.

## Dados e importacao

- O startup nao importa planilhas automaticamente; a importacao e disparada
  por acao (botao Reescanear na GUI, `--force-rescan` na CLI).
- As planilhas-fonte ficam na pasta de documentos configurada; o banco fica
  em `data/`. "Atualizar dados" (GUI) e incremental: arquivos ja processados
  sao reconhecidos por controle de estado, e cada SSA atualiza seu proprio
  registro (upsert por `numero_ssa`). O `--force-rescan` e a reanalise
  completa: recria o banco so com as planilhas presentes (o anterior fica em
  `data/ssas.db.full_rescan_backup_*`).
- Um banco por usuario: o lock que serializa as gravacoes fica na pasta
  temporaria de cada usuario, entao o mesmo `ssas.db` aberto por usuarios
  diferentes (pasta de rede, OneDrive compartilhado) nao e protegido contra
  gravacoes simultaneas e nao e suportado.
- Planilhas especiais cujo nome comeca com `SSAs Derivadas e Relacionadas`
  nao entram na fase comum: suas arestas alimentam a fase dedicada de
  derivadas.
- Arquivos processados sao movidos para `processadas/` com nomes
  reservados atomicamente; conflitos e falhas por arquivo sao reportados
  sem abortar o lote.
- Datas e duracoes ficam em ISO no banco (`YYYY-MM-DD HH:MM:SS`, `P1Y9M22DT5H47M`);
  so a exibicao formata (datas dd/mm/aaaa, Tempo Excedido no formato do SAM).
- O resumo da importacao separa SSAs novas, atualizadas (algum valor mudou) e
  verificadas (mesmos dados, so o arquivo de origem foi atualizado).
- Bancos, planilhas e configuracoes pessoais ficam fora do controle de versao.

Detalhes da importacao nos docs locais `ARQUITETURA_IMPORTACAO.md`,
`ARCH_DB_UPSERT.md` e `TROUBLESHOOTING_IMPORTACAO.md`.

## Derivadas

As relacoes pai-filho entre SSAs vem de duas fontes: o campo `derivada_de`
das planilhas comuns e as planilhas especiais `SSAs Derivadas e
Relacionadas*.xlsx`. A sincronizacao materializa a matriz, o fecho
transitivo e o sumario em tabelas dedicadas (`ssa_derivada_*`), dentro de
uma unica transacao com verificacao de consistencia.

Quando ocorre:

- apos a importacao, quando ha planilhas especiais no lote ou arquivos
  processados com relacoes novas;
- automaticamente, quando o banco tem arestas sem materializacao ou o
  ultimo run falhou (preflight cacheado por estado do arquivo — sem custo
  quando nada mudou);
- no full rescan, dentro do banco candidato antes da promocao;
- por acao manual: menu `Banco de dados > Atualizar derivadas` na GUI ou
  `scripts/derivadas_cli.py sync` na CLI.

Um run com falha fica registrado como `error` em `ssa_derivada_sync_run` e
e refeito na proxima importacao — falha nunca passa em silencio.

## Relatorios de derivadas

A CLI de derivadas continua imprimindo o resultado JSON no stdout. Os comandos
`sync`, `heal` e `maintenance` tambem aceitam `--report-json`, `--report-csv` e
`--report-tsv` para salvar arquivos, inclusive os tres formatos na mesma execucao.
JSON preserva o resultado completo; CSV e TSV resumem a reconciliacao. Arquivos
existentes exigem `--overwrite-reports`.

Na GUI, use `Database > Exportar relatorio de derivadas...` apos uma sincronizacao
manual concluida. O dialogo oferece JSON, CSV e TSV do ultimo resultado valido
para o banco atual. Trocar de banco ou iniciar outra sincronizacao invalida esse
resultado.

Guia de derivadas, plano de validacao e relatorio de correcoes nos docs
locais `DERIVADAS_SYNC_RUNBOOK.md`, `VALIDATION_PLAN.md` e
`AUDIT_FIXES_REPORT.md`.

## Recuperacao do banco

Snapshots consistentes sao gravados periodicamente em
`data/historico_backups/`. Na inicializacao da importacao:

- **banco ausente ou zerado**: o snapshot valido mais recente e restaurado
  (snapshots com dados tem prioridade sobre vazios); sem snapshot
  utilizavel, o schema e criado vazio;
- **banco corrompido**: o original e preservado como evidencia forense
  `.corrupt_<timestamp>.db` e o snapshot valido mais recente assume;
- **falha critica durante a restauracao**: a operacao aborta e o estado em
  disco e preservado para analise — nada e recriado por cima.

Selecionar um banco externo pela GUI copia o arquivo para `data/` com
validacao estritamente de leitura da origem (sem tocar no arquivo do
usuario) e promocao atomica com arquivamento do anterior.

## Exportacoes

- **Lista filtrada**: CSV, XLSX e JSON pela CLI; TSV pela GUI. Celulas
  iniciadas por `=`, `+`, `-`, `@` ou controles sao neutralizadas contra
  injecao de formula em planilhas.
- **Relatorios de derivadas**: JSON/CSV/TSV pela CLI ou pela GUI (secao
  acima).
- **Grafo de derivadas de uma SSA**: PNG/SVG/Mermaid a partir do dialogo
  de detalhes na GUI.
- Textos exibidos no terminal passam por sanitizacao de caracteres de
  controle (ANSI/OSC) para impedir sequestrar a saida.

## CI e validacao

O GitHub verifica PRs para `main`/`dev`/`rev` e pushes nessas branches. O GitLab
verifica MRs, a branch padrao, execucoes manuais e pushes em `dev`, `rev` e
branches `fix/`; a suite completa e automatica. So `main` (e PR/MR para ela)
reprova a execucao; nas demais branches a falha aparece sem reprovar. O secret
scan bloqueia em qualquer branch. Os gates publicam
diagnosticos e o GitLab preserva JSONL e relatorio JUnit por 14 dias. O log da
suite identifica cada teste e resume as 20 maiores duracoes.

Contratos de CI e resultados de PR nos docs locais `TESTING_STRATEGY.md` e
`AUDIT_FIXES_REPORT.md`.

## Distribuicao

Builds partem de `dev`, com o mesmo commit de origem e ambientes separados por
sistema e arquitetura. Cada entrega exige verificacao dos metadados, arquitetura,
smoke da CLI e abertura visual da GUI a partir do pacote.

| Alvo | Ambiente Windows | Saida dos executaveis | Pacote no Mac |
| --- | --- | --- | --- |
| Windows AMD64 | `.venv-win` | `launchers/dist/windows_amd64/` | `builds/packages/windows_amd64/` |
| Windows ARM64 | `.venv-win-arm64` | `launchers/dist/windows_arm64/` | `builds/packages/windows_arm64/` |
| macOS ARM64 | Nao se aplica | `launchers/dist/macos_arm64/` | DMG no mesmo diretorio |

Na VM VMware Windows 11 ARM64, AMD64 usa Python x64 sob emulacao e produz PE
AMD64; ARM64 usa Python ARM64 nativo e produz PE ARM64. O build macOS ARM64 roda
no Mac. Configuracoes, ambientes internos e temporarios do builder ficam em
`launchers/platforms/<alvo>/`, sem compartilhar artefatos entre alvos.

Os comandos Windows usam explicitamente `-Platform windows_amd64` ou
`-Platform windows_arm64`; o comando macOS usa `--platform macos_arm64`.
Os ZIPs Windows devem ser copiados da VM para os diretorios do Mac indicados
acima, comparando SHA-256 na origem e no destino.

Entregar assim que os pacotes solicitados passarem nessas verificacoes. Registrar
limites de validacao no relatorio da entrega; ampliar testes somente diante de
falha concreta. Uma correcao posterior apenas de documentacao nao exige rebuild.

[Guia de distribuicao](docs/GUIA_DISTRIBUICAO.md). Comandos por alvo e
detalhes do builder nos docs locais `BUILD_WINDOWS_ARM64_AMD64.md` e
`BUILD_MULTIPLATFORM.md`.

### Pasta do clone (guarda nativa)

Os scripts de ambiente, testes, hooks e build (`release.ps1`, `release.sh`,
`.envrc`, `dev_env/`, `scripts/env/`, `scripts/run_tests.sh`,
`scripts/install_hooks.sh`) passam por `scripts/env/native_host_guard.ps1` ou
`native_host_guard.sh`. A guarda exige um layout fixo de proposito: um checkout
ou venv nunca e compartilhado entre Windows e WSL/Linux.

| Host | Pasta aceita | Bloqueado |
| --- | --- | --- |
| Windows (PowerShell nativo) | `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`; no GitHub Actions, `GITHUB_WORKSPACE` | outra pasta, caminho UNC (`\\wsl$`), ponto de reparse, PowerShell aberto a partir do WSL |
| WSL | `~/gitlab_repo/ssa_consulta_rapida_pyqt6`, em ext4 | `/mnt/*`, `~/gitlab` e qualquer outra pasta |
| Linux e macOS | qualquer pasta nativa | `/mnt/*` e `~/gitlab` (nome reservado ao link do clone Windows) |

Chamado direto, sem esses scripts, `uv run --no-sync python main.py` nao passa
pela guarda.
