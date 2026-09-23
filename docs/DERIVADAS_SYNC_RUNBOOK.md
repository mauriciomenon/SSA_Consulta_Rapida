# Operacao e relatorios de derivadas

Este guia cobre sincronizacao, consulta e exportacao de relatorios pela CLI e
pela GUI. Execute os comandos na raiz do repositorio.

## JSON em stdout continua disponivel

`sync`, `heal` e `maintenance` imprimem o resultado completo em JSON na saida
padrao (stdout), inclusive com o formato de saida padrao `text`. Para tornar a
intencao explicita em scripts, use `--output json` antes do subcomando.

```sh
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync > sync.json
```

O redirecionamento `>` e feito pelo shell: ele substitui o arquivo sem a
validacao de destinos da CLI. Nunca redirecione para o banco ou para uma fonte.
As novas flags abaixo permitem salvar arquivos com validacao de destino e nao
substituem nem acrescentam mensagens ao JSON emitido em stdout.

## Salvar JSON, CSV e TSV pela CLI

As tres flags podem ser combinadas em `sync`, `heal` e `maintenance`:

```sh
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync --report-json sync.json --report-csv sync.csv --report-tsv sync.tsv
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json heal --report-json heal.json --report-csv heal.csv --report-tsv heal.tsv
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json maintenance --min-interval-seconds 3600 --report-json maintenance.json --report-csv maintenance.csv --report-tsv maintenance.tsv
```

- JSON preserva o resultado completo, incluindo verificacoes, motivos para nao
  executar uma operacao e relatorios internos de `heal` e `maintenance`.
- CSV e TSV representam a reconciliacao: uma linha com timestamp, modo,
  `verify_only` e sete contagens de arestas, conflitos, orfaos e ciclos. CSV usa
  virgula e TSV usa tabulacao; ambos incluem cabecalho e usam UTF-8.
- Em `heal`, a reconciliacao vem de `sync`; em `maintenance`, de `heal.sync`.
  Se a operacao nao precisou sincronizar, CSV/TSV nao sao gerados. A CLI explica
  o motivo em stderr e retorna 1. JSON continua disponivel e nao sao fabricadas
  contagens zero para representar uma reconciliacao que nao aconteceu.
- Os arquivos sao independentes. Se uma exportacao falhar, as demais ainda sao
  tentadas. O JSON em stdout permanece o resultado da operacao original.
- Os destinos sao validados antes da operacao. A pasta precisa existir; banco,
  arquivos auxiliares SQLite e planilhas de origem ficam protegidos. Destinos
  repetidos, inclusive aliases existentes do mesmo arquivo, sao recusados.
- Arquivos existentes sao recusados por padrao. Para substituir relatorios,
  acrescente `--overwrite-reports`. Essa flag nao permite substituir fontes.
- Cada arquivo e publicado somente depois de ser gravado por completo. Uma
  falha de serializacao preserva o relatorio anterior.
- Falha ao salvar depois da operacao produz mensagem em stderr e retorno 1.
  A sincronizacao ja executada nao e desfeita. Confira o JSON em stdout antes
  de decidir repetir o comando.

Sem as flags de exportacao, os formatos e codigos de saida anteriores permanecem
inalterados. Falhas da propria operacao continuam seguindo o tratamento existente.

## Salvar pela GUI

Depois da sincronizacao manual de derivadas, use **Database > Exportar relatorio
de derivadas...**. Escolha JSON, CSV ou TSV e o destino no dialogo de salvamento.
O dialogo pede confirmacao para substituir arquivo existente. O banco e as fontes
da operacao continuam protegidos.

O relatorio fica disponivel enquanto a janela mantiver o resultado dessa
sincronizacao. Exportar nao executa uma nova sincronizacao. JSON contem as fases
completas; CSV/TSV incluem uma linha por fase executada, com a coluna adicional
`phase` (`db` ou `sheets`). Isso preserva a distincao entre reconciliar o banco e
aplicar as planilhas. CSV/TSV nao resumem fases que nao foram executadas.

## Quando a sincronizacao acontece

- **Apos a importacao de planilhas**: arquivos cujo nome comeca com
  `SSAs Derivadas e Relacionadas` (`.xlsx`) sao detectados e pulam a fase
  de importacao comum — suas arestas entram na fase dedicada de sync, que
  mescla as arestas da planilha com as do campo `derivada_de` do banco.
- **Preflight DB-only**: quando nenhum arquivo mudou, o sync roda se o
  ultimo run falhou, se ha arestas no banco sem matriz/sumario
  materializado, ou se a contagem divergiu do ultimo run. A decisao e
  cacheada por estado do arquivo do banco — sem custo quando nada mudou.
- **Full rescan**: o sync roda dentro do banco candidato antes da
  promocao; um sync quebrado nao toca o banco ativo.
- **Manual**: menu `Banco de dados > Atualizar derivadas` na GUI, ou
  `scripts/derivadas_cli.py sync` na CLI.
- Se um run falha, ele fica registrado como `error` em
  `ssa_derivada_sync_run` e e refeito automaticamente na proxima
  importacao — inclusive quando o banco nao tem arestas proprias.

## Consultas e manutencao

