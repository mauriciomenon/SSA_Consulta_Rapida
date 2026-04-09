# HISTORICO DE VERSOES E RELEASES

Este documento consolida informacoes de todas as versoes e releases do SSA Consulta Rapida.

## HISTORICAL SNAPSHOT

Este arquivo e um snapshot legado de planejamento antigo (serie v3.x).
Fonte ativa de release atual: `docs/HISTORICO_RELEASES.md` (baseline `v4.37`).
Nao usar este arquivo como referencia unica para estado atual.

## **ULTIMA VERSAO DA SERIE v3.x E ROADMAP LEGADO**

- **Ultima versao v3.x**: v3.10 (Setembro 2025)
- **Plano v3.x na epoca**: v3.0.7 (melhorias incrementais)
- **Proxima major na epoca**: v4.0 (planejada para 2026)

---

## **LINHA DO TEMPO DE RELEASES**

### **v3.10 (04/09/2025) - Consolidacao Visual**
**Status**:  Release Final
- **Foco**: Melhorias visuais e estabilidade da GUI
- **Principais Features**:
  - Painel "Filtros por Coluna" compacto
  - Estabilidade de larguras de colunas
  - Sistema de temas (Gruvbox padrao)
  - Dicas de busca visiveis
  - CLI com banner unico

### **v3.0.7 (Meta) - Melhorias Incrementais**
**Status**:  Em Desenvolvimento
- **Foco**: Correcoes e otimizacoes
- **Principais Objetivos**:
  - Isolamento completo de configuracoes
  - Melhorias no sistema de banco de dados
  - Otimizacoes de performance

### **v3.0.5 (25/08/2025) - Estabilidade e Polimento**
**Status**:  Release Estavel
- **Foco**: Sistema CLI Enhanced e robustez
- **Principais Features**:
  - CLI Enhanced System completo
  - Sistema de larguras deterministicas
  - Remocao de mensagens debug
  - Banner e navegacao aprimorados
  - 67 testes automatizados passando

### **v3.0.3 (Meta) - Funcionalidades Core**
**Status**:  Release Historico
- **Foco**: Implementacao de funcionalidades essenciais
- **Base**: Sistema de importacao e consulta robusto

### **v3.0.2 (Meta) - Correcoes Criticas**
**Status**:  Release Historico
- **Foco**: Correcoes de bugs criticos
- **Base**: Sistema estavel de banco de dados

### **v3.0.1 (Meta) - Primeiro Release Estavel**
**Status**:  Release Historico
- **Foco**: Funcionalidade basica estavel
- **Base**: Sistema funcional de consulta de SSAs

### **v3.0.0 (Meta) - Release Inicial**
**Status**:  Release Historico
- **Foco**: Implementacao inicial
- **Base**: Sistema basico funcionando

---

## **FEATURES POR VERSAO**

### **Implementacoes da v3.0.5**

#### **CLI Enhanced System**
- **CLI Width Manager**: Sistema de larguras fixas identico ao GUI
- **Enhanced Table Printer**: Renderizacao ASCII otimizada com word wrap
- **CLI Enhancement Manager**: Gerenciamento de configuracoes das melhorias
- **Comandos Novos**: status-cli, toggle-debug, enhanced-on/off
- **Compatibilidade**: 100% retrocompativel

#### **Melhorias Tecnicas**
- **Determinismo**: Larguras de coluna identicas ao GUI
- **Performance**: Cache inteligente para renderizacao
- **Usabilidade**: Comandos intuitivos e fallback automatico
- **Configuracao**: Sistema unificado com GUI

### **Implementacoes da v3.10**

#### **GUI Aprimorada**
- **Filtros Compactos**: Painel reorganizado com labels proximos
- **Estabilidade Visual**: Larguras nao mudam em operacoes normais
- **Sistema de Temas**: Gruvbox padrao, Tema Claro otimizado
- **UX Melhorada**: Dicas de busca sempre visiveis

#### **CLI Polido**
- **Banner Unico**: Sem duplicacao de informacoes
- **Help Otimizado**: Guia sem bordas laterais
- **Consistencia**: Alinhamento com melhorias da GUI

---

## **ARQUITETURA DE CONFIGURACOES**

### **Evolucao do Sistema de Configuracoes**

