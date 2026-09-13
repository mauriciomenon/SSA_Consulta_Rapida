Correcao de contagem em 12/09/2026: ha 16 commits com credito proibido em dev..ca542fb5. A contagem anterior de 15 usava intervalo que excluia 36dc3137; foi corrigida neste documento. O primeiro commit tambem contem Generated with e Co-Authored-By.

Registro historico do commit ca542fb5. Em 12/09/2026 o mantenedor autorizou implementar exportacao JSON/CSV/TSV na CLI e GUI, preservando APIs/stdout, e corrigir F3, F4 e residuos de fechamento/concorrencia. A recomendacao anterior de adiar interfaces foi substituida por esse pedido. Estado atual em AUDIT_FIXES_REPORT.md. Em 13/09/2026 as correcoes foram commitadas e publicadas ate 1ef9edaf; este laudo preserva o diagnostico da base, nao descreve defeitos ainda abertos nessa ponta.

Laudo de revisao e de decisoes da auditoria SSA Consulta Rapida, em 12/09/2026.

Escopo: cinco anexos fornecidos pelo mantenedor, relatorio local e codigo de `fix/audit-surgical-fixes` em `ca542fb535b604575666f50aeb37d125c1324dc3`. As duas tabelas mestre anexadas sao identicas. Esta rodada executou diagnostico, leitura e testes; nao aplicou correcoes ao projeto nem operacoes de escrita no Git. Os comandos de reescrita citados nos anexos foram tratados como propostas, nao como autorizacao.

**Parecer sobre o commit publicado ca542fb5, antes da implementacao:** ha correcoes reais e verificadas, mas o encerramento anunciado esta incompleto. F3 continua aberto, N11 nao cobre derivadas, N8 ainda pode perder o resultado atual, e N7 tem residuos. Exportacao e uma escolha de produto; consistencia dos gates, resultados de operacoes e cumprimento da regra de autoria sao responsabilidades tecnicas/processuais.

Uma decisao informada precisa conter o comportamento atual, a necessidade atendida, o impacto de mudar, a alternativa de manter e uma recomendacao. A tabela abaixo distingue esses casos.

| Assunto | Natureza | Recomendacao | O que depende do mantenedor |
|---|---|---|---|
| CD-1: expor exportadores | Funcionalidade opcional | Manter API e stdout agora; se houver necessidade recorrente, priorizar JSON no CLI | Necessidade de nova interface e publico atendido |
| F3: reparo seguido de rejeicao contraditoria | Defeito tecnico | Aplicar a politica estrutural/dados tambem depois do reparo | Aprovar plano de correcao; nao escolher se a contradicao deve existir |
| N7/N11: fechamento e retomada | Defeitos/residuos tecnicos | Completar os caminhos de adiamento e reconhecer todas as operacoes | Aprovar plano; mudar a politica de fechamento seria outra decisao |
| N8: resultado valido sobrescrito | Defeito de concorrencia residual | Impedir entrega antiga de apagar resultado atual | Aprovar plano de correcao |
| F4: promocao com dados inconsistentes | Politica A5 implementada mais lacuna de visibilidade | Manter promocao e informar ressalvas sem bloquear o fluxo | Mudar a politica A5 ou escolher outra apresentacao |
| N3: textos de coautoria nos commits | Descumprimento da regra explicita de autoria | Remover os textos mediante reescrita autorizada | Autorizar escopo e momento da reescrita publicada |
| Remover APIs e wrappers | Manutencao/compatibilidade | Limpeza dedicada com consumidores e contratos conferidos | Aprovar eventual quebra de API e prioridade |
| Itens fora de escopo | Pendencias de outra rodada | Manter inventario com impacto e evidencia por item | Prioridade de UX; defeitos concretos continuam sendo tecnicos |

**CD-1: o que as funcoes entregam e o que falta de fato.**

