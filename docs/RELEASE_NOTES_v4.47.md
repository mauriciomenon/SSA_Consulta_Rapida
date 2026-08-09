# SSA Consulta Rapida v4.47

Release estavel de manutencao da familia 4.x.

## Destaques

- Atalhos de situacao da barra superior alternam entre inclusao, exclusao e estado neutro.
- Estado excluido usa o filtro existente `!STATUS`, sem novo operador ou mudanca no core.
- Estados positivos e negativos podem ser combinados, por exemplo `SCA SPG !APG`.
- Caixa rapida de setor executor mostra `...` quando mais de um setor esta ativo.
- Barra rapida, lista de filtros, filtros por coluna e painel avancado permanecem sincronizados.

## Estabilidade Windows

- Scripts de ativacao e teste usam caminhos nativos Windows com tratamento consistente.
- Build de release exige clone nativo em `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`.
- Pacotes PyInstaller continuam `onedir`, com CLI e GUI separados.
- Quando incluido, banco runtime fica somente em `data\ssas.db`, fora de `_internal`.
- Pastas gravaveis externas permanecem `data`, `docs_entrada`, `docs_saida`, `exportacao`, `reports` e `logs`.

## Compatibilidade

- Sem alteracao de schema de banco.
- Sem alteracao da API das dependencias de runtime da aplicacao.
- Locks transitiveis de build/dev/web atualizados para as primeiras versoes seguras: `gitpython 3.1.58`, `python-multipart 0.0.31`, `setuptools 83.0.0` e `starlette 1.3.1`.
- Sem alteracao de layout ou posicao dos controles.
- Sem alteracao dos operadores de filtro existentes.

## Commits principais

- `0f164b3ab2c75d7aefe2d22d7d6650e12b527da3` - ciclo tri-state dos atalhos de situacao.
- `f7f71a486b1d5f4d230637355f09ba8396597b13` - portabilidade Windows e scripts.
- `7200ce339d9c61a62972a20d366e999e7a27cb32` - indicador `...` para multiplos setores.

## Artefatos Windows AMD64

- ZIP portatil CLI PyInstaller.
- ZIP portatil GUI PyInstaller.
- Instalador Inno Setup.
- Relatorio JSON de release com hashes e resultado dos smokes.

Artefatos so podem ser publicados apos testes completos, smoke funcional do executavel empacotado, verificacao do banco runtime e validacao de seguranca.

## Validacao da candidata

- Suite completa: `2551 passed, 16 skipped`; a unica falha encontrada era uma expectativa visual antiga no teste do seletor rapido.
- Modulo GUI afetado apos a correcao da expectativa: `550 passed, 1 skipped`.
- Contratos focados de release e multiplataforma: `122 passed, 6 skipped`.
- `ruff`, `ty`, `py_compile`, validadores de configuracao e documentacao: OK.
- `semgrep`: 0 achados bloqueantes; `bandit`: 0 achados medios ou altos.
- `pip-audit`: nenhuma vulnerabilidade conhecida apos os patches minimos dos locks de build/dev/web.
- O build publicado deve conter o relatorio JSON final, hashes e smokes do executavel real.
