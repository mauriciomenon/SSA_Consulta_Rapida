# ESTRUTURA E ORGANIZAÇÃO DO PROJETO

Este documento consolida toda a documentação sobre estrutura, organização e padrões do projeto SSA Consulta Rápida.

## **ESTRUTURA DO PROJETO OTIMIZADA**

### **Visão Geral da Arquitetura**
```
SSA_Consulta_Rapida/
├── main.py                          # Ponto de entrada principal
├── requirements.txt                 # Dependências de produção
├── pyproject.toml                   # Configuração do projeto
├── 
├── core/                           # Lógica de negócio central
│   ├── app_logic.py               # Orquestração principal
│   ├── config_manager.py          # Gerenciamento de configurações
│   ├── cache_manager.py           # Sistema de cache
│   └── handler_base.py            # Classes base
├── 
├── armazenamento/                  # Camada de dados
│   ├── database.py               # Interface padrão
│   └── database_optimized.py     # Versão otimizada
├── 
├── gui/                           # Interface gráfica
│   ├── gui_ssa.py                # Interface principal
│   ├── simple_width_manager.py   # Gerenciamento de larguras
│   └── components/               # Componentes reutilizáveis
├── 
├── interface/                     # Interface CLI
│   └── cli_*.py                  # Módulos da linha de comando
├── 
├── utils/                        # Utilitários
│   ├── helpers.py               # Funções auxiliares
│   ├── validators.py            # Validações
│   └── themes.py                # Temas da interface
├── 
├── config/                       # Configurações
│   ├── settings.json            # Configurações gerais
│   ├── column_mappings.json     # Mapeamento de colunas
│   └── *_preferences.json       # Preferências por componente
├── 
├── data/                         # Dados persistentes
│   ├── ssas.db                  # Banco principal
│   └── historico_backups/       # Backups automáticos
├── 
├── launchers/                    # Sistema de build
│   ├── build_multiplatform.py   # Build multiplataforma
│   ├── platforms/               # Configs por plataforma
│   └── dist/                    # Executáveis gerados
├── 
├── docs/                        # Documentação
│   ├── CHECKLIST_MASTER.md      # Status e planejamento
│   ├── ANALISES_TECNICAS.md     # Análises consolidadas
│   ├── TROUBLESHOOTING.md       # Solução de problemas
│   ├── RELATORIOS_DESENVOLVIMENTO.md # Relatórios
│   └── GUIA_MIGRACAO_NOVA_INSTALACAO.md # Setup
└── 
└── tests/                       # Testes automatizados
    ├── unit/                   # Testes unitários
    ├── integration/            # Testes de integração
    └── fixtures/               # Dados para testes
```

### **Provisionamento Automático de Diretórios**
O módulo `utils.setup_project_structure` garante, no início da execução, que diretórios fundamentais existam (ex.: `data/`, `data/historico_backups/`, `logs/`, `reports/`, `extracao/`, `exportacao/`).

Características:
- Idempotente: múltiplas chamadas não recriam nem alteram existentes.
- Log de nível INFO apenas quando algo novo é criado (silencioso em execuções subsequentes).
- Extensível por variáveis de ambiente:
    - `SSA_EXTRA_DIRS="dir1,dir2"` para acrescentar diretórios adicionais.
    - `SSA_LEGACY_SETUP_MODULE=/caminho/legacy_setup.py` para mesclar diretórios definidos por `legacy_required_dirs()` (se disponível).
- Teste de guarda: `tests/test_setup_project_structure.py` evita remoção acidental.

Uso isolado (diagnóstico):
```bash
python -c "from utils import setup_project_structure as s; print(s.setup_dirs())"
```

### **PRINCÍPIOS ARQUITETURAIS**

