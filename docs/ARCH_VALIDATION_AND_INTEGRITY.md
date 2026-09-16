# Validacao e integridade

`armazenamento/database_integrity.py` separa falha estrutural de inconsistencia
de dados. A politica A5 permite continuar a importacao com inconsistencias de
conteudo para que uma reimportacao possa corrigi-las, com diagnostico preservado.

## Recuperacao de banco ausente, zerado ou corrompido

`ensure_database_integrity` decide por estado do arquivo:

- **Ausente ou 0 bytes** (`needs_creation`): primeiro tenta restaurar o
  snapshot integro mais recente de `historico_backups/` — delecao manual ou
  arquivo truncado nao descartam dados recuperaveis. Entre snapshots com
  dados vale o mais recente; um snapshot vazio so e usado como ultimo
  recurso. Sem snapshot utilizavel, cria o schema e segue (bootstrap).
- **Corrompido** (falha no `integrity_check`): o original e preservado como
  forense `.corrupt_<timestamp>.db` (com sidecars) e o snapshot valido mais
  recente e promovido com revalidacao funcional; em falha, o original volta
  e o proximo snapshot e tentado.
- **Falha critica no rollback** da restauracao: o bootstrap e abortado e o
  estado em disco e preservado como evidencia — nao se cria schema por cima
  de estado indeterminado.
- **Tabela ausente ou coluna obrigatoria faltando**: reparo automatico
  bloqueado; exige migracao explicita.

A leitura com `read_only=True` (`mode=ro`) nunca escreve no `.db` da origem
e falha se o arquivo nao existir — usada na validacao de bancos externos.
Limitacao do SQLite: em banco WAL, a abertura ainda pode materializar
`-shm`/`-wal` ao lado da origem.

## Selecao de banco externo (staging)

`gui/ssa/database_operations.py` copia o arquivo escolhido para `data/` em
duas fases: `stage_database_copy` grava o snapshot em
`<destino>.copy-<timestamp>` via `sqlite3.Connection.backup` com a origem
em `mode=ro`, e `commit_staged_database_copy` promove com `os.replace`
apos arquivar o destino anterior (com rollback se a promocao falhar). O
arquivo do usuario nunca e modificado.

Stagings vivos sao registrados em processo (`_ACTIVE_STAGED_COPIES`): o
varredor de `.copy-*` orfaos so remove arquivo nao registrado (nem
sidecar de registrado) e com mtime alem da janela minima — uma copia
lenta nunca e apagada pela idade. No encerramento, a GUI nao aceita o
fechamento enquanto existir staging ativo: a barreira
`bar_new_staged_copies()` trava novos stagings e conta os vivos sob o
mesmo lock do registro, entao nenhum `sqlite3.backup()` pode comecar
entre a ultima checagem e o `accept`. A entrega do resultado do worker
(`pending_result`) e a invalidacao por timeout/janela destruida sao
coordenadas por `delivery_lock` — um resultado publicado na janela da
decisao nunca vira orfao nem e perdido.

## Reparo conservador e bloqueios

Apos um reparo, a decisao usa os mesmos requisitos estruturais: banco acessivel,
tabela fisica presente, schema valido, integridade SQLite valida e permissoes
suficientes. O reparo nao transforma uma dessas falhas em aviso. O reparo conserva a reverificacao existente; nao se acrescentou uma nova
varredura apenas para mudar a mensagem da GUI.

`is_valid=False` por inconsistencia de dados nao equivale sozinho a bloqueio de
importacao. O relatorio conserva `issues`, `warnings` e `data_consistent` para
explicar o resultado, inclusive apos adicionar uma coluna opcional ausente.

## Resultado apresentado pela GUI

`RescanWorker` consome o `integrity_report` do resultado real da importacao.
Ressalvas nao bloqueantes dos lotes sao reunidas sem repeticao e apresentadas no
dialogo de progresso e no estado final como `Concluido com ressalvas...`.
Falhas bloqueantes e falhas de recarga continuam sendo erros; uma frase de
sucesso nao substitui o resultado da operacao.

## Referencias

- [Schema e importacao](SCHEMA_UNIFICADO_IMPORTACAO.md)
- [Regra de numero SSA](REGRA_NUMERO_SSA.md)
- [Diagnostico de importacao](TROUBLESHOOTING_IMPORTACAO.md)
- [Plano de validacao da auditoria](VALIDATION_PLAN.md)
