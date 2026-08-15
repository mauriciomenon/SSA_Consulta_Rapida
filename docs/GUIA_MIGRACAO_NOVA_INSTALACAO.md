# Guia Completo de Migracao - SSA Consulta Rapida v4.44

**Data de Criacao:** 27 de Agosto de 2025
**Versao do Sistema:** v4.44 (Baseline local)
**Tipo:** Migracao Completa para Nova Instalacao
**Sync:** 06/07/2026 09:45 -0300

---

## INDICE

1. [Pre-requisitos](#pre-requisitos)
2. [Clonagem e Configuracao](#clonagem-e-configuracao)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Configuracao do Ambiente](#configuracao-do-ambiente)
5. [Verificacao da Instalacao](#verificacao-da-instalacao)
6. [Importacao de Dados](#importacao-de-dados)
7. [Testes do Sistema](#testes-do-sistema)
8. [Solucao de Problemas](#solucao-de-problemas)
9. [Arquivos Importantes](#arquivos-importantes)

---

## PRE-REQUISITOS

### **Sistema Operacional**
- Windows 10/11 (testado)
- Python 3.10+ (preferir 3.13+)
- Git for Windows
- PowerShell 5.1+ ou PowerShell Core

### **Ferramentas Necessarias**
```powershell
# Verificar versoes instaladas
uv --version             # uv instalado e acessivel no PATH
uv run --python 3.13 python --version   # Runtime preferencial
uv run --python 3.12 python --version   # Fallback 1 se 3.13 nao existir
git --version             # Qualquer versao recente
uv pip --version          # Gerenciado pelo uv
```

---

## CLONAGEM E CONFIGURACAO

### **Passo 1: Clonar o Repositorio**
```powershell
# Navegar para o diretorio desejado
cd C:\Users\[SEU_USUARIO]\git

# Clonar o repositorio
git clone https://github.com/mauriciomenon/SSA_Consulta_Rapida.git

# Entrar na pasta do projeto
cd SSA_Consulta_Rapida
```

### **Passo 2: Verificar Integridade**
```powershell
# Verificar se esta na branch correta
git branch -v
# Deve mostrar branch valida do seu fluxo (ex.: main/dev/feature em andamento)

# Verificar status
git status
# Deve mostrar: "working tree clean"

# Listar arquivos principais
ls main.py, requirements.txt, README.md
```

### **Passo 3: Configurar Ambiente Virtual**
```powershell
# Fluxo recomendado (uv-first)
# OBS: usando uv run, nao e necessario ativar venv manualmente
uv venv
uv sync

# Definir runtime com fallback explicito
# Ordem recomendada: 3.13 -> 3.12 -> 3.11 -> 3.10
$PY_RUNTIME = "3.13"
uv run --python $PY_RUNTIME python --version

# Opcional: fluxo manual sem uv (apenas fallback)
python -m venv .venv

# Ativar ambiente (apenas para fluxo manual fallback)
# Metodo 1 - PowerShell
.\.venv\Scripts\Activate.ps1

# Metodo 2 - CMD/Batch
.\.venv\Scripts\activate.bat

# Metodo 3 - Usar script incluido
.\activate_env.ps1
```

### **Passo 4: Instalar Dependencias**
```powershell
# Fluxo recomendado (uv-first)
uv sync

# Compatibilidade sem uv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Verificar instalacao
python -m pip list
```

---

## ESTRUTURA DO PROJETO

### **Arquivos de Configuracao Essenciais**
```
SSA_Consulta_Rapida/
├── main.py                    # ← PONTO DE ENTRADA PRINCIPAL
├── main_dev.py               # ← Versao de desenvolvimento
├── requirements.txt          # ← Dependencias Python
├── README.md                 # ← Documentacao principal
├── GUIA_MODO_OPTIMIZED.md   # ← Guia de otimizacao
├── config/
│   ├── schema.sql            # ← Estrutura do banco
│   └── gui_*.json           # ← Configuracoes da GUI
├── core/                     # ← Logica principal
├── armazenamento/           # ← Gestao do banco de dados
├── interface/               # ← CLI e interfaces
├── gui/                     # ← Interface grafica
├── tests/                   # ← Todos os testes
├── docs_entrada/            # ← Arquivos Excel (criar se nao existir)
└── data/                    # ← Banco de dados (criado automaticamente)
```

### **Pastas Criadas Automaticamente**
```
data/                        # ← Criada na primeira execucao
├── ssas.db                  # ← Banco principal
├── file_cache.json         # ← Cache de arquivos
└── historico_backups/      # ← Backups automaticos
```

---

## **CONFIGURACAO DO AMBIENTE**

### **Passo 1: Ativacao Automatica do Ambiente**
```powershell
# Usar o script incluido (RECOMENDADO)
.\activate_env.ps1

# Ou criar um atalho personalizado
# Editar activate_env.ps1 se necessario
```

### **Passo 2: Configurar PowerShell (se necessario)**
```powershell
# Se houver erro de politica de execucao
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verificar politica atual
Get-ExecutionPolicy -List
```

### **Passo 3: Verificar Configuracao**
```powershell
# Verificar se o ambiente esta ativo
python -c "import sys; in_venv = sys.prefix != sys.base_prefix; print('Ambiente ativo:' if in_venv else 'Ambiente NAO ativo')"

# Listar pacotes instalados
python -m pip list | findstr -i "pandas pyqt6 openpyxl"
```

---

## VERIFICACAO DA INSTALACAO

### **Teste 1: Help do Sistema**
```powershell
# Verificar help completo (uv-first)
uv run --python $PY_RUNTIME main.py --help

# Fallback manual sem uv
python main.py --help

# Deve exibir help detalhado com todas as opcoes
```

### **Teste 2: Verificacao da Estrutura**
```powershell
# Verificar modulos principais (uv-first)
uv run --python $PY_RUNTIME python -c "
import sys, os
sys.path.insert(0, '.')
try:
    from core import app_logic
    from armazenamento import database
    from interface import cli
    print('Todos os modulos carregados com sucesso')
except ImportError as e:
    print(f'Erro ao importar: {e}')
"

# Fallback manual sem uv
python -c "
import sys, os
sys.path.insert(0, '.')
try:
    from core import app_logic
    from armazenamento import database
    from interface import cli
    print('Todos os modulos carregados com sucesso')
except ImportError as e:
    print(f'Erro ao importar: {e}')
"
```

### **Teste 3: Criacao do Banco**
```powershell
# Criar estrutura do banco (sem dados, uv-first)
uv run --python $PY_RUNTIME main.py --reset-db

# Fallback manual sem uv
python main.py --reset-db

# Verificar se o banco foi criado
ls data\ssas.db
```

---

---

## **IMPORTACAO DE DADOS**

### **Comando Basico de Importacao**
```powershell
# Criar pasta se nao existir
mkdir docs_entrada -ErrorAction SilentlyContinue

# Verificar estrutura da pasta
ls docs_entrada
```

**Formatos de arquivo suportados:**
- `.xlsx` (Excel 2007+)
- `.xls` (Excel 97-2003)
- Multiplos arquivos
- Diferentes estruturas de coluna

**Fluxo seguro pela GUI (`Importar XLS/XLSX externo`):**
- voce pode selecionar um ou mais `.xlsx` de qualquer pasta local
- cada arquivo selecionado e copiado para `docs_entrada` quando ainda estiver fora dessa pasta
- se o arquivo ja estiver em `docs_entrada`, ele e reaproveitado sem copia duplicada
- a atualizacao no banco e aplicada somente para os arquivos explicitamente selecionados nessa acao

### **Passo 2: Importacao Inicial**
```powershell
# Importacao padrao (primeira vez, uv-first)
uv run --python $PY_RUNTIME main.py

# Fallback manual sem uv
python main.py

# Ou importacao otimizada (recomendado para arquivos grandes, uv-first)
uv run --python $PY_RUNTIME main.py --optimized

# Fallback manual sem uv
python main.py --optimized

# Ou forcar reimportacao completa (uv-first)
uv run --python $PY_RUNTIME main.py --force-rescan

# Fallback manual sem uv
python main.py --force-rescan
```

### **Passo 3: Verificar Importacao**
```powershell
# Verificar tamanho do banco
ls data\ssas.db | Format-Table Name, Length

# Verificar cache de arquivos
type data\file_cache.json
```

---

## TESTES DO SISTEMA

### **Teste 1: Interface CLI**
```powershell
# Testar CLI interativo (uv-first)
uv run --python $PY_RUNTIME main.py

# Fallback manual sem uv
python main.py

# Comandos de teste na CLI:
# - Digite: help
# - Digite: buscar teste
# - Digite: sair
```

### **Teste 2: Interface Grafica**
```powershell
# Testar GUI (uv-first)
uv run --python $PY_RUNTIME main.py --gui

# Fallback manual sem uv
python main.py --gui

# Verificar funcionalidades:
# - Carregamento da tabela
# - Filtros de busca
# - Ordenacao por colunas
```

### **Teste 3: Executar Testes Automatizados**
```powershell
# Executar testes basicos (uv-first)
uv run --python $PY_RUNTIME -m pytest tests\test_imports.py -v

# Fallback manual sem uv
python -m pytest tests\test_imports.py -v

# Executar teste de banco (uv-first)
uv run --python $PY_RUNTIME -m pytest tests\test_database.py -q

# Fallback manual sem uv
python -m pytest tests\test_database.py -q

# Executar teste de sistema completo
uv run --python $PY_RUNTIME python tests\teste_sistema_completo.py
```

---

## SOLUCAO DE PROBLEMAS

### **Problema: Erro de Dependencias**
```powershell
# Reinstalar dependencias
uv pip uninstall --python $PY_RUNTIME -r requirements.txt -y
uv pip install --python $PY_RUNTIME -r requirements.txt
```

### **Problema: Erro de Permissao no PowerShell**
```powershell
# Alterar politica de execucao
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Problema: Modulos Nao Encontrados**
```powershell
# Verificar PYTHONPATH
uv run --python $PY_RUNTIME python -c "import sys; print('\n'.join(sys.path))"

# Executar do diretorio correto
cd SSA_Consulta_Rapida
uv run --python $PY_RUNTIME main.py
```

### **Problema: Banco Corrompido**
```powershell
# Reset completo do banco
uv run --python $PY_RUNTIME main.py --reset-db

# Limpar cache
del data\file_cache.json

# Reimportar dados
uv run --python $PY_RUNTIME main.py --force-rescan
```

### **Problema: GUI Nao Abre**
```powershell
# Verificar PyQt6
uv pip install --python $PY_RUNTIME --upgrade PyQt6

# Testar importacao
uv run --python $PY_RUNTIME python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

---

##  **ARQUIVOS IMPORTANTES PARA LER**

### **1. Documentacao Principal**
```powershell
# Ler em ordem de prioridade:
type README.md                           # ← Visao geral do projeto
type GUIA_MODO_OPTIMIZED.md             # ← Otimizacoes de performance
type CHANGELOG_IMPLEMENTACOES.md        # ← Historico de mudancas
type REGRAS_DE_OURO.md                  # ← Boas praticas
```

### **2. Configuracoes e Schema**
```powershell
type config\schema.sql                   # ← Estrutura do banco
type requirements.txt                    # ← Dependencias Python
type config\gui_main_preferences.json   # ← Configuracoes da GUI principal
type config\gui_poc_preferences.json    # ← Configuracoes da GUI POC
```

### **3. Arquivos de Exemplo e Testes**
```powershell
# Ver exemplos de uso
ls tests\teste_*.py                      # ← Testes de exemplo
type tests\main_test.py                  # ← Teste do main
type tests\test_imports.py               # ← Teste de importacao
```

### **4. Scripts de Desenvolvimento**
```powershell
type activate_env.ps1                    # ← Script de ativacao
type activate_env.bat                    # ← Alternativa CMD
ls scripts_desenvolvimento\              # ← Ferramentas de desenvolvimento
ls utils\                               # ← Utilitarios diversos
```

---

## **COMANDOS RAPIDOS DE REFERENCIA**

### **Inicializacao Diaria**
```powershell
# Sequencia completa de inicializacao
cd C:\Users\[SEU_USUARIO]\git\SSA_Consulta_Rapida
.\activate_env.ps1
uv run --python $PY_RUNTIME main.py
```

### **Manutencao Semanal**
```powershell
# Atualizar repositorio
git pull

# Limpar dados antigos
uv run --python $PY_RUNTIME main.py --clean-data

# Teste rapido
uv run --python $PY_RUNTIME main.py --help
```

### **Reimportacao Completa**
```powershell
# Quando houver mudancas significativas nos dados
uv run --python $PY_RUNTIME main.py --reset-db
uv run --python $PY_RUNTIME main.py --optimized --force-rescan
```

---

##  **SUPORTE E DOCUMENTACAO**

### **Logs do Sistema**
```powershell
# Verificar logs (se habilitados)
ls logs\                                # ← Pasta de logs
type logs\ssa.log                       # ← Log principal
```

### **Arquivos de Estado**
```powershell
type data\file_cache.json               # ← Estado dos arquivos
ls data\historico_backups\              # ← Backups disponiveis
```

### **Informacoes de Debug**
```powershell
# Executar com log detalhado
uv run --python $PY_RUNTIME main.py --log-level DEBUG

# Verificar configuracao do sistema
uv run --python $PY_RUNTIME python -c "
import sys, platform, sqlite3
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'SQLite: {sqlite3.sqlite_version}')
"
```

---

---

## **NOTAS IMPORTANTES**

1. **Backup**: Sempre faca backup antes de usar em producao
2. **Performance**: Use `--optimized` para arquivos grandes (>5MB)
3. **GUI**: A interface grafica requer PyQt6 funcionando

---

## CHECKLIST FINAL

- [ ] Repositorio clonado com sucesso
- [ ] Ambiente virtual criado e ativado
- [ ] Dependencias instaladas
- [ ] Help do sistema funcionando
- [ ] Banco de dados criado
- [ ] Importacao de dados testada
- [ ] CLI funcionando
- [ ] GUI funcionando (se necessario)
- [ ] Testes basicos executados

**Se todos os itens estao marcados, a migracao foi bem-sucedida!**

---

*Ultima atualizacao: 06/07/2026 - v4.44*
*Para duvidas ou problemas, consulte o repositorio no GitHub*


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
