# Handoff: Otimização Aba Filtros Avançados

## CURRENT STATUS 2026-02-26

- Este arquivo fica como historico de referencia tecnica da evolucao da aba Filtros.
- Estado operacional atual deve ser lido em:
  - `docs/AGENTS_HANDOFF_NEXT_CYCLE.md`
  - `docs/NEXT_CHAT_MIGRATION.md`
  - `docs/RECOVERY_BACKLOG.md`
- Branch ativa atual: `dev`.
- Release local atual: `4.36`.
- Runtime padrao atual: `uv run --python 3.13 ...` (fallback 3.12 -> 3.11 -> 3.10).

---

**Data:** 2026-01-08  
**Contexto:** Otimização de performance e layout da aba "Filtros" (nova) em GUI PyQt6  
**Arquivo Principal:** `gui/gui_ssa.py` (5449 linhas)  
**Objetivo:** Layout compacto, responsivo, dados carregando corretamente

---

## REGRAS CRÍTICAS DO USUÁRIO

### 1. Aba de Trabalho EXCLUSIVA
- **NUNCA modificar aba "SSAs"** - apenas aba "Filtros" pode ser alterada
- Verificação: `if tab_kind == "filters":` antes de qualquer mudança de layout
- Proporções, larguras, heights - TUDO deve ser condicional à aba Filtros

### 2. Try/Except = MAL
- **PROIBIDO:** `except Exception: pass` que silencia erros
- **OBRIGATÓRIO:** Logging explícito ou re-raise
- **Aceitável:** Try/except apenas para APIs Qt instáveis (setStyleSheet, etc)
- **Razão:** Silencia bugs críticos, impede debug, má prática

### 3. Commits Equilibrados
- **NÃO:** Commit a cada mudança mínima
- **SIM:** Commits em pontos de retorno significativos
- **Formato:** `feat(gui): Descrição clara e concisa`
- **Frequência:** Após completar funcionalidade ou grupo de correções

### 4. Comunicação Direta
- **NÃO usar emojis, acentos, cedilhas** em código
- Respostas concisas (1-3 sentenças para confirmações)
- Explicar comandos impactantes (system-modifying operations)
- Documentação técnica pode ser detalhada

### 5. Ferramentas e Análise
- **Sempre usar ferramentas de leitura** antes de modificar código
- `semantic_search`, `grep_search`, `read_file` para contexto completo
- Análise profunda quando múltiplos erros aparecem
- Evitar "adivinhar" - investigar primeiro

---

## ESTADO ATUAL DO CÓDIGO

### Últimas Modificações (Sessão Atual)

####  RESOLVIDO
1. **QLayout Parent Error** 
   - Removido container intermediário `grid_container`
   - Grid adicionado diretamente: `outer.addLayout(main_grid)`
   - Antes causava: "QLayout::addChildLayout: layout already has a parent"

2. **NameError: cache não definido**
   - `_refresh_responsavel_options()` linha ~2417
   - Adicionado: `cache = getattr(self, "_adv_values_cache", {})`

3. **Try/Except Duplo Aninhado**
   - `_bind_tab_context()` linha ~1391-1399
   - Removidos 2 níveis de try/except que silenciavam TODOS os erros
   - Adicionado: `logger.info("Refresh de filtros avancados...")`

4. **Proporção Layout Corrigida**
   - Detalhes da SSA: **40% máximo** (stretch=2)
   - Filtros Avançados: **60% mínimo** (stretch=3)
   - APENAS na aba Filtros: `if tab_kind == "filters":`

5. **Responsividade Implementada**
   - `search_input`: Removido setMinimumWidth(425) + setMaximumWidth(950)
   - Botões: Unificados em 100px (reprog_button era 80px)
   - Campos semana: setFixedWidth(60) → setMaximumWidth(60)
   - Scroll menus: setFixedHeight(320) → setMaximumHeight(360)

6. **Layout Grid 6x3 Compacto**
   ```
   Linha 1: Emissor | Executor | Divisao | Situacao | Ano Emis | Ano Exec
   Linha 2: Reprog | Prio Emis | Prio Plan | Derivadas (2 cols) | Macro
   Linha 3: Sem Emis | Sem Exec | Solicitante | Resp Prog | Resp Exec | Resp Emis
   ```
   - Margins: 2px, Spacing: 2px
   - Labels curtos (antes: "Setor Emissor" → agora: "Emissor")

