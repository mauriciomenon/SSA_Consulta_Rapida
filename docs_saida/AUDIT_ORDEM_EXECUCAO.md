# 🔍 AUDIT DE ORDEM DE EXECUÇÃO - ANÁLISE COMPLETA

## 📋 PROBLEMAS IDENTIFICADOS

### 1. 🔄 **CONFLITO: Recarga de Configurações**

**Problema**: GUI e CLI carregam configurações de forma diferente e concorrente

#### GUI (`gui_ssa.py`):
```python
# Linhas 28-74: Carregamento no import
GUI_MAIN_PREFERENCES = load_gui_main_preferences()
# Linhas 354-394: Carregamento no __init__
self.display_map = load_display_mappings()
```

#### CLI (`cli.py`):
```python
# Linhas 363-365: Recarga a cada iteração do loop
settings = load_settings() 
display_map = load_display_mappings_integrity()
```

**CONFLITO**: GUI carrega uma vez, CLI recarrega constantemente → inconsistências.

---

### 2. ⚡ **INTERFERÊNCIA: Best-Fit vs Configurações Salvas**

**Problema**: Algoritmos de largura de coluna conflitam entre si

#### GUI - Ordem de Aplicação:
```python
# Linha 744: Sempre recalcula best-fit
self._compute_gui_column_widths(display_df)

# Linhas 761-786: Aplica larguras em ordem conflitante
# 1. Best-fit calculado
px = self._gui_column_pixel_widths.get(col_key)
# 2. Configuração salva manualmente
if px is None:
    px = self._saved_gui_column_widths.get(col_key)
# 3. Fallbacks hardcoded
```

**INTERFERÊNCIA**: Best-fit pode ser sobrescrito por configurações antigas.

---

### 3. 🔧 **CONFLITO: Thread Safety**

**Problema**: Múltiplas threads modificando estado sem sincronização

#### Threads Concorrentes:
1. **DataLoaderWorker** (linha 115)
2. **FilterWorker** (linha 178)  
3. **QTimer para debounce** (linha 386)
4. **QTimer para resize** (linha 1306)

**CONFLITO**: 
- `self.df_completo` modificado por DataLoaderWorker
- `self.df_exibido` modificado por FilterWorker
- `self._gui_column_pixel_widths` modificado por resize timer
- Sem locks ou sincronização

---

### 4. 📊 **ORDEM CONFLITANTE: Inicialização da GUI**

**Problema**: Dependências circulares na ordem de inicialização

#### Sequência Atual:
```python
# main.py linhas 110-122
1. setup_project_structure.setup_dirs()
2. ensure_default_settings()
3. run_importer_logic()
4. start_cli_loop() OU SSAMainWindow()
```

#### Problema na GUI:
```python
# gui_ssa.py linhas 354-394
1. __init__() carrega configurações
2. init_ui() usa configurações
3. load_data() carrega dados
4. on_data_loaded() processa dados
```

**CONFLITO**: GUI pode inicializar antes do banco estar pronto.

---

### 5. 🔄 **RECARREGAMENTO EXCESSIVO: CLI Loop**

**Problema**: Configurações recarregadas desnecessariamente

#### CLI Loop (linhas 363-365):
```python
while True:
    # RECARREGA A CADA ITERAÇÃO
    settings = load_settings() 
    display_map = load_display_mappings_integrity()
```

**DESPERDÍCIO**: I/O desnecessário a cada comando do usuário.

---

### 6. ⚙️ **CONFIGURAÇÕES INCONSISTENTES: GUI vs CLI**

**Problema**: Sistemas usam arquivos de configuração diferentes

#### GUI Main:
- ❌ **PROBLEMA**: Ainda usa `core.config_manager` (compartilhado)
- ❌ **FALTANDO**: `gui_main_preferences.json` isolado

#### CLI:
- ✅ Usa `default_settings.json` + `display_mappings.json`

#### GUI PoC: 
- ✅ Usa `gui_poc_preferences.json` (isolado)

**INCONSISTÊNCIA**: GUI Main não tem isolamento como GUI PoC.

---

## 🔧 SOLUÇÕES PROPOSTAS

### 1. **CONFIGURAÇÕES: Carregamento Único**
```python
# Em vez de recarregar a cada iteração
class ConfigCache:
    def __init__(self):
        self.last_modified = {}
        self.cached_config = {}
    
    def get_config(self, file_path):
        if self._needs_reload(file_path):
            self.cached_config[file_path] = self._load_config(file_path)
        return self.cached_config[file_path]
```

### 2. **THREADS: Sincronização**
```python
# Adicionar locks para dados compartilhados
import threading

class SSAMainWindow(QMainWindow):
    def __init__(self):
        self._data_lock = threading.RLock()
        self._config_lock = threading.RLock()
```

### 3. **BEST-FIT: Ordem Determinística**
```python
# Priorizar sempre best-fit sobre configurações salvas
def _apply_column_widths(self):
    # 1. SEMPRE: Best-fit calculado (prioridade máxima)
    # 2. FALLBACK: Configurações salvas apenas se best-fit falhou
    # 3. ÚLTIMO RECURSO: Hardcoded defaults
```

### 4. **INICIALIZAÇÃO: Ordem Garantida**
```python
# main.py - Verificar dependências antes de GUI
def main():
    # 1. Setup obrigatório
    setup_project_structure.setup_dirs()
    ensure_default_settings()
    
    # 2. Dados obrigatórios
    db_updated = run_importer_logic()
    
    # 3. Verificar se DB existe antes de GUI
    if args.gui:
        if not os.path.exists(db_path):
            logger.error("Banco não existe. Execute main.py primeiro.")
            return
        start_gui()
```

### 5. **CLI: Carregamento Inteligente**
```python
# Carregar apenas quando necessário
def start_cli_loop():
    config_cache = ConfigCache()
    
    while True:
        # Só recarrega se arquivo mudou
        settings = config_cache.get_config('default_settings.json')
        display_map = config_cache.get_config('display_mappings.json')
```

---

## 🎯 PRIORIDADE DE CORREÇÕES

### **CRÍTICO** 🔴
1. ✅ **GUI Main Isolamento**: Implementar `gui_main_preferences.json`
2. ✅ **Thread Safety**: Adicionar locks para dados compartilhados
3. ✅ **Best-Fit Conflitos**: Ordem determinística de aplicação

### **IMPORTANTE** 🟡  
4. ⚠️ **Recarregamento CLI**: Cache inteligente de configurações
5. ⚠️ **Inicialização GUI**: Verificar dependências

### **MELHORIA** 🟢
6. 📈 **Performance**: Otimizar carregamento desnecessário

---

## 🧪 TESTES RECOMENDADOS

### 1. **Teste de Concorrência**
```python
def test_thread_safety():
    # Abrir GUI, filtrar, redimensionar simultaneamente
    # Verificar se dados ficam consistentes
```

### 2. **Teste de Configurações**
```python
def test_config_isolation():
    # Modificar CLI, verificar se GUI não muda
    # Modificar GUI, verificar se CLI não muda
```

### 3. **Teste de Best-Fit**
```python
def test_best_fit_priority():
    # Definir larguras salvas
    # Redimensionar janela
    # Verificar se best-fit tem prioridade
```

---

## 📊 RESUMO EXECUTIVO

**Problemas Encontrados**: 6 conflitos principais
**Impacto**: Médio a Alto (interferências funcionais)
**Soluções**: Implementáveis com refatoração moderada
**Prioridade**: Implementar isolamento GUI Main primeiro

**Status Geral**: ⚠️ **ATENÇÃO NECESSÁRIA** - Conflitos identificados mas gerenciáveis
