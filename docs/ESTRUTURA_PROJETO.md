# ESTRUTURA E ORGANIZACAO DO PROJETO

Este documento consolida toda a documentacao sobre estrutura, organizacao e padroes do projeto SSA Consulta Rapida.

## **ESTRUTURA DO PROJETO OTIMIZADA**

### **Visao Geral da Arquitetura**
```
SSA_Consulta_Rapida/
├── main.py                          # Ponto de entrada principal
├── requirements.txt                 # Dependencias de producao
├── pyproject.toml                   # Configuracao do projeto
├── 
├── core/                           # Logica de negocio central
│   ├── app_logic.py               # Orquestracao principal
│   ├── config_manager.py          # Gerenciamento de configuracoes
│   ├── cache_manager.py           # Sistema de cache
│   └── handler_base.py            # Classes base
├── 
├── armazenamento/                  # Camada de dados
│   ├── database.py               # Interface padrao
│   └── database_optimized.py     # Versao otimizada
├── 
├── gui/                           # Interface grafica
│   ├── gui_ssa.py                # Interface principal
│   ├── simple_width_manager.py   # Gerenciamento de larguras
│   └── components/               # Componentes reutilizaveis
├── 
├── interface/                     # Interface CLI
│   └── cli_*.py                  # Modulos da linha de comando
├── 
├── utils/                        # Utilitarios
│   ├── helpers.py               # Funcoes auxiliares
│   ├── validators.py            # Validacoes
│   └── themes.py                # Temas da interface
├── 
├── config/                       # Configuracoes
│   ├── settings.json            # Configuracoes gerais
│   ├── column_mappings.json     # Mapeamento de colunas
│   └── *_preferences.json       # Preferencias por componente
├── 
├── data/                         # Dados persistentes
│   ├── ssas.db                  # Banco principal
│   └── historico_backups/       # Backups automaticos
├── 
├── launchers/                    # Sistema de build
│   ├── build_multiplatform.py   # Build multiplataforma
│   ├── platforms/               # Configs por plataforma
│   └── dist/                    # Executaveis gerados
├── 
├── docs/                        # Documentacao
│   ├── ARQUITETURA_IMPORTACAO.md # Analises tecnicas ativas
│   ├── TROUBLESHOOTING.md       # Solucao de problemas
│   ├── CHANGELOG_IMPLEMENTACOES.md # Historico de implementacao
│   └── GUIA_MIGRACAO_NOVA_INSTALACAO.md # Setup
└── 
└── tests/                       # Testes automatizados
    ├── unit/                   # Testes unitarios
    ├── integration/            # Testes de integracao
    └── fixtures/               # Dados para testes
```

### **Provisionamento Automatico de Diretorios**
O modulo `utils.setup_project_structure` garante, no inicio da execucao, que diretorios fundamentais existam (ex.: `data/`, `data/historico_backups/`, `logs/`, `reports/`, `extracao/`, `exportacao/`).

Caracteristicas:
- Idempotente: multiplas chamadas nao recriam nem alteram existentes.
- Log de nivel INFO apenas quando algo novo e criado (silencioso em execucoes subsequentes).
- Extensivel por variaveis de ambiente:
    - `SSA_EXTRA_DIRS="dir1,dir2"` para acrescentar diretorios adicionais.
    - `SSA_LEGACY_SETUP_MODULE=/caminho/legacy_setup.py` para mesclar diretorios definidos por `legacy_required_dirs()` (se disponivel).
- Teste de guarda: `tests/test_setup_project_structure.py` evita remocao acidental.

Uso isolado (diagnostico):
```bash
python -c "from utils import setup_project_structure as s; print(s.setup_dirs())"
```

### **PRINCIPIOS ARQUITETURAIS**

