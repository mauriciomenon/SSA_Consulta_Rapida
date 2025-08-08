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
    prazo_limite TEXT,                 
    tempo_disponivel TEXT,             
    data_limite TEXT,                  
    tempo_excedido TEXT,               
    desde TEXT,                        
    tempo_total TEXT,                  
    desde_1 TEXT,                      
    total_tempo_tpe_planejado REAL,    
    total_tempo_tex_planejado REAL,    
    total_tempo_tpo_planejado REAL,    
    total_horas_programadas REAL,      
    semana_executada INTEGER,          
    num_reprogramacoes INTEGER,        
    execucao_parcial TEXT,             
    anomalia TEXT,
    sistema_origem TEXT,               -- COLUNA ADICIONADA
    PRIMARY KEY(numero_ssa) ON CONFLICT REPLACE
);

-- Adiciona índices para melhorar o desempenho das consultas
CREATE INDEX IF NOT EXISTS idx_ssas_setor_executor ON ssas(setor_executor);
CREATE INDEX IF NOT EXISTS idx_ssas_situacao ON ssas(situacao);
CREATE INDEX IF NOT EXISTS idx_ssas_data_cadastro ON ssas(data_cadastro);
CREATE INDEX IF NOT EXISTS idx_ssas_numero_ssa ON ssas(numero_ssa);