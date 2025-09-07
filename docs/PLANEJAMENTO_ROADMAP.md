# PLANEJAMENTO E ROADMAP

Este documento consolida o planejamento estratégico, melhorias futuras e roadmap de desenvolvimento do projeto SSA Consulta Rápida.

## **MELHORIAS PLANEJADAS**

### **Categorização por Impacto**

#### **🟢 BAIXO IMPACTO (Implementação Rápida)**

##### **1. Formatação de Datas na GUI**
**Problema**: Formatação hardcoded de datas na interface gráfica  
**Arquivos Afetados**: `gui/gui_ssa_poc.py`  
**Solução**: Utilizar função padronizada de `utils/formatting.py`

```python
# ANTES (hardcoded)
if col_name == 'data_cadastro' and len(item_text) > 10:
    if ' ' in item_text:
        item_text = item_text.split(' ')[0]

# DEPOIS (padronizado)
from utils.formatting import format_cell
if col_name == 'data_cadastro':
    item_text = format_cell(value, col_name)
```

**Benefícios**:
- Consistência entre CLI e GUI
- Suporte a múltiplos formatos de data
- Redução de duplicação de código
- Tratamento robusto de edge cases

##### **2. Gerenciamento de Configurações**
**Problema**: Valores de configuração espalhados pelo código  
**Arquivos Afetados**: `gui/gui_ssa_poc.py`, `interface/cli.py`  
**Solução**: Centralizar em arquivos JSON externos

```python
# ANTES (hardcoded na GUI)
default_config = {
    'window_width': 1200,
    'window_height': 800,
    'columns_visible': ['numero_ssa', 'descricao', 'status']
}

# DEPOIS (externalizado)
config = ConfigManager.load_gui_config()
window_width = config.get('window_width', 1200)
```

**Estrutura de Configuração Proposta**:
```json
{
    "gui_preferences": {
        "window": {
            "width": 1200,
            "height": 800,
            "remember_size": true
        },
        "table": {
            "default_columns": ["numero_ssa", "descricao", "status"],
            "row_height": 25,
            "alternate_colors": true
        },
        "filters": {
            "remember_last": true,
            "default_mode": "contains"
        }
    },
    "cli_preferences": {
        "pagination": {
            "items_per_page": 20,
            "show_progress": true
        },
        "display": {
            "use_colors": true,
            "compact_mode": false
        }
    }
}
```

##### **3. Logging Estruturado**
**Problema**: Logging inconsistente entre componentes  
**Solução**: Sistema de logging centralizado e configurável

```python
# Implementação proposta
class StructuredLogger:
    def __init__(self, component_name):
        self.component = component_name
        self.logger = logging.getLogger(f"ssa.{component_name}")
    
    def log_operation(self, operation, details=None, level=logging.INFO):
        """Log estruturado de operações."""
        log_data = {
            'component': self.component,
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False))
    
    def log_performance(self, operation, duration, metrics=None):
        """Log específico para performance."""
        perf_data = {
            'type': 'performance',
            'operation': operation,
            'duration_ms': duration * 1000,
            'metrics': metrics or {}
        }
        self.log_operation('performance_metric', perf_data)
```

---

#### **🟡 MÉDIO IMPACTO (Planejamento Necessário)**

##### **1. Sistema de Plugins**
**Objetivo**: Extensibilidade através de plugins  
**Arquivos Afetados**: Criação de nova estrutura `plugins/`

**Arquitetura Proposta**:
```
plugins/
├── __init__.py
├── plugin_manager.py
├── base_plugin.py
└── builtin/
    ├── excel_enhanced/
    ├── pdf_export/
    └── analytics/
```

**Interface de Plugin**:
```python
class BasePlugin:
    """Interface base para plugins."""
    
    def __init__(self):
        self.name = None
        self.version = None
        self.description = None
        self.dependencies = []
    
    def initialize(self, app_context):
        """Inicializa plugin com contexto da aplicação."""
        pass
    
    def register_cli_commands(self, cli_parser):
        """Registra comandos CLI específicos do plugin."""
        pass
    
    def register_gui_components(self, main_window):
        """Registra componentes GUI específicos do plugin."""
        pass
    
    def cleanup(self):
        """Limpa recursos do plugin."""
        pass
```

