# Validacao e integridade

`armazenamento/database_integrity.py` separa falha estrutural de inconsistencia
de dados. A politica A5 permite continuar a importacao com inconsistencias de
conteudo para que uma reimportacao possa corrigi-las, com diagnostico preservado.

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
