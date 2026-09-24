# Candidata local v4.51

Data do registro: 2026-09-24. Fonte: branch `dev` local.

Esta candidata consolida correcoes locais de importacao, cancelamento, armazenamento, derivadas, caches e GUI. A ultima release publicada e `v4.50`; esta candidata nao possui tag, push, CI remoto ou binarios concluidos.

## Evidencia local ja obtida

- No tip de codigo `ba9ab08c`, antes da troca de metadados de versao, a suite completa terminou com 3377 testes aprovados, 9 ignorados e 11 subtestes aprovados (`QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q`, 1072,10 s).
- Apos a troca dos metadados para 4.51, os testes de versao e inicializacao terminaram com 34 aprovados. `uv lock --check` passou.
- Essas verificacoes nao substituem os builds nativos, a medicao de desempenho nem a CI no commit exato da candidata.

## Ponto de desempenho pendente

Uma medicao local registrou **0,436 s** para o backup SQLite de uma copia de **161 MiB**. No fluxo normal atual de selecao de banco alternativo, `gui/gui_ssa.py` faz o staging com `sqlite3.backup()` no worker e so promove o resultado na thread GUI depois de conferir `request_id`. O caminho sincrono usado pelos testes ainda copia na thread chamadora. Portanto, os 0,436 s medem o custo da copia, mas nao demonstram uma pausa atual de 0,436 s na GUI. A medida isolada nao estabelece a distribuicao de latencia nem o pico de memoria.

Antes de promover a candidata, medir o fluxo completo de selecao de banco em bancos reais de tamanhos representativos, com repeticoes em cada plataforma alvo. Registrar latencias **p50 e p95** do staging e da promocao, pico e variacao de memoria do processo, e responsividade da GUI durante a operacao. Definir limites de aceitacao com esses dados. Se a pausa ou o uso de memoria excederem os limites, a candidata permanece pendente ate a correcao ser implementada e revalidada.

A promocao permanece na thread GUI para descartar resultados com `request_id` obsoleto antes de trocar o banco selecionado. Qualquer mudanca dessa fronteira exige preservar a verificacao de identidade da requisicao, cancelamento e descarte de resultado tardio, com teste de corrida.

## Condicao de release

Fechar a revisao dos achados, documentar as medicoes do backup e seus limites, validar os alvos nativos solicitados e executar os gates remotos no commit exato a publicar. Nenhum desses gates e declarado concluido por estas notas.