`armazenamento/derivadas_sync.py:2184` exporta um resumo CSV de reconciliacao. `:2211` serializa o relatorio completo em JSON. Sao funcoes importaveis, sem consumidores internos ou testes diretos identificados nos arquivos versionados.

O commit `8f6e75a2` introduziu as funcoes e o CLI juntos. A CLI original ja imprimia JSON e nao chamava os exportadores. A busca historica nao demonstrou uma chamada removida por refatoracao. Portanto, a classificacao sustentada e API sem consumo interno identificado; a ausencia de ligacao nao comprova implementacao defeituosa ou perda de funcionalidade antes existente.

O CLI atual ja entrega os relatorios em stdout (`scripts/derivadas_cli.py:355`). O runbook recomenda arquivar saidas JSON (`docs/DERIVADAS_SYNC_RUNBOOK.md:38`). Redirecionar stdout permite salvar essa saida sem novo recurso. Isso distingue ausencia de flags dedicadas de ausencia de acesso ao relatorio.

| Caminho | Beneficio | Custo/limite real | Parecer |
|---|---|---|---|
| Manter como esta | Preserva API e automacoes; JSON ja disponivel | Continua sem acao de arquivo no app | Recomendado enquanto nao houver necessidade recorrente demonstrada |
| Flag JSON no CLI | Facilita arquivamento em rotinas | Tratar destinos, sobrescrita e erro de exportacao sem alterar stdout/exit codes | Primeira extensao indicada se o arquivamento direto for desejado |
| Flag CSV no CLI | Facilita comparacao de contagens em planilhas | O CSV atual tem formato especifico de sync e nao equivale ao JSON completo | Limitar inicialmente a sync ou definir explicitamente outros casos |
| Acao na GUI | Permite salvar sem terminal | Exige reter o relatorio da execucao correta, dialogo, cancelamento e feedback | Justificada por necessidade de operadores GUI; nao por zero callers |
| Deletar as funcoes | Reduz superficie de manutencao | Pode quebrar scripts externos; nenhum ganho de desempenho foi demonstrado | Nao recomendada nesta auditoria apenas para reduzir cerca de 30 linhas |

A alternativa de manter API sem nova interface estava ausente da proposta A/B/C. Ela preserva o comportamento estabilizado e nao impede uma extensao posterior. Nao e necessario adicionar funcionalidade para justificar duas funcoes existentes, nem remove-las para declarar uma auditoria concluida.

O CSV possui uma linha e dez colunas: timestamp, modo, verify_only, contagens de arestas, filhos com multiplos pais, pais/filhos orfaos, conflitos banco-planilha e nos envolvidos em ciclos. Omite detalhes presentes no JSON, inclusive amostras e estados de manutencao.

| Resultado | Uso do CSV atual |
|---|---|
| sync normal ou verify-only | Relatorio de reconciliacao no nivel esperado |
| heal com reparo | Relatorio de sync dentro de `result["sync"]` |
| heal sem reparo | Nao existe relatorio de sync |
| maintenance com reparo | Relatorio dentro de `result["heal"]["sync"]` |
| maintenance adiada/sem reparo, scan, stats | Nao possuem o formato esperado pelo exportador |

Passar diretamente o resultado raiz de heal ou maintenance ao helper CSV pode gerar identificacao vazia e contagens zero, porque ele usa valores padrao sem validar o formato. Isso e um risco de uma ligacao futura indiscriminada, nao uma regressao ativa no CLI atual.

Ambos os exportadores usam abertura em modo `w`: sobrescrevem o destino, nao criam diretorio pai e nao fazem substituicao atomica. A falha propaga ao chamador. Uma interface nova deve evitar colisao com banco/planilhas e distinguir falha ao salvar de falha na sincronizacao. A transacao de sync ja foi confirmada antes de retornar o relatorio (`derivadas_sync.py:1765`); um erro de exportacao posterior nao desfaz a operacao.

