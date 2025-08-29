# CORREÇÕES CRÍTICAS v3.0.4 - ALGORITMO DE LARGURAS GUI

## ⚠️ IMPORTANTE - NÃO MEXER NO QUE FOI CORRIGIDO! ⚠️

### PROBLEMA ORIGINAL
- Algoritmo de larguras da GUI estava quebrado
- Colunas com larguras inconsistentes e imprecisas
- Texto sendo cortado mesmo com espaço disponível
- Mapeamento incorreto entre colunas calculadas e tabela real
- Ordem de colunas inconsistente entre componentes

### CORREÇÃO IMPLEMENTADA - CLASSES ENVOLVIDAS

#### 1. SimpleWidthManager (`gui/simple_width_manager.py`)
**O QUE FOI CORRIGIDO:**
- ✅ Implementadas larguras FIXAS EXATAS por tipo de coluna:
  - `#` = 25px (fixo)
  - `numero_ssa` = 65px (fixo)
  - `situacao` = 35px (fixo)
  - `semana_cadastro` = 60px (fixo)
  - `semana_programada` = 45px (fixo)
  - `derivada_de` = 65px (fixo)
  - `localizacao_codigo` = 50px (fixo)
  - `data_cadastro` = 85px (fixo)
  - `setor_executor` = 40px (fixo)
  - `setor_emissor` = 40px (fixo)
  - `solicitante` = 160px (fixo)
  - `descricao_ssa` = 450px (base, expansível)
  - `descricao_execucao` = 350px (base, expansível)

**ALGORITMO 50/50 PARA DESCRIÇÕES:**
- ✅ Crescimento proporcional entre `descricao_ssa` e `descricao_execucao`
- ✅ Espaço extra dividido igualmente (50% cada)
- ✅ Resto distribuído para `descricao_ssa` quando ímpar

**CÓDIGO CRÍTICO - NÃO ALTERAR:**
```python
def calculate_widths(self, available_width, visible_columns, column_order=None):
    # ... código de larguras fixas ...
    
    # Colunas expansíveis (50/50)
    expandable_cols = []
    if 'descricao_ssa' in column_order:
        expandable_cols.append('descricao_ssa')
    if 'descricao_execucao' in column_order:
        expandable_cols.append('descricao_execucao')
    
    # Distribuição 50/50 do espaço extra
    if expandable_cols and extra_space > 0:
        per_col = extra_space // len(expandable_cols)
        remainder = extra_space % len(expandable_cols)
        
        for col in expandable_cols:
            widths[col] += per_col
        
        # Resto vai para descricao_ssa
        if remainder > 0 and 'descricao_ssa' in widths:
            widths['descricao_ssa'] += remainder
```

#### 2. GUI SSA (`gui/gui_ssa.py`)
**O QUE FOI CORRIGIDO:**
- ✅ Removida função `_pin` que reordenava colunas incorretamente
- ✅ Corrigido `_apply_computed_widths_only` para usar colunas filtradas
- ✅ Mapeamento correto entre índices calculados e tabela real

**CORREÇÃO CRÍTICA - NÃO ALTERAR:**
```python
def _apply_computed_widths_only(self, computed_widths):
    """Aplica larguras computadas às colunas da tabela usando mapeamento correto"""
    
    # CORREÇÃO CRÍTICA: Usar colunas filtradas, não DataFrame completo
    table_columns = self._current_display_columns  # NÃO ALTERAR ESTA LINHA!
    
    for i, col_name in enumerate(table_columns):
        if col_name in computed_widths:
            target_width = computed_widths[col_name]
            current_width = self.table.columnWidth(i)
            
            if current_width != target_width:
                self.table.setColumnWidth(i, target_width)
```

#### 3. Configuração de Colunas (`config/gui_main_preferences.json`)
**O QUE FOI CORRIGIDO:**
- ✅ Ordem determinística de colunas em `display_columns`
- ✅ Lista de colunas ocultas em `hidden_columns`

**CONFIGURAÇÃO CRÍTICA - NÃO ALTERAR A ORDEM:**
```json
{
  "display_columns": [
    "numero_ssa",
    "situacao", 
    "semana_cadastro",
    "semana_programada",
    "derivada_de",
    "localizacao_codigo",
    "data_cadastro",
    "descricao_ssa",
    "setor_executor",
    "setor_emissor",
    "solicitante",
    "descricao_execucao"
  ]
}
```

### LIÇÕES APRENDIDAS

#### 1. PROBLEMA ROOT CAUSE: Desalinhamento de Índices
- WidthManager calculava para 13 colunas (conforme preferences)
- Tabela tinha 38 colunas (DataFrame completo)
- Índices ficavam desalinhados (ex: semana_programada no índice 18 vs 4)

#### 2. SOLUÇÃO: Filtragem Consistente
- `_current_display_columns` contém apenas colunas visíveis
- Mapeamento 1:1 entre cálculo e aplicação
- Ordem determinística via `gui_main_preferences.json`

#### 3. ALGORITMO DE LARGURAS HIERÁRQUICO
1. **Larguras Fixas**: Valores exatos por tipo de coluna
2. **Espaço Extra**: Calculado após larguras fixas
3. **Distribuição 50/50**: Apenas para colunas de descrição
4. **Resto**: Vai para `descricao_ssa`

### ARQUIVOS MODIFICADOS - NÃO ALTERAR SEM CUIDADO

1. **`gui/simple_width_manager.py`**
   - Larguras fixas implementadas
   - Algoritmo 50/50 para descrições
   - Debug logging para troubleshooting

2. **`gui/gui_ssa.py`**
   - Função `_pin` removida
   - `_apply_computed_widths_only` corrigida
   - Mapeamento de colunas filtradas

3. **`config/gui_main_preferences.json`**
   - Ordem de colunas determinística
   - Lista de colunas ocultas

### TESTES DE VALIDAÇÃO

**Cenário 1 - Espaço Limitado (1400px):**
- ✅ Larguras fixas mantidas
- ✅ Descrições ficam no mínimo (450px + 350px)

**Cenário 2 - Espaço Extra (1862px):**
- ✅ Extra de 392px dividido: +196px cada
- ✅ descricao_ssa: 450px → 646px
- ✅ descricao_execucao: 350px → 546px

**Cenário 3 - Debug Logs:**
```
DEBUG APLICAÇÃO: Coluna 8 (descricao_ssa): 450px → 646px
DEBUG APLICAÇÃO: Coluna 12 (descricao_execucao): 350px → 546px
```

### PRÓXIMOS PASSOS
- ✅ Larguras funcionando corretamente
- 🔄 Investigar renderização de texto (wrapping/clipping)
- 🔄 Otimizar performance se necessário

### RESUMO EXECUTIVO
**ANTES:**
- Algoritmo quebrado com índices desalinhados
- Larguras inconsistentes
- Texto cortado

**DEPOIS:**
- Larguras fixas exatas conforme especificação
- Crescimento 50/50 para descrições
- Mapeamento correto entre cálculo e aplicação
- Ordem determinística de colunas

**STATUS:** ✅ CORREÇÃO BEM-SUCEDIDA - PROTEGER CÓDIGO MODIFICADO