####  PENDENTE (CRÍTICO)
1. **Dados NÃO carregam nos botões multiselect**
   - Sintoma: Todos botões mostram "Sem dados"
   - Root cause: Ainda investigando
   - Suspeita: Race condition no timing de `_refresh_advanced_filter_options()`
   - Última tentativa: Chamar após `_refresh_after_filter_change()` em `on_data_loaded`

2. **Reorganização Responsiva Desabilitada**
   - `_reorganize_advanced_filters_grid()` implementado mas NÃO ativo
   - `resizeEvent()` comentado - causava QLayout errors
   - Estrutura pronta para 3 breakpoints (>1400px: 6x3, 900-1400px: 3x6, <900px: 2x9)

3. **191 Try/Except Silenciosos**
   - Encontrados via `grep_search`
   - Principais corrigidos (bind_tab_context, on_data_loaded)
   - Restantes são defensivos (Qt APIs) - analisar caso a caso

---

## ARQUITETURA E FLUXO

### Fluxo de Carregamento de Dados
```
1. main.py --gui
2. SSAMainWindow.__init__()
3. Usuário clica "Carregar Dados"
4. DataLoaderWorker (thread separada)
5. on_data_loaded(df) - SLOT
   ├─ self.df_completo = df.copy()
   ├─ _refresh_after_filter_change() → display_current_page()
   └─ SE tab_kind == "filters":
      └─ _refresh_advanced_filter_options() ← AQUI DEVE POPULAR
         ├─ Cache: exec_vals, emis_vals, status_vals, etc
         ├─ _rebuild_multiselect_menu() para cada botão
         │  ├─ menu.clear()
         │  ├─ Cria checkboxes
         │  └─ Retorna lista de checks
         └─ self.adv_executor_checks = checks ← DEVE TER DADOS
6. _update_multiselect_button() atualiza texto do botão
   └─ Se len(checks) == 0 → "Sem dados" ← PROBLEMA ATUAL
```

### Estrutura de Tabs
```python
# gui_ssa.py linha ~970
self.main_tabs = QTabWidget()
self._tab_contexts = [
    self._build_tab_content(page1, tab_kind="main"),    # Aba SSAs
    self._build_tab_content(page2, tab_kind="filters")  # Aba Filtros
]
self.main_tabs.currentChanged.connect(self._on_tab_changed)
```

### Layout da Aba Filtros
```
┌─────────────────────────────────────────────────────┐
│ Pesquisa Geral: [...................] [Aplicar]    │
│ Paginator | Perfil | Filtros Summary               │
├──────────────────┬──────────────────────────────────┤
│                  │                                  │
│  Tabela SSAs     │  Filtros Avançados (Grid 6x3)   │
│  (dados)         │  ┌──────────────────────────┐   │
│                  │  │ Emissor | Executor | ... │   │
│                  │  │ Reprog  | Prio Emis| ... │   │
├──────────────────┤  │ Sem Emis| Sem Exec | ... │   │
│  Detalhes SSA    │  └──────────────────────────┘   │
│  Selecionada     │  [Aplicar] [Limpar] [Salvar]    │
│  (40% max)       │  (60% min)                       │
└──────────────────┴──────────────────────────────────┘
```

---

## INVESTIGAÇÃO: Por que Dados Não Carregam?

### Hipóteses Testadas
1.  Try/except silenciando erros → REMOVIDO, ainda sem dados
2.  Cache não definido → CORRIGIDO, ainda sem dados
3.  QLayout parent error → CORRIGIDO, ainda sem dados
4. ⏳ Timing: `_refresh_advanced_filter_options()` chamado antes de widgets existirem?

### Próximos Passos de Debug
```python
# Adicionar em _refresh_advanced_filter_options() linha ~3043
logger.info(f"REFRESH: df_completo shape={self.df_completo.shape if self.df_completo is not None else None}")
logger.info(f"REFRESH: hasattr adv_executor_menu={hasattr(self, 'adv_executor_menu')}")
logger.info(f"REFRESH: exec_vals length={len(exec_vals)}")

# Adicionar em _rebuild_multiselect_menu() linha ~1614
logger.info(f"REBUILD: button={button}, menu={menu}, values length={len(values)}")
logger.info(f"REBUILD: created checks length={len(checks)}")

# Verificar ordem de execução
# Expectativa: _build_advanced_filters_panel() → _refresh_advanced_filter_options()
# Se invertido: widgets não existem ainda!
```

