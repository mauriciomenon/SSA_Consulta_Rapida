# Controle das correcoes da revisao

## CURRENT TRUTH

Inicio: 2026-09-08 13:41 -03:00. Branch: `dev`.
Pedido: corrigir os achados aplicaveis e ampliar a revisao. Em 2026-09-08 15:20 -03:00, o usuario autorizou ampliar para cache de posicoes, itens menores do CodeRabbit, validacao visual, ferramenta e outros pontos de falha.
Historico Git: reescrita excluida pelo usuario. Autoria exclusivamente humana.
Este documento controla a rodada atual. O plano anterior registra o ciclo avaliado.

## Lista de controle

| ID | Item e criterio de aceite | Estado |
| --- | --- | --- |
| C1 | Importadores preservam campos nao vazios, ordem e regras canonical em duplicados; medir desempenho | Entregue; meta antiga 0,50x canonical nao validada |
| C2a | Resultado de importacao isolado entre invocacoes concorrentes | Entregue |
| C2b | Lotes acumulam alteracoes; erro posterior nao impede recarga nem oculta falha | Entregue |
| C2c | Streamlit prioriza estado bloqueante sobre mensagem de sucesso | Entregue |
| C2d | Diagnostico da promocao usa a mesma classificacao de arquivos bloqueantes | Entregue |
| C3 | Relatorio de integridade descreve o banco efetivamente restaurado | Entregue |
| C4 | Busca vazia cancela requisicao anterior, conserva desfazer e rejeita retorno atrasado | Entregue; busca, limpeza e desfazer confirmados visualmente |
| C5a | Digest integral: mediana <=10 ms e p95 <=15 ms em 500x84; sem colisao por falha | Entregue |
| C5b | Falha de fingerprint nao permite reuso de cache por tamanho/colunas | Entregue |
| C5c | Mapear os quatro grupos de cache de S9, copias, limites e invalidacao; medir tempo/RSS | Entregue; oito fluxos aprovados e RSS estabilizado em 200 ciclos |
| C6a | Teardowns nao ocultam falhas inesperadas de workers | Entregue |
| C6b | Teste de restore valida resultado e conteudo, alem de chamadas | Entregue |
| C6c | Texto de discovery descreve raiz/processadas/nosurvivor sem contradicao | Entregue |
| C6d | Retirar estado morto da promocao e busca repetida do redutor, quando confirmado sem uso | Entregue |
| C7a | Compilacao, lint, tipos, testes focados e integrados | Entregue: 982 integrados; 67 e 17 nas rodadas finais focadas |
| C7b | Revisao independente ampliada e scanners apos o patch final | Parcial: gates executados, limites abaixo |
| C7c | GUI real: busca, limpeza, filtros, detalhes, evidencia visual e RSS | Parcial: GUI real exercitada; repeticao final interrompida por pedido do usuario |
| C8 | Cache de detalhes guarda posicoes, sem reter DataFrames filtrados | Entregue; contratos de memoria/Mapping e matriz final aprovados |
| C9 | Itens menores: medicao unica por admissao, falhas de copia visiveis, caches de datas pareados | Entregue; testes, scanners e revisao independente aprovados |
| C10 | Cancelamento tardio e restore inicial propagam mudanca real para recarga da GUI | Entregue; dois erros reproduzidos e corrigidos |
| C11 | Fallback Streamlit registra a causa da falha | Entregue; falha registrada e fallback preservado |
| P1 | Reversao anterior de S7 sem autorizacao: ocorrencia registrada; nao executar nova reversao | Registrado |
| P2 | Fechamento anterior de S9 sem evidencias suficientes: substituir por estado verificavel nesta lista | Entregue; S9 permanece parcial de forma explicita |
| P3 | Comandos desta rodada preservam codigo de falha; pipelines usam pipefail | Entregue; falhas registradas |
| F1 | Sugestao de inserir rtk em printf/tr no guard | Falso positivo: sem defeito demonstrado |
| F2 | Sugestao de inserir rtk em echo/jq nos gates | Falso positivo: sem defeito demonstrado |