A estimativa de aproximadamente 15 linhas descreve a ligacao mais curta, mas nao demonstra uma entrega completa com contratos, erros e testes. Minha recomendacao e manter CD-1 como melhoria opcional. Se for solicitado arquivamento direto, priorizar JSON no CLI, preservar stdout e tratar CSV de sync separadamente.

**F3: defeito confirmado, sem necessidade de escolher uma nova politica.**

O caminho sem reparo permite inconsistencia de dados quando as condicoes estruturais sao adequadas (`armazenamento/database_integrity.py:573`). Depois de adicionar colunas opcionais, o codigo volta a exigir `is_valid` pleno (`:627`). `core/app_logic.py:1404` converte a rejeicao em `DatabaseCorruptionError`.

Reproducao com SQLite real e temporario:

| Entrada | Resultado |
|---|---|
| Opcionais presentes + situacao ZZZ | Aceita |
| Opcionais ausentes + situacao ADM | Repara e aceita |
| Opcionais ausentes + situacao ZZZ | Repara colunas, mas rejeita na primeira tentativa |
| Segunda tentativa do caso anterior | Aceita os mesmos dados inconsistentes |

SQLite e schema estavam validos depois do reparo. Isso demonstra a assimetria. A reproducao nao sustenta chamar o bloqueio de permanente: uma segunda tentativa passou. Ainda assim, a primeira tentativa rejeita um banco que a politica A5 deveria permitir reimportar.

Recomendacao: aplicar ao resultado pos-reparo os mesmos criterios de estrutura, permissoes e qualidade de dados. Nao basta substituir a checagem por `return True`; os bloqueios estruturais e de escrita precisam continuar ativos. Testar a combinacao, nao somente cada problema isolado.

**F4: a politica de promocao e a qualidade da informacao sao assuntos distintos.**

A5 permite promover um banco estruturalmente utilizavel com inconsistencias de dados para evitar bloquear a reimportacao. Alterar essa politica exige uma decisao de comportamento. F3 e a aplicacao inconsistente dessa politica.

F4 diz respeito a informacao apresentada. A promocao devolve `ok=True` com `integrity_report.is_valid=False` (`core/app_logic.py:1289`). O relatorio completo permanece em `ImportOutcome`; a GUI nao precisa inventar outra verificacao.

O aviso usa o logger `core.app_logic`, enquanto o RescanWorker conecta a captura ao logger `ssa` (`gui/workers/rescan_worker.py:234`). Em ensaio com sinais Qt reais, um aviso de controle em `ssa` chegou ao sinal; o aviso da promocao nao produziu output_line nem error_line. O encerramento do worker apresenta sucesso sem consumir as ressalvas (`:744`). O JSON de execucao preserva validade e contagens, mas nao todos os detalhes (`core/import_run_report.py:214`).

Recomendacao: manter A5 e informar sucesso com ressalvas por meio do relatorio ja disponivel. Um aviso final nao modal, com mensagem objetiva e acesso a detalhes quando disponiveis, e o padrao indicado. Canal, texto e persistencia visual sao escolhas de apresentacao. Exibir apenas sucesso quando existem inconsistencias conhecidas e uma lacuna tecnica de visibilidade demonstrada, nao uma ausencia abstrata de preferencia do mantenedor.

**A revisao atual nao confirma que somente F3 e os textos de coautoria restam.**

| Item | Evidencia no ca542fb5 | Estado sustentado |
|---|---|---|
| N11 / F2 | Identidades comparadas incluem running_workers, mas nao a thread de derivadas (`gui/gui_ssa.py:5643`, `:5661`) | Parcial: Qt testado passa; novo episodio somente de derivadas reutiliza prazo antigo |
| N8 | `_work` ainda escreve incondicionalmente no campo compartilhado (`gui/gui_ssa.py:5372`) | Corrige aplicacao do resultado antigo, mas ainda permite perder resultado atual |
| N7, persistencia | Excecao ou timeout do gravador retorna False sem restaurar a flag (`gui/gui_ssa.py:5690`) | Residuo anterior presente |
| N7, timer | Timer SAM e parado antes da decisao de fechamento e nao retomado no adiamento | Residuo operacional reproduzido |
| N7, fechamento forcado | Evento aceito com `_is_shutting_down=False` | Invariante ainda incorreta; novas guardas de objeto destruido reduzem o risco anterior |

