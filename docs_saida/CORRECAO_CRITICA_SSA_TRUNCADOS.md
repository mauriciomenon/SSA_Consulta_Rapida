# RELATÓRIO – CORREÇÃO CRÍTICA DE SSA TRUNCADOS

Este relatório documenta a identificação e correção de registros SSA truncados detectados durante rotinas de validação.

## 1. Contexto
Durante auditoria foram encontrados registros cujos campos de identificação ou descrição estavam cortados (truncados) abaixo do comprimento esperado, afetando consultas e correlacionamentos.

## 2. Sintomas Observados
- Diferença no total de registros retornados entre consultas GUI vs CLI.
- Colunas de texto com sufixos abruptos (ex.: quebra inesperada ou ausência de sufixo padrão).
- Falha em filtros que dependem do campo completo.

## 3. Causa Raiz
| Fator | Descrição | Evidência |
|-------|-----------|-----------|
| Import parcial | Interrupção de processo antes de commit final | Logs incompletos em execução interrompida |
| Limite de tamanho | Campo armazenado com restrição inadequada | Definição antiga no schema legado |
| Normalização agressiva | Função de limpeza removendo mais caracteres que o necessário | Diff de função antiga vs atual |

## 4. Estratégia de Correção
1. Backup completo do banco (`data/ssas.db`) com timestamp.
2. Extração de registros suspeitos (query baseada em comprimento < limiar).
3. Reprocessamento seletivo a partir da fonte original (planilhas / arquivos brutos).
4. Ajuste do schema (se aplicável) removendo limites inadequados.
5. Validação pós-correção (contagem, hashes de linhas críticas, amostragem manual).

## 5. Consultas Utilizadas (Exemplos)
```sql
-- Seleciona SSAs com descrição truncada (ex.: menor que 12 chars)
SELECT id, codigo, descricao, LENGTH(descricao) AS len
FROM ssas
WHERE LENGTH(descricao) < 12;

-- Contagem comparativa antes/depois
SELECT COUNT(*) FROM ssas;
```

## 6. Métricas de Validação
| Métrica | Antes | Depois | Alvo |
|---------|-------|--------|------|
| Registros truncados detectados | (preencher) | (preencher) | 0 |
| Tempo reprocessamento (min) |  |  | < 10 |
| Divergência GUI vs CLI (registros) |  |  | 0 |

## 7. Resultados
Resumo a preencher após execução: total corrigido, impacto em performance, existência de registros irrecuperáveis.

## 8. Riscos Remanescentes
| Risco | Mitigação |
|-------|-----------|
| Fonte original incompleta | Recoletar arquivo fonte | 
| Novo truncamento futuro | Adicionar validação de comprimento em pipeline | 
| Campo sem padronização final | Revisar normalizador pós-pipeline | 

## 9. Próximos Passos
- Automatizar verificação periódica (script scheduled / manual).
- Logar discrepâncias em arquivo separado para auditoria.
- Incluir checagem em rotina de import (falhar cedo se truncamento > 0).

## 10. Histórico
Documento gerado para substituir placeholder vazio (12/09/2025). Atualizar com valores reais após execução do processo.

