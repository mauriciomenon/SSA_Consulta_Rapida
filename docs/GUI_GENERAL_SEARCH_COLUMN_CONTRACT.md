# Contrato De Colunas Da Busca Geral Da GUI

## Objetivo

Este documento define o contrato da busca geral da GUI.

Regra central:
1. a GUI decide quais colunas entram na busca geral;
2. o core continua oferecendo `filter_dataframe(..., search_columns=None)` como fallback generico;
3. o fallback do core nao e a fonte de verdade do comportamento da GUI.

## Semantica Atual

1. virgula na busca geral = `AND` implicito;
2. `!` exclui termo;
3. `^`, `$`, `=`, `~` mantem os modos atuais;
4. filtro por coluna continua com semantica propria dentro da coluna.

Fora de escopo neste ciclo:
1. fuzzy search;
2. alias de negocio;
3. mudanca da semantica da virgula.

## Erro Historico

Durante muito tempo, a decisao de quais colunas a GUI pesquisava ficou escondida no
default interno de `core.app_logic.filter_dataframe(..., search_columns=None)`.

Isso gerou um erro arquitetural:
1. a GUI parecia ter "busca geral";
2. mas o contrato real estava enterrado em `priority_columns` no core;
3. novas expectativas de produto batiam em uma implementacao implicita e pouco visivel;
4. a documentacao acompanhou o detalhe interno em vez do contrato correto.

Correcao desta frente:
1. a GUI passa uma lista explicita de colunas para `filter_dataframe(...)`;
2. a lista e derivada a partir do DataFrame atual;
3. a documentacao passa a tratar isso como contrato da GUI, nao como heuristica do core.

## Lista Base Explicita

Estas colunas entram primeiro, nesta ordem, se existirem no DataFrame atual:

1. `numero_ssa`
2. `situacao`
3. `derivada_de`
4. `localizacao_codigo`
5. `descricao_localizacao`
6. `equipamento`
7. `descricao_ssa`
8. `descricao_execucao`
9. `setor_emissor`
10. `setor_executor`
11. `solicitante`
12. `responsavel_solicitante`
13. `responsavel_programacao`
14. `responsavel_execucao`
15. `responsavel_emissor`
16. `servico_origem`
17. `sistema_origem`
18. `arquivo_origem`
19. `justificativa`
20. `anomalia`
21. `situacao_espera`
22. `situacao_reprogramacao`
23. `situacao_de_desvio`
24. `atividade_especial`
25. `destino`
26. `origem`
27. `numero_ssa_relacionada_1`
28. `numero_ssa_relacionada_2`
29. `numero_ssa_relacionada_3`
30. `setor_emissor_relacionado_1`
31. `setor_emissor_relacionado_2`
32. `setor_executor_relacionado_1`
33. `setor_executor_relacionado_2`
34. `situacao_relacionada_1`
35. `situacao_relacionada_2`
36. `relacao`
37. `grau_prioridade`
38. `grau_prioridade_emissao`
39. `grau_prioridade_planejamento`
40. `prioridade_emissao`
41. `prioridade_planejamento`
42. `semana_cadastro`
43. `semana_programada`
44. `semana_executada`

## Lista Base Excluida

Estas colunas ficam fora da busca geral por default.
Motivos principais:
1. datas puras e melhores nos filtros especificos;
2. campos de tempo, totalizacao e contagem geram ruido;
3. seriais e campos tecnicos nao sao bons candidatos para busca livre.

1. `id`
2. `data_cadastro`
3. `data_planilha`
4. `execucao_simples`
5. `prazo_limite`
6. `prazo_limite_str`
7. `status_execucao_prazo`
8. `tempo_disponivel`
9. `data_limite`
10. `tempo_excedido`
11. `desde`
12. `tempo_total`
13. `desde_1`
14. `total_tempo_tpe_planejado`
15. `total_tempo_tex_planejado`
16. `total_tempo_tpo_planejado`
17. `total_horas_programadas`
18. `total_tempo_tpe_executada`
19. `num_reprogramacoes`
20. `execucao_parcial`
21. `registros_espera`
22. `num_reprobaciones`
23. `numero_desvios`
24. `ate`
25. `total_tempo_tex_executada`
26. `parciais`
27. `situacao_da_parcial`
28. `ate_1`
29. `ate_2`
30. `desde_2`
31. `total_tempo_tpo_executada`
32. `equipamento_retirado`
33. `sn_retirado`
34. `equipamento_instalado`
35. `sn_instalado`
36. `sn_extra`
37. `desativacao_da_localizacao`
38. `instalacao_estimada`
39. `executado`
40. `concluido`
41. `data_inicio_programada`
42. `data_programacao`
43. `data_inicio_reprogramada`
44. `data_reprogramacao`
45. `total_de_reprogramacoes`
46. `data_arquivo_origem`
47. `data_cadastro_str`

## Regra De Extensao Automatica

Depois da lista base explicita, a GUI pode incluir automaticamente novas colunas
textuais elegiveis presentes no DataFrame atual.

Entram automaticamente:
1. colunas textuais novas;
2. colunas categoriais;
3. colunas de objeto usadas como texto;
4. colunas que nao estejam na lista base excluida;
5. colunas que nao parecam campos tecnicos de data, total, tempo, serial ou cache.

Ficam fora automaticamente:
1. prefixos `_`, `data_`, `tempo_`, `total_`, `sn_`;
2. sufixos `_ts`, `_timestamp`, `_str`;
3. qualquer coluna explicitamente listada como excluida.

Importante:
1. `semana*` e `grau_prioridade*` sao dados relevantes e permanecem dentro da busca geral;
2. datas puras continuam fora da busca livre por decisao de produto deste ciclo.

## Relacao Entre GUI E Core

1. a GUI monta a lista de colunas por `build_gui_general_search_columns(df)`;
2. a GUI passa essa lista explicitamente ao `filter_dataframe(...)`;
3. o `FilterWorker` so consome a lista recebida;
4. o core continua com suporte a `search_columns=None` como fallback generico.

## Doc De Continuidade

Ao retomar esta frente, conferir tambem:
1. `docs/README.md`
2. `README.md`
3. `AGENTS.md`

## Deferido

1. fuzzy search permanece deferido para release futuro;
2. qualquer tentativa de alias ou sinonimo de negocio continua proibida sem aprovacao explicita.