#### **1. Separacao de Responsabilidades**
- **core/**: Logica de negocio pura, sem dependencia de interface
- **gui/**: Interface grafica, depende apenas do core
- **interface/**: CLI, depende apenas do core
- **armazenamento/**: Persistencia, interface bem definida
- **utils/**: Funcoes auxiliares e bootstrap, com dependencias controladas de ambiente quando necessario

#### **2. Configuracao Centralizada**
- **config/**: Todos os arquivos de configuracao
- JSON para dados modificaveis
- Codigo para logica imutavel
- Versionamento de configuracoes

#### **3. Modularidade**
- Cada modulo tem responsabilidade especifica
- Interfaces bem definidas entre modulos
- Possibilidade de extensao sem modificacao

---

## **ORGANIZACAO DA DOCUMENTACAO PROFISSIONAL**

### **ESTRUTURA HIERARQUICA**

#### **Nivel 1 - Documentos Principais**
1. **README.md** - Visao geral e quick start
2. **GUIA_MIGRACAO_NOVA_INSTALACAO.md** - Setup completo
3. **ESTRUTURA_PROJETO.md** - Este documento
4. **TROUBLESHOOTING.md** - Solucao de problemas

#### **Nivel 2 - Documentos Especializados**
1. **ARQUITETURA_IMPORTACAO.md** - Analises consolidadas
2. **CHANGELOG_IMPLEMENTACOES.md** - Historico de desenvolvimento
3. **BUILD_SYSTEM.md** - Sistema de build

#### **Nivel 3 - Documentos de Referencia**
1. **REGRAS_DE_OURO.md** - Boas praticas
2. **COMANDOS_RAPIDOS.md** - Referencia rapida
3. **GUIA_MODO_OPTIMIZED.md** - Performance
4. **THEMING_AND_PACKAGING_PLAN.md** - Futuro

### **PADROES DE DOCUMENTACAO**

#### **Estrutura Padrao de Documentos**
```markdown
# TITULO PRINCIPAL

Breve descricao do proposito do documento.

## **SECAO PRINCIPAL**

### **Subsecao**

Conteudo organizado de forma hierarquica.

#### **Detalhes Especificos**
- Listas quando apropriado
- Exemplos de codigo quando relevante
- Comandos praticos

**Status**: Indicador de estado quando aplicavel
```

#### **Convencoes de Nomenclatura**
- **MAIUSCULAS** para documentos principais
- **snake_case** para arquivos de codigo
- **kebab-case** para recursos web
- **PascalCase** para classes Python

#### **Linguagem e Tom**
- **Profissional**: Sem girias, emojis ou linguagem informal
- **Tecnico**: Preciso e especifico
- **Objetivo**: Direto ao ponto
- **Consistente**: Mesma terminologia em todo projeto

---

## **PADROES DE DESENVOLVIMENTO**

### **ESTRUTURA DE CODIGO**

#### **Arquivos Python**
```python
"""
Modulo: nome_do_modulo.py
Proposito: Descricao breve da funcionalidade
"""

# Imports padrao
import os
import sys

# Imports de terceiros
import pandas as pd
from PyQt6.QtWidgets import QWidget

# Imports locais
from core.app_logic import AppLogic
from utils.helpers import Helper

class NomeClasse:
    """Classe para [proposito especifico]."""
    
    def __init__(self):
        """Inicializacao da classe."""
        pass
    
    def metodo_publico(self):
        """Metodo publico com docstring."""
        pass
    
    def _metodo_privado(self):
        """Metodo privado com docstring."""
        pass
```

#### **Configuracoes JSON**
```json
{
    "version": "3.10",
    "description": "Configuracoes para [componente]",
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

### **CONVENCOES DE NOMENCLATURA**

#### **Variaveis e Funcoes**
- `snake_case` para funcoes e variaveis
- `UPPER_SNAKE_CASE` para constantes
- Nomes descritivos e especificos
- Evitar abreviacoes desnecessarias

#### **Classes e Modulos**
- `PascalCase` para classes
- `snake_case` para modulos
- Nomes que indicam responsabilidade clara
- Sufixos descritivos (Manager, Handler, Provider)

#### **Arquivos e Diretorios**
- `snake_case` para arquivos Python
- `kebab-case` para outros arquivos
- Diretorios em minusculas
- Estrutura reflete arquitetura

### **ORGANIZACAO DE IMPORTS**
1. **Bibliotecas padrao** do Python
2. **Bibliotecas de terceiros**
3. **Modulos locais**
4. Linha em branco entre cada grupo
5. Ordenacao alfabetica dentro de cada grupo

### **TRATAMENTO DE ERROS**
```python
def funcao_com_tratamento():
    """Funcao com tratamento adequado de erros."""
    try:
        # Operacao que pode falhar
        resultado = operacao_perigosa()
        return resultado
    except ValueError as e:
        logger.error(f"Erro de valor: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise
    finally:
        # Limpeza necessaria
        cleanup()
```

---

## **GESTAO DE CONFIGURACOES**

### **HIERARQUIA DE CONFIGURACOES**

#### **1. Configuracoes de Sistema (config/)**
- `settings.json` - Configuracoes globais
- `column_mappings.json` - Mapeamento de colunas
- `column_priority.json` - Prioridades de exibicao
- `display_mappings.json` - Formatacao de exibicao

#### **2. Configuracoes de Usuario**
- `gui_main_preferences.json` - Preferencias da GUI principal
- `gui_poc_preferences.json` - Preferencias da POC
- `cli_enhancements.json` - Melhorias do CLI

#### **3. Configuracoes de Build**
- `launchers/platforms/*/build_config.json` - Por plataforma
- `pyproject.toml` - Metadados do projeto
- `requirements.txt` - Dependencias

### **EXEMPLO DE CONFIGURACAO ESTRUTURADA**
```json
{
    "metadata": {
        "version": "3.10",
        "component": "gui_main",
        "description": "Preferencias da interface principal",
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
- Analise de requisitos
- Design da solucao
- Estimativa de esforco
- Documentacao inicial

#### **2. Implementacao**
- Desenvolvimento seguindo padroes
- Testes unitarios
- Documentacao atualizada
- Code review

#### **3. Validacao**
- Testes de integracao
- Testes de performance
- Validacao de usuario
- Documentacao final

#### **4. Deploy**
- Build para multiplas plataformas
- Testes em ambiente real
- Release notes
- Monitoramento

### **PROCESSO DE RELEASE**

#### **Preparacao**
1. Atualizacao de versao em `config/version.json`
2. Atualizacao de `CHANGELOG.md`
3. Build de todos os executaveis
4. Testes finais em cada plataforma

#### **Publicacao**
1. Tag no Git com versionamento semantico
2. Release no GitHub com assets
3. Documentacao atualizada
4. Comunicacao de mudancas

#### **Pos-Release**
1. Monitoramento de feedback
2. Hotfixes se necessario
3. Planejamento da proxima versao
4. Licoes aprendidas

---

## **BOAS PRATICAS ESTABELECIDAS**

### **CODIGO**
- Seguir PEP 8 para Python
- Docstrings em todas as funcoes publicas
- Type hints quando apropriado
- Tratamento adequado de erros
- Logging estruturado

### **DOCUMENTACAO**
- Manter atualizada com mudancas
- Linguagem profissional e tecnica
- Exemplos praticos quando relevante
- Estrutura consistente
- Versionamento junto com codigo

### **CONFIGURACAO**
- JSON para dados modificaveis
- Validacao de configuracoes
- Valores padrao sensatos
- Migracao automatica quando possivel
- Backup antes de mudancas

### **PERFORMANCE**
- Profiling regular de codigo critico
- Otimizacao baseada em dados reais
- Monitoramento de recursos
- Escalabilidade considerada desde o inicio
- Cache estrategico

### **QUALIDADE**
- Testes automatizados
- Code review obrigatorio
- Analise estatica de codigo
- Monitoramento de metricas
- Feedback continuo

---

## **EVOLUCAO FUTURA**

### **ARQUITETURA**
- Manter modularidade
- Considerar microservicos se necessario
- API REST para integracoes
- Plugins para extensibilidade

### **DOCUMENTACAO**
- Automatizacao de documentacao
- Wiki para conhecimento dinamico
- Tutoriais interativos
- Documentacao de API

### **PROCESSO**
- CI/CD mais robusto
- Automacao de testes
- Deploy automatizado
- Monitoramento proativo

**Status**: Estrutura estabilizada e pronta para crescimento sustentavel.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
