# SSA Consulta Rapida v4.47

Release estavel de manutencao da familia 4.x.

## Filtros e interface

- Atalhos de situacao da barra superior alternam entre inclusao, exclusao e estado neutro.
- Estado excluido usa o filtro existente `!STATUS`, sem novo operador ou mudanca no core.
- Estados positivos e negativos podem ser combinados, por exemplo `SCA SPG !APG`.
- Barra rapida, lista de filtros, filtros por coluna e painel avancado permanecem sincronizados.
- Caixa rapida de setor executor mostra `...` quando mais de um setor esta ativo, inclusive por filtro avancado.
- Atualizacao apenas visual de filtros nao invalida mais a revisao dos dados; o cache de busca normalizada e reutilizado no DataFrame real.
- Mascaras nullable de busca exata e faixas sao preenchidas antes das combinacoes booleanas.

## Banco, importacao e recovery

- Reparacao valida a tabela SSA canonica e nao aceita coluna funcional renomeada como reparo bem-sucedido.
- Recovery nao cria uma segunda tabela SSA nem descarta tabelas auxiliares ao reconstruir a base.
- Snapshots e copias de build usam a API de backup SQLite, incluindo dados ainda presentes no WAL ativo.
- Snapshot recente e reutilizado apenas depois de `PRAGMA quick_check`; snapshot corrompido e substituido.
- Backups forenses de tentativas de recovery falhas possuem retencao limitada.
- Escritas temporarias e rotacao de banco preservam transacao do chamador e fazem rollback coerente em falha.
- Importacao com todas as linhas rejeitadas retorna classificacao deterministica, inclusive no worker de rescan.
- Caminhos ativos e utilitarios de manutencao fecham conexoes SQLite tambem em excecao no Windows.

## Release e isolamento de hosts

- `release.ps1` aceita somente `-Target windows` e bloqueia ambiente WSL, checkout montado e venv de outro host antes de efeitos colaterais.
- Debian deve usar `./release.sh` dentro de clone Linux nativo, sem compartilhar checkout ou venv com Windows.
- WSL fica restrito ao CodeRabbit em clone Linux proprio; ele nao executa Python, uv, testes ou build.
- Scripts Windows falham de forma fechada quando pre-condicoes, banco runtime, hash, smoke ou instalador obrigatorio nao sao validos.
- Pacotes PyInstaller continuam `onedir`, com CLI e GUI separados.
- Quando incluido, o banco runtime fica somente em `data\ssas.db`, fora de `_internal`.
- Pastas gravaveis externas permanecem `data`, `docs_entrada`, `docs_saida`, `exportacao`, `reports` e `logs`.

## Compatibilidade

- Sem alteracao de schema de banco.
- Sem alteracao dos operadores ou da semantica central de filtros.
- Sem alteracao de layout ou posicao dos controles.
- Sem nova god class, mixin, wrapper ou helper de dominio.
- Dependencias foram apenas auditadas nesta rodada; nao houve salto de versao sem vulnerabilidade reproduzida.

## Artefatos Windows AMD64

- ZIP portatil CLI PyInstaller.
- ZIP portatil GUI PyInstaller.
- Instalador Inno Setup.
- Relatorio JSON de release com hashes, banco runtime e resultado dos smokes.

O comando canonico desta release e:

```powershell
.\release.ps1 -Target windows -Backend pyinstaller -IncludeRuntimeDb -Yes
```

Artefatos so podem ser publicados apos suite final, smoke funcional do executavel empacotado, verificacao do banco runtime, revisao independente e gates de seguranca.

## Validacao da candidata

- Grupos criticos de banco, importacao, build/release, filtros, nullable, cache e manutencao executados no Windows nativo sem falha.
- Banco real validado com integridade SQLite, schema funcional, dados consistentes e nenhuma situacao desconhecida.
- `uv lock --check` e `pip-audit` sem vulnerabilidade conhecida.
- Resultado consolidado da suite final, scanners e build real sera registrado antes da tag.