N11 foi reproduzido com os metodos extraidos do commit: a operacao de derivadas A termina, B comeca, e o primeiro X durante B aceita o fechamento usando o prazo de A. O CodeRabbit apontou independentemente esse mesmo caso como major. A correcao cobre os workers do teste novo, mas nao todas as classes de operacao.

N8 foi reproduzido com ordem de entregas controlada, executando os corpos originais de `_work` e `_poll_delivery`: A ja expirou; B termina e grava resultado com tag 2; A termina atrasada e sobrescreve o campo com tag 1; o poll de B descarta a tag 1; o resultado de B desapareceu e B termina por timeout. O risco de selecionar A foi tratado, mas o transporte compartilhado ainda permite perder B. O teste acrescentado exercita o finalizador diretamente e nao essa ordem de entregas.

Nao repito a alegacao de crash nativo como se as novas guardas nao existissem. Elas foram acrescentadas e protegem caminhos antes expostos. O ensaio atual confirmou a flag incorreta no fechamento forcado, sem reproduzir um novo crash completo da aplicacao.

Correcoes presentes no codigo incluem bloqueio por permissao insuficiente, restauracao de UI na falha de inicio de derivadas, restauracao do conteudo de filtros, rollback de inicio do vacuum e acao manual no menu SAM API. A cobertura executada nesta rodada esta discriminada abaixo; nao houve consulta real a API remota.

**Autoria e historico: requisito definido, operacao ainda sujeita a autorizacao.**

Os tres destinos retornaram `ca542fb5` para a branch. O autor esta unificado em Mauricio Menon com o email noreply configurado. Entretanto, 16 commits em dev..ca542fb5 ainda contem texto de coautoria proibido pela regra fornecida pelo mantenedor.

Alterar autor/email nao remove texto das mensagens. A exigencia de autoria exclusivamente humana ja esta definida; nao cabe perguntar novamente se o texto de coautoria pode permanecer. O que requer autorizacao especifica e reescrever commits publicados e atualizar as referencias remotas.

A operacao altera hashes e afeta checkouts, referencias de revisao e trabalho concorrente. Os tres destinos precisam ser verificados individualmente; `origin` tem tres URLs de push configuradas. Uma autorizacao futura deve delimitar a branch, os destinos e a preservacao de conteudo, com comparacao dos hashes remotos esperados antes de cada atualizacao. Nao houve reescrita ou push nesta revisao.

Recomendacao: fechar primeiro os defeitos tecnicos e remover os textos de coautoria e de credito nas mensagens dos commits, apos autorizacao especifica de reescrita, com mapa de hashes e verificacao das arvores. Nenhuma mudanca na politica de autoria e necessaria.

Conferencias factuais adicionais:

- Os 21 pares de commits entre os historicos `e4c910ad` e `ca542fb5` preservam suas arvores e mensagens correspondentes. A reescrita preservou o conteudo verificado.
- Doze hashes foram preservados e nove mudaram. A tabela anexada que fala em 16 hashes originais preservados esta incorreta.
- `dev` esta em `e62a85bf` localmente e nos tres destinos. Existem 21 commits em `dev..ca542fb5`.
- O intervalo exclusivo `36dc3137..ca542fb5` tem 20 commits, mas `36dc3137` e o primeiro commit da auditoria, nao o tip de dev. O numero e correto para aquele intervalo, nao para o total da branch acima de dev.
- O report local examinado naquela revisao marcava N3 como resolvido e menciona historico nao reescrito (`docs/AUDIT_FIXES_REPORT.md:69`); esse texto estava desatualizado e foi corrigido na rodada de implementacao.