### Possível Root Cause
```python
# _bind_tab_context() linha ~1387
if tab_kind == "filters" and hasattr(self, "adv_filters_group"):
    if getattr(self, "_adv_options_dirty", False):
        self._refresh_advanced_filter_options()  # ← Chamado ANTES de widgets?

# Mas widgets criados em _build_advanced_filters_panel() linha ~1845
# Que é chamado em _build_tab_content() linha ~1308
# Que é chamado em __init__() para criar self._tab_contexts

# VERIFICAR: self.adv_executor_button existe quando _refresh é chamado?
```

---

## CÓDIGO CRÍTICO - LOCALIZAÇÕES

### Criação de Botões Multiselect
- **Função:** `_make_multiselect_box()` linha ~1497
- **Retorno:** `box, button, menu, exclude`
- **Usado em:** `_build_advanced_filters_panel()` linha ~1845

### População de Menus
- **Função:** `_rebuild_multiselect_menu()` linha ~1614
- **Parâmetros:** values (lista de strings), selected_set, on_toggle, on_apply
- **Retorno:** `checks, exclude_checks` (listas de QCheckBox)
- **Problema:** Se values=[], retorna checks=[] → "Sem dados"

### Atualização Visual
- **Função:** `_update_multiselect_button()` linha ~1557
- **Lógica:** 
  ```python
  if len(checks) == 0:
      text = "Sem dados"  # ← SINTOMA
  ```

### Carregamento de Dados
- **Slot:** `on_data_loaded()` linha ~3586
- **Thread:** DataLoaderWorker (arquivo separado)
- **Chamadas:**
  1. `_refresh_after_filter_change()` (sempre)
  2. `_refresh_advanced_filter_options()` (só se tab_kind=="filters")

---

## COMANDOS ÚTEIS

### Compilar e Limpar Cache
```powershell
python -m py_compile "C:\Users\mauri\git\SSA_Consulta_Rapida\gui\gui_ssa.py"
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### Executar GUI
```powershell
python main.py --gui
```

### Debug com Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Já configurado no código
```

### Buscar Problemas
```bash
# Try/except silenciosos
grep_search --isRegexp "except.*:\n\s+pass" --includeIgnoredFiles

# Larguras fixas
grep_search --isRegexp "setFixedWidth|setMinimumWidth|setMaximumWidth"

# QLayout operations
grep_search --isRegexp "addLayout|addWidget|setParent"
```

---

## BOAS PRÁTICAS ESTABELECIDAS

### 1. Análise Antes de Ação
```python
# MAU
def fix_bug():
    # Tentar algo e ver se funciona
    try:
        self.widget.setValue(10)
    except:
        pass

# BOM
# 1. semantic_search("setValue widget initialization")
# 2. read_file para entender contexto
# 3. grep_search para encontrar padrões
# 4. Implementar solução informada
```

### 2. Modificações Condicionais
```python
# MAU (afeta ambas abas)
bottom_layout.addWidget(details_group, 2)

# BOM (só aba Filtros)
if tab_kind == "filters":
    bottom_layout.addWidget(right_col_widget, 3)
else:
    bottom_layout.addWidget(right_col_widget, 5)
```

### 3. Error Handling
```python
# MAU
try:
    critical_operation()
except Exception:
    pass  # Silencia erro

# BOM
try:
    critical_operation()
except Exception as e:
    logger.error(f"Erro em critical_operation: {e}", exc_info=True)
    # Opcionalmente re-raise ou fallback
```

### 4. Larguras Responsivas
```python
# MAU (rígido)
widget.setFixedWidth(425)

# BOM (adaptável)
widget.setMaximumWidth(425)  # Limite superior, pode encolher
widget.setSizePolicy(QSizePolicy.Policy.Expanding, ...)
```

---

## ESTATÍSTICAS DO CÓDIGO

- **Linhas totais:** 5449
- **Try/except:** 191 encontrados
  - Críticos corrigidos: 3
  - Defensivos aceitáveis: ~180
  - Pendentes análise: ~8
- **Widgets principais:**
  - Botões multiselect: 17
  - Checkboxes: 3 (Derivadas)
  - Combos: 2 (Reprog mode, Macro)
  - LineEdits: 4 (Sem Emis/Exec Ini/Fim)
- **Menus dinâmicos:** Todos (executor, emissor, divisão, status, anos, prioridades, responsáveis)

---

## PRÓXIMA AÇÃO RECOMENDADA

### Debugging Imediato
1. **Adicionar logging em 3 pontos:**
   - `_refresh_advanced_filter_options()` início
   - `_rebuild_multiselect_menu()` início e fim
   - `_update_multiselect_button()` quando len(checks)==0

2. **Executar e capturar logs:**
   ```powershell
   python main.py --gui 2>&1 | Tee-Object debug.log
   ```

