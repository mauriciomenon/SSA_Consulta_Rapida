# SSA Consulta Rapida

Aplicacao para importar, consultar e exportar relatorios de SSAs, com interfaces de terminal e PyQt6.

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

Para a interface de terminal, retire `--gui`. Use `--help` para consultar os argumentos.
No Windows, use PowerShell e o ambiente nativo descrito no [guia de ambiente](dev_env/ENVIRONMENT_GUIDE.md).

## Dados e importacao

- O startup nao importa planilhas automaticamente.
- A importacao incremental preserva o contrato de atualizacao por SSA.
- Sincronizacao de derivadas ocorre apos a importacao quando ha planilhas
  especiais (`SSAs Derivadas e Relacionadas*.xlsx`) ou divergencia no banco,
  no full rescan, e por acao manual dedicada (menu `Atualizar derivadas`
  ou `scripts/derivadas_cli.py`).
- Se o banco estiver ausente ou zerado, a inicializacao restaura o snapshot
  valido mais recente de `data/historico_backups/` em vez de iniciar vazio;
  sem snapshot utilizavel, o schema e criado. Banco corrompido e preservado
  como evidencia forense antes da restauracao.
- O full rescan constroi um banco candidato isolado e so o promove apos
  passar na verificacao de integridade; o banco anterior fica arquivado.
- Bancos, planilhas e configuracoes pessoais ficam fora do controle de versao.

[Importacao](docs/ARQUITETURA_IMPORTACAO.md) | [Regras de atualizacao](docs/ARCH_DB_UPSERT.md) | [Diagnostico](docs/TROUBLESHOOTING_IMPORTACAO.md)

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