**Como avaliar os demais itens classificados como decisao ou fora de escopo.**

Menus desabilitados versus mensagens de operacao ocupada sao escolhas de apresentacao quando as guardas impedem comprovadamente a reentrada. Se uma acao concorrente altera dados ou estado indevidamente, o problema e tecnico. O mesmo criterio vale para cancelamento: a granularidade entre arquivos pode ser uma limitacao aceita de UX, mas integridade e resposta honesta a cancelamento nao sao opcionais.

Aliases de colunas e formatos de entrada podem conter caracteres exigidos pelas planilhas. Padronizar texto tecnico nao autoriza quebrar esse contrato. Wrappers de compatibilidade e funcoes usadas por testes precisam ser avaliados antes de exclusao.

Nao revalidei individualmente todas as cerca de 24 pendencias antigas declaradas fora de escopo. Essa etiqueta descreve trabalho adiado; nao prova que todos os itens sejam cosmeticos, seguros ou escolhas de produto. Tambem nao certifiquei o placar agregado de 34 corrigidos, que mistura referencias a problemas relacionados.

**Validacao independente da revisao anterior a implementacao.**

Ambiente: Python 3.13.12; ty 0.0.79. Codigo revisado: os tres commits posteriores a N7, `e701bbf1..ca542fb5`, com 21 arquivos Python, +419/-22 linhas; consultas adicionais ao contexto e ao historico.

| Verificacao | Resultado |
|---|---|
| Testes GUI de fechamento, validacao de banco e filtros | 20 passed, 545 deselected |
| Testes de controlador de derivadas e menu de importacao | 23 passed |
| Testes CLI de derivadas | 16 passed |
| Testes maintenance e reconciliacao verify-only | 10 passed |
| Testes focados de integridade/promocao/reparo | 14 passed |
| Total das selecoes acima | 83 aprovacoes |
| Ensaio adicional de contratos de fechamento | 2 passed, 3 failed; falhas reproduzem os residuos descritos |
| Ensaios adicionais F3, F4 e entrega atrasada N8 | Reproducoes confirmadas; distintos da suite completa |
| CodeRabbit committed | Concluido, uma issue major sobre derivadas/deadline |
| py_compile e Ruff dos 21 arquivos | Passaram |
| ty nos 21 arquivos | Falhou com um erro novo no teste de filtro |
| ty check sem argumentos | Falhou: 18 erros e 4 avisos; demais diagnosticos fora do patch |
| pip-audit na .venv | 46 dependencias, zero vulnerabilidades; pacote local ignorado |
| Gitleaks, detect-secrets, Trufflehog | Nenhum segredo reportado no escopo executado |
| Bandit | 23 avisos em linhas novas, todos em testes; nenhum em linha nova de producao |
| Vulture | 195 candidatos no escopo; nenhum em linha alterada; nao sao prova de codigo morto |
| Semgrep | Zero findings, mas dois timeouts de regra no arquivo de testes GUI; resultado parcial |
| ShellCheck/PSScriptAnalyzer | Nao aplicaveis: nenhum script shell/PowerShell alterado |

O erro novo de ty esta em `tests/test_gui_filter_logic.py:14743`, na atribuicao de `_fake_apply` ao metodo `_apply_advanced_filters_from_ui`, com assinatura incompativel para o verificador. Os demais diagnosticos do comando amplo nao foram atribuidos a esta rodada.

Semgrep terminou com exit 0, mas seu JSON registra timeout nas regras `python.boto3.security.hardcoded-token.hardcoded-token` e `python.lang.security.audit.dangerous-system-call-tainted-env-args.dangerous-system-call-tainted-env-args`. Por isso, nao foi classificado como verificacao integral verde.

