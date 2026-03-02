# Guia de Troubleshooting - Sistema de Importação

## Índice
1. [Erros Comuns](#erros-comuns)
2. [Problemas de Performance](#problemas-de-performance)
3. [Problemas de Dados](#problemas-de-dados)
4. [Diagnóstico Avançado](#diagnóstico-avançado)
5. [Ferramentas de Debug](#ferramentas-de-debug)

---

## Erros Comuns

### 1. Erro: "Falha ao ler planilha"

**Sintoma**:
```
ERROR - Falha ao ler planilha /caminho/arquivo.xlsx: ...
```

**Causas Prováveis**:
1. Arquivo corrompido
2. Formato inesperado (não é Excel válido)
3. Permissões de leitura
4. Arquivo aberto em outro programa

**Diagnóstico**:
```python
# Teste manual
import pandas as pd
df = pd.read_excel('/caminho/arquivo.xlsx', engine='openpyxl')
print(df.head())
```

**Soluções**:
- Verifique se o arquivo pode ser aberto no Excel/LibreOffice
- Copie o arquivo para outro local e tente novamente
- Verifique permissões: `ls -la arquivo.xlsx`
- Feche o arquivo em outros programas

---

### 2. Erro: "Nenhuma linha válida restou após validação"

**Sintoma**:
```
ERROR - Nenhuma linha válida restou após validação de 'arquivo.xlsx'
```

**Causas Prováveis**:
1. Coluna `numero_ssa` não encontrada ou vazia
2. Todas as linhas foram marcadas como inválidas
3. Cabeçalho não detectado corretamente

**Diagnóstico**:
```bash
# Ativar modo debug
export SSA_IMPORT_DEBUG=1
python main.py --force-rescan
```

**Soluções**:
1. Verifique se a planilha tem coluna com número SSA
2. Verifique nomes de colunas no arquivo `config/column_mappings.json`
3. Adicione mapeamento personalizado se necessário
4. Verifique se há linhas de cabeçalho mesclado/título

---

### 3. Erro: "Dados com problemas críticos"

**Sintoma**:
```
ERROR - Dados com problemas críticos em 'arquivo.xlsx': [...]
WARNING - Tentando inserção apesar dos problemas críticos...
```

**Causas Prováveis**:
1. Validação detectou violações de schema
2. Campos obrigatórios ausentes
3. Tipos de dados incompatíveis

**Diagnóstico**:
Verifique o log completo para ver quais regras foram violadas:
```
Regra X atingiu N linha(s) (ex.: 202500123, 202500124)
```

**Soluções**:
- Corrija os dados na planilha fonte
- Ajuste regras de validação em `database.py` se necessário
- Verifique se as colunas obrigatórias estão preenchidas

---

### 4. Erro: "Erro critico na importação de dados"

**Sintoma**:
```
CRITICAL - Erro critico na importacao de dados: ...
```

**Causas Prováveis**:
1. Falha catastrófica no banco de dados
2. Espaço em disco insuficiente
3. Corrupção do arquivo SQLite

**Diagnóstico**:
```bash
# Verificar espaço em disco
df -h

# Verificar integridade do banco
sqlite3 data/ssas.db "PRAGMA integrity_check;"

# Verificar tamanho do banco
ls -lh data/ssas.db
```

**Soluções**:
1. Libere espaço em disco
2. Restaure backup do banco: `cp data/ssas.db.backup data/ssas.db`
3. Recrie o banco: `python main.py --clear-all`

---

## Problemas de Performance

### 1. Importação Muito Lenta

**Sintoma**: Importação leva mais de 5 minutos para arquivos pequenos (< 10MB)

**Diagnóstico**:
```bash
# Verificar se modo otimizado está ativo
grep "OTIMIZADA" logs/ssa.log

# Deve aparecer:
# "Modo de importacao OTIMIZADA ativo (padrao)"
```

**Causas e Soluções**:

**a) Modo não-otimizado**:
```python
# Verificar em main.py ou app_logic.py
from armazenamento.database_optimized import enable_optimized_import
enable_optimized_import()  # Deve ser chamado antes de importar
```

**b) WAL Mode não ativado**:
```sql
-- Verificar
sqlite3 data/ssas.db "PRAGMA journal_mode;"
-- Deve retornar: wal

-- Corrigir
sqlite3 data/ssas.db "PRAGMA journal_mode=WAL;"
```

**c) Disco lento (HDD vs SSD)**:
- Considere mover o banco de dados para um SSD
- Use temp_store=MEMORY (já configurado)

**d) Arquivo muito grande**:
- Divida em planilhas menores
- Considere processar em batches

---

### 2. Alto Uso de Memória

**Sintoma**: Processo consome > 2GB RAM durante importação

**Diagnóstico**:
```bash
# Monitorar uso de memória
htop
# ou
ps aux | grep python | grep -v grep
```

**Causas e Soluções**:

**a) Arquivo Excel muito grande**:
- Problema conhecido: `pd.read_excel()` carrega tudo na memória
- Solução temporária: Dividir arquivo em partes menores
- Solução definitiva: Implementar chunking (pendente)

