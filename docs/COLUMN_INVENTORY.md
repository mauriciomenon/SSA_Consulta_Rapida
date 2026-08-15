# Column Inventory Overview

- Total schema columns: 82
- Columns without display mapping: id, ate, total_tempo_tpe_executada, total_tempo_tex_executada, numero_desvios, justificativa, situacao_da_parcial, registros_espera, situacao_espera, num_reprobaciones, parciais
- Display mapping entries not in schema: numero_ssa_sem_acento
- Default GUI columns: 12
- Hidden by default: 7

## Categories

### Identificacao (6)
- arquivo_origem, id, numero_ssa, numero_ssa_relacionada_1, numero_ssa_relacionada_2, numero_ssa_relacionada_3

### Status (8)
- situacao, situacao_da_parcial, situacao_de_desvio, situacao_espera, situacao_relacionada_1, situacao_relacionada_2
- situacao_reprogramacao, status_execucao_prazo

### Localizacao (11)
- ate, ate_1, ate_2, desativacao_da_localizacao, descricao_localizacao, desde
- desde_1, desde_2, destino, localizacao_codigo, origem

### Equipamentos (6)
- equipamento, equipamento_instalado, equipamento_retirado, sn_extra, sn_instalado, sn_retirado

### Datas e Prazos (22)
- concluido, data_cadastro, data_inicio_programada, data_inicio_reprogramada, data_limite, data_programacao
- data_reprogramacao, executado, instalacao_estimada, prazo_limite, semana_cadastro, semana_executada
- semana_programada, tempo_disponivel, tempo_excedido, tempo_total, total_tempo_tex_executada, total_tempo_tex_planejado
- total_tempo_tpe_executada, total_tempo_tpe_planejado, total_tempo_tpo_executada, total_tempo_tpo_planejado

### Pessoas e Setores (9)
- responsavel_execucao, responsavel_programacao, setor_emissor, setor_emissor_relacionado_1, setor_emissor_relacionado_2, setor_executor
- setor_executor_relacionado_1, setor_executor_relacionado_2, solicitante

### Prioridades (2)
- grau_prioridade_emissao, grau_prioridade_planejamento

### Execucao e Fluxo (7)
- atividade_especial, execucao_parcial, execucao_simples, num_reprogramacoes, parciais, registros_espera
- total_de_reprogramacoes

### Qualidade e Desvios (4)
- anomalia, justificativa, num_reprobaciones, numero_desvios

### Metadados Diversos (7)
- derivada_de, descricao_execucao, descricao_ssa, relacao, servico_origem, sistema_origem, total_horas_programadas

## Observacoes
- 'id' permanece apenas para compatibilidade com consultas diretas; nao e exibido na interface.
- Campos sem rotulo em 'display_mappings' (por exemplo 'numero_desvios', 'situacao_da_parcial') aparecem apenas em fluxos internos; convem definir nomes amigaveis antes de leva-los para a UI.
- 'arquivo_origem' e preenchido durante a importacao e fica oculto por padrao; pode ser exposto em relatorios conforme necessidade.
- As categorias acima foram geradas por heuristicas baseadas no nome das colunas; revise antes de qualquer ajuste visual.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