**Plugin Manager**:
```python
class PluginManager:
    """Gerenciador de plugins."""
    
    def __init__(self):
        self.plugins = {}
        self.plugin_dirs = ['plugins/builtin', 'plugins/user']
    
    def discover_plugins(self):
        """Descobre plugins disponíveis."""
        for plugin_dir in self.plugin_dirs:
            for item in os.listdir(plugin_dir):
                plugin_path = os.path.join(plugin_dir, item)
                if self.is_valid_plugin(plugin_path):
                    self.load_plugin(plugin_path)
    
    def load_plugin(self, plugin_path):
        """Carrega plugin específico."""
        spec = importlib.util.spec_from_file_location(
            "plugin", os.path.join(plugin_path, "__init__.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'Plugin'):
            plugin = module.Plugin()
            self.plugins[plugin.name] = plugin
            return True
        return False
```

##### **2. API REST**
**Objetivo**: Acesso programático aos dados via API  
**Tecnologia**: FastAPI para performance e documentação automática

**Endpoints Propostos**:
```python
from fastapi import FastAPI, HTTPException
from typing import List, Optional

app = FastAPI(title="SSA Consulta Rápida API", version="1.0.0")

@app.get("/ssas/", response_model=List[SSAModel])
async def list_ssas(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista SSAs com filtros opcionais."""
    # Implementação usando core/app_logic.py
    pass

@app.get("/ssas/{ssa_number}", response_model=SSAModel)
async def get_ssa(ssa_number: str):
    """Obtém SSA específico."""
    pass

@app.post("/ssas/import")
async def import_excel(file: UploadFile):
    """Importa dados de arquivo Excel via API."""
    pass

@app.get("/stats/")
async def get_statistics():
    """Retorna estatísticas do sistema."""
    pass
```

**Modelos de Dados**:
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SSAModel(BaseModel):
    numero_ssa: str
    descricao: str
    status_atual: str
    data_abertura: datetime
    executor: Optional[str] = None
    prioridade: Optional[str] = None
    
    class Config:
        orm_mode = True

class ImportResponse(BaseModel):
    success: bool
    imported_count: int
    error_count: int
    errors: List[str] = []
```

##### **3. Dashboard Analytics**
**Objetivo**: Análises visuais e métricas do sistema  
**Tecnologia**: Plotly + Dash para interatividade

**Métricas Propostas**:
- Distribuição de SSAs por status
- Tendências temporais de abertura/fechamento
- Performance por executor
- Análise de aging (SSAs antigas)
- Heatmap de atividade por período

**Implementação**:
```python
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go