Nao reexecutei os 2924 testes completos; esse total permanece como resultado informado nos anexos. Nao fiz ensaio visual completo, consulta real a SAM API, comparacao de CPU/memoria ou verificacao em Windows/Linux. Os ensaios isolados complementam os testes existentes; nao equivalem a validacao completa de GUI.

**Entrega e proxima atividade.**

Entregue: laudo de decisoes, verificacao dos anexos, evidencias de codigo/historico, testes focados e recomendacoes. Parcial: certificacao global de todos os itens e de todas as plataformas. Nao realizado: correcoes ao codigo, alteracao do relatorio original, exclusao de API, commit, reescrita, push ou merge.

O plano de correcao apontado nesta revisao foi posteriormente aprovado pelo mantenedor, com exportacao adicional JSON/CSV/TSV nas duas interfaces e sem novos testes ou validacao pesada nesta rodada. As APIs foram mantidas. A remocao de textos de coautoria em commits publicados continua dependendo de autorizacao especifica para reescrever o historico.


Estado da primeira implementacao em 12/09/2026 (substituido pela complementacao abaixo): foram acrescentadas exportacoes CLI/GUI e correcoes de F3, F4 e concorrencia. ty passou naquele escopo de 12 arquivos. A revisao posterior confirmou residuos em preferencias/prazo e na protecao de exportacao; portanto aquela entrega nao encerrava integralmente os casos. O estado atual esta no comparativo e nas secoes I1-I5 de AUDIT_FIXES_REPORT.md. Naquela primeira entrega nao houve publicacao ou reescrita; a publicacao posterior esta registrada abaixo.


Complementacao apos a entrega incompleta: a revisao adicional confirmou fila de preferencias parada no adiamento, prazo antigo apos preferencias, protecao incompleta de WAL com symlink, revalidacao ausente depois do segundo dialogo e falta de coordenacao entre operacoes. Esses casos foram corrigidos; N8/F3 permaneceram confirmados. A7/C2 e casos concretos de D7 receberam correcao. Hooks de autoria agora estao instalados e ativos; CI implementada e posteriormente publicada em c49dbac7, sem execucao remota comprovada. O comparativo antes/depois, a validacao atual e cada item nao feito constam de AUDIT_FIXES_REPORT.md. Este laudo continua descrevendo a revisao historica de ca542fb5; nao usar seus numeros de linha/placares como estado atual.


## Resultado da implementacao e publicacao em 13/09/2026

| Decisao/defeito examinado | Desfecho |
|---|---|
| API de exportacao | Mantida; JSON/CSV existentes e TSV nova. Ausencia de caller interno nao implica API removivel. |
| CLI e GUI | Implementadas juntas em 9548f41e, preservando JSON no stdout. Guia DERIVADAS_SYNC_RUNBOOK.md. |
| F3 | Corrigido em 0448f5c8 sem mudar A5 nem enfraquecer SQLite/schema/permissoes. |
| F4 | Corrigido em 9548f41e com os avisos reais do ImportOutcome, preservados no resultado GUI. |
| N7/N8/N11 | Residuos corrigidos em 9548f41e, inclusive preferencias, resultado tardio e prazo por operacao. |
| Autoria preventiva | c49dbac7: regra versionada, hooks ativos e CI publicada. Limites online continuam discriminados. |
| Creditos antigos | 16 mensagens em e62a85bf..ca542fb5 permanecem; autor e committer sao humanos. Nao houve reescrita nesta rodada. |
| C2/menus/feedback | C2 em 1ef9edaf; coordenacao de menus e cinco casos de feedback em 9548f41e. |
| Reteste completo | Passagem pronta em VALIDATION_PLAN.md; suite pesada nao executada nesta implementacao. |

Os quatro commits de codigo foram publicados por push normal nos tres destinos.
A documentacao e consolidada em commit posterior. A referencia para antes/depois,
validacao efetiva e pendencias e AUDIT_FIXES_REPORT.md. O diagnostico historico
deste laudo nao e autorizacao de reescrita nem atestado de defeitos ainda atuais.
