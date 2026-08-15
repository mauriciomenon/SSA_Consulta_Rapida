-- config/schema_optimized.sql
-- Schema otimizado para o banco de dados SSA_Consulta_Rapida
-- Remove duplicações e padroniza estrutura mantendo compatibilidade

CREATE TABLE IF NOT EXISTS ssa_table (
    -- Chave primária
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificadores e Status (CONSOLIDADO)
    numero_ssa TEXT,
    situacao TEXT,
    derivada_de TEXT,

    -- Localização (CONSOLIDADO)
    localizacao_codigo TEXT,
    descricao_localizacao TEXT,
    equipamento TEXT,

    -- Datas e Cronometragem (CONSOLIDADO)
    semana_cadastro INTEGER,
    data_cadastro TEXT,      -- Formato: DD/MM/AAAA HH:MM:SS ou YYYY-MM-DD HH:MM:SS

    -- Descrições (CONSOLIDADO)
    descricao_ssa TEXT,
    descricao_execucao TEXT,

    -- Setores e Pessoas (CONSOLIDADO)
    setor_emissor TEXT,
    setor_executor TEXT,
    solicitante TEXT,
    responsavel_programacao TEXT,
    responsavel_execucao TEXT,

    -- Serviços e Origem (CONSOLIDADO)
    servico_origem TEXT,
    sistema_origem TEXT,
    arquivo_origem TEXT,
    data_planilha TEXT,

    -- Prioridades (CONSOLIDADO)
    grau_prioridade_emissao TEXT,
    grau_prioridade_planejamento TEXT,

    -- Flags e Características
    execucao_simples TEXT,

    -- Programação
    semana_programada INTEGER,

    -- Prazos e Tempo
    prazo_limite TEXT,
    status_execucao_prazo TEXT,
    tempo_disponivel TEXT,
    data_limite TEXT,
    tempo_excedido TEXT,
    desde TEXT,
    tempo_total TEXT,
    desde_1 TEXT,
    total_tempo_tpe_planejado TEXT,
    total_tempo_tex_planejado TEXT,
    total_tempo_tpo_planejado TEXT,
    total_horas_programadas TEXT,
    total_tempo_tpe_executada TEXT,

    -- Execução
    semana_executada INTEGER,
    num_reprogramacoes INTEGER,
    execucao_parcial TEXT,
    anomalia TEXT,

    -- Campos adicionais encontrados nos arquivos Excel
    registros_espera TEXT,
    num_reprobaciones INTEGER,
    situacao_espera TEXT,
    numero_desvios INTEGER,
    ate TEXT,
    justificativa TEXT,
    total_tempo_tex_executada TEXT,
    parciais TEXT,
    situacao_da_parcial TEXT,
    ate_1 TEXT,
    ate_2 TEXT,
    desde_2 TEXT,
    total_tempo_tpo_executada TEXT,
    atividade_especial TEXT,
    equipamento_retirado TEXT,
    sn_retirado TEXT,
    destino TEXT,
    equipamento_instalado TEXT,
    sn_instalado TEXT,
    sn_extra TEXT,
    origem TEXT,
    desativacao_da_localizacao TEXT,
    instalacao_estimada TEXT,
    executado TEXT,
    concluido TEXT,
    data_inicio_programada TEXT,
    data_programacao TEXT,
    data_inicio_reprogramada TEXT,
    data_reprogramacao TEXT,
    situacao_reprogramacao TEXT,
    total_de_reprogramacoes INTEGER,
    situacao_de_desvio TEXT,
    numero_ssa_relacionada_1 TEXT,
    numero_ssa_relacionada_2 TEXT,
    numero_ssa_relacionada_3 TEXT,
    setor_emissor_relacionado_1 TEXT,
    setor_emissor_relacionado_2 TEXT,
    setor_executor_relacionado_1 TEXT,
    setor_executor_relacionado_2 TEXT,
    situacao_relacionada_1 TEXT,
    situacao_relacionada_2 TEXT,
    relacao TEXT

    -- REMOVIDAS as seguintes colunas duplicadas:
    -- "Número da SSA" (migrado para numero_ssa)
    -- "Semana de Cadastro" (migrado para semana_cadastro)  
    -- "Descrição Execução" (migrado para descricao_execucao)
    -- "Responsável na Programação" (migrado para responsavel_programacao)
    -- "Responsável na Execução" (migrado para responsavel_execucao)
    -- "Grau de Prioridade Emissão" (migrado para grau_prioridade_emissao)
    -- "Grau de Prioridade Planejamento" (migrado para grau_prioridade_planejamento)
);

-- Índices para melhorar performance de consultas
CREATE INDEX IF NOT EXISTS idx_numero_ssa ON ssa_table (numero_ssa);
CREATE INDEX IF NOT EXISTS idx_situacao ON ssa_table (situacao);
CREATE INDEX IF NOT EXISTS idx_setor_executor ON ssa_table (setor_executor);
CREATE INDEX IF NOT EXISTS idx_setor_emissor ON ssa_table (setor_emissor);
CREATE INDEX IF NOT EXISTS idx_semana_cadastro ON ssa_table (semana_cadastro);
CREATE INDEX IF NOT EXISTS idx_semana_programada ON ssa_table (semana_programada);
CREATE INDEX IF NOT EXISTS idx_semana_executada ON ssa_table (semana_executada);
CREATE INDEX IF NOT EXISTS idx_data_cadastro ON ssa_table (data_cadastro);
CREATE INDEX IF NOT EXISTS idx_localizacao_codigo ON ssa_table (localizacao_codigo);

-- Índices compostos para consultas complexas
CREATE INDEX IF NOT EXISTS idx_numero_ssa_situacao ON ssa_table (numero_ssa, situacao);
CREATE INDEX IF NOT EXISTS idx_setor_executor_semana ON ssa_table (setor_executor, semana_cadastro);
CREATE INDEX IF NOT EXISTS idx_situacao_semana ON ssa_table (situacao, semana_cadastro);

-- Compatibilidade retroativa: alias legada 'ssas' para leitura
-- Algumas rotinas de teste/legado ainda consultam a tabela 'ssas'.
-- Criamos uma VIEW para manter compatibilidade sem duplicar dados.
CREATE VIEW IF NOT EXISTS ssas AS SELECT * FROM ssa_table;
-- View legada adicional para testes antigos que referenciam 'ssa_chamados'
CREATE VIEW IF NOT EXISTS ssa_chamados AS SELECT * FROM ssa_table;
