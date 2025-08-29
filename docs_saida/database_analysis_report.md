# Relatório de Análise do Banco de Dados SSA

**Data de Análise:** 25/08/2025 12:22:18  
**Banco Analisado:** data/ssas.db  
**Backup Criado:** data/backups\ssas_backup_20250825_122217.db

## Resumo Executivo

**Total de Registros:** 14426  
**Total de Colunas:** 44  
**Grupos de Colunas Duplicadas:** 7

## Problemas Identificados

### Integridade de Dados
- **Missing Numero Ssa:** 1676 registros
- **Missing Descricao:** 6 registros
- **Missing Area Emissora:** 6 registros
- **Missing Localizacao:** 6 registros
- **Duplicate Numbers:** 4196 registros
- **Invalid Dates:** 0 registros
- **Empty Records:** 6 registros

## Análise de Estrutura

### Colunas Duplicadas Detectadas

#### Numero Ssa

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Número da SSA | TEXT | 12750 | ✅ Primária (com dados) |
| numero_ssa | INTEGER | 1670 | ❌ Legado (vazia/poucos dados) |

#### Semana Cadastro

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Semana de Cadastro | INTEGER | 12750 | ✅ Primária (com dados) |
| semana_cadastro | INTEGER | 1670 | ❌ Legado (vazia/poucos dados) |

#### Descricao Execucao

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Descrição Execução | TEXT | 10845 | ✅ Primária (com dados) |
| descricao_execucao | TEXT | 1195 | ❌ Legado (vazia/poucos dados) |

#### Responsavel Programacao

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Responsável na Programação | TEXT | 11376 | ✅ Primária (com dados) |
| responsavel_programacao | TEXT | 1327 | ❌ Legado (vazia/poucos dados) |

#### Responsavel Execucao

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Responsável na Execução | TEXT | 11188 | ✅ Primária (com dados) |
| responsavel_execucao | TEXT | 1259 | ❌ Legado (vazia/poucos dados) |

#### Grau Prioridade Emissao

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Grau de Prioridade Emissão | TEXT | 12750 | ✅ Primária (com dados) |
| grau_prioridade_emissao | TEXT | 1670 | ❌ Legado (vazia/poucos dados) |

#### Grau Prioridade Planejamento

| Nome da Coluna | Tipo | Registros | Status |
|----------------|------|-----------|--------|
| Grau de Prioridade Planejamento | TEXT | 11058 | ✅ Primária (com dados) |
| grau_prioridade_planejamento | TEXT | 1494 | ❌ Legado (vazia/poucos dados) |


## Distribuição de Dados por Coluna

| Coluna | Registros com Dados |
|--------|--------------------|
| situacao | 14420 |
| localizacao_codigo | 14420 |
| descricao_localizacao | 14420 |
| descricao_ssa | 14420 |
| setor_emissor | 14420 |
| setor_executor | 14420 |
| solicitante | 14420 |
| servico_origem | 14420 |
| execucao_simples | 14413 |
| equipamento | 14357 |
| data_cadastro | 14343 |
| semana_programada | 12773 |
| Número da SSA | 12750 |
| Semana de Cadastro | 12750 |
| Grau de Prioridade Emissão | 12750 |
| Responsável na Programação | 11376 |
| Responsável na Execução | 11188 |
| Grau de Prioridade Planejamento | 11058 |
| Descrição Execução | 10845 |
| derivada_de | 3810 |
| numero_ssa | 1670 |
| grau_prioridade_emissao | 1670 |
| semana_cadastro | 1670 |
| grau_prioridade_planejamento | 1494 |
| responsavel_programacao | 1327 |
| responsavel_execucao | 1259 |
| descricao_execucao | 1195 |
| anomalia | 715 |
| prazo_limite | 583 |
| execucao_parcial | 556 |
| tempo_disponivel | 533 |
| tempo_total | 533 |
| desde | 510 |
| data_limite | 493 |
| total_tempo_tex_planejado | 469 |
| total_tempo_tpe_planejado | 457 |
| total_tempo_tpo_planejado | 457 |
| num_reprogramacoes | 447 |
| semana_executada | 446 |
| total_horas_programadas | 107 |
| tempo_excedido | 98 |
| sistema_origem | 22 |
| id | 0 |
| desde_1 | 0 |

## Recomendações

### Ações Prioritárias
1. **Consolidação de Colunas Duplicadas:** Migrar dados das colunas com espaços para as versões padronizadas
2. **Limpeza de Dados:** Corrigir 1676 SSAs sem número
3. **Validação:** Implementar verificações de integridade para evitar duplicações futuras

### Próximos Passos
1. Executar migração de dados com backup
2. Atualizar schema para versão limpa
3. Ajustar mapeamentos de configuração
4. Validar funcionamento de CLI e GUI

---
*Relatório gerado automaticamente pelo sistema de manutenção do banco de dados.*