**b) DataFrame não sendo liberado**:
```python
# Verificar se há referências pendentes
import gc
gc.collect()  # Forçar garbage collection
```

---

### 3. Bloqueio durante Importação (GUI)

**Sintoma**: Interface congela durante importação

**Causa**: Operações síncronas na thread principal

**Solução**: A importação já deveria ser assíncrona via Workers. Verifique:
```python
# Em gui_ssa.py, verificar se RescanWorker está sendo usado
from gui.workers import RescanWorker
# Deve ser criado e startado, não executado na thread principal
```

---

## Problemas de Dados

### 1. Números SSA Duplicados

**Sintoma**: Mesma SSA aparece múltiplas vezes no banco

**Diagnóstico**:
```sql
-- Encontrar duplicatas
SELECT numero_ssa, COUNT(*) as cnt 
FROM ssa_table 
GROUP BY numero_ssa 
HAVING cnt > 1;
```

**Causas e Soluções**:

**a) Falha na deduplicação**:
- Verifique logs por: `Deduplicacao: removidos=X`
- Verifique se `data_cadastro` existe para usar na deduplicação

**b) Reimportação sem force-rescan**:
- Use sempre `--force-rescan` para garantir limpeza
- Ou limpe o banco: `python main.py --clear-all`

**c) Smart upsert não funcionando**:
```python
# Verificar se insert_dataframe_with_smart_upsert está sendo usado
# em vez de insert simples
```

---

### 2. Datas Incorretas

**Sintoma**: Datas aparecem trocadas (dia/mês) ou em formato errado

**Diagnóstico**:
```sql
-- Verificar formato das datas
SELECT data_cadastro, typeof(data_cadastro) 
FROM ssa_table 
LIMIT 5;
```

**Causas e Soluções**:

**a) Ambiguidade DD/MM vs MM/DD**:
```python
# Em robust_importer.py, verificar parse_any_date()
# Datas como 02/03/2025 são ambíguas
```

**b) Serial Excel não reconhecido**:
- Valores como 45234 (dias desde 1900)
- Devem ser convertidos automaticamente por `parse_any_date()`

**Solução Manual**:
```python
from shared.date_utils import parse_any_date
print(parse_any_date("02/03/2025"))  # Verificar resultado
```

---

### 3. Colunas Não Reconhecidas

**Sintoma**: Dados de colunas não aparecem no banco

**Diagnóstico**:
```python
# Verificar mapeamento
import json
with open('config/column_mappings.json') as f:
    mappings = json.load(f)
    print(json.dumps(mappings, indent=2))
```

**Soluções**:

**a) Adicionar mapeamento**:
```json
{
  "nome_coluna_canonica": [
    "variacao1",
    "variacao2",
    "variacao3"
  ]
}
```

**b) Verificar normalização**:
- Acentos são removidos: `Número` → `numero`
- Espaços normalizados: `Numero SSA` → `numero_ssa`

**c) Ativar debug**:
```bash
export SSA_IMPORT_DEBUG=1
# Verá no log: "Mapeamento colunas => {...}"
```

