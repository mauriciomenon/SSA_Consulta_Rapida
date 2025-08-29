# CORREÇÃO CRÍTICA: Mapeamento de Colunas do Banco de Dados

## 📅 Data: 19 de Agosto de 2025

## 🔍 **PROBLEMA IDENTIFICADO**

### Sintomas:
- **GUI**: Dados carregando mas campos essenciais vazios (numero_ssa, semana_cadastro, descricao_execucao)
- **CLI**: Mesmos campos aparecendo como "-" (vazio)
- Interface funcionando mas dados não exibidos corretamente

### Causa Raiz:
**Mapeamento de colunas incorreto em `config/column_mappings.json`**

O banco de dados `ssas` contém **colunas duplicadas** com nomes diferentes:
- ✅ `"Número da SSA"` (com espaços) = **12.750 registros**
- ❌ `numero_ssa` (sem espaços) = **0 registros**
- ✅ `"Semana de Cadastro"` (com espaços) = **12.750 registros** 
- ❌ `semana_cadastro` (sem espaços) = **0 registros**
- ✅ `"Descrição Execução"` (com espaços) = **10.845 registros**
- ❌ `descricao_execucao` (sem espaços) = **0 registros**

## ✅ **SOLUÇÃO IMPLEMENTADA**

### 1. Correção do Mapeamento (`config/column_mappings.json`)
```json
"numero_ssa": [
    "Nº SSA", "Nº SSA*", "Nº SSA Original", "Numero SSA", "Nº da SSA",
    "Número da SSA"  // <- ADICIONADO
],
"semana_cadastro": [
    "Sem.\nCadastro", "Sem. Cadastro", "Semana Cadastro",
    "Semana de Cadastro"  // <- ADICIONADO
],
"descricao_execucao": [
    "Descrição da Execução", "Descricao da Execucao",
    "Descrição Execução"  // <- ADICIONADO
]
```

### 2. Correção da Query na GUI (`gui/gui_ssa.py`)
Substituída consulta `SELECT * FROM ssas` por query customizada que mapeia colunas corretamente:
```sql
SELECT 
    "Número da SSA" as numero_ssa,
    "Semana de Cadastro" as semana_cadastro,
    "Descrição Execução" as descricao_execucao,
    -- outros campos...
FROM ssas
```

### 3. Otimização das Larguras das Colunas
- Aumentado limite máximo de 600px para 800px
- Adicionada função `_force_column_widths()` com timer para garantir aplicação
- Fallback para `numero_ssa`: 80px → 100px

## 📊 **RESULTADO**
- ✅ **GUI**: 12.750 SSAs com dados completos
- ✅ **CLI**: Campos agora exibem valores reais 
- ✅ **Larguras**: Colunas de descrição com espaço adequado

## ⚠️ **ARQUIVOS AFETADOS**
- `config/column_mappings.json` - Mapeamento corrigido
- `gui/gui_ssa.py` - Query customizada + otimizações de largura
- **CLI e GUI** - Ambos beneficiados pela correção

## 🎯 **LIÇÕES APRENDIDAS**
1. Sempre verificar **nomes reais das colunas** no banco
2. **Testar CLI e GUI** para problemas similares  
3. **Dados vazios** nem sempre significa problema de conexão - pode ser mapeamento
4. **Colunas duplicadas** em bancos podem causar confusão nos mapeamentos

## 🔄 **PRÓXIMOS PASSOS**
- Verificar se outros campos têm o mesmo problema
- Considerar criar ferramenta de validação de mapeamentos
- Documentar nomes reais vs. mapeados para referência futura

---
*Esta correção resolve definitivamente o problema de dados vazios que afetava tanto a interface CLI quanto a GUI.*
