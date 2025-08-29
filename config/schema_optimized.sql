-- config/schema_optimized.sql
-- Schema otimizado para o banco de dados SSA_Consulta_Rapida
-- Remove duplicações e padroniza estrutura mantendo compatibilidade

CREATE TABLE IF NOT EXISTS ssas (
    -- Chave primária
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificadores e Status (CONSOLIDADO)
    numero_ssa INTEGER,
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

    -- Prioridades (CONSOLIDADO)
    grau_prioridade_emissao TEXT,
    grau_prioridade_planejamento TEXT,

    -- Flags e Características
    execucao_simples TEXT,

    -- Programação
    semana_programada INTEGER,

    -- Prazos e Tempo
    prazo_limite TEXT,
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

    -- Execução
    semana_executada INTEGER,
    num_reprogramacoes INTEGER,
    execucao_parcial TEXT,
    anomalia TEXT

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
CREATE INDEX IF NOT EXISTS idx_numero_ssa ON ssas (numero_ssa);
CREATE INDEX IF NOT EXISTS idx_situacao ON ssas (situacao);
CREATE INDEX IF NOT EXISTS idx_setor_executor ON ssas (setor_executor);
CREATE INDEX IF NOT EXISTS idx_setor_emissor ON ssas (setor_emissor);
CREATE INDEX IF NOT EXISTS idx_semana_cadastro ON ssas (semana_cadastro);
CREATE INDEX IF NOT EXISTS idx_semana_programada ON ssas (semana_programada);
CREATE INDEX IF NOT EXISTS idx_semana_executada ON ssas (semana_executada);
CREATE INDEX IF NOT EXISTS idx_data_cadastro ON ssas (data_cadastro);
CREATE INDEX IF NOT EXISTS idx_localizacao_codigo ON ssas (localizacao_codigo);

-- Índices compostos para consultas complexas
CREATE INDEX IF NOT EXISTS idx_numero_ssa_situacao ON ssas (numero_ssa, situacao);
CREATE INDEX IF NOT EXISTS idx_setor_executor_semana ON ssas (setor_executor, semana_cadastro);
CREATE INDEX IF NOT EXISTS idx_situacao_semana ON ssas (situacao, semana_cadastro);