---

### 4. Encoding/Charsets Estranhos

**Sintoma**: Caracteres especiais aparecem como "�" ou "Ã§"

**Causa**: Excel em encoding diferente do esperado (UTF-8)

**Soluções**:
1. Salve o Excel como UTF-8 antes de importar
2. Verifique configuração regional do sistema
3. Use LibreOffice para converter se necessário

---

## Diagnóstico Avançado

### 1. Verificar Estatísticas da Última Importação

```bash
# Últimas estatísticas são salvas em:
cat reports/last_import_stats.json | python -m json.tool
```

Campos importantes:
- `total_rows_in/out`: Eficiência do processamento
- `duplicate_rows_dropped`: Quantidade de duplicatas
- `invalid_numero_ssa_rows`: Problemas de normalização SSA
- `date_parse_failures`: Problemas com datas
- `alias_hits`: Quão bem os mapeamentos funcionaram

---

### 2. Análise de Logs Detalhada

```bash
# Últimos erros
tail -n 100 logs/ssa.log | grep ERROR

# Estatísticas de importação
tail -n 100 logs/ssa.log | grep -E "(Iniciando|Final|removidos|Deduplicacao)"

# Performance
tail -n 100 logs/ssa.log | grep -E "(tempo|segundos|Inserção|OTIMIZADA)"
```

---

### 3. Teste de Componente Individual

```python
# Testar robust_importer isoladamente
from utils.robust_importer import import_excel_robust

df, stats = import_excel_robust(
    'caminho/arquivo.xlsx',
    drop_empty_numero_ssa=True,
    deduplicate=True
)

print(f"Linhas: {stats['total_rows_out']}")
print(f"Colunas: {stats['mapped_columns_count']}")
print(f"Duplicatas removidas: {stats['duplicate_rows_dropped']}")
print(f"SSA inválidos: {stats['invalid_numero_ssa_rows']}")
```

---

### 4. Verificar Consistência do Banco

```sql
-- Contar registros
SELECT COUNT(*) FROM ssa_table;

-- Verificar integridade
PRAGMA integrity_check;

-- Verificar tamanho das tabelas
SELECT name, SUM(pgsize) FROM dbstat GROUP BY name;

-- Índices existentes
SELECT name FROM sqlite_master WHERE type='index';
```

---

## Ferramentas de Debug

### 1. Script de Diagnóstico Completo

Execute: `python scripts_manutencao/verificacao_completa.py`

Verifica:
- Estrutura do banco
- Integridade dos dados
- Performance de queries
- Problemas comuns

---

### 2. Analisador de Arquivos Problemáticos

Execute: `python scripts_manutencao/debug_arquivos_problematicos.py`

Identifica:
- Arquivos que falharam na importação
- Padrões de erro
- Sugestões de correção

---

### 3. Importação de Teste

Execute: `python tests/run_import_detailed.py`

Faz:
- Importação com apenas 3 arquivos
- Relatório detalhado
- Validação completa

---

### 4. Verificação de Performance

Execute: `python tests/test_performance_import.py`

Mede:
- Tempo de importação
- Uso de memória
- Bottlenecks identificados

---

## Checklist de Resolução de Problemas

### Antes de Reportar um Bug:

- [ ] Verifique logs em `logs/ssa.log`
- [ ] Execute `verificacao_completa.py`
- [ ] Teste com `SSA_IMPORT_DEBUG=1`
- [ ] Verifique espaço em disco
- [ ] Verifique permissões de arquivos
- [ ] Tente importar arquivo individualmente
- [ ] Verifique versão: `python main.py --version`

### Informações Necessárias para Suporte:

1. **Logs relevantes** (últimas 50 linhas com ERROR/WARNING)
2. **Versão do sistema** (`main.py --version`)
3. **Tamanho do arquivo** problemático (`ls -lh arquivo.xlsx`)
4. **Estatísticas da importação** (`reports/last_import_stats.json`)
5. **Ambiente**: SO, Python version, versão do SQLite

---

**Documento gerado em**: 2025-03-01  
**Versão**: 1.0