3. **Analisar ordem de execução:**
   - Se `_rebuild_multiselect_menu()` não for chamado → problema em `_refresh_advanced_filter_options()`
   - Se chamado mas values=[] → problema no cache
   - Se values OK mas checks=[] → problema no grid/menu

### Fallback se Logging Não Resolver
4. **Teste isolado de _rebuild_multiselect_menu:**
   ```python
   # No console Python ou notebook
   values_test = ["MC11", "MC12", "MBL3"]
   checks, _ = window._rebuild_multiselect_menu(
       window.adv_executor_button,
       window.adv_executor_menu,
       values_test,
       set(),
       None, None, None, None
   )
   print(f"Checks criados: {len(checks)}")
   ```

5. **Verificar hasattr no momento certo:**
   ```python
   # Adicionar em on_data_loaded() ANTES de chamar refresh
   logger.info(f"Widgets existem? executor={hasattr(self, 'adv_executor_button')}")
   logger.info(f"Tab atual: {getattr(self, '_current_tab_kind', None)}")
   ```

---

## COMMITS REALIZADOS (PARA ROLLBACK SE NECESSÁRIO)

1. `632af01` - feat(gui): Otimiza layout aba Filtros - botoes 100px, proporcao 62/38, refresh direto
2. `d898a50` - feat(gui): Layout responsivo grid 6x3/3x6/2x9 + proporcao Detalhes 40% max

**Branch:** dev  
**Último commit estável:** `632af01` (antes de reorganização automática)

---

## REFERÊNCIAS DE CÓDIGO

### PyQt6 APIs Usadas
- `QToolButton` - Botões com menu dropdown
- `QMenu` + `QWidgetAction` - Menus customizados com scroll
- `QGridLayout` - Layout grid 6x3
- `QScrollArea` - Scroll vertical (preparado, não ativo)
- `QSizePolicy` - Políticas de expansão
- `QTimer.singleShot()` - Debouncing (300ms)

### Estrutura de Mixins
```
SSAMainWindow (gui_ssa.py)
└── herda FilterGUISSAMixin (gui/mixins/filter_gui_ssa_mixin.py)
    ├── _refresh_after_filter_change() - linha 1009
    ├── _apply_column_filters()
    └── _update_col_filter_indicator()
```

### Imports Principais
```python
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QGroupBox, QToolButton, QMenu,
    QCheckBox, QPushButton, QLineEdit, QComboBox, QLabel,
    QGridLayout, QHBoxLayout, QVBoxLayout, QScrollArea,
    QWidgetAction, QSizePolicy, QFrame, QTextBrowser
)
from PyQt6.QtCore import QTimer, Qt
import pandas as pd
```

---

## GLOSSÁRIO ESPECÍFICO DO PROJETO

- **SSA:** Solicitação de Serviço de Apoio (documento principal)
- **STE/SCA:** Situações específicas que podem ser excluídas
- **Derivada:** SSA que deriva de outra (hierarquia)
- **Reprog:** Número de reprogramações
- **Setor Executor/Emissor:** Setores responsáveis
- **Divisão:** SMIN, outros (agrupamento de setores)

---

## MENSAGEM FINAL PARA PRÓXIMA SESSÃO

Estamos a **um passo** de resolver o problema dos dados. A estrutura está correta, layout funcional, sem QLayout errors. O único problema restante é **por que `_rebuild_multiselect_menu()` não está sendo chamado ou retorna listas vazias**.

**Foco Imediato:** Adicionar logging detalhado nos 3 pontos mencionados e analisar a ordem de execução. Muito provavelmente é um problema de timing/sequência de chamadas.

**Se precisar reverter:** `git checkout 632af01` retorna ao último estado estável antes das mudanças de reorganização.

**Lembre-se:** NUNCA modificar aba SSAs, sempre usar logging em vez de try/except pass, e fazer análise profunda com ferramentas antes de mudanças.

Boa sorte! 
# STATUS 2026-02-26

Este arquivo e historico de iteracoes.
Fonte operacional atual:
- `docs/FILTER_TAB_OPTIMIZATIONS.md` (algoritmo atual v4.22)
- `docs/NEXT_CHAT_MIGRATION.md` (estado atual de execucao)

Pendencias absorvidas nesta migracao:
1. estado e release atual movidos para docs ativos.
2. backlog e matriz de pendencias sincronizados com snapshot atual.
3. este arquivo segue como apoio de handoff; fonte primaria de execucao fica nos docs ativos listados acima.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

