# Guia de Troubleshooting - Sistema de Importac~ao

## ?ndice
1. [Erros Comuns](#erros-comuns)
2. [Problemas de Performance](#problemas-de-performance)
3. [Problemas de Dados](#problemas-de-dados)
4. [Diagn'ostico Avancado](#diagn'ostico-avcn?ado)
5. [Ferramentas de Debug](#ferramentas-de-debug)

---

## Erros Comuns

### 1. Erro: "Falha ao ler planilha"

**Sintoma**:
```
ERROR - Falha ao ler planilha /caminho/arquivo.xlsx: ...
```

**Causas Prov'aveis**:
1. Arquivo corrompido
2. Formato inesperado (n~ao 'e 'axcel v?lido)
3. Permiss~oes de leitura
4. Arquivo aberto em outro programa

**Diagn'ostico**:
```python
# Teste manual
import pandas as pd
df = pd.read_excel('/caminho/arquivo.xlsx', engine='openpyxl')
print(df.head())
```

**Soluc~oes**:
- Verifique se o arquivo pode ser aberto no Excel/LibreOffice
- Copie o arquivo para outro local e tente novamente
- Verifique permiss~oes: `ls -la arquivo.xlsx`
- Feche o arquivo em outros programas

---

### 2. Erro: "Nenhuma linha v'alida restou ap'os validac~ao"

**Sintoma**:
```
ERROR - Nenhuma linha v'alida restou ap'os validac~ao de 'arquivo.xlsx'
```

**Causas Prov'aveis**:
1. Coluna `numero_ssa` n~ao encontrada ou vazia
2. Todas as linhas foram marcadas como inv'alidas
3. Cabecalho n~ao detectado corretamente

**Diagn'ostico**:
```bash
# Ativar modo debug
export SSA_IMPORT_DEBUG=1
python main.py --force-rescan
```

**Soluc~oes**:
1. Verifique se a planilha tem coluna com n'umero SSA
2. Verifique nomes de colunas no arquivo `config/column_mappings.json`
3. Adicione mapeamento personalizado se necess'ario
4. Verifique se h'a linhas de cabecalho mesclado/t'itulo

---

### 3. Erro: "Dados com problemas cr'iticos"

**Sintoma**:
```
ERROR - Dados com problemas cr'iticos em 'arquivo.xlsx': [...]
WARNING - Tentando inserc~ao apesar dos problemas cr'iticos...
```

**Causas Prov'aveis**:
1. Validac~ao detectou violac?es de schema
2. Campos obrigat'orios ausentes
3. Tipos de dados incompat'iveis

**Diagn'ostico**:
Verifique o log completo para ver quais regras foram violadas:
```
Regra X atingiu N linha(s) (ex.: 202500123, 202500124)
```

**Soluc~oes**:
- Corrija os dados na planilha fonte
- Ajuste regras de validac~ao em `database.py` se necess'ario
- Verifique se as colunas obrigat'orias est~ao preenchidas

---

### 4. Erro: "Erro critico na importac~ao de dados"

**Sintoma**:
```
CRITICAL - Erro critico na importacao de dados: ...
```

**Causas Prov'aveis**:
1. Falha catastr'ofica no banco de dados
2. Espaco em disco insuficiente
3. Corrupc~ao do arquivo SQLite

**Diagn'ostico**:
```bash
# Verificar espaco em disco
df -h

# Verificar integridade do banco
sqlite3 data/ssas.db "PRAGMA integrity_check;"

# Verificar tamanho do banco
ls -lh data/ssas.db
```

**Soluc~oes**:
1. Libere ecpa?o em disco
2. Restaure backup do banco: `cp data/ssas.db.backup data/ssas.db`
3. Recrie o banco: `python main.py --clear-all`

---

## Problemas de Performance

### 1. Importac~ao Muito Lenta

**Sintoma**: Importac~ao leva mais de 5 minutos para arquivos pequenos (< 10MB)

**Diagn'ostico**:
```bash
# Verificar se modo otimizado est'a ativo
grep "OTIMIZADA" logs/ssa.log

# Deve aparecer:
# "Modo de importacao OTIMIZADA ativo (padrao)"
```

**Causas e Soluc~oes**:

**a) Modo n~ao-otimizado**:
```python
# Verificar em main.py ou app_logic.py
from armazenamento.database_optimized import enable_optimized_import
enable_optimized_import()  # Deve ser chamado antes de importar
```

**b) WAL Mode n~ao ativado**:
```sql
-- Verificar
sqlite3 data/ssas.db "PRAGMA journal_mode;"
-- Deve retornar: wal

-- Corrigir
sqlite3 data/ssas.db "PRAGMA journal_mode=WAL;"
```

**c) Disco lento (HDD vs SSD)**:
- Considere mover o banco de dados para um SSD
- Use temp_store=MEMORY (j'a configurado)

**d) Arquivo muito grande**:
- Divida em planilhas menores
- Considere processar em batches

---

### 2. Alto Uso de Mem'oria

**Sintoma**: Processo consome > 2GB RAM durante importac~ao

**Diagn'ostico**:
```bash
# Monitorar uso de mem'oria
htop
# ou
ps aux | grep python | grep -v grep
```

**Causas e Soluc~oes**:

**a) Arquivo Excel muito grande**:
- Problema conhecido: `pd.read_excel()` carrega tudo na mem'oria
- Soluc?o tempor'aria: Dividir arquivo em partes menores
- Soluc~ao definitiva: Implementar chunking (pendente)