## Regras de fechamento

1. Registrar falha reproduzida, correcao e teste por item.
2. Separar resultado funcional de sugestao de ferramenta ainda nao confirmada.
3. Executar Python pelo uv com ambiente nativo validado, sem sincronizacao de dependencias.
4. Nao considerar timeout, pipeline truncado ou testes simulados como aprovacao da GUI.
5. Registrar limites de plataforma, medicoes e revisoes que nao concluirem.
6. Nao criar branch, PR, commit ou push nesta rodada sem instrucao especifica.

## Evidencias

### Correcoes funcionais

- C1: duplicados e modo complementar usam o redutor canonical existente. O caminho de IDs unicos permanece vetorizado. DDL e DML agora compartilham a transacao; as 16 colunas de data usam o mesmo contrato. Testes cobrem ordem, campos vazios, datas, rollback de schema e estado terminal.
- C2: resultado usa armazenamento por thread; lotes acumulam gravacoes e preservam falhas. A GUI recarrega dados gravados antes de exibir erro/cancelamento, inclusive no segundo lote parcial. Streamlit e CLI priorizam o resultado tipado.
- C3: restore devolve o relatorio produzido para o banco restaurado. O teste abre o SQLite e verifica conteudo real.
- C4: busca vazia conserva o estado para desfazer e cancela trabalho anterior. O worker direto conserva seu contrato de copia e cancelamento.
- C5: digest integral usa hashing nativo; falha de fingerprint invalida o reuso. Caches recebem orcamentos em bytes e invalidacao por revisao de dados. Revisao de ordenacao preserva o cache de ordenacao. Opcoes avancadas mantem ou removem o conjunto completo.
- C6: testes deixam de ocultar erros de teardown; discovery descreve corretamente raiz/processadas. O teste CLI agora produz rejeicao real no coletor de progresso, em vez de simular uma estrutura sem uso.

### Desempenho de importacao

Referencia: `b754aef1f4e4aa3f4d8f14b8c04c5f9ca44b5f2c`, `2026-09-08T06:07:37-03:00`, `HOTFIX_BLOCKER: formatted-page cache disabled when content digest is None`.
Comparacao do modulo otimizado anterior/atual com dependencias atuais comuns, em 12 processos isolados. Medianas de tres processos por versao/cenario. RSS corrente em MiB.

| Entrada | Tempo anterior / atual | RSS anterior, inicio -> fim | RSS atual, inicio -> fim |
| --- | --- | --- | --- |
| 5.000 IDs unicos | 106,35 / 112,62 ms | 76,02 -> 85,36 | 75,92 -> 86,80 |
| 5.000 linhas, 100 IDs repetidos | 2.068,98 / 1.959,37 ms | 76,04 -> 79,86 | 75,84 -> 79,92 |

Unicos: +5,9% no tempo. Duplicados: -5,3%. Todos produziram a contagem esperada. Esta matriz nao mede o redutor canonical separado; nao comprova a meta antiga de tempo <=0,50x canonical. A meta nao significa 0,5 segundo.

### GUI, memoria e medicoes anteriores

Digest 500x84, 50 iteracoes: mediana 12,284 -> 4,398 ms; p95 12,803 -> 4,547 ms. Subblocos atuais: hashing 4,377 ms, metadados 0,029 ms. RSS no mesmo processo: 104.336 -> 106.160 KiB anterior; 106.160 -> 106.768 KiB atual. C5a atende aos limites definidos.

Orcamentos implementados: normalizacao 64 MiB; worker 16 MiB; colunas 16 MiB; resultado de refresh 8 MiB; avancados 8 MiB; responsaveis 8 MiB; ordenacao 8 MiB; formatacao 8 MiB por gerenciador; caches nomeados 8 MiB agregados. O estimador conta payloads e evita duplicacao por identidade. Objetos Mapping customizados e mutaveis nao sao admitidos no cache nomeado atual.