```sh
# Verificar schema sem gravar.
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json schema-scan
# Verificar consistencia sem gravar.
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json scan
# Conferir a mesclagem de fontes sem gravar no banco.
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync --verify-only
# Reconstruir e remover linhas antigas da matriz.
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json sync --full-rebuild
# Consultar estatisticas.
uv run --no-sync python scripts/derivadas_cli.py --db data/ssas.db --output json stats
```

## Reconstrucao completa

1. Interrompa gravacoes externas no banco quando possivel.
2. Guarde uma copia consistente do banco antes da reconstrucao. Com todos os
   processos escritores parados, copie o arquivo para um backup com data/hora.
3. Execute `schema-scan`, `scan` e `sync --verify-only`.
4. Execute `sync --full-rebuild`.
5. Execute `stats` e `scan` para conferir o resultado.
6. Arquive o relatorio JSON para rastreabilidade.

Para restaurar um backup, pare os processos escritores, substitua o banco pela
copia e execute `schema-scan` e `scan`. Reative as gravacoes somente depois de
conferir a consistencia.

## Observacoes

- `sync` exige ao menos uma fonte: banco habilitado ou planilha informada.
- Os verificadores automaticos so pulam `sync --verify-only` quando confirmam a
  ausencia de `ssa_table` no banco de destino.
- A importacao reconhece aliases das colunas de pai, filho e relacao.
- `scan` e independente da importacao e nao modifica o banco.
- `maintenance` respeita o intervalo minimo e pode encerrar sem sincronizar.
- As APIs `export_report_json` e `export_reconciliation_csv` foram preservadas;
  `export_reconciliation_tsv` foi acrescentada. Por compatibilidade, chamadas
  diretas das APIs permitem substituir arquivo. CLI e GUI aplicam sua propria
  autorizacao de substituicao e passam os caminhos protegidos aos exportadores.


## Operacoes em andamento

Durante carga, sincronizacao, rescan, SAM, compactacao ou validacao de outro banco, as acoes de dados conflitantes ficam indisponiveis. Aguarde a conclusao antes de iniciar outra operacao. Filtros e navegacao existentes permanecem disponiveis quando nao dependem da carga em andamento; eles nao apagam o progresso de derivadas.

Ao tentar fechar durante gravacao de preferencias, a janela pode permanecer
aberta. A tentativa de fechamento nao encerra a fila de gravacao. Se a escrita
falhar, o status informa `Falha ao salvar preferencias. Verifique o log antes de
encerrar.`; essa falha nao e apresentada como gravacao concluida. Corrigida a
causa, uma nova gravacao bem-sucedida permite confirmar as preferencias.

Se a sincronizacao de derivadas, compactacao ou validacao de outro banco nao
puder construir ou iniciar sua thread, a GUI informa a falha e libera o estado
para outra tentativa. Uma operacao antiga nao pode substituir o resultado ou
liberar os controles de uma nova operacao.

Se a SAM API concluir e a recarga da tabela falhar, o status indica
`SAM API concluida; falha ao recarregar. Use Recarregar dados.`. A falha tambem
fica no log; recarregue os dados sem repetir automaticamente a importacao.


## Copia de banco externo (staging)

Selecionar outro banco pela GUI copia o arquivo para `data/<nome>.db` em
duas fases: primeiro um snapshot consistente da origem (aberta em modo
read-only) e gravado como `data/<nome>.db.copy-<timestamp>`; depois a
promocao atomica, que arquiva o banco anterior como `.bak-<timestamp>` e
restaura o arquivado se a promocao falhar.

- Um `.copy-*` registrado como ativo neste processo nunca e removido pelo
  varredor de temporarios — nem ele nem seus sidecars (`-wal`, `-shm`,
  `-journal`), mesmo que a copia demore mais que a janela de idade. So
  entram no varredor arquivos de processos mortos E com mtime alem da
  janela minima.
- Fechar a janela durante a copia adia o encerramento; o fechamento
  forcado tambem nao abandona staging — uma barreira atomica impede
  novos stagings e bloqueia o `accept` enquanto houver copia viva,
  inclusive de thread cuja referencia a GUI ja perdeu (pedido expirado
  ou substituido). Um `.copy-*` deixado por processo morto e removido na
  proxima copia.
- Se o pedido expirar (timeout de validacao) ou a janela morrer antes da
  promocao, o staging tardio e descartado, nunca promovido.


## Falha ao apresentar um resultado concluido

Se houver erro ao aplicar o resultado de derivadas na interface, a GUI informa
a falha, restaura os controles e invalida o relatorio dessa entrega. A operacao
no banco nao e desfeita automaticamente. Uma thread ainda viva continua retida;
aguarde seu termino antes de uma nova sincronizacao.

Se apenas a recarga dos dados falhar depois de atualizar derivadas, o status
informa que as derivadas foram atualizadas e orienta usar `Recarregar Dados`.
O controlador retorna falha de recarga, sem repetir automaticamente a operacao.

Na selecao de outro banco, uma falha anterior a selecao conserva o banco atual.
Se a selecao ja ocorreu, uma falha de dialogo ou recarga conserva o novo banco,
invalida o relatorio anterior e informa como recarregar. Falha de compactacao
na apresentacao tambem fica no status/log; nao confundir com a conclusao da
operacao no SQLite. Os detalhes de reproducao estao na secao L do relatorio.