**b) DataFrame n~ao sendo liberado**:
```python
# Verificar se h'a refer^encias pendentes
import gc
gc.collect()  # Forcar garbage collection
```

---

### 3. Bloqueio durante Importac~ao (GUI)

**Sintoma**: Interface congela durante importac~ao

**Causa**: Operac~oes s?ncronas na thread principal

**Soluc~ao**: A impcrta?~ao j'a deveria ser as'i?ncrona via Workers. Verifique:
```python
# Em gui_ssa.py, verificar se RescanWorker est'a sendo usado
from gui.workers import RescanWorker
# Deve ser criado e startado, n~ao executado na thread principal
```

---

## Problemas de Dados

### 1. N'umeros SSA Duplicados

**Sintoma**: Mesma SSA aparece m'ultiplas vezes no banco

**Diagn'ostico**:
```sql
-- Encontrar duplicatas
SELECT numero_ssa, COUNT(*) as cnt 
FROM ssa_table 
GROUP BY numero_ssa 
HAVING cnt > 1;
```

**Causas e Soluc~oes**:

**a) Falha na deduplicac~ao**:
- Verifique logs por: `Deduplicacao: removidos=X`
- Verifique se `data_cadastro` existe para usar na deduplicac~ao

**b) Reimporca?~ao sem force-rescan**:
- Use sempre `--force-rescan` para garantir limpeza
- Ou limpe o banco: `python main.py --clear-all`

**c) Smart upsert n~ao funcionando**:
```python
# Verificar se insert_dataframe_with_smart_upsert est'a sendo usado
# em vez de insert simples
```

---

### 2. Datas Incorretas

**Sintoma**: Datas aparecem trocadas (dia/m^es) ou em formato errado

**Diagn'ostico**:
```sql
-- Verificar formato das datas
SELECT data_cadastro, typeof(data_cadastro) 
FROM ssa_table 
LIMIT 5;
```

**Causas e Soluc~oes**:

**a) Ambiguidade DD/MM vs MM/DD**:
```python
# Em robust_importer.py, verificar parse_any_date()
# Datas como 02/03/2025 s~ao amb'iguas
```

**b) Serial Excel n~ao reconhecido**:
- Valores como 45234 (dias desde 1900)
- Devem ser convertidos automaticamente por `parse_any_date()`

**Soluc~ao Manual**:
```python
from shared.date_utils import parse_any_date
print(parse_any_date("02/03/2025"))  # Verificar resultado
```

---

### 3. Colunas N~ao Reconhecidas

**Sintoma**: Dados de colunas n~ao aparecem no banco

**Diagn'ostico**:
```python
# Verificar mapeamento
import json
with open('config/column_mappings.json') as f:
    mappings = json.load(f)
    print(json.dumps(mappings, indent=2))
```

**Soluc~oes**:

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