O primeiro comparativo GUI executou 80 processos e 1.600 ciclos em oito fluxos, com hashes de entrada e celulas renderizadas iguais. Ele encontrou uma regressao introduzida no patch: limpar filtros invalidava tambem dados de detalhes/derivadas validos. A invalidacao nomeada passou para a revisao do conjunto de dados. Nova medicao da limpeza: 40,063 -> 38,439 ms; crescimento maximo de RSS 1,656 -> 1,312 MiB. Filtro rapido: 31,351 -> 33,802 ms (+7,82%). Esses resultados precedem a ultima regra de admissao de Mapping; nao sao aprovacao final dos oito fluxos.

O perfil encontrou sete DataFrames extras retidos pelo indice lazy de detalhes. Recontar todos esses objetos a cada insercao elevou warm de 28,746 para 103,403 ms. A regra atual evita reter esse indice e removeu essa regressao. Ultimo piloto, 20 ciclos por processo:

| Fluxo | Mediana anterior / atual, ms | p95 anterior / atual, ms | RSS anterior, inicio -> fim, MiB | RSS atual, inicio -> fim, MiB |
| --- | --- | --- | --- | --- |
| Busca repetida | 28,488 / 28,738 | 29,397 / 31,003 | 245,141 -> 253,484 | 231,859 -> 234,063 |
| Detalhes da mesma SSA | 16,756 / 20,060 | 18,317 / 22,942 | 235,531 -> 236,453 | 222,047 -> 223,406 |
| Detalhes de SSAs diferentes | 16,838 / 19,713 | 17,933 / 21,383 | 235,500 -> 236,547 | 222,016 -> 223,359 |

Conclusao: resultado funcional preservado e menos memoria na busca, mas detalhes custam cerca de 3 ms adicionais, +17% a +20%. C5c nao esta fechado. Procedimento local: `/tmp/ssa_c5_gui_benchmark.py`; evidencia do ultimo piloto: `/tmp/ssa_c5c2_pilot_results.jsonl`.

Ampliacao aprovada e aplicada em `gui/ssa/gui_details.py`, funcao existente `_get_df_ssa_series_index`: o cache guarda o dict de posicoes e constroi o `DetailsSeriesIndex` existente com o DataFrame atual. Sem nova classe ou funcao. Os contratos cobrem reutilizacao, ausencia de retencao do DataFrame, duplicados, SSA ausente e revisao dos dados. A matriz final substituira os pilotos acima.

O perfil do caminho de filtros encontrou recontagem de caches nomeados em 36 chamadas, com 3,992 s em 7,705 s de CPU acumulada. `SimpleCacheManager` agora guarda payload e tamanho medido na admissao. O total soma os tamanhos das entradas; nao existe contador paralelo que possa divergir apos limpeza. Os produtores atuais entregam snapshots estaveis. Testes cobrem substituicao, quota, entrada excessiva e limpeza direta.

A interacao visual passou a usar o CUA Driver existente, por PID e ID da janela, com captura em caminho canonico. Nao houve alteracao de permissoes nem instalacao. Na base sintetica de 2.000 linhas: busca grupo3 retornou 200; limpeza retornou 2.000; desfazer retornou 200; APV combinado retornou 67; limpeza global retornou 2.000. Capturas locais em `/private/tmp/ssa_visual_*.png`. O smoke final precisa usar processo aberto apos o ultimo patch.

### HISTORICAL SNAPSHOT: matriz GUI com posicoes em dict

10.000 linhas x 84 colunas. Cinco processos por versao/fluxo, 20 ciclos cada: 80 processos e 1.600 ciclos, todos com exit code zero. Hashes de dados, configuracao e celulas renderizadas iguais. Tempos incluem o fluxo Qt real em plataforma offscreen; o smoke nativo com cliques e capturas e evidenciado separadamente.

