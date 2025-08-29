# VERIFICAÇÕES DE BANCO DE DADOS NO PROCESSO DE IMPORTAÇÃO

## 📋 Resumo das Implementações

Este documento descreve as novas funcionalidades de verificação e integridade do banco de dados implementadas no sistema SSA Consulta Rápida.

## 🎯 Funcionalidades Implementadas

### 1. **Verificação de Integridade do Banco de Dados**
**Função:** `verify_database_integrity(db_path, table_name)`

**Verificações realizadas:**
- ✅ Existência do arquivo de banco de dados
- ✅ Permissões de leitura/escrita no arquivo
- ✅ Espaço em disco disponível (mínimo 100MB)
- ✅ Acessibilidade do banco SQLite
- ✅ Existência da tabela principal
- ✅ Validação do schema (colunas obrigatórias)
- ✅ Integridade dos dados SQLite (`PRAGMA integrity_check`)

**Retorno:** Relatório detalhado com status e problemas encontrados

### 2. **Validação de Dados Antes da Inserção**
**Função:** `validate_dataframe_before_insert(df, table_name)`

**Validações realizadas:**
- ✅ Verificação de colunas críticas (numero_ssa, situacao)
- ✅ Validação de números SSA (formato YYYYNNNNN)
- ✅ Validação de formatos de data
- ✅ Detecção de duplicatas por numero_ssa
- ✅ Verificação de tamanhos de string (evitar truncamento)

**Retorno:** Relatório com problemas críticos e avisos

### 3. **Reparo Automático de Banco de Dados**
**Função:** `repair_database_if_needed(db_path, schema_file)`

**Ações de reparo:**
- 🔧 Criação de novo banco se não existir
- 🔧 Recriação de schema se tabela estiver ausente
- 🔧 Backup e restauração em caso de corrupção
- 🔧 Extração de dados válidos de banco corrompido

### 4. **Tratamento de Erros Específicos**

**Novas classes de exceção:**
- `DatabaseConnectionError` - Problemas de conexão
- `DatabaseCorruptionError` - Corrupção de dados
- `DatabaseSchemaError` - Problemas de schema
- `DatabaseSpaceError` - Espaço insuficiente
- `DataValidationError` - Dados inválidos

## 🔄 Integração no Processo de Importação

### Fluxo Atualizado:

1. **Verificação de Integridade** (NOVO)
   - Executada antes de qualquer importação
   - Reparo automático se necessário
   - Falha crítica se banco permanece inválido

2. **Determinação de Arquivos**
   - Processo original mantido

3. **Processamento por Arquivo** (MELHORADO)
   - Validação de dados extraídos antes da inserção
   - Tratamento específico por tipo de erro
   - Recuperação automática quando possível

4. **Atualização de Cache**
   - Processo original mantido

### Estratégias de Recuperação:

**Erro de Conexão:** Para todo o processamento
**Corrupção:** Tenta reparo automático e continua
**Schema:** Recria schema e continua  
**Espaço:** Para todo o processamento
**Validação:** Pula arquivo com dados inválidos
**Extração:** Pula arquivo com problemas de leitura

## 📊 Relatórios de Verificação

### Relatório de Integridade:
```python
{
    'is_valid': True/False,
    'issues': ['problema1', 'problema2'],
    'warnings': ['aviso1', 'aviso2'],
    'database_exists': True/False,
    'database_accessible': True/False,
    'table_exists': True/False,
    'schema_valid': True/False,
    'data_consistent': True/False,
    'disk_space_sufficient': True/False,
    'file_permissions_ok': True/False
}
```

### Relatório de Validação:
```python
{
    'is_valid': True/False,
    'issues': ['erro_crítico1'],
    'warnings': ['aviso1', 'aviso2'],
    'row_count': 1000,
    'invalid_rows': [5, 10, 15],
    'fixed_rows': 3
}
```

## 🧪 Testes Implementados

**Arquivo:** `tests/test_database_verification.py`

**Cenários testados:**
- ✅ Banco inexistente
- ✅ Banco válido
- ✅ Banco corrompido
- ✅ DataFrame vazio
- ✅ Dados válidos
- ✅ Números SSA inválidos
- ✅ Datas inválidas
- ✅ Reparo de banco

## 🚀 Como Usar

### Verificação Manual:
```python
from armazenamento.database import verify_database_integrity

report = verify_database_integrity('data/ssas.db')
if not report['is_valid']:
    print("Problemas encontrados:", report['issues'])
```

### Validação de Dados:
```python
from armazenamento.database import validate_dataframe_before_insert

report = validate_dataframe_before_insert(df)
if report['warnings']:
    print("Avisos:", report['warnings'])
```

### Reparo Automático:
```python
from armazenamento.database import repair_database_if_needed

success = repair_database_if_needed('data/ssas.db')
if not success:
    print("Falha no reparo do banco")
```

## 📝 Logs Gerados

### Níveis de Log:
- **INFO:** Verificações bem-sucedidas
- **WARNING:** Problemas não-críticos detectados
- **ERROR:** Falhas na verificação/reparo
- **CRITICAL:** Falhas que impedem funcionamento

### Exemplos de Mensagens:
```
INFO: ✓ Integridade do banco de dados verificada
WARNING: Aviso do banco: Pouco espaço em disco: 0.05GB disponível
ERROR: Banco de dados inacessível: [sqlite3.DatabaseError: database disk image is malformed]
```

## 🔧 Configurações

### Limites Configuráveis:
- **Espaço mínimo:** 100MB (configurável em `verify_database_integrity`)
- **Batch size:** 500 registros (configurável em `insert_dataframe_to_db`)
- **Timeout:** Por padrão do SQLite (configurável via pragma)

### Colunas Obrigatórias:
```python
required_columns = ['numero_ssa', 'situacao', 'data_cadastro', 'descricao_ssa']
```

## 🎯 Benefícios

1. **Detecção Precoce:** Problemas identificados antes da importação
2. **Recuperação Automática:** Reparos automáticos quando possível
3. **Dados Íntegros:** Validação previne inserção de dados inválidos
4. **Logs Detalhados:** Rastreabilidade completa de problemas
5. **Robustez:** Sistema mais resistente a falhas
6. **Manutenção:** Facilita diagnóstico e correção de problemas

## 📈 Próximas Melhorias

- [ ] Interface gráfica para relatórios de verificação
- [ ] Alertas por email em caso de problemas críticos
- [ ] Métricas de performance da verificação
- [ ] Backup automático antes de reparos
- [ ] Configuração via arquivo de settings

---

**Implementado em:** Agosto 2025  
**Versão:** SSA Consulta Rápida v3.2+  
**Status:** ✅ Produção