#### **v3.0.x - Sistema Compartilhado (Problematico)**
```
config/
├── default_settings.json        → CLI + GUI (conflitos)
├── column_mappings.json         → Compartilhado
└── display_mappings.json        → CLI especifico
```

#### **v3.0.5+ - Sistema Isolado (Atual)**
```
config/
├── gui_poc_preferences.json     → GUI PoC (isolado)
├── gui_main_preferences.json    → GUI main.py (isolado)
├── default_settings.json        → CLI (inalterado)
├── column_mappings.json         → Base compartilhada
└── display_mappings.json        → CLI especifico
```

### **Beneficios da Arquitetura Atual**
1. **Isolamento Completo**: Sem conflitos entre componentes
2. **Flexibilidade**: Cada interface com suas configuracoes
3. **Robustez**: Sistema de fallback automatico
4. **Manutenibilidade**: Configuracoes organizadas e documentadas

---

## **TESTES E QUALIDADE**

### **Cobertura de Testes por Versao**

#### **v3.0.5 - 67 Testes Passando**
- **Formatacao**: tests/test_formatting.py, tests/test_cli_formatting.py
- **CLI**: tests/test_cli_commands.py, tests/test_table_printer.py
- **GUI**: tests/test_gui_components.py
- **Banco**: tests/test_database.py, tests/test_db_reset_and_upsert.py
- **Exportacao**: tests/test_exporter.py
- **Integridade**: tests/test_column_mappings_integrity.py

#### **Sistema de Validacao**
- **Testes Automatizados**: 67 testes cobrindo funcionalidades principais
- **Smoke Tests**: Verificacao basica de funcionamento
- **Testes de Integracao**: Workflow completo CLI/GUI
- **Testes de Edge Cases**: Larguras extremas, dados malformados

### **Problemas Conhecidos e Resolvidos**

#### **Problema de Encoding (v3.0.5)**
```
PROBLEMA: UnicodeEncodeError com emojis em Windows (cp1252)
SOLUCAO: Substituicao de emojis por caracteres ASCII seguros
STATUS:  Resolvido
```

#### **Conflitos de Configuracao (v3.0.x)**
```
PROBLEMA: GUI e CLI compartilhando configuracoes
SOLUCAO: Isolamento completo com arquivos especificos
STATUS:  Resolvido na v3.0.5+
```

#### **Duplicacao de Colunas no Banco (Detectado)**
```
PROBLEMA: 7 grupos de colunas duplicadas no schema
ANALISE: 4,196 registros duplicados (29.1%)
STATUS:  Identificado, aguardando correcao
```

---

## **ROADMAP FUTURO**

### **v3.0.7 (Proxima)**
- **Prioridade ALTA**: Correcao de duplicatas no banco
- **Melhorias**: Sistema de verificacao de integridade
- **Otimizacoes**: Performance de importacao
- **Documentacao**: Guias atualizados

### **v4.0 (Planejada)**
- **Arquitetura**: Sistema de plugins
- **Interface**: API REST para integracao
- **Web**: Interface web complementar
- **Avancado**: IA para analise de dados

### **Criterios para v4.0**
1. **Estabilidade**: v3.x completamente estavel
2. **Demanda**: Necessidade real de novas funcionalidades
3. **Recursos**: Equipe/tempo para desenvolvimento major
4. **Compatibilidade**: Migracao suave da v3.x

---

## **LICOES APRENDIDAS**

### **Desenvolvimento**
1. **Isolamento e Critico**: Configuracoes compartilhadas causam conflitos
2. **Testes Salvam Tempo**: 67 testes previnem regressoes
3. **Documentacao e Essencial**: Rastreabilidade facilita manutencao
4. **Performance Importa**: Otimizacoes fazem diferenca real

### **Arquitetura**
1. **Modularidade**: Componentes independentes sao mais robustos
2. **Configuracao Flexivel**: Cada interface precisa suas proprias configuracoes
3. **Backward Compatibility**: Manter compatibilidade reduz friction
4. **Fallback Systems**: Sistemas de fallback previnem crashes

### **Qualidade**
1. **Encoding Matters**: Considerar diferentes ambientes desde inicio
2. **Database Integrity**: Verificacoes regulares previnem corrupcao
3. **User Experience**: Pequenos detalhes fazem grande diferenca
4. **Professional Polish**: Remocao de debug messages e essencial

**Ultima Atualizacao**: Setembro 2025  
**Proxima Revisao**: Com release da v3.0.7

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