| Fluxo | Mediana anterior / atual, ms | p95 anterior / atual, ms | RSS anterior, inicio -> fim, MiB | RSS atual, inicio -> fim, MiB |
| --- | --- | --- | --- | --- |
| Busca fria | 79.774 / 83.584 | 83.032 / 84.852 | 243.922 -> 268.531 | 230.797 -> 234.188 |
| Busca repetida | 29.219 / 27.789 | 33.003 / 29.899 | 245.234 -> 253.609 | 231.875 -> 234.203 |
| Filtro rapido | 31.695 / 34.732 | 34.881 / 37.239 | 244.078 -> 255.281 | 231.312 -> 237.516 |
| Filtro avancado | 34.120 / 31.704 | 36.063 / 35.252 | 235.469 -> 239.125 | 222.938 -> 224.625 |
| Desfazer | 45.916 / 50.783 | 48.930 / 53.090 | 246.906 -> 313.969 | 233.875 -> 242.578 |
| Limpeza | 41.321 / 39.961 | 44.590 / 41.947 | 242.688 -> 244.297 | 229.672 -> 230.672 |
| Pagina de 500 | 41.624 / 42.261 | 43.796 / 44.541 | 237.719 -> 239.578 | 224.547 -> 226.391 |
| Recarga | 95.749 / 101.207 | 99.059 / 104.254 | 261.719 -> 330.688 | 248.953 -> 250.984 |

Desfazer ultrapassou o limite de +10%: +10,60%. Repeticao independente com tres processos por versao confirmou +10,30% (44,897 -> 49,523 ms); p95 +9,60%. Nao foi repetido ate produzir resultado verde. O perfil restrito ao bloco medido confirmou custo de admissao do dict de posicoes. Foi aprovado ajuste de representacao nos metodos existentes; C5c aguarda sua validacao.

Busca repetida por 200 ciclos: 28,174 ms de mediana, 30,368 ms de p95; RSS 232,203 -> 246,688 MiB. DataFrames vivos permaneceram em nove; payload nomeado estabilizou em 5,092 MB, com 64 normalizacoes e oito indices de posicoes. RSS igual nos ciclos 180 e 200. Isso mostra estabilizacao nessa carga; nao equivale a prova universal de ausencia de vazamento.

### Ajuste final de representacao das posicoes

Plano autorizado dentro da ampliacao: trocar o dict de posicoes por Series em `gui_details.py` e adaptar os metodos existentes em `details_series_index.py`, sem novos metodos/classes. Cerca de 13 linhas funcionais. Contrato Mapping preservado: chaves em ordem, primeira duplicata, KeyError para ausente, default de get, posicao int ou None e copia isolada do argumento.

Diagnostico previo identificou crescimento tardio do indice pandas: 660.000 -> 924.232 bytes em 10.000 entradas. Construir o indice de busca antes de admitir a entrada manteve a medicao estavel apos consultas existentes e ausentes. Microbenchmark incluindo engine pronto: estimacao 4,372 -> 0,460 ms em 10.000 entradas e 44,862 -> 4,478 ms em 100.000. Em 100.000, 8.713.576 bytes ultrapassam o teto de 8 MiB e a entrada deve ser recusada; o dict anterior tambem ultrapassa o teto. O fluxo funcional deve continuar sem cache. 210 testes focados passaram, com compilacao, Ruff, ty e Semgrep aprovados. A revisao independente nao identificou novo defeito. O teste de indice com 10.000 entradas manteve bytes estaveis apos consultas existentes e ausentes; o teste de referencia fraca confirmou liberacao do DataFrame.

Piloto com tres processos por versao e 20 ciclos: desfazer 44,357 -> 44,415 ms (+0,13%), crescimento maximo de RSS 67,141 -> 6,875 MiB; busca repetida 28,673 -> 27,683 ms; detalhes da mesma SSA 16,805 -> 16,708 ms e de SSAs diferentes 16,816 -> 16,721 ms. Nenhum p95 ultrapassou +10%. Matriz final dos oito fluxos em execucao.

