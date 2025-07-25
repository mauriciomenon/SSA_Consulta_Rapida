-- config/schema.sql
-- Schema do banco de dados para o projeto SSA_Consulta_Rapida

CREATE TABLE IF NOT EXISTS ssas (
    -- Chave primária
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificadores e Status
    numero_ssa INTEGER,
    situacao TEXT,
    derivada_de TEXT,

    -- Localização
    localizacao_codigo TEXT,
    descricao_localizacao TEXT,
    equipamento TEXT,

    -- Datas e Cronometragem
    semana_cadastro INTEGER, -- Tipo INTEGER conforme tratamento no extractor
    data_cadastro TEXT,      -- Armazenada como TEXT no formato DD/MM/AAAA HH:MM:SS

    -- Descrições
    descricao_ssa TEXT,
    descricao_execucao TEXT,

    -- Setores e Pessoas
    setor_emissor TEXT,
    setor_executor TEXT,
    solicitante TEXT,
    responsavel_programacao TEXT,
    responsavel_execucao TEXT,

    -- Serviços e Origem
    servico_origem TEXT,
    sistema_origem TEXT,

    -- Prioridades
    grau_prioridade_emissao TEXT,
    grau_prioridade_planejamento TEXT,

    -- Flags e Características
    execucao_simples TEXT,

    -- Programação
    semana_programada INTEGER, -- Tipo INTEGER

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
    semana_executada INTEGER, -- Tipo INTEGER
    num_reprogramacoes INTEGER, -- Tipo INTEGER
    execucao_parcial TEXT,
    anomalia TEXT
    -- Adicione outras colunas conforme necessário, baseando-se nos seus arquivos e mapeamentos
);

-- Indices podem ser adicionados para melhorar a performance de buscas
-- CREATE INDEX idx_numero_ssa ON ssas (numero_ssa);
-- CREATE INDEX idx_setor_executor ON ssas (setor_executor);
-- CREATE INDEX idx_semana_cadastro ON ssas (semana_cadastro);
-- CREATE INDEX idx_situacao ON ssas (situacao);
