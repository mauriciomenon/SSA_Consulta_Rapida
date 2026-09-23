# SSA Consulta Rapida

Aplicacao para importar planilhas de SSAs para um banco SQLite local e
consultar, filtrar e exportar os dados, com tres interfaces: terminal (CLI),
desktop (PyQt6) e web (Streamlit).

## Versao

Versao do codigo: **4.50**. As fontes centrais sao `VERSION`, `config/version.json` e os metadados do pacote.

[Notas da versao](docs/RELEASE_NOTES_v4.50.md) | [Documentacao](docs/INDEX.md)

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

## Dados e importacao

- O startup nao importa planilhas automaticamente; a importacao e disparada
  por acao (botao Reescanear na GUI, `--force-rescan` na CLI).
- As planilhas-fonte ficam na pasta de documentos configurada; o banco fica
  em `data/`. A importacao e incremental: arquivos ja processados sao
  reconhecidos por controle de estado, e cada SSA atualiza seu proprio
  registro (upsert por `numero_ssa`).
- Planilhas especiais cujo nome comeca com `SSAs Derivadas e Relacionadas`
  nao entram na fase comum: suas arestas alimentam a fase dedicada de
  derivadas.
- Arquivos processados sao movidos para `processadas/` com nomes
  reservados atomicamente; conflitos e falhas por arquivo sao reportados
  sem abortar o lote.
- Bancos, planilhas e configuracoes pessoais ficam fora do controle de versao.

[Importacao](docs/ARQUITETURA_IMPORTACAO.md) | [Regras de atualizacao](docs/ARCH_DB_UPSERT.md) | [Diagnostico](docs/TROUBLESHOOTING_IMPORTACAO.md)

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

[Guia e exemplos de derivadas](docs/DERIVADAS_SYNC_RUNBOOK.md) |
[Plano de validacao da auditoria](docs/VALIDATION_PLAN.md) |
[Relatorio de correcoes e estabilizacao de estado](docs/AUDIT_FIXES_REPORT.md)

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

O GitHub verifica PRs para `main`/`dev` e pushes nessas branches. O GitLab
verifica MRs, a branch padrao, execucoes manuais e pushes em branches `fix/`;
nessas execucoes, a suite completa e automatica e bloqueante. Os gates publicam
diagnosticos e o GitLab preserva JSONL e relatorio JUnit por 14 dias. O log da
suite identifica cada teste e resume as 20 maiores duracoes.

[Contratos e comandos de CI](docs/TESTING_STRATEGY.md#ci-github-gitlab-e-release-windows) |
[Resultados e bloqueios da PR](docs/AUDIT_FIXES_REPORT.md#m-correcao-de-cicd-e-preparacao-da-pr)

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

[Comandos e validacao dos tres alvos](docs/BUILD_WINDOWS_ARM64_AMD64.md) |
[Guia de distribuicao](docs/GUIA_DISTRIBUICAO.md) |
[Build multiplataforma](docs/BUILD_MULTIPLATFORM.md)