### Matriz final aprovada com posicoes em Series

Mesma referencia e entrada da matriz anterior: 10.000 x 84, cinco processos por versao/fluxo, 20 ciclos. Os 80 processos e 1.600 ciclos terminaram com exit code zero. Hashes de dados, configuracao e tabela renderizada iguais. Todos os oito fluxos atenderam ao limite de +10% na mediana e no p95.

| Fluxo | Mediana anterior / atual, ms | p95 anterior / atual, ms | RSS anterior, inicio -> fim, MiB | RSS atual, inicio -> fim, MiB |
| --- | --- | --- | --- | --- |
| Busca fria | 79.524 / 82.813 | 83.256 / 85.363 | 244.188 -> 268.578 | 231.031 -> 234.375 |
| Busca repetida | 28.858 / 27.553 | 31.321 / 29.381 | 245.500 -> 253.922 | 232.234 -> 234.562 |
| Filtro rapido | 31.244 / 34.095 | 34.309 / 36.997 | 244.438 -> 255.234 | 231.578 -> 239.672 |
| Filtro avancado | 31.111 / 28.807 | 33.033 / 31.498 | 235.859 -> 239.891 | 223.234 -> 224.906 |
| Desfazer | 45.009 / 45.715 | 46.768 / 47.024 | 246.641 -> 313.750 | 233.188 -> 240.188 |
| Limpeza | 40.412 / 38.936 | 43.381 / 41.945 | 242.891 -> 244.531 | 229.797 -> 230.859 |
| Pagina de 500 | 41.322 / 41.625 | 43.361 / 42.967 | 237.828 -> 239.734 | 224.750 -> 226.641 |
| Recarga | 91.395 / 90.576 | 95.202 / 94.567 | 261.938 -> 330.609 | 249.062 -> 254.094 |

Busca por 200 ciclos no estado final: mediana 27,282 ms, p95 29,910 ms; RSS 232,313 -> 246,703 MiB, identico nos ciclos 180 e 200. Nove DataFrames antes/depois; uma thread antes/depois; nenhum worker retirado pendente. Payload estabilizado em 5.102.689 bytes desde o ciclo 120. Evidencias locais: `/tmp/ssa_c5_series_final_summary.json` e `/tmp/ssa_c5_series_final_long_warm.log`.

Caminho medido: restauracao do filtro, reconstrucao da normalizacao, indice de posicoes e renderizacao da tabela/detalhes. O perfil isolou a admissao do dict como custo extra. Trocar a representacao nos metodos existentes e materializar o indice antes de medir removeu a travessia Python desse payload; evitou novo gerenciador, contador paralelo ou helper. A reversao futura pode ser feita por commit atomico do slice, somente mediante comando explicito. Nenhuma reversao foi executada nesta rodada.

### Correcoes adicionais de importacao e isolamento

- C10: SQLite corrompido com snapshot valido e sem XLSX candidato agora registra restauracao do banco principal e recarrega a GUI. O bool legado permanece compativel; o worker respeita o resultado tipado apos verificar bloqueantes.
- C10: cancelamento recebido apos gravacao e antes do callback final recarrega os dados antes do status cancelado, sem repetir recarga previa bem-sucedida.
- C11: falha na conversao de colunas para Streamlit gera warning com causa e preserva o fallback anterior.
- A fixture de `test_import_outcome_isolation.py` agora restaura tanto ausencia previa de resultado quanto objeto previo, evitando interferencia entre testes.
- 138 testes focados passaram; compilacao, Ruff, ty, Semgrep e Bandit de producao passaram. Dois B102 nos testes executam AST do proprio fonte local, sem entrada externa; classificados como falsos positivos e mantidos visiveis.

### Revisao e limites em aberto

