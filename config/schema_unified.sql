-- config/schema_unified.sql
-- Schema unificado oficial. Base = ssa_table.
-- Superset de colunas presentes em schema.sql + schema_optimized.sql + colunas adicionais recentes.
-- Manter views de compatibilidade (ssas, ssa_chamados) para código legado.
-- Futuras migrações: usar scripts em scripts/migracao/ para ALTER TABLE incremental.

PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS ssa_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Identificadores
    numero_ssa TEXT,
    situacao TEXT,
    derivada_de TEXT,

    -- Localização
    localizacao_codigo TEXT,
    descricao_localizacao TEXT,
    equipamento TEXT,

    -- Datas básicas
    semana_cadastro INTEGER,
    data_cadastro TEXT,

    -- Descrições
    descricao_ssa TEXT,
    descricao_execucao TEXT,

    -- Setores / Pessoas
    setor_emissor TEXT,
    setor_executor TEXT,
    solicitante TEXT,
    responsavel_programacao TEXT,
    responsavel_execucao TEXT,

    -- Origem / Serviço / Sistema
    servico_origem TEXT,
    sistema_origem TEXT,

    -- Prioridades
    grau_prioridade_emissao TEXT,
    grau_prioridade_planejamento TEXT,

    -- Flags / Características
    execucao_simples TEXT,
    execucao_parcial TEXT,

    -- Programação
    semana_programada INTEGER,
    semana_executada INTEGER,
    num_reprogramacoes INTEGER,

    -- Métricas de tempo / prazos
    prazo_limite TEXT,
    status_execucao_prazo TEXT,
    tempo_disponivel TEXT,
    data_limite TEXT,
    tempo_excedido TEXT,
    desde TEXT,
    desde_1 TEXT,
    ate TEXT,
    tempo_total TEXT,
    total_tempo_tpe_planejado TEXT,
    total_tempo_tex_planejado TEXT,
    total_tempo_tpo_planejado TEXT,
    total_horas_programadas TEXT,
    total_tempo_tpe_executada TEXT,
    total_tempo_tex_executada TEXT,

    -- Qualidade / Anomalias / Desvios
    numero_desvios INTEGER,
    anomalia TEXT,
    justificativa TEXT,
    situacao_de_desvio TEXT,
    situacao_da_parcial TEXT,

    -- Campos de espera / registros adicionais
    registros_espera TEXT,
    situacao_espera TEXT,
    num_reprobaciones INTEGER,
    parciais TEXT,
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
);

-- Índices essenciais
CREATE INDEX IF NOT EXISTS idx_ssa_numero ON ssa_table (numero_ssa);
CREATE INDEX IF NOT EXISTS idx_ssa_situacao ON ssa_table (situacao);
CREATE INDEX IF NOT EXISTS idx_ssa_executor ON ssa_table (setor_executor);
CREATE INDEX IF NOT EXISTS idx_ssa_emissor ON ssa_table (setor_emissor);
CREATE INDEX IF NOT EXISTS idx_ssa_semana_cad ON ssa_table (semana_cadastro);
CREATE INDEX IF NOT EXISTS idx_ssa_semana_prog ON ssa_table (semana_programada);
CREATE INDEX IF NOT EXISTS idx_ssa_semana_exec ON ssa_table (semana_executada);
CREATE INDEX IF NOT EXISTS idx_ssa_data_cad ON ssa_table (data_cadastro);
CREATE INDEX IF NOT EXISTS idx_ssa_loc_codigo ON ssa_table (localizacao_codigo);
CREATE INDEX IF NOT EXISTS idx_ssa_numero_situacao ON ssa_table (numero_ssa, situacao);

-- Views de compatibilidade
CREATE VIEW IF NOT EXISTS ssas AS SELECT * FROM ssa_table;
CREATE VIEW IF NOT EXISTS ssa_chamados AS SELECT * FROM ssa_table;

COMMIT;