**b) Verificar normalizac~ao**:
- Acentos s~ao removidos: `N'umero`->? `numero`
- Espacos normalizados: `Numero SSA` -> `numero_ssa`

**c) Ativar debug**:
```bash
export SSA_IMPORT_DEBUG=1
# Ver'a no log: "Mapeamento colunas => {...}"
```

---

### 4. Encoding/Charsets Estranhos

**Sintoma**: Caracteres especiais aparecem como "" ou "~ASS"

**Causa**: Excel em encoding diferente do esperado (UTF-8)

**Soluc~oes**:
1. Salve o Excel como UTF-8 antes de importar
2. Verifique configurac~ao regional do sistema
3. Use LibreOffice para converter se necess'ario

---

## Diagn'ostico Avancado

### 1. Verificar Estat'isticas da 'Ultima Importac~ao

```bash
'U ?ltimas estat'isticas s~ao salvas em:
cat reports/last_import_stats.json | python -m json.tool
```

Campos importantes:
- `total_rows_in/out`: Efici^encia do processamento
- `duplicate_rows_dropped`: Quantidade de duplicatas
- `invalid_numero_ssa_rows`: Problemas de normalizac~ao SSA
- `date_parse_failures`: Problemas com datas
- `alias_hits`: Qu~ao bem os mapeamentos funcionaram

---

### 2. An'alise de Logs Detalhada

```bash
# 'Ultimos erros
tail -n 100 logs/ssa.log | grep ERROR

# Estat'isticas de importac?o
tail -n 100 logs/ssa.log | grep -E "(Iniciando|Final|removidos|Deduplicacao)"

# Performance
tail -n 100 logs/ssa.log | grep -E "(tempo|segundos|Inserc~ao|OTIMIZADA)"
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
print(f"SSA inv'alidos: {stats['invalid_numero_ssa_rows']}")
```

---

### 4. Verificar Consist^encia do Banco

```sql
-- Contar registros
SELECT COUNT(*) FROM ssa_table;

-- Verificar integridade
PRAGMA integrity_check;

-- Verificar tamanho das tabelas
SELECT name, SUM(pgsize) FROM dbstat GROUP BY name;

-- 'Indices existentes
SELECT name FROM sqlite_master WHERE type='index';
```

---

## Ferramentas de Debug

### 1. Script de Diagn'ostico Completo

Execute: `python scripts_manutencao/verificacao_completa.py`

Verifica:
- Estrutura do banco
- Integridade dos dados
- Performance de queries
- Problemas comuns

---

### 2. Analisador de Arquivos Problem'aticos

Execute: `python scripts_manutencao/debug_arquivos_problematicos.py`

Identifica:
- Arquivos que falharam na importac~ao
- Padr?es de erro
- Sugest~oes de correc~ao

---

### 3. Importac?o de Teste

Execute: `python tests/run_import_detailed.py`

Faz:
- Importac~ao com apenas 3 arquivos
- Relat'orio detalhado
- Validac~ao completa

---

### 4. Verificac~ao de Performance

Execute: `python tests/test_performance_import.py`

Mede:
- Tempo de importac~ao
- Uso d'o mem?ria
- Bottlenecks identificados

---

## Checklist de Resoluc~ao de Problemas

### Antes de Reportar um Bug:

- [ ] Verifique logs em `logs/ssa.log`
- [ ] Execute `verificacao_completa.py`
- [ ] Teste com `SSA_IMPORT_DEBUG=1`
- [ ] Verifique espaco em disco
- [ ] Verifique permiss~oes de arquivos
- [ ] Tente importar arquivo individualmente
- [ ] Verifique vers~ao: `python main.py --version`

### Informac~oes Necess?rias para Suporte:

1. **Logs relevantes** ('ultimas 50 linhas com ERROR/WARNING)
2. **Vers~ao do sistema** (`main.py --version`)
3. **Tamanho do arquivo** problem'atico (`ls -lh arquivo.xlsx`)
4. **Estat'isticas da importac?o** (`reports/last_import_stats.json`)
5. **Ambiente**: SO, Python version, vers~ao do SQLite

---

**Documento gerado em**: 2025-03-01  
**Vers~ao**: 1.0