- Gate integrado: `uv run --no-sync python -m py_compile`, `ruff check` e `ty check` em todos os Python alterados/novos, aprovados. `pytest` de banco, upsert, importacao, launcher, GUI, caches, concorrencia e filtros: 982 passaram, um pulado, 32 avisos de datas mistas, em 316,63 segundos.
- Apos o ultimo patch de caches: 67 testes focados passaram em 22,77 segundos. Apos as tres correcoes de testes da rodada 3: 17 passaram, com verificacao adicional de identidade do resultado e da lista de workers preexistentes. Compilacao, lint e tipos foram repetidos no estado final e passaram. Os totais de rodadas nao devem ser somados como testes distintos.
- O teste pulado depende de checkbox oculto na interface atual; o contrato funcional correspondente tem outro teste ativo. Nao foi ocultada falha nova.
- O primeiro gate de tipos encontrou dois problemas em testes; ambos corrigidos antes da rodada integrada aprovada.
- Semgrep final: zero achados e zero erros. Detect-secrets, Gitleaks e Trufflehog: zero segredos. Trufflehog executado sem verificacao externa de credenciais.
- Duas regras Semgrep atingiram timeout no arquivo grande de testes GUI. Repeticao calibrada com 30 segundos por regra concluiu com zero achados e zero erros. Os tres testes corrigidos na rodada 3 tambem passaram em Semgrep e Bandit (B101 excluido por representar asserts pytest).
- Bandit apos incluir a suite GUI alterada: 2.499 low e dois medium. Dos low, 2.497 sao asserts de testes e um e um token de revisao de dados sintetico, sem autenticacao. Os dois medium sao SQL com colunas parametrizadas por lista fixa de teste e execucao de AST do proprio fonte no teste Streamlit. Classificacao desses 2.500 apontamentos: falso positivo no contexto. O low restante era um `except/pass` legado em `dev_env/streamlit_app.py:1672`, na conversao de colunas; corrigido na ampliacao com log da causa. A rodada historica nao foi declarada limpa.
- Nenhum shell ou PowerShell alterado; ShellCheck e PSScriptAnalyzer nao se aplicam ao diff.

- CodeRabbit: tres rodadas concluidas (32, 32 e 33 arquivos rastreados). Total de 21 apontamentos, incluindo repeticoes: um critical, 15 major, um minor e quatro trivial. Rodada 1: payload parcial corrigido. Rodada 2: extracao de utilitario deferida. Rodada 3: triagem completa abaixo. Sem conhecimento externo ou recomendacao RTK reportados. A ultima regra de admissao Mapping recebeu revisao independente e scanners apos o snapshot externo.
- Revisao independente dos quatro arquivos novos e dos fluxos CLI/GUI de erro: nenhum novo P1/P2 demonstrado.
- Clawpatch: bloqueado por HTTP 429 de cota esgotada. Execucao interrompida; nao representa revisao limpa.
- pip-audit: dez ocorrencias em dois pacotes instalados, GitPython 3.1.58 e pip 25.3; uma dependencia local sem registro PyPI. Atualizacao de dependencias fica fora deste patch e requer slice proprio.
- Vulture: quatro parametros sem uso direto, preservados por compatibilidade de assinatura ou por mocks de teste. Nao representam caminho executavel morto demonstrado.
- HISTORICAL SNAPSHOT da primeira tentativa de CUA: runtime temporario e SQLite sintetico com 2.000 linhas. Processo carregou a GUI, RSS observado 263,1 -> 262,7 MiB em repouso. A ferramenta CUA nao reconheceu o processo Python do uv; cliques e captura visual estao bloqueados. O processo de teste foi encerrado. Nao usar este resultado como aprovacao visual.
- Validacao de Windows/Linux e artefatos empacotados nao executada nesta rodada macOS.
- Sem commit, push, nova branch, PR, stash ou reescrita de historico nesta rodada.

### Triagem completa da terceira rodada CodeRabbit

