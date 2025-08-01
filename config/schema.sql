-- config/schema.sql
-- Schema completo e robusto para a tabela de SSAs, incluindo todas as colunas
-- identificadas nos arquivos de origem para prevenir erros de importação.

CREATE TABLE IF NOT EXISTS ssas (
    numero_ssa INTEGER,
    situacao TEXT,
    derivada_de TEXT,
    localizacao_codigo TEXT,
    descricao_localizacao TEXT,
    equipamento TEXT,
    semana_cadastro INTEGER,
    data_cadastro TEXT,
    descricao_ssa TEXT,
    setor_emissor TEXT,
    setor_executor TEXT,
    solicitante TEXT,
    servico_origem TEXT,
    grau_prioridade_emissao TEXT,
    grau_prioridade_planejamento TEXT,
    execucao_simples TEXT,
    responsavel_programacao TEXT,
    semana_programada INTEGER,
    responsavel_execucao TEXT,
    descricao_execucao TEXT,
    prazo_limite TEXT,                 -- COLUNA ADICIONADA
    tempo_disponivel TEXT,             -- COLUNA ADICIONADA
    data_limite TEXT,                  -- COLUNA ADICIONADA
    tempo_excedido TEXT,               -- COLUNA ADICIONADA
    desde TEXT,                        -- COLUNA ADICIONADA
    tempo_total TEXT,                  -- COLUNA ADICIONADA
    desde_1 TEXT,                      -- COLUNA ADICIONADA
    total_tempo_tpe_planejado REAL,    -- COLUNA ADICIONADA
    total_tempo_tex_planejado REAL,    -- COLUNA ADICIONADA
    total_tempo_tpo_planejado REAL,    -- COLUNA ADICIONADA
    total_horas_programadas REAL,      -- COLUNA ADICIONADA
    semana_executada INTEGER,          -- COLUNA ADICIONADA
    num_reprogramacoes INTEGER,        -- COLUNA ADICIONADA
    execucao_parcial TEXT,             -- COLUNA ADICIONADA
    anomalia TEXT,                     -- COLUNA ADICIONADA
    sistema_origem TEXT,               -- COLUNA ADICIONADA
    PRIMARY KEY(numero_ssa) ON CONFLICT REPLACE -- Garante que SSAs sejam únicas ou atualizadas
);