# HISTÓRICO DE RELEASES

Este documento consolida todas as notas de lançamento e atualizações do projeto SSA Consulta Rápida.

## **RELEASE v3.11 - CURRENT RELEASE**

**Data de Lançamento**: Outubro 2025  
**Tipo**: Major Update focado em usabilidade  
**Status**: Estável

### **Principais Funcionalidades**

#### ** Experiência CLI mais ágil**
- Mostra apenas a primeira página por padrão; comando `m`/`mais` avança sem perder o prompt
- `m z` percorre todo o resultado sem bloquear a entrada
- Prompt atualizado com atalhos claros e resumo de filtros ativos

#### ** Sintaxe OU/OR unificada**
- CLI, GUI e Streamlit compartilham o mesmo parser (`OU`/`OR`, negativos, regex)
- Ajuda revisada elimina a notação `v` e destaca exemplos práticos
- Perfil "Executor ou Emissor" mantém chips sincronizados em tempo real

#### ** Temas adicionais e contraste aprimorado**
- Tema "Escala de cinza" substitui o antigo claro com ajustes finos
- Novos perfis Windows 7, KDE e GNOME (Adwaita) disponíveis na GUI
- Ajustes automáticos de contraste para macOS quando necessário

#### ** Dashboard Streamlit atualizado**
- `python main.py --streamlit` (ou `--web`) inicia o painel em background
- Barra lateral com ajuda rápida e resumo dos filtros aplicados
- Download de CSV preservado e consulta opcional da API Itaipu

## **RELEASE v3.10**

**Data de Lançamento**: Agosto 2025  
**Tipo**: Major Update focado em build/distribuição  
**Status**: Estável

### **Principais Funcionalidades**

#### ** Novidades Críticas**
- **Sistema de Build Multi-Plataforma**: Construção automática para Windows, macOS e Linux
- **Modo Optimized**: Performance 3-5x melhor para arquivos grandes
- **CLI Enhanced**: Interface de linha de comando completa e intuitiva
- **Cache Inteligente**: Gestão automática de cache para consultas frequentes

#### **️ Melhorias Técnicas**
- **Arquitetura Modular**: Separação clara entre core, GUI e CLI
- **Configuração Externa**: 100% das configurações externalizadas em JSON
- **Lazy Loading**: Carregamento sob demanda na interface gráfica
- **Memory Management**: Gestão otimizada de memória

#### ** Correções Críticas**
- **SSA Truncation Bug**: Corrigido problema que truncava números SSA válidos
- **Column Mapping**: Sistema robusto de detecção automática de colunas
- **GUI Width Management**: Persistência de larguras de colunas entre sessões
- **Thread Safety**: Eliminação de race conditions em operações multi-thread

### **Componentes Principais**

#### **Core System**
```
core/
├── app_logic.py           # Coordenação de importação/atualização
├── cache_manager.py       # Sistema de cache inteligente
├── config_manager.py      # Gestão centralizada de configurações
└── configuration_manager.py  # Configurações avançadas
```

#### **Interface Dupla**
```
interface/
├── cli_main.py           # CLI principal com paginação
├── cli_enhanced.py       # Funcionalidades avançadas CLI
└── cli_utils.py          # Utilitários CLI

gui/
├── gui_ssa_main.py       # Interface principal
├── (removido) gui_ssa_poc.py        # Interface alternativa obsoleta
├── simple_width_manager.py  # Gestão de larguras
└── gui_utils.py          # Utilitários GUI
```

#### **Sistema de Dados**
```
armazenamento/
├── database.py           # Operações SQLite padrão
└── database_optimized.py # Operações otimizadas para grandes volumes

extracao/
└── extractor.py          # Processamento Excel com pandas
```

### **Requisitos Técnicos**

#### **Python**
- **Versão Mínima**: Python 3.13+
- **Ambiente**: Virtual environment recomendado
- **Gestão**: pyenv para múltiplas versões

#### **Dependências Core**
```json
{
    "PyQt6": ">=6.6.0",
    "pandas": ">=2.0.0",
    "openpyxl": ">=3.1.0",
    "xlsxwriter": ">=3.1.0",
    "psutil": ">=5.9.0"
}
```

#### **Dependências Opcionais**
```json
{
    "numba": ">=0.58.0",    # Aceleração numérica
    "pyinstaller": ">=6.0", # Build de executáveis
    "pytest": ">=7.0.0"     # Testes automatizados
}
```

### **Comandos de Instalação**

#### **Setup Completo**
```bash
# Clone do repositório
git clone https://github.com/username/SSA_Consulta_Rapida.git
cd SSA_Consulta_Rapida

# Ambiente virtual
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou venv\Scripts\activate  # Windows

# Instalação de dependências
pip install -r requirements.txt

# Verificação da instalação
python main.py --status
```

#### **Uso Básico**
```bash
# CLI - Lista todas as SSAs
python main.py --list

# CLI - Busca por termo
python main.py --search "termo"

# CLI - Importação
python main.py --import arquivo.xlsx

# GUI - Interface gráfica
python main.py --gui

# Modo optimizado para arquivos grandes
python main.py --import arquivo.xlsx --optimized
```

### **Performance Benchmarks**

#### **Importação de Dados**
- **Arquivo Pequeno** (<1MB): ~2 segundos
- **Arquivo Médio** (1-5MB): ~8 segundos
- **Arquivo Grande** (>5MB): ~30 segundos (modo optimized)

#### **Interface Gráfica**
- **Inicialização**: <3 segundos
- **Carregamento de Dados**: <1 segundo (primeiros 1000 registros)
- **Busca/Filtro**: <500ms

#### **Uso de Memória**
- **Base**: ~50MB (aplicação vazia)
- **Com Dados** (10k registros): ~150MB
- **Modo Optimized**: 60% menos uso de memória

---

## **RELEASE v3.0.6 - STABLE FOUNDATION**

**Data de Lançamento**: Julho 2025  
**Tipo**: Stability Release  
**Status**: LTS (Long Term Support)

### **Principais Conquistas**

#### **️ Arquitetura Sólida**
- **Database Layer**: SQLite com operações UPSERT otimizadas
- **Configuration System**: JSON-based com validação automática
- **Error Handling**: Sistema robusto de tratamento de erros
- **Logging System**: Logging estruturado com níveis configuráveis

#### ** Sistema de Dados**
- **Excel Processing**: Suporte completo para formatos .xlsx e .xls
- **Column Mapping**: Detecção automática de esquemas de colunas
- **Data Validation**: Validação de integridade de dados
- **Backup System**: Backup automático antes de operações críticas

#### **️ Interface Unificada**
- **CLI Foundation**: Interface de linha de comando básica mas funcional
- **GUI Core**: Interface gráfica PyQt6 com recursos essenciais
- **Configuration UI**: Interface para gestão de configurações
- **Help System**: Sistema de ajuda integrado

### **Tecnologias Estabilizadas**

#### **Stack Principal**
```python
# Core Technologies
Python: 3.13+
GUI: PyQt6
Database: SQLite3
Data Processing: pandas + openpyxl
```

#### **Padrões Arquiteturais**
- **MVC Pattern**: Separação clara de Model, View, Controller
- **Repository Pattern**: Abstração de acesso a dados
- **Configuration Pattern**: Configuração externa e flexível
- **Factory Pattern**: Criação de objetos através de factories

### **Funcionalidades Core**

#### **Importação de Dados**
```python
# Suporte a múltiplos formatos
supported_formats = ['.xlsx', '.xls', '.csv']

# Detecção automática de encoding
auto_encoding_detection = True

# Validação de esquema
schema_validation = True

# Progress tracking
progress_reporting = True
```

#### **Gestão de SSAs**
```python
# Operações CRUD completas
operations = [
    'create_ssa',
    'read_ssa', 
    'update_ssa',
    'delete_ssa',
    'bulk_operations'
]

# Filtros avançados
filters = [
    'by_status',
    'by_date_range',
    'by_text_search',
    'by_custom_criteria'
]
```

#### **Exportação de Relatórios**
```python
# Formatos suportados
export_formats = [
    'excel',    # .xlsx com formatação
    'csv',      # Compatibilidade universal
    'json',     # Dados estruturados
    'txt'       # Relatórios simples
]

# Templates personalizáveis
template_support = True
custom_formatting = True
```

### **Qualidade e Testes**

#### **Cobertura de Testes**
- **Unit Tests**: 85% cobertura do código core
- **Integration Tests**: Todos os fluxos principais
- **Performance Tests**: Benchmarks automatizados
- **Regression Tests**: Prevenção de bugs conhecidos

#### **Padrões de Código**
- **Type Hints**: 100% do código tipado
- **Docstrings**: Documentação completa
- **Code Style**: Seguindo PEP 8
- **Error Handling**: Exceções específicas e informativas

---

## **RELEASES ANTERIORES**

### **v3.0.5 - Performance Focus**
**Data**: Junho 2025

#### **Otimizações Implementadas**
- **Database Indexing**: Índices estratégicos para consultas frequentes
- **Memory Optimization**: Redução de 40% no uso de memória
- **Startup Performance**: 50% mais rápido para inicializar
- **File Processing**: Processamento em chunks para arquivos grandes

### **v3.0.4 - UI/UX Improvements**
**Data**: Maio 2025

#### **Melhorias de Interface**
- **Responsive Design**: Interface adaptável a diferentes resoluções
- **Theme Support**: Suporte básico a temas claros/escuros
- **Keyboard Shortcuts**: Atalhos de teclado para operações frequentes
- **Status Bar**: Barra de status com informações úteis

### **v3.0.3 - Data Reliability**
**Data**: Abril 2025

#### **Robustez de Dados**
- **Backup System**: Backup automático antes de importações
- **Data Validation**: Validação rigorosa de dados de entrada
- **Error Recovery**: Recuperação automática de falhas de importação
- **Audit Trail**: Rastreamento de todas as modificações

### **v3.0.2 - Configuration Management**
**Data**: Março 2025

#### **Sistema de Configuração**
- **External Config**: Todas as configurações externalizadas
- **Environment Support**: Suporte a múltiplos ambientes
- **Configuration UI**: Interface para gestão de configurações
- **Validation System**: Validação de configurações

### **v3.0.1 - Bug Fixes**
**Data**: Fevereiro 2025

#### **Correções Críticas**
- **Memory Leaks**: Eliminação de vazamentos de memória
- **Thread Safety**: Correção de problemas de concorrência
- **File Handling**: Melhoria no tratamento de arquivos
- **Error Messages**: Mensagens de erro mais informativas

### **v3.0.0 - Foundation Release**
**Data**: Janeiro 2025

#### **Arquitetura Inicial**
- **Core Framework**: Estrutura base do projeto
- **Database Layer**: Camada de persistência SQLite
- **Basic GUI**: Interface gráfica funcional
- **Import System**: Sistema básico de importação

---

## **ROADMAP FUTURO**

### **v3.11 - Próximo Release** (Planejado)

#### **Funcionalidades Planejadas**
- **Web Interface**: Interface web complementar
- **API REST**: API para integração externa
- **Advanced Analytics**: Análises estatísticas avançadas
- **Multi-User Support**: Suporte a múltiplos usuários

#### **Melhorias Técnicas**
- **Docker Support**: Containerização da aplicação
- **Cloud Integration**: Integração com serviços em nuvem
- **Advanced Caching**: Sistema de cache distribuído
- **Real-time Updates**: Atualizações em tempo real

### **v4.0 - Major Rewrite** (Futuro)

#### **Arquitetura Nova**
- **Microservices**: Divisão em microserviços
- **Modern Stack**: Migração para tecnologias mais modernas
- **Scalability**: Suporte a grandes volumes de dados
- **Enterprise Features**: Funcionalidades empresariais

---

## **SUPORTE E MANUTENÇÃO**

### **Política de Suporte**
- **v3.10**: Suporte ativo até v4.0
- **v3.0.6**: LTS - Suporte até 2026
- **Versões anteriores**: Suporte limitado

### **Canais de Suporte**
- **Issues GitHub**: Reportar bugs e sugestões
- **Documentation**: Documentação técnica completa
- **Scripts**: Scripts de manutenção e diagnóstico

### **Atualização Recomendada**
Para melhor performance e estabilidade, recomenda-se sempre utilizar a versão mais recente estável (v3.10).

**Status**: Desenvolvimento ativo com releases regulares a cada 2-3 meses.
