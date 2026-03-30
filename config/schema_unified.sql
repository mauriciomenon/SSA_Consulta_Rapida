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
    arquivo_origem TEXT,
    data_planilha TEXT,

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

-- ============================================================
-- Derivadas: matriz canonica + fonte por aresta + fechamento + resumo
-- ============================================================
CREATE TABLE IF NOT EXISTS ssa_derivada_matrix (
    parent_ssa TEXT NOT NULL,
    child_ssa TEXT NOT NULL,
    source_flags INTEGER NOT NULL DEFAULT 0,
    relation_type INTEGER NOT NULL DEFAULT 0,
    relation_raw_label TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (parent_ssa, child_ssa),
    CHECK (parent_ssa <> child_ssa),
    CHECK (length(parent_ssa) = 9),
    CHECK (length(child_ssa) = 9),
    CHECK (parent_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (child_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (source_flags >= 0),
    CHECK (active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_derivada_matrix_parent ON ssa_derivada_matrix (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_child ON ssa_derivada_matrix (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_flags ON ssa_derivada_matrix (source_flags);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active ON ssa_derivada_matrix (active);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_parent ON ssa_derivada_matrix (active, parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_matrix_active_child ON ssa_derivada_matrix (active, child_ssa);

CREATE TABLE IF NOT EXISTS ssa_derivada_source (
    parent_ssa TEXT NOT NULL,
    child_ssa TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_flag INTEGER NOT NULL DEFAULT 0,
    relation_type INTEGER NOT NULL DEFAULT 0,
    relation_raw_label TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (parent_ssa, child_ssa, source_name),
    CHECK (parent_ssa <> child_ssa),
    CHECK (length(parent_ssa) = 9),
    CHECK (length(child_ssa) = 9),
    CHECK (parent_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (child_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (source_name <> ''),
    CHECK (source_flag >= 0),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_derivada_source_name ON ssa_derivada_source (source_name);
CREATE INDEX IF NOT EXISTS idx_derivada_source_active ON ssa_derivada_source (is_active);
CREATE INDEX IF NOT EXISTS idx_derivada_source_parent ON ssa_derivada_source (parent_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_child ON ssa_derivada_source (child_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_source_name_active ON ssa_derivada_source (source_name, is_active);

CREATE TABLE IF NOT EXISTS ssa_derivada_closure (
    ancestor_ssa TEXT NOT NULL,
    descendant_ssa TEXT NOT NULL,
    min_distance INTEGER NOT NULL,
    max_distance INTEGER NOT NULL,
    path_count INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT NOT NULL,
    PRIMARY KEY (ancestor_ssa, descendant_ssa),
    CHECK (ancestor_ssa <> descendant_ssa),
    CHECK (length(ancestor_ssa) = 9),
    CHECK (length(descendant_ssa) = 9),
    CHECK (ancestor_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (descendant_ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (min_distance >= 1),
    CHECK (max_distance >= min_distance),
    CHECK (path_count >= 1)
);

CREATE INDEX IF NOT EXISTS idx_derivada_closure_ancestor ON ssa_derivada_closure (ancestor_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_descendant ON ssa_derivada_closure (descendant_ssa);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_min_distance ON ssa_derivada_closure (min_distance);
CREATE INDEX IF NOT EXISTS idx_derivada_closure_max_distance ON ssa_derivada_closure (max_distance);

CREATE TABLE IF NOT EXISTS ssa_derivada_summary (
    ssa TEXT PRIMARY KEY,
    direct_parents_count INTEGER NOT NULL DEFAULT 0,
    direct_children_count INTEGER NOT NULL DEFAULT 0,
    ancestors_count INTEGER NOT NULL DEFAULT 0,
    descendants_count INTEGER NOT NULL DEFAULT 0,
    level_from_root_min INTEGER,
    level_from_root_max INTEGER,
    levels_above_max INTEGER NOT NULL DEFAULT 0,
    levels_below_max INTEGER NOT NULL DEFAULT 0,
    component_size INTEGER NOT NULL DEFAULT 1,
    has_cycle INTEGER NOT NULL DEFAULT 0,
    last_sync_at TEXT NOT NULL,
    CHECK (length(ssa) = 9),
    CHECK (ssa GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    CHECK (direct_parents_count >= 0),
    CHECK (direct_children_count >= 0),
    CHECK (ancestors_count >= 0),
    CHECK (descendants_count >= 0),
    CHECK (levels_above_max >= 0),
    CHECK (levels_below_max >= 0),
    CHECK (component_size >= 1),
    CHECK (has_cycle IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_derivada_summary_direct_children ON ssa_derivada_summary (direct_children_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_descendants ON ssa_derivada_summary (descendants_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_ancestors ON ssa_derivada_summary (ancestors_count);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_below ON ssa_derivada_summary (levels_below_max);
CREATE INDEX IF NOT EXISTS idx_derivada_summary_levels_above ON ssa_derivada_summary (levels_above_max);

CREATE TABLE IF NOT EXISTS ssa_derivada_sync_run (
    sync_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT '',
    managed_sources TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    db_edges INTEGER NOT NULL DEFAULT 0,
    sheet_edges INTEGER NOT NULL DEFAULT 0,
    merged_edges INTEGER NOT NULL DEFAULT 0,
    active_edges INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    multiparent_count INTEGER NOT NULL DEFAULT 0,
    orphan_parent_count INTEGER NOT NULL DEFAULT 0,
    orphan_child_count INTEGER NOT NULL DEFAULT 0,
    cycle_node_count INTEGER NOT NULL DEFAULT 0,
    graph_fingerprint TEXT,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_status ON ssa_derivada_sync_run (status);
CREATE INDEX IF NOT EXISTS idx_derivada_sync_run_started ON ssa_derivada_sync_run (started_at);

COMMIT;