| ID | Severidade reportada | Apontamento | Classificacao e destino |
| --- | --- | --- | --- |
| R3.1 | major | Reduzir try no estimador | Corrigido na ampliacao: somente medicao protegida; falhas de copia/insercao propagam |
| R3.2 | trivial | Chamar invalidate_cache publico | FALSO_POSITIVO; SimpleCacheManager nao tem esse metodo |
| R3.3 | major | Limitar numero de objetos percorridos | NAO_BLOQUEANTE_DEFERIDO; seen ja evita ciclos, sem repro concreto |
| R3.4 | major | Recontagem e guarda de progresso na expulsao | Corrigido na ampliacao: cada DataFrame medido uma vez; remocao sem progresso falha explicitamente |
| R3.5 | minor | Restaurar resultado anterior na fixture | BUG_REAL de isolamento de teste; corrigido e validado |
| R3.6 | trivial | Preservar workers anteriores no teardown | BUG_REAL de isolamento de teste; corrigido e validado |
| R3.7 | major | Fechar conexoes SQLite antes de sobrescrever arquivo | BUG_REAL multiplataforma no teste; corrigido e validado |
| R3.8 | trivial | Trocar formula por oracle explicito no teste | NAO_BLOQUEANTE_DEFERIDO; sem defeito demonstrado |
| R3.9 | major | Extrair helpers publicos compartilhados | NAO_BLOQUEANTE_DEFERIDO; repete recomendacao estrutural da rodada 2 |
| R3.10 | major | Reduzir recontagem dos caches de coluna | NAO_BLOQUEANTE_DEFERIDO; sem hotspot reproduzido |
| R3.11 | major | Expor propriedades publicas no worker | NAO_BLOQUEANTE_DEFERIDO; mudanca de arquitetura |
| R3.12 | major | Evitar copia vazia no worker direto | NAO_BLOQUEANTE_DEFERIDO; GUI vazia ja usa fluxo sincrono, preservar API do worker |
| R3.13 | major | API publica para limpar cache normalizado | NAO_BLOQUEANTE_DEFERIDO; mudanca de arquitetura |
| R3.14 | trivial | Contador incremental de bytes nos named | Custo corrigido com tamanho por entrada; contador total paralelo continua deferido |
| R3.15 | major | Redistribuir orcamento de responsaveis | NAO_BLOQUEANTE_DEFERIDO; ajuste de politica sem repro |
| R3.16 | critical | CLI deve falhar para qualquer rejeicao | FALSO_POSITIVO; contraria resultado tipado aprovado para rejeicoes nao bloqueantes |
| R3.17 | major | Aumentar teto de ordenacao por limite de linhas | FALSO_POSITIVO; limite de linhas nao obriga admitir entradas acima do teto de bytes |
| R3.18 | major | Podar caches date/parsed em conjunto | Corrigido na ampliacao: poda entradas orfas apos aplicar os dois limites |
| R3.19 | major | Medir apenas values do payload avancado | FALSO_POSITIVO; seen ja evita contar aliases compartilhados duas vezes |

### Triagem da quarta rodada CodeRabbit

Rodada concluida com exit code zero: 19 apontamentos em 35 arquivos rastreados; seis major, tres minor e dez trivial. Houve progresso e novos apontamentos durante cerca de 6 min 35 s; nao ocorreu timeout da ferramenta. Os quatro arquivos novos receberam revisao independente. Os patches posteriores ao snapshot receberam nova revisao independente e scanners.