#### **1. Separação de Responsabilidades**
- **core/**: Lógica de negócio pura, sem dependência de interface
- **gui/**: Interface gráfica, depende apenas do core
- **interface/**: CLI, depende apenas do core
- **armazenamento/**: Persistência, interface bem definida
- **utils/**: Funções auxiliares, sem dependências internas

#### **2. Configuração Centralizada**
- **config/**: Todos os arquivos de configuração
- JSON para dados modificáveis
- Código para lógica imutável
- Versionamento de configurações

#### **3. Modularidade**
- Cada módulo tem responsabilidade específica
- Interfaces bem definidas entre módulos
- Possibilidade de extensão sem modificação

---

## **ORGANIZAÇÃO DA DOCUMENTAÇÃO PROFISSIONAL**

### **ESTRUTURA HIERÁRQUICA**

#### **Nível 1 - Documentos Principais**
1. **README.md** - Visão geral e quick start
2. **GUIA_MIGRACAO_NOVA_INSTALACAO.md** - Setup completo
3. **ESTRUTURA_PROJETO.md** - Este documento
4. **TROUBLESHOOTING.md** - Solução de problemas

#### **Nível 2 - Documentos Especializados**
1. **CHECKLIST_MASTER.md** - Status e planejamento
2. **ANALISES_TECNICAS.md** - Análises consolidadas
3. **RELATORIOS_DESENVOLVIMENTO.md** - Histórico de desenvolvimento
4. **BUILD_SYSTEM.md** - Sistema de build

#### **Nível 3 - Documentos de Referência**
1. **REGRAS_DE_OURO.md** - Boas práticas
2. **COMANDOS_RAPIDOS.md** - Referência rápida
3. **GUIA_MODO_OPTIMIZED.md** - Performance
4. **THEMING_AND_PACKAGING_PLAN.md** - Futuro

### **PADRÕES DE DOCUMENTAÇÃO**

#### **Estrutura Padrão de Documentos**
```markdown
# TÍTULO PRINCIPAL

Breve descrição do propósito do documento.

## **SEÇÃO PRINCIPAL**

### **Subseção**

Conteúdo organizado de forma hierárquica.

#### **Detalhes Específicos**
- Listas quando apropriado
- Exemplos de código quando relevante
- Comandos práticos

**Status**: Indicador de estado quando aplicável
```

#### **Convenções de Nomenclatura**
- **MAIÚSCULAS** para documentos principais
- **snake_case** para arquivos de código
- **kebab-case** para recursos web
- **PascalCase** para classes Python

#### **Linguagem e Tom**
- **Profissional**: Sem gírias, emojis ou linguagem informal
- **Técnico**: Preciso e específico
- **Objetivo**: Direto ao ponto
- **Consistente**: Mesma terminologia em todo projeto

---

## **PADRÕES DE DESENVOLVIMENTO**

### **ESTRUTURA DE CÓDIGO**

#### **Arquivos Python**
```python
"""
Módulo: nome_do_modulo.py
Propósito: Descrição breve da funcionalidade
"""

# Imports padrão
import os
import sys

# Imports de terceiros
import pandas as pd
from PyQt6.QtWidgets import QWidget

# Imports locais
from core.app_logic import AppLogic
from utils.helpers import Helper

class NomeClasse:
    """Classe para [propósito específico]."""
    
    def __init__(self):
        """Inicialização da classe."""
        pass
    
    def metodo_publico(self):
        """Método público com docstring."""
        pass
    
    def _metodo_privado(self):
        """Método privado com docstring."""
        pass
```

#### **Configurações JSON**
```json
{
    "version": "3.10",
    "description": "Configurações para [componente]",
    "settings": {
        "opcao1": "valor1",
        "opcao2": 42,
        "opcao3": true
    },
    "metadata": {
        "created": "2025-09-07",
        "modified": "2025-09-07"
    }
}
```

### **CONVENÇÕES DE NOMENCLATURA**

#### **Variáveis e Funções**
- `snake_case` para funções e variáveis
- `UPPER_SNAKE_CASE` para constantes
- Nomes descritivos e específicos
- Evitar abreviações desnecessárias

#### **Classes e Módulos**
- `PascalCase` para classes
- `snake_case` para módulos
- Nomes que indicam responsabilidade clara
- Sufixos descritivos (Manager, Handler, Provider)

#### **Arquivos e Diretórios**
- `snake_case` para arquivos Python
- `kebab-case` para outros arquivos
- Diretórios em minúsculas
- Estrutura reflete arquitetura

### **ORGANIZAÇÃO DE IMPORTS**
1. **Bibliotecas padrão** do Python
2. **Bibliotecas de terceiros**
3. **Módulos locais**
4. Linha em branco entre cada grupo
5. Ordenação alfabética dentro de cada grupo

### **TRATAMENTO DE ERROS**
```python
def funcao_com_tratamento():
    """Função com tratamento adequado de erros."""
    try:
        # Operação que pode falhar
        resultado = operacao_perigosa()
        return resultado
    except ValueError as e:
        logger.error(f"Erro de valor: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise
    finally:
        # Limpeza necessária
        cleanup()
```

---

## **GESTÃO DE CONFIGURAÇÕES**

### **HIERARQUIA DE CONFIGURAÇÕES**

#### **1. Configurações de Sistema (config/)**
- `settings.json` - Configurações globais
- `column_mappings.json` - Mapeamento de colunas
- `column_priority.json` - Prioridades de exibição
- `display_mappings.json` - Formatação de exibição

#### **2. Configurações de Usuário**
- `gui_main_preferences.json` - Preferências da GUI principal
- `gui_poc_preferences.json` - Preferências da POC
- `cli_enhancements.json` - Melhorias do CLI

#### **3. Configurações de Build**
- `launchers/platforms/*/build_config.json` - Por plataforma
- `pyproject.toml` - Metadados do projeto
- `requirements.txt` - Dependências

### **EXEMPLO DE CONFIGURAÇÃO ESTRUTURADA**
```json
{
    "metadata": {
        "version": "3.10",
        "component": "gui_main",
        "description": "Preferências da interface principal",
        "schema_version": "1.0"
    },
    "interface": {
        "window": {
            "width": 1200,
            "height": 800,
            "maximized": false
        },
        "table": {
            "column_widths": {
                "numero_ssa": 120,
                "descricao": 300,
                "status": 100
            },
            "sort_column": "numero_ssa",
            "sort_order": "asc"
        }
    },
    "performance": {
        "auto_optimized": true,
        "cache_size": 1000,
        "lazy_loading": true
    }
}
```

---

## **FLUXO DE DESENVOLVIMENTO**

### **CICLO DE VIDA DE FEATURES**

#### **1. Planejamento**
- Análise de requisitos
- Design da solução
- Estimativa de esforço
- Documentação inicial

#### **2. Implementação**
- Desenvolvimento seguindo padrões
- Testes unitários
- Documentação atualizada
- Code review

#### **3. Validação**
- Testes de integração
- Testes de performance
- Validação de usuário
- Documentação final

#### **4. Deploy**
- Build para múltiplas plataformas
- Testes em ambiente real
- Release notes
- Monitoramento

### **PROCESSO DE RELEASE**

#### **Preparação**
1. Atualização de versão em `config/version.json`
2. Atualização de `CHANGELOG.md`
3. Build de todos os executáveis
4. Testes finais em cada plataforma

#### **Publicação**
1. Tag no Git com versionamento semântico
2. Release no GitHub com assets
3. Documentação atualizada
4. Comunicação de mudanças

#### **Pós-Release**
1. Monitoramento de feedback
2. Hotfixes se necessário
3. Planejamento da próxima versão
4. Lições aprendidas

---

## **BOAS PRÁTICAS ESTABELECIDAS**

### **CÓDIGO**
- Seguir PEP 8 para Python
- Docstrings em todas as funções públicas
- Type hints quando apropriado
- Tratamento adequado de erros
- Logging estruturado

### **DOCUMENTAÇÃO**
- Manter atualizada com mudanças
- Linguagem profissional e técnica
- Exemplos práticos quando relevante
- Estrutura consistente
- Versionamento junto com código

### **CONFIGURAÇÃO**
- JSON para dados modificáveis
- Validação de configurações
- Valores padrão sensatos
- Migração automática quando possível
- Backup antes de mudanças

### **PERFORMANCE**
- Profiling regular de código crítico
- Otimização baseada em dados reais
- Monitoramento de recursos
- Escalabilidade considerada desde o início
- Cache estratégico

### **QUALIDADE**
- Testes automatizados
- Code review obrigatório
- Análise estática de código
- Monitoramento de métricas
- Feedback contínuo

---

## **EVOLUÇÃO FUTURA**

### **ARQUITETURA**
- Manter modularidade
- Considerar microserviços se necessário
- API REST para integrações
- Plugins para extensibilidade

### **DOCUMENTAÇÃO**
- Automatização de documentação
- Wiki para conhecimento dinâmico
- Tutoriais interativos
- Documentação de API

### **PROCESSO**
- CI/CD mais robusto
- Automação de testes
- Deploy automatizado
- Monitoramento proativo

**Status**: Estrutura estabilizada e pronta para crescimento sustentável.
