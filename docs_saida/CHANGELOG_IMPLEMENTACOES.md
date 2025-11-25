# CHANGELOG DE IMPLEMENTACOES

## 2025-08-14 - Ajustes de exibição e filtros críticos
- Revisado `column_priority.json` para estabilizar `essential` e `always_visible`, evitando regressao de colunas em dashboards CLI/GUI.
- GUI recebeu correcoes nos tooltips de filtros, mantendo paridade textual com o CLI e reduzindo duvida em conectivos OU/OR.
- Atualizacao do README enfatizando politicas de remocao de artefatos de IA e links diretos para o changelog tecnico.

## 2025-07-29 - Preparacao release 4.12
- Sincronizacao dos metadados de versao (arquivo `VERSION` + `config/version.json`) antes do congelamento de build.
- Conferencia de scripts de logging para garantir que handlers continuem emitindo metricas de desempenho em execucoes GUI/CLI.
- Revisao das prioridades de colunas para exportacao, validando novamente as chaves `short_labels` e `fixed_widths` usadas no CLI.