| ID | Severidade | Apontamento | Classificacao e destino |
| --- | --- | --- | --- |
| R4.1 | minor | Geracao da invalidacao de busca | FALSO_POSITIVO; clear e incremento usam o mesmo lock |
| R4.2 | trivial | Limitar travessia do estimador | NAO_BLOQUEANTE_DEFERIDO; truncamento aproximado pode violar teto |
| R4.3 | major | Ledger persistente no cache formatado | NAO_BLOQUEANTE_DEFERIDO; medicao unica por insercao ja aplicada; nova metadata amplia invalidacao |
| R4.4 | major | API publica de invalidacao | FALSO_POSITIVO; metodo proposto nao existe nesse gerenciador |
| R4.5 | trivial | Trocar erro de remocao sem progresso por log/return | DECISAO_INTENCIONAL; estado inconsistente deve falhar explicitamente |
| R4.6 | major | Lista duplicada de colunas de data | Corrigido; configuracao usa copia list da constante unica; 68 testes aprovados |
| R4.7 | trivial | Restaurar cache normalizado no teste de tabela | Corrigido; fixture restaura identidade, conteudo e geracao |
| R4.8 | trivial | Preservar workers anteriores no teste de tabela | Corrigido; finally restaura estado mesmo com falha de Qt |
| R4.9 | trivial | Renomear utilitario privado | NAO_BLOQUEANTE_DEFERIDO; mudanca estrutural sem defeito funcional |
| R4.10 | trivial | Contagem duplicada no payload avancado | FALSO_POSITIVO; seen evita duplicacao por identidade |
| R4.11 | trivial | Orcamento unico para os dois caches de data | NAO_BLOQUEANTE_DEFERIDO; muda politica; chaves ja permanecem pareadas |
| R4.12 | trivial | Limitar frequencia de warning | NAO_BLOQUEANTE_DEFERIDO; sem spam reproduzido; evitar estado extra |
| R4.13 | trivial | Propriedades publicas do lifecycle | NAO_BLOQUEANTE_DEFERIDO; mudanca estrutural |
| R4.14 | trivial | Retirar clear quando medicao falha | FALSO_POSITIVO; entradas sem medida nao podem garantir o teto |
| R4.15 | major | Copia rasa no worker | DECISAO_INTENCIONAL; preservar contrato de copia isolada testado |
| R4.16 | major | Guardar tamanhos no cache de coluna | NAO_BLOQUEANTE_DEFERIDO; sem hotspot demonstrado nesse owner |
| R4.17 | major | Contabilizacao da metadata nomeada | Corrigido; payload e overhead medidos separadamente; extracao publica continua deferida |
| R4.18 | minor | Divisor quatro no cache de responsaveis | FALSO_POSITIVO; apenas tres owners recebem entradas |
| R4.19 | minor | Entrada nova expulsa antes de namespaces antigos | Corrigido; admissao preserva a entrada nova e respeita a quota |

Triagem: cinco eventos corrigidos, cinco falsos positivos, duas decisoes intencionais e sete melhorias deferidas. Total das quatro rodadas, incluindo repeticoes: 40 eventos; um critical, 21 major, quatro minor e 14 trivial. O critical contrariava o contrato aprovado de rejeicoes nao bloqueantes. Nenhum conhecimento externo foi reportado pelo CodeRabbit.

Os testes de tabela passaram em 15 casos; uma falha deliberada em processEvents comprovou restauracao dos caches, geracao e lista de workers. Gitleaks, Detect-secrets e Trufflehog no diff ampliado de 39 arquivos: zero achados, exit code zero; Trufflehog sem verificacao externa de credenciais.

## Proxima atividade

Validar posicoes em Series nos metodos existentes, com indice de busca materializado antes da medicao. Repetir smoke no runtime final, consolidar tempo/RSS e revisao independente dos dois arquivos afetados. C10/C11 e os apontamentos aplicaveis de R4 estao corrigidos. Nao ha stash para aplicar ou descartar.

Retomada ampliada: 2026-09-08 15:20 -03:00. Codigo local permanece sem commit. Nenhum banco operacional foi alterado. Os limites historicos de CUA e as pendencias de cache registrados acima descrevem rodadas anteriores; os estados atuais estao na lista de controle.

## Publicacao v4.50

Usuario autorizou commit, push padrao para GitHub/GitLab, tag e release v4.50. Retestes interrompidos por pedido explicito. Nenhum binario novo foi gerado.