class DashboardAnalytics:
    """Dashboard de analytics para SSAs."""
    
    def __init__(self, database):
        self.db = database
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Define layout do dashboard."""
        self.app.layout = html.Div([
            html.H1("Dashboard SSA Analytics"),
            
            # Filtros
            html.Div([
                dcc.DatePickerRange(id='date-range'),
                dcc.Dropdown(id='status-filter', multi=True),
                dcc.Dropdown(id='executor-filter', multi=True)
            ], className='filters'),
            
            # Gráficos
            html.Div([
                dcc.Graph(id='status-distribution'),
                dcc.Graph(id='temporal-trends'),
                dcc.Graph(id='executor-performance'),
                dcc.Graph(id='aging-analysis')
            ])
        ])
    
    def setup_callbacks(self):
        """Define callbacks para interatividade."""
        @self.app.callback(
            [Output('status-distribution', 'figure'),
             Output('temporal-trends', 'figure')],
            [Input('date-range', 'start_date'),
             Input('date-range', 'end_date'),
             Input('status-filter', 'value')]
        )
        def update_charts(start_date, end_date, status_filter):
            # Busca dados filtrados
            data = self.get_filtered_data(start_date, end_date, status_filter)
            
            # Gráfico de distribuição por status
            status_fig = px.pie(
                data.groupby('status_atual').size().reset_index(name='count'),
                values='count',
                names='status_atual',
                title='Distribuição por Status'
            )
            
            # Tendências temporais
            temporal_data = data.groupby([data['data_abertura'].dt.date, 'status_atual']).size().reset_index(name='count')
            temporal_fig = px.line(
                temporal_data,
                x='data_abertura',
                y='count',
                color='status_atual',
                title='Tendências Temporais'
            )
            
            return status_fig, temporal_fig
```

---

#### **🔴 ALTO IMPACTO (Requer Arquitetura)**

##### **1. Arquitetura Microserviços**
**Objetivo**: Escalabilidade e separação de responsabilidades  
**Justificativa**: Preparação para uso empresarial

**Componentes Propostos**:
```
microservices/
├── api-gateway/          # Gateway único de entrada
├── ssa-service/          # CRUD de SSAs
├── import-service/       # Processamento de imports
├── export-service/       # Geração de relatórios
├── notification-service/ # Notificações e alertas
├── auth-service/         # Autenticação e autorização
└── analytics-service/    # Análises e métricas
```

**Comunicação Entre Serviços**:
```python
# Message Bus usando Redis/RabbitMQ
class MessageBus:
    def __init__(self):
        self.redis_client = redis.Redis()
    
    def publish_event(self, event_type, data):
        """Publica evento para outros serviços."""
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'service': 'ssa-service'
        }
        self.redis_client.publish(f'events.{event_type}', json.dumps(event))
    
    def subscribe_to_events(self, event_types, callback):
        """Subscreve a eventos de outros serviços."""
        pubsub = self.redis_client.pubsub()
        for event_type in event_types:
            pubsub.subscribe(f'events.{event_type}')
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                event = json.loads(message['data'])
                callback(event)
```

##### **2. Sistema Multi-Tenant**
**Objetivo**: Suporte a múltiplas organizações  
**Implementação**: Isolamento por tenant com shared schema

**Estrutura de Dados**:
```sql
-- Tabela de tenants
CREATE TABLE tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    tenant_name VARCHAR(200) NOT NULL,
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- SSAs com tenant_id
CREATE TABLE ssas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id VARCHAR(50) NOT NULL,
    numero_ssa VARCHAR(20) NOT NULL,
    descricao TEXT,
    status_atual VARCHAR(50),
    data_abertura DATE,
    executor VARCHAR(100),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    UNIQUE(tenant_id, numero_ssa)
);
```

**Middleware de Tenant**:
```python
class TenantMiddleware:
    """Middleware para isolamento por tenant."""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Extrai tenant do header ou subdomain
        tenant_id = self.extract_tenant_id(environ)
        
        if not tenant_id:
            return self.unauthorized_response(start_response)
        
        # Injeta tenant no contexto da request
        environ['tenant_id'] = tenant_id
        
        return self.app(environ, start_response)
    
    def extract_tenant_id(self, environ):
        """Extrai tenant_id da request."""
        # Via header
        if 'HTTP_X_TENANT_ID' in environ:
            return environ['HTTP_X_TENANT_ID']
        
        # Via subdomain
        host = environ.get('HTTP_HOST', '')
        if '.' in host:
            subdomain = host.split('.')[0]
            if self.is_valid_tenant(subdomain):
                return subdomain
        
        return None
```

##### **3. Interface Web Moderna**
**Objetivo**: Interface web responsiva e moderna  
**Tecnologia**: Vue.js/React + TypeScript

**Arquitetura Frontend**:
```
frontend/
├── src/
│   ├── components/        # Componentes reutilizáveis
│   │   ├── SSATable.vue
│   │   ├── SearchFilter.vue
│   │   └── ImportDialog.vue
│   ├── views/            # Páginas/Views
│   │   ├── Dashboard.vue
│   │   ├── SSAList.vue
│   │   └── Analytics.vue
│   ├── stores/           # Gestão de estado (Pinia/Vuex)
│   │   ├── ssaStore.js
│   │   └── userStore.js
│   ├── services/         # Serviços de API
│   │   └── api.js
│   └── utils/            # Utilitários
├── public/
└── tests/
```

**Componente Example (Vue 3 + TypeScript)**:
```vue
<template>
  <div class="ssa-table">
    <div class="filters">
      <SearchFilter 
        v-model:search="searchTerm"
        v-model:status="statusFilter"
        @filter-change="onFilterChange"
      />
    </div>
    
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th v-for="column in visibleColumns" 
                :key="column.key"
                @click="sortBy(column.key)">
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ssa in filteredSSAs" 
              :key="ssa.numero_ssa"
              @click="selectSSA(ssa)">
            <td v-for="column in visibleColumns" :key="column.key">
              {{ formatCell(ssa[column.key], column.type) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <Pagination 
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-change="onPageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSSAStore } from '@/stores/ssaStore'
import SearchFilter from '@/components/SearchFilter.vue'
import Pagination from '@/components/Pagination.vue'

interface SSA {
  numero_ssa: string
  descricao: string
  status_atual: string
  data_abertura: string
  executor?: string
}

const ssaStore = useSSAStore()
const searchTerm = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const itemsPerPage = 20

const filteredSSAs = computed(() => {
  return ssaStore.getFilteredSSAs(searchTerm.value, statusFilter.value)
})

const totalPages = computed(() => {
  return Math.ceil(filteredSSAs.value.length / itemsPerPage)
})

onMounted(() => {
  ssaStore.loadSSAs()
})
</script>
```

---

## **ROADMAP ESTRATÉGICO**

### **Q1 2026 - Melhorias Fundamentais**
- ✅ Consolidação de documentação (Completo)
- 🟡 Sistema de logging estruturado
- 🟡 Configurações externalizadas
- 🟡 Testes automatizados expandidos
- 🟡 Performance profiling contínuo

### **Q2 2026 - Extensibilidade**
- 🔴 Sistema de plugins básico
- 🔴 API REST inicial
- 🔴 Dashboard analytics
- 🔴 Notificações automáticas
- 🔴 Backup automático

### **Q3 2026 - Escalabilidade**
- 🔴 Arquitetura microserviços (Fase 1)
- 🔴 Interface web moderna
- 🔴 Sistema multi-tenant básico
- 🔴 Cache distribuído
- 🔴 Monitoramento avançado

### **Q4 2026 - Recursos Empresariais**
- 🔴 Autenticação e autorização
- 🔴 Audit trail completo
- 🔴 Integração com sistemas externos
- 🔴 Relatórios avançados
- 🔴 Mobile app (PWA)

---

## **CRITÉRIOS DE PRIORIZAÇÃO**

### **Impacto no Usuário**
1. **Alto**: Funcionalidades que melhoram significativamente a experiência
2. **Médio**: Melhorias de eficiência e conveniência
3. **Baixo**: Refinamentos e otimizações

### **Complexidade Técnica**
1. **Baixa**: Mudanças localizadas, poucos arquivos
2. **Média**: Múltiplos componentes, requer planejamento
3. **Alta**: Mudanças arquiteturais, requer redesign

### **Recursos Necessários**
1. **Desenvolvedor**: Tempo de desenvolvimento
2. **Infraestrutura**: Recursos de servidor/cloud
3. **Testing**: Tempo de QA e validação
4. **Documentação**: Atualização de docs e treinamento

### **Dependências**
- **Bloqueantes**: Funcionalidades que impedem outras
- **Habilitadoras**: Funcionalidades que facilitam outras
- **Independentes**: Funcionalidades que podem ser desenvolvidas isoladamente

---

## **MÉTRICAS DE SUCESSO**

### **Performance**
- **Tempo de Resposta**: <2 segundos para operações comuns
- **Throughput**: >1000 SSAs processados por minuto
- **Uso de Memória**: <500MB para datasets típicos
- **Uptime**: >99.9% para componentes críticos

### **Qualidade**
- **Cobertura de Testes**: >90% do código core
- **Bug Rate**: <1 bug crítico por release
- **Code Quality**: Score >8.0 em ferramentas de análise
- **Documentation**: 100% das APIs documentadas

### **Adoção**
- **User Satisfaction**: >4.5/5.0 em pesquisas
- **Feature Usage**: >80% das funcionalidades utilizadas
- **Support Tickets**: <5% das operações geram tickets
- **Training Time**: <2 horas para novos usuários

### **Evolução**
- **Release Frequency**: Release mensal com features incrementais
- **Backward Compatibility**: 100% entre versões minor
- **Migration Success**: <1 hora para upgrades
- **API Stability**: Versionamento semântico rigoroso

**Status**: Roadmap estabelecido com prioridades claras e métricas mensuráveis para evolução sustentável do projeto.
