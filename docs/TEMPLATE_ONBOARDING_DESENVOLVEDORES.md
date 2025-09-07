# Template de Onboarding para Desenvolvedores - SSA Consulta Rapida

## Guia de Integracao Tecnica para Novos Desenvolvedores

### Informacoes do Projeto
- **Nome**: SSA Consulta Rapida
- **Versao Atual**: v3.10 (estavel e bem documentada)
- **Objetivo**: Sistema de consulta rapida de SSAs (Solicitacoes de Servicos de Apoio)
- **Tecnologia**: Python 3.13+ com PyQt6, SQLite, Pandas

### Estrutura de Onboarding

**PRIMEIRA ETAPA - DOCUMENTACAO ESSENCIAL:**

**Documentos Obrigatorios (em ordem de prioridade):**
1. `README.md` - Visao geral completa do projeto
2. `REGRAS_DE_OURO.md` - Politicas e diretrizes de desenvolvimento
3. `ESTRUTURA_PROJETO.md` - Arquitetura e organizacao do codigo
4. `CHANGELOG_IMPLEMENTACOES.md` - Historico detalhado de mudancas

**Documentos Complementares:**
5. `GUIA_MIGRACAO_NOVA_INSTALACAO.md` - Estado atual e configuracao
6. `GUIA_MODO_OPTIMIZED.md` - Funcionalidades otimizadas implementadas
7. `BUILD_SYSTEM.md` - Sistema de build multi-plataforma
8. `ANALISE_PROBLEMAS_DESENVOLVIMENTO_ANTERIOR.md` - Licoes aprendidas

### Configuracao do Ambiente de Desenvolvimento

**Requisitos do Sistema:**
- Python 3.13+ (obrigatorio)
- Sistema operacional: Windows, macOS ou Linux
- IDE recomendada: VS Code com extensoes Python

**Scripts de Configuracao Automatica:**
```bash
# Windows
./dev_env/bootstrap.ps1

# macOS/Linux  
./dev_env/bootstrap.sh
```

**Verificacao da Instalacao:**
```bash
python verificar_instalacao.py
```

### Componentes Principais do Sistema

**Arquitetura Core:**
- `core/app_logic.py` - Logica principal de coordenacao
- `armazenamento/database.py` - Interface com banco SQLite
- `extracao/extractor.py` - Processamento de dados Excel/Pandas

**Interface de Usuario:**
- `gui/gui_ssa*.py` - Interface grafica PyQt6
- `interface/cli_*.py` - Interface de linha de comando
- `config/*.json` - Configuracoes e mapeamentos

**Sistema de Build:**
- `launchers/build_multiplatform.py` - Build automatizado
- `launchers/platforms/` - Configuracoes por plataforma

### Tarefas de Desenvolvimento Comuns

**Para Importacao e Processamento:**
```bash
# CLI basico
python main.py --import arquivo.xlsx

# CLI com otimizacoes
python main.py --import arquivo.xlsx --optimized

# Interface grafica
python main.py --gui
```

**Para Build e Distribuicao:**
```bash
# Build todas as plataformas
python launchers/build_multiplatform.py --all

# Build especifico
python launchers/build_multiplatform.py --apps gui --platforms windows_amd64
```

### Diretrizes de Desenvolvimento

**Politicas de Codigo:**
1. **Nao modificar** `core/`, `armazenamento/`, `extracao/` sem backup
2. **Sempre testar** em `scripts_desenvolvimento/` antes de implementar
3. **Documentar mudancas** em arquivos .md relevantes
4. **Manter compatibilidade** entre CLI e GUI

**Qualidade e Performance:**
- Remover prints de DEBUG em codigo de producao
- Implementar tratamento robusto de erros
- Usar modo `--optimized` para arquivos grandes
- Manter limpeza adequada de recursos (threads, memoria)

### Referencias Tecnicas

**Configuracoes Criticas:**
- `config/column_mappings.json` - Mapeamento de colunas Excel
- `config/gui_main_preferences.json` - Configuracoes de interface
- `config/default_settings.json` - Configuracoes padrao do sistema

**Scripts de Manutencao:**
- `scripts_manutencao/verificar_integridade.py` - Verificacao do banco
- `scripts_manutencao/debug_*.py` - Scripts de diagnostico
- `tests/` - Suite de testes automatizados

### Historico e Contexto

**Versoes Importantes:**
- **v3.0.4**: Correcao critica do sistema de larguras GUI
- **v3.0.5**: Melhorias significativas no CLI enhanced
- **v3.0.7**: Consolidacao e estabilizacao
- **v3.10**: Sistema de build multi-plataforma e melhorias finais

**Problemas Historicos Resolvidos:**
- Sistema de larguras GUI instavel (corrigido em v3.0.4)
- Performance de importacao (otimizado com modo --optimized)
- Build manual propenso a erros (automatizado em v3.10)

### Proximos Passos Recomendados

1. **Configurar ambiente** usando scripts automaticos
2. **Verificar funcionamento** com `verificar_instalacao.py`
3. **Testar funcionalidades** basicas (importacao, GUI, CLI)
4. **Revisar documentacao** tecnica relevante para sua area de trabalho
5. **Identificar melhorias** usando checklists de pendencias existentes

---
**Documento Tecnico**: Template de Onboarding para Desenvolvedores  
**Versao do Sistema**: v3.10  
**Data de Atualizacao**: 2025-01-28  
**Status**: Documentacao Ativa - Guia de Integracao
