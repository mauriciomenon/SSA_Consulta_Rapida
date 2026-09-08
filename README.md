# SSA Consulta Rapida

Aplicacao para importar, consultar e exportar relatorios de SSAs, com interfaces de terminal e PyQt6.

## Versao

Versao do codigo: **4.50**. As fontes centrais sao `VERSION`, `config/version.json` e os metadados do pacote.

[Notas da versao](docs/RELEASE_NOTES_v4.50.md) | [Documentacao](docs/INDEX.md)

## Execucao

Use um checkout e ambiente Python nativos do sistema operacional. Nao compartilhe a pasta `.venv` entre sistemas.

No macOS ou Linux, execute a partir da raiz do repositorio:

```bash
source scripts/env/direnv_common.sh || exit $?
ssa_env::apply || exit $?
ssa_native_guard_tools uv || exit $?
uv run --python 3.13 main.py --gui
```

Para a interface de terminal, retire `--gui`. Use `--help` para consultar os argumentos.
No Windows, use PowerShell e o ambiente nativo descrito no [guia de ambiente](dev_env/ENVIRONMENT_GUIDE.md).

## Dados e importacao

- O startup nao importa planilhas automaticamente.
- A importacao incremental preserva o contrato de atualizacao por SSA.
- Sincronizacao de derivadas ocorre no full rescan ou por acao manual dedicada.
- O full rescan recria o banco. Preserve backup antes de executa-lo.
- Bancos, planilhas e configuracoes pessoais ficam fora do controle de versao.

[Importacao](docs/ARQUITETURA_IMPORTACAO.md) | [Regras de atualizacao](docs/ARCH_DB_UPSERT.md) | [Diagnostico](docs/TROUBLESHOOTING_IMPORTACAO.md)

## Distribuicao

Esta versao disponibiliza fontes. Nenhum novo binario ou instalador acompanha esta publicacao.
Builds devem ocorrer no host nativo e passar por smoke funcional do executavel gerado.

[Guia de distribuicao](docs/GUIA_DISTRIBUICAO.md) | [Build multiplataforma](docs/BUILD_MULTIPLATFORM.md)
