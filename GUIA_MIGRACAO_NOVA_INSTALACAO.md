# 🚀 Guia Completo de Migração - SSA Consulta Rápida v3.0.6

**Data de Criação:** 27 de Agosto de 2025  
**Versão do Sistema:** v3.0.6 (Estável)  
**Tipo:** Migração Completa para Nova Instalação  

---

## 📋 **ÍNDICE**

1. [Pré-requisitos](#pré-requisitos)
2. [Clonagem e Configuração](#clonagem-e-configuração)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Configuração do Ambiente](#configuração-do-ambiente)
5. [Verificação da Instalação](#verificação-da-instalação)
6. [Importação de Dados](#importação-de-dados)
7. [Testes do Sistema](#testes-do-sistema)
8. [Solução de Problemas](#solução-de-problemas)
9. [Arquivos Importantes](#arquivos-importantes)

---

## 🔧 **PRÉ-REQUISITOS**

### **Sistema Operacional**
- ✅ Windows 10/11 (testado)
- ✅ Python 3.8+ (recomendado 3.9+)
- ✅ Git for Windows
- ✅ PowerShell 5.1+ ou PowerShell Core

### **Ferramentas Necessárias**
```powershell
# Verificar versões instaladas
python --version          # Deve ser 3.8+
git --version             # Qualquer versão recente
pip --version             # Incluído com Python
```

---

## 📦 **CLONAGEM E CONFIGURAÇÃO**

### **Passo 1: Clonar o Repositório**
```powershell
# Navegar para o diretório desejado
cd C:\Users\[SEU_USUARIO]\git

# Clonar o repositório
git clone https://github.com/mauriciomenon/SSA_Consulta_Rapida.git

# Entrar na pasta do projeto
cd SSA_Consulta_Rapida
```

### **Passo 2: Verificar Integridade**
```powershell
# Verificar se está na branch correta
git branch -v
# Deve mostrar: * main [commit_hash] [última mensagem]

# Verificar status
git status
# Deve mostrar: "working tree clean"

# Listar arquivos principais
ls main.py, requirements.txt, README.md
```

### **Passo 3: Configurar Ambiente Virtual**
```powershell
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (escolha um dos métodos)
# Método 1 - PowerShell
.\venv\Scripts\Activate.ps1

# Método 2 - CMD/Batch
.\venv\Scripts\activate.bat

# Método 3 - Usar script incluído
.\activate_env.ps1
```

### **Passo 4: Instalar Dependências**
```powershell
# Atualizar pip
python -m pip install --upgrade pip

# Instalar dependências do projeto
pip install -r requirements.txt

# Verificar instalação
pip list
```

---

## 📁 **ESTRUTURA DO PROJETO**

### **Arquivos de Configuração Essenciais**
```
📁 SSA_Consulta_Rapida/
├── 📄 main.py                    # ← PONTO DE ENTRADA PRINCIPAL
├── 📄 main_dev.py               # ← Versão de desenvolvimento
├── 📄 requirements.txt          # ← Dependências Python
├── 📄 README.md                 # ← Documentação principal
├── 📄 GUIA_MODO_OPTIMIZED.md   # ← Guia de otimização
├── 📁 config/
│   ├── 📄 schema.sql            # ← Estrutura do banco
│   └── 📄 gui_*.json           # ← Configurações da GUI
├── 📁 core/                     # ← Lógica principal
├── 📁 armazenamento/           # ← Gestão do banco de dados
├── 📁 interface/               # ← CLI e interfaces
├── 📁 gui/                     # ← Interface gráfica
├── 📁 tests/                   # ← Todos os testes
├── 📁 docs_entrada/            # ← Arquivos Excel (criar se não existir)
└── 📁 data/                    # ← Banco de dados (criado automaticamente)
```

### **Pastas Criadas Automaticamente**
```
📁 data/                        # ← Criada na primeira execução
├── 📄 ssas.db                  # ← Banco principal
├── 📄 file_cache.json         # ← Cache de arquivos
└── 📁 historico_backups/      # ← Backups automáticos
```

---

## ⚙️ **CONFIGURAÇÃO DO AMBIENTE**

### **Passo 1: Ativação Automática do Ambiente**
```powershell
# Usar o script incluído (RECOMENDADO)
.\activate_env.ps1

# Ou criar um atalho personalizado
# Editar activate_env.ps1 se necessário
```

### **Passo 2: Configurar PowerShell (se necessário)**
```powershell
# Se houver erro de política de execução
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verificar política atual
Get-ExecutionPolicy -List
```

### **Passo 3: Verificar Configuração**
```powershell
# Verificar se o ambiente está ativo
python -c "import sys; print('✅ Ambiente ativo:' if 'venv' in sys.path[0] else '❌ Ambiente NÃO ativo')"

# Listar pacotes instalados
pip list | findstr -i "pandas pyqt6 openpyxl"
```

---

## ✅ **VERIFICAÇÃO DA INSTALAÇÃO**

### **Teste 1: Help do Sistema**
```powershell
# Verificar help completo
python main.py --help

# Deve exibir help detalhado com todas as opções
```

### **Teste 2: Verificação da Estrutura**
```powershell
# Verificar módulos principais
python -c "
import sys, os
sys.path.insert(0, '.')
try:
    from core import app_logic
    from armazenamento import database
    from interface import cli
    print('✅ Todos os módulos carregados com sucesso')
except ImportError as e:
    print(f'❌ Erro ao importar: {e}')
"
```

### **Teste 3: Criação do Banco**
```powershell
# Criar estrutura do banco (sem dados)
python main.py --reset-db

# Verificar se o banco foi criado
ls data\ssas.db
```

---

## 📊 **IMPORTAÇÃO DE DADOS**

### **Passo 1: Preparar Arquivos Excel**
```powershell
# Criar pasta se não existir
mkdir docs_entrada -ErrorAction SilentlyContinue

# Verificar estrutura da pasta
ls docs_entrada
```

**Formatos de arquivo suportados:**
- ✅ `.xlsx` (Excel 2007+)
- ✅ `.xls` (Excel 97-2003)
- ✅ Múltiplos arquivos
- ✅ Diferentes estruturas de coluna

### **Passo 2: Importação Inicial**
```powershell
# Importação padrão (primeira vez)
python main.py

# Ou importação otimizada (recomendado para arquivos grandes)
python main.py --optimized

# Ou forçar reimportação completa
python main.py --force-rescan
```

### **Passo 3: Verificar Importação**
```powershell
# Verificar tamanho do banco
ls data\ssas.db | Format-Table Name, Length

# Verificar cache de arquivos
type data\file_cache.json
```

---

## 🧪 **TESTES DO SISTEMA**

### **Teste 1: Interface CLI**
```powershell
# Testar CLI interativo
python main.py

# Comandos de teste na CLI:
# - Digite: help
# - Digite: buscar teste
# - Digite: sair
```

### **Teste 2: Interface Gráfica**
```powershell
# Testar GUI
python main.py --gui

# Verificar funcionalidades:
# - Carregamento da tabela
# - Filtros de busca
# - Ordenação por colunas
```

### **Teste 3: Executar Testes Automatizados**
```powershell
# Executar testes básicos
python -m pytest tests\test_imports.py -v

# Executar teste de banco
python tests\test_db_check.py

# Executar teste de sistema completo
python tests\teste_sistema_completo.py
```

---

## 🔧 **SOLUÇÃO DE PROBLEMAS**

### **Problema: Erro de Dependências**
```powershell
# Reinstalar dependências
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### **Problema: Erro de Permissão no PowerShell**
```powershell
# Alterar política de execução
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Problema: Módulos Não Encontrados**
```powershell
# Verificar PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"

# Executar do diretório correto
cd SSA_Consulta_Rapida
python main.py
```

### **Problema: Banco Corrompido**
```powershell
# Reset completo do banco
python main.py --reset-db

# Limpar cache
del data\file_cache.json

# Reimportar dados
python main.py --force-rescan
```

### **Problema: GUI Não Abre**
```powershell
# Verificar PyQt6
pip install --upgrade PyQt6

# Testar importação
python -c "from PyQt6.QtWidgets import QApplication; print('✅ PyQt6 OK')"
```

---

## 📚 **ARQUIVOS IMPORTANTES PARA LER**

### **1. Documentação Principal**
```powershell
# Ler em ordem de prioridade:
type README.md                           # ← Visão geral do projeto
type GUIA_MODO_OPTIMIZED.md             # ← Otimizações de performance
type CHANGELOG_IMPLEMENTACOES.md        # ← Histórico de mudanças
type REGRAS_DE_OURO.md                  # ← Boas práticas
```

### **2. Configurações e Schema**
```powershell
type config\schema.sql                   # ← Estrutura do banco
type requirements.txt                    # ← Dependências Python
type config\gui_main_preferences.json   # ← Configurações da GUI principal
type config\gui_poc_preferences.json    # ← Configurações da GUI POC
```

### **3. Arquivos de Exemplo e Testes**
```powershell
# Ver exemplos de uso
ls tests\teste_*.py                      # ← Testes de exemplo
type tests\main_test.py                  # ← Teste do main
type tests\test_imports.py               # ← Teste de importação
```

### **4. Scripts de Desenvolvimento**
```powershell
type activate_env.ps1                    # ← Script de ativação
type activate_env.bat                    # ← Alternativa CMD
ls scripts_desenvolvimento\              # ← Ferramentas de desenvolvimento
ls utils\                               # ← Utilitários diversos
```

---

## 🚀 **COMANDOS RÁPIDOS DE REFERÊNCIA**

### **Inicialização Diária**
```powershell
# Sequência completa de inicialização
cd C:\Users\[SEU_USUARIO]\git\SSA_Consulta_Rapida
.\activate_env.ps1
python main.py
```

### **Manutenção Semanal**
```powershell
# Atualizar repositório
git pull

# Limpar dados antigos
python main.py --clean-data

# Teste rápido
python main.py --help
```

### **Reimportação Completa**
```powershell
# Quando houver mudanças significativas nos dados
python main.py --reset-db
python main.py --optimized --force-rescan
```

---

## 📞 **SUPORTE E DOCUMENTAÇÃO**

### **Logs do Sistema**
```powershell
# Verificar logs (se habilitados)
ls logs\                                # ← Pasta de logs
type logs\ssa.log                       # ← Log principal
```

### **Arquivos de Estado**
```powershell
type data\file_cache.json               # ← Estado dos arquivos
ls data\historico_backups\              # ← Backups disponíveis
```

### **Informações de Debug**
```powershell
# Executar com log detalhado
python main.py --log-level DEBUG

# Verificar configuração do sistema
python -c "
import sys, platform, sqlite3
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'SQLite: {sqlite3.sqlite_version}')
"
```

---

## ⚠️ **NOTAS IMPORTANTES**

1. **🔒 Backup**: O sistema cria backups automáticos antes de operações destrutivas
2. **📊 Performance**: Use `--optimized` para arquivos grandes (>5MB)
3. **🖥️ GUI**: A interface gráfica requer PyQt6 funcionando
4. **📁 Estrutura**: Não altere a estrutura de pastas sem necessidade
5. **🔄 Cache**: O cache acelera reimportações, mas pode ser limpo se necessário

---

## ✅ **CHECKLIST FINAL**

- [ ] Repositório clonado com sucesso
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas
- [ ] Help do sistema funcionando
- [ ] Banco de dados criado
- [ ] Importação de dados testada
- [ ] CLI funcionando
- [ ] GUI funcionando (se necessário)
- [ ] Testes básicos executados

**Se todos os itens estão marcados, a migração foi bem-sucedida! 🎉**

---

*Última atualização: 27/08/2025 - v3.0.6*
*Para dúvidas ou problemas, consulte o repositório no GitHub*
