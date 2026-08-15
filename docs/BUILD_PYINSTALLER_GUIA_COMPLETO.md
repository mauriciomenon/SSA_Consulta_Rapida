# Guia Completo (Historico/Referencia) - Build com PyInstaller

## CURRENT TRUTH (baseline v4.43)

- Sync deste guia: `2026-04-15 15:45 -0300`.
- Caminho operacional principal:
  - build: `uv run --python 3.13 launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui`
  - artefatos: `launchers/dist/windows_amd64/`
  - distribuicao: `uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller`
- Referencias a `build_pyinstaller.bat` e `builds/pyinstaller` neste arquivo sao historicas.
- Para fluxo atual, usar `launchers/dist/*` como fonte canonica.
- Sempre que houver conflito entre exemplos antigos e o pipeline atual, prevalece `launchers/dist/*`.
- Validacao 2026-03-10 (host macOS arm64):
  - `pyinstaller --version` OK (`6.19.0`)
  - `uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller --skip-installer` gerou ZIP com sucesso
  - `uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller` gerou ZIP, mas installer falhou por ausencia de origem Windows/Inno no host atual
- `pytoexe`/`py2exe` nao fazem parte do backend suportado deste repo.

## HISTORICAL SNAPSHOT NOTICE

Este documento preserva detalhes de troubleshooting historico.
Quando houver conflito, prevalece o bloco CURRENT TRUTH acima.

## ATENCAO OPERACIONAL

- ESTE ARQUIVO E REFERENCIA HISTORICA.
- NAO USAR ESTE RUNBOOK COMO FLUXO PRINCIPAL DE RELEASE.
- PARA OPERACAO ATUAL, USAR:
  - `uv run --python 3.13 launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui`
  - `uv run --python 3.13 scripts/create_distribution.py --build-system pyinstaller`

**Data historica original do snapshot preservado**: 2025-11-14

> Nota: a data historica acima pertence ao material preservado. O status
> operacional atual deste guia fica no bloco `CURRENT TRUTH`.

**Autor**: Claude Code
**Projeto**: SSA_Consulta_Rapida v4.43
**Sistema Operacional**: Windows 10/11
**Ambiente**: MSYS2 UCRT64 / CMD / PowerShell

---

## INDICE

1. [Introducao](#introducao)
2. [Pre-requisitos](#pre-requisitos)
3. [Instalacao do PyInstaller](#instalacao-do-pyinstaller)
4. [Configuracao do Ambiente](#configuracao-do-ambiente)
5. [Estrutura do Projeto](#estrutura-do-projeto)
6. [Arquivo de Configuracao](#arquivo-de-configuracao)
7. [Processo de Build Passo a Passo](#processo-de-build-passo-a-passo)
8. [Analise da Saida](#analise-da-saida)
9. [Otimizacoes Aplicadas](#otimizacoes-aplicadas)
10. [Erros Comuns e Solucoes](#erros-comuns-e-solucoes)
11. [Licoes Aprendidas](#licoes-aprendidas)
12. [Troubleshooting Avancado](#troubleshooting-avancado)
13. [Comparacao com Outros Build Systems](#comparacao-com-outros-build-systems)
14. [Referencias](#referencias)

---

## INTRODUCAO

PyInstaller e uma ferramenta madura e amplamente utilizada para converter aplicacoes Python em executaveis standalone. Ele funciona empacotando o interpretador Python completo junto com todas as dependencias da aplicacao em um unico diretorio ou arquivo executavel.

### Por que PyInstaller?

- **Maturidade**: Desenvolvimento ativo desde 2005
- **Compatibilidade**: Suporta Python 3.8-3.13
- **Simplicidade**: Configuracao relativamente simples
- **Comunidade**: Grande base de usuarios e documentacao extensa
- **Multiplataforma**: Windows, Linux, macOS

### Quando Usar PyInstaller

Use PyInstaller quando:
- Precisa de build rapido (2-3 minutos)
- Quer maxima compatibilidade com bibliotecas Python
- Tamanho do executavel nao e critico (aceita 30-50 MB)
- Precisa de debugging facil
- Trabalha com dependencias complexas (PyQt, numpy, pandas)

### Quando NAO Usar PyInstaller

Evite PyInstaller quando:
- Tamanho e critico (< 20 MB)
- Precisa de performance maxima de startup
- Quer compilacao nativa para C
- Precisa de distribuicao em ambiente com restricoes de tamanho

---

## PRE-REQUISITOS

### Sistema Operacional

- **Windows**: 10 ou 11 (64-bit)
- **Permissoes**: Usuario padrao (nao precisa admin para build)
- **Espaco em Disco**: 500 MB livres para build completo

### Python

```
Versao: 3.13.12 (recomendado) ou 3.8-3.13
Gerenciador: pyenv-win (recomendado) ou instalacao manual
Localizacao: C:\Users\menon\.pyenv\pyenv-win\
```

**Verificacao**:
```bash
python --version
# Saida esperada: Python 3.13.12

which python
# Saida esperada: /c/Users/menon/.pyenv/pyenv-win/shims/python
```

### Ferramentas de Desenvolvimento

**Opcional mas recomendado**:
- Git for Windows 2.40+
- Visual Studio Code
- Windows Terminal
- MSYS2 UCRT64 (para ferramentas Unix)

### Dependencias Python do Projeto

Todas instaladas via requirements.txt:

```
pandas>=2.0.0
openpyxl>=3.1.0
PyQt6>=6.5.0
streamlit>=1.28.0
plotly>=5.18.0
tabulate>=0.9.0
python-dotenv>=1.0.0
```

**Instalacao**:
```bash
pip install -r requirements.txt
```

---

## INSTALACAO DO PYINSTALLER

### Metodo 1: Via pip (Recomendado)

```bash
pip install pyinstaller==6.16.0
```

### Metodo 2: Via requirements_build.txt

```bash
pip install -r requirements_build.txt
```

Conteudo de requirements_build.txt:
```
pyinstaller==6.16.0
pyinstaller-hooks-contrib>=2024.0
```

### Verificacao da Instalacao

```bash
pyinstaller --version
# Saida esperada: 6.16.0

which pyinstaller
# Saida esperada: /c/Users/menon/.pyenv/pyenv-win/shims/pyinstaller
```

### Modulos Adicionais

PyInstaller instala automaticamente:
- **pyinstaller-hooks-contrib**: Hooks para bibliotecas populares
- **altgraph**: Analise de dependencias
- **pefile**: Manipulacao de arquivos PE (Windows)
- **pywin32-ctypes**: Integracao com Windows API

---

## CONFIGURACAO DO AMBIENTE

### PATH

Certifique-se de que Python esta no PATH:

```bash
echo $PATH | tr ':' '\n' | grep python
```

Saida esperada:
```
/c/Users/menon/.pyenv/pyenv-win/bin
/c/Users/menon/.pyenv/pyenv-win/shims
```

### Variaveis de Ambiente

Nenhuma variavel especial necessaria. PyInstaller usa:
- `TEMP` ou `TMP` para arquivos temporarios
- `PATH` para encontrar Python e ferramentas

### Configuracao do Antivirus

**CRITICO**: Windows Defender e outros antivirus podem bloquear PyInstaller.

**Adicionar exclusoes**:

Via PowerShell (Admin):
```powershell
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\build"
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\dist"
```

Via Interface:
1. Windows Security > Virus & threat protection
2. Manage settings > Add or remove exclusions
3. Adicionar pastas: build/, dist/

**Verificar exclusoes**:
```powershell
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

---

## ESTRUTURA DO PROJETO

### Arvore de Diretorios

```
SSA_Consulta_Rapida/
|
|-- main.py                      # Entry point da aplicacao
|-- requirements.txt              # Dependencias runtime
|-- requirements_build.txt        # Dependencias build
|
|-- core/                         # Modulos principais
|   |-- __init__.py
|   |-- database.py
|   |-- queries.py
|   |-- version.py
|
|-- gui/                          # Interface PyQt6
|   |-- __init__.py
|   |-- main_window.py
|   |-- dialogs/
|   |-- widgets/
|
|-- extracao/                     # Extracao de dados
|   |-- __init__.py
|   |-- excel_extractor.py
|
|-- exportacao/                   # Exportacao resultados
|   |-- __init__.py
|   |-- pdf_exporter.py
|   |-- excel_exporter.py
|
|-- config/                       # Configuracoes e schemas
|   |-- schema.sql
|   |-- settings.json
|
|-- data/                         # Banco de dados
|   |-- ssas.db
|
|-- docs/                         # Documentacao
|-- tests/                        # Testes unitarios
|
|-- build_pyinstaller.bat         # Script de build
|-- pyinstaller.spec              # Arquivo spec (gerado)
|
|-- build/                        # Temporario (gitignored)
|-- dist/                         # Temporario (gitignored)
|-- builds/                       # Builds finais
    |-- pyinstaller/
        |-- SSA_Consulta_Rapida.exe
        |-- _internal/            # Dependencias
```

### Modulos Criticos

**main.py**:
- Entry point principal
- Parse de argumentos CLI
- Inicializacao do banco de dados
- Lancamento da GUI ou CLI

**core/version.py**:
```python
APP_VERSION = "4.43"
APP_NAME = "SSA Consulta Rapida"
```

**gui/main_window.py**:
- Interface PyQt6 principal
- Gerenciamento de janelas
- Comunicacao com backend

---

## ARQUIVO DE CONFIGURACAO

### Script build_pyinstaller.bat

Conteudo completo:

```batch
REM HISTORICO: este trecho usa layout antigo em builds/pyinstaller
@echo off
REM Build script para PyInstaller 6.16.0
REM Autor: Claude Code
REM Data: 2025-11-14

echo Iniciando build com PyInstaller...
echo.

REM Limpar builds anteriores
if exist build\pyinstaller rmdir /s /q build\pyinstaller
if exist dist\SSA_Consulta_Rapida rmdir /s /q dist\SSA_Consulta_Rapida
if exist SSA_Consulta_Rapida.spec del /q SSA_Consulta_Rapida.spec

echo Limpeza concluida.
echo.

REM Build com PyInstaller
pyinstaller ^
    --name="SSA_Consulta_Rapida" ^
    --windowed ^
    --onedir ^
    --add-data="config;config" ^
    --add-data="data;data" ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=plotly ^
    --hidden-import=streamlit ^
    --collect-all=pandas ^
    --collect-all=openpyxl ^
    --collect-all=PyQt6 ^
    --icon=icon.ico ^
    --version-file=version_info.txt ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo.
    echo Criando estrutura em builds/pyinstaller/
    if not exist builds\pyinstaller mkdir builds\pyinstaller
    xcopy /E /I /Y dist\SSA_Consulta_Rapida\* builds\pyinstaller\
    echo.
    echo Executavel em: builds\pyinstaller\SSA_Consulta_Rapida.exe
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

pause
```

### Parametros Explicados

**--name="SSA_Consulta_Rapida"**
- Nome do executavel final
- Define nome da pasta em dist/

**--windowed**
- Nao abre console Windows
- Use `--console` para debug (ver prints/errors)

**--onedir**
- Cria diretorio com exe + dependencias
- Alternativa: `--onefile` (um unico exe, mais lento)

**--add-data="config;config"**
- Sintaxe: `fonte;destino`
- Copia pasta config/ para dentro do build
- Separador `;` no Windows, `:` no Linux

**--hidden-import=pandas**
- Forca importacao de modulo
- Necessario quando import e dinamico (importlib, __import__)

**--collect-all=PyQt6**
- Coleta TODOS arquivos do pacote
- Inclui: plugins, DLLs, recursos

**--icon=icon.ico**
- Define icone do exe
- Formato: ICO (Windows), ICNS (macOS)

**--version-file=version_info.txt**
- Metadata do executavel
- Visivel em propriedades do arquivo

### Arquivo pyinstaller.spec (Gerado)

Apos primeiro build, PyInstaller cria `SSA_Consulta_Rapida.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config', 'config'), ('data', 'data')],
    hiddenimports=['pandas', 'openpyxl', 'PyQt6', ...],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SSA_Consulta_Rapida',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SSA_Consulta_Rapida',
)
```

**Personalizacao do spec**:

Edite `SSA_Consulta_Rapida.spec` e rode:
```bash
pyinstaller SSA_Consulta_Rapida.spec
```

---

## PROCESSO DE BUILD PASSO A PASSO

### Passo 1: Preparacao

```bash
# Navegar para diretorio do projeto
cd c:/Users/menon/git/SSA_Consulta_Rapida

# Verificar Python
python --version

# Verificar PyInstaller
pyinstaller --version

# Verificar dependencias
pip list | grep -E "(pandas|PyQt6|openpyxl)"
```

### Passo 2: Limpeza de Builds Anteriores

```bash
# Remover builds antigos
rm -rf build/ dist/ *.spec

# Ou usar script batch
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
```

**Por que limpar?**
- Evita conflitos de versoes antigas
- Libera espaco em disco
- Garante build limpo

### Passo 3: Executar Build

**Via Batch (Recomendado)**:
```batch
build_pyinstaller.bat
```

**Via Linha de Comando**:
```bash
pyinstaller --name="SSA_Consulta_Rapida" --windowed --onedir \
    --add-data="config;config" \
    --hidden-import=pandas \
    --hidden-import=PyQt6 \
    main.py
```

### Passo 4: Monitorar Progresso

PyInstaller mostra:

```
1 INFO: PyInstaller: 6.16.0
2 INFO: Python: 3.13.12
3 INFO: Platform: Windows-10-10.0.26100-SP0
...
100 INFO: Analyzing main.py
150 INFO: Processing module hooks...
200 INFO: Looking for dynamic libraries...
250 INFO: Collecting submodules...
300 INFO: Building PKG (CArchive)...
350 INFO: Building EXE from EXE-00.toc
400 INFO: Building COLLECT SSA_Consulta_Rapida
```

Tempo tipico: **2-3 minutos**

### Passo 5: Verificar Saida

```bash
# Listar conteudo de dist/
ls -lh dist/SSA_Consulta_Rapida/

# Ver tamanho total
du -sh dist/SSA_Consulta_Rapida/
# Esperado: ~380-400 MB
```

### Passo 6: Copiar para builds/

```bash
# Criar estrutura
mkdir -p builds/pyinstaller

# Copiar tudo
cp -r dist/SSA_Consulta_Rapida/* builds/pyinstaller/

echo "Build copiado para builds/pyinstaller/"
```

### Passo 7: Testar Executavel

```bash
cd builds/pyinstaller

# Teste 1: Versao
./SSA_Consulta_Rapida.exe --version
# Esperado: 4.43

# Teste 2: Help
./SSA_Consulta_Rapida.exe --help

# Teste 3: GUI
./SSA_Consulta_Rapida.exe --gui
```

---

## ANALISE DA SAIDA

### Estrutura de dist/SSA_Consulta_Rapida/

```
SSA_Consulta_Rapida/
|
|-- SSA_Consulta_Rapida.exe      # Executavel principal (25 MB)
|
|-- _internal/                    # Dependencias (360 MB)
    |
    |-- python313.dll             # Interpretador Python (4 MB)
    |-- _ssl.pyd                  # Modulos C compilados
    |-- Qt6Core.dll               # PyQt6 DLLs (30 MB)
    |-- Qt6Gui.dll                # (25 MB)
    |-- Qt6Widgets.dll            # (20 MB)
    |
    |-- pandas/                   # Bibliotecas Python
    |-- openpyxl/
    |-- PyQt6/
    |-- numpy/
    |-- plotly/
    |
    |-- config/                   # Dados copiados
    |   |-- schema.sql
    |   |-- settings.json
    |
    |-- data/                     # Banco de dados
    |   |-- ssas.db
    |
    |-- base_library.zip          # Stdlib Python comprimido (10 MB)
```

### Tamanhos Detalhados

```bash
cd dist/SSA_Consulta_Rapida

# Tamanho do executavel
ls -lh SSA_Consulta_Rapida.exe
# 25 MB

# Maiores componentes em _internal/
du -sh _internal/* | sort -h | tail -10

# PyQt6 DLLs: 150 MB
# pandas + numpy: 80 MB
# Python stdlib: 40 MB
# Outros: 90 MB
```

### Arquivos Criticos

**Nao podem ser removidos**:
- SSA_Consulta_Rapida.exe
- python313.dll
- Qt6*.dll
- base_library.zip
- Pasta config/
- Pasta data/

**Podem ser removidos** (se nao usados):
- Qt6Network.dll (se nao usar rede)
- Qt6Multimedia.dll (se nao usar audio/video)
- Arquivos .pyc em modulos nao usados

---

## OTIMIZACOES APLICADAS

### 1. --onedir vs --onefile

**--onedir** (Usado):
- Startup rapido (1-2 segundos)
- Tamanho: 380 MB (descomprimido)
- Facil debug (ver arquivos internos)

**--onefile**:
- Startup lento (5-10 segundos)
- Tamanho: 80 MB (comprimido)
- Extrai tudo para TEMP a cada execucao

**Decisao**: --onedir para melhor UX

### 2. UPX Compression

**Habilitado por padrao** via `upx=True` no spec.

UPX comprime executavel:
- Sem UPX: 40 MB
- Com UPX: 25 MB
- Economia: 37%

**Trade-off**:
- Menor tamanho
- Startup ligeiramente mais lento (decompressao)
- Alguns antivirus detectam UPX como suspeito

**Desabilitar UPX**:
```python
# No arquivo .spec
exe = EXE(
    ...
    upx=False,
)
```

### 3. Hidden Imports

Importacoes explicitas evitam erro runtime:

```python
--hidden-import=pandas
--hidden-import=pandas.core
--hidden-import=pandas.io.formats.excel
```

**Como descobrir hidden imports faltando**:
1. Rodar executavel
2. Ver erro: `ModuleNotFoundError: No module named 'X'`
3. Adicionar `--hidden-import=X`
4. Rebuild

### 4. Collect-all

`--collect-all=PyQt6` garante que:
- Plugins Qt (platforms/, styles/) sao incluidos
- DLLs adicionais sao copiadas
- Recursos (icones, traducoes) vem junto

Sem `--collect-all`, erro comum:
```
This application failed to start because no Qt platform plugin could be initialized.
```

### 5. Exclude Modules

**Nao usado neste projeto**, mas util para reduzir tamanho:

```python
# No arquivo .spec
a = Analysis(
    ...
    excludes=['tkinter', 'unittest', 'pydoc'],
)
```

Modulos grandes raramente usados:
- tkinter (GUI alternativa)
- unittest (testes)
- pydoc (documentacao)

---

## ERROS COMUNS E SOLUCOES

### Erro 1: "PyInstaller is not recognized"

**Sintoma**:
```
'pyinstaller' is not recognized as an internal or external command
```

**Causa**: PyInstaller nao esta no PATH

**Solucao**:
```bash
# Verificar instalacao
pip show pyinstaller

# Reinstalar
pip install --force-reinstall pyinstaller==6.16.0

# Usar caminho completo
python -m PyInstaller main.py
```

### Erro 2: "Failed to execute script main"

**Sintoma**:
Executavel abre e fecha imediatamente

**Causa**: Excecao nao capturada no codigo

**Solucao**:
```bash
# Build com console habilitado para ver erro
pyinstaller --console main.py

# Executar e ler mensagem de erro
./dist/main/main.exe
```

Erros comuns revelados:
- Arquivo config nao encontrado
- Biblioteca compartilhada faltando
- Import dinamico falhou

### Erro 3: "No module named 'X'"

**Sintoma**:
```
ModuleNotFoundError: No module named 'pandas.core.computation'
```

**Causa**: Modulo importado dinamicamente nao foi detectado

**Solucao**:
```bash
# Adicionar hidden import
pyinstaller --hidden-import=pandas.core.computation main.py

# Ou collect-all
pyinstaller --collect-all=pandas main.py
```

### Erro 4: Qt Platform Plugin Error

**Sintoma**:
```
This application failed to start because no Qt platform plugin could be initialized.
Available platforms: windows
```

**Causa**: Plugins Qt nao foram copiados

**Solucao**:
```bash
# Collect-all PyQt6
pyinstaller --collect-all=PyQt6 main.py

# Ou copiar manualmente plugins
cp -r /path/to/PyQt6/Qt6/plugins dist/app/_internal/
```

### Erro 5: DLL Load Failed

**Sintoma**:
```
ImportError: DLL load failed while importing _sqlite3
```

**Causa**: DLL do sistema nao encontrada

**Solucao**:
```bash
# Adicionar binary especifico
pyinstaller --add-binary="C:/Windows/System32/sqlite3.dll;." main.py

# Ou instalar Visual C++ Redistributable
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Erro 6: Antivirus Bloqueou

**Sintoma**:
Executavel sumiu de dist/ ou nao executa

**Causa**: Windows Defender ou outro antivirus

**Solucao**:
```powershell
# PowerShell Admin
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida"

# Verificar
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### Erro 7: File in Use

**Sintoma**:
```
Error: failed to remove dist/app/app.exe
PermissionError: [WinError 32] The process cannot access the file
```

**Causa**: Executavel ainda esta rodando

**Solucao**:
```bash
# Matar processos
taskkill /F /IM SSA_Consulta_Rapida.exe

# Ou fechar manualmente no Task Manager
```

---

## LICOES APRENDIDAS

### 1. Sempre Use --onedir para GUI Apps

Aplicacoes GUI com PyQt6 devem usar `--onedir`:
- Startup mais rapido
- Plugins Qt funcionam melhor
- Debugging mais facil

`--onefile` e tentador (um unico exe), mas:
- Extrai 300+ MB para TEMP a cada inicio
- Usuario espera 10+ segundos
- Antivirus mais suspeito

### 2. Build com --console Primeiro

Sempre faça build inicial com `--console`:

```bash
pyinstaller --console main.py
```

Vantagens:
- Vê erros imediatamente
- Depura import problems
- Identifica arquivos faltando

Depois de funcionar, switch para `--windowed`.

### 3. Adicionar Exclusoes de Antivirus Antes

**Ordem correta**:
1. Adicionar exclusoes
2. Fazer build
3. Testar executavel

**Ordem errada**:
1. Fazer build
2. Antivirus deleta exe
3. Adicionar exclusoes (tarde demais)

### 4. Versionar arquivo .spec

Depois de build bem-sucedido:

```bash
git add SSA_Consulta_Rapida.spec
git commit -m "Add PyInstaller spec"
```

Vantagens:
- Build reproducivel
- Customizacoes preservadas
- Outros devs usam mesma config

### 5. Testar em Sistema Limpo

Executavel funciona na maquina de build, mas:
- Usuario pode nao ter Visual C++ Redistributable
- Usuario pode nao ter .NET Framework
- Caminhos hardcoded falham

**Solucao**: Testar em VM Windows limpa.

### 6. Nao Confiar em CWD

Codigo quebrado:
```python
config_path = "config/schema.sql"  # Assume CWD
```

Codigo robusto:
```python
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(base_path, "config", "schema.sql")
```

### 7. Logar para Arquivo em Producao

Em modo frozen, print() nao aparece:

```python
import logging

if getattr(sys, 'frozen', False):
    log_file = os.path.join(os.path.dirname(sys.executable), "app.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.DEBUG)
```

Usuario pode enviar app.log para debug.

### 8. Tamanho de Download

380 MB e muito para download:

**Solucoes**:
- Compactar com 7-Zip: 380 MB -> 120 MB
- Usar instalador (NSIS, Inno Setup)
- Hospedar em CDN rapido
- Considerar PyOxidizer (11 MB) se tamanho critico

### 9. Atualizacoes

Estrutura `--onedir` facilita updates:

```
builds/pyinstaller/
|-- SSA_Consulta_Rapida.exe      # 25 MB (atualizar sempre)
|-- _internal/                    # 360 MB (atualizar so se deps mudaram)
```

Update incremental:
- Baixar so novo exe (25 MB)
- Reusar _internal/ existente

Requer versionamento cuidadoso de deps.

### 10. Assinatura Digital

Executavel nao assinado:
- Windows mostra "Publisher: Unknown"
- SmartScreen bloqueia
- Usuarios desconfiam

**Solucao**: Comprar certificado code signing:
- Digicert: $400/ano
- Sectigo: $300/ano
- GlobalSign: $350/ano

Assinatura:
```batch
signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com SSA_Consulta_Rapida.exe
```

---

## TROUBLESHOOTING AVANCADO

### Debug com PyInstaller Bootloader

Habilitar logs verbose:

```bash
pyinstaller --log-level=DEBUG main.py
```

Saida em `build/main/warn-main.txt`:
- Imports detectados
- Hooks executados
- Binaries copiados
- Dependencias resolvidas

### Analisar Dependencias

Ver grafo de imports:

```bash
pyi-archive_viewer dist/SSA_Consulta_Rapida/SSA_Consulta_Rapida.exe
```

Comandos interativos:
- `O nome_modulo` - Extrair modulo
- `X nome_modulo` - Ver dependencias
- `S` - Mostrar sumario

### Analisar DLLs

Ver DLLs usadas:

```powershell
# PowerShell
Get-ChildItem dist\SSA_Consulta_Rapida\_internal\*.dll | Select-Object Name, Length

# Dependency Walker (ferramenta externa)
depends.exe dist\SSA_Consulta_Rapida\SSA_Consulta_Rapida.exe
```

Identifica:
- DLLs faltando
- Conflitos de versao
- DLLs desnecessarias

### Reduzir Tamanho

Tecnicas avancadas:

**1. Remover stdlib nao usado**:
```python
# No .spec
a = Analysis(
    ...
    excludes=['tkinter', 'unittest', 'email', 'xml', 'pydoc'],
)
```

**2. Strip symbols**:
```python
exe = EXE(
    ...
    strip=True,  # Remove debug symbols
)
```

**3. Comprimir com UPX**:
```bash
# Manual compression (mais agressivo)
upx --best dist/SSA_Consulta_Rapida/SSA_Consulta_Rapida.exe
upx --best dist/SSA_Consulta_Rapida/_internal/*.dll
```

**4. Excluir traducoes Qt**:
```bash
# Apos build
rm dist/SSA_Consulta_Rapida/_internal/PyQt6/Qt6/translations/*.qm
# Mantem so pt_BR.qm e en_US.qm
```

Reducao tipica: 380 MB -> 280 MB

### Performance Profiling

Medir tempo de startup:

```python
# No inicio de main.py
import time
start_time = time.time()

# No fim de __init__
print(f"Startup time: {time.time() - start_time:.2f}s")
```

Otimizacoes:
- Lazy imports (importar so quando usar)
- Remover imports desnecessarios no topo
- Compilar .py para .pyc antes de empacotar

### Cross-version Compatibility

Executavel Python 3.13 pode nao rodar em Windows 7:

**Solucao**: Build em Python 3.8 para maxima compatibilidade:

```bash
pyenv install 3.8.18
pyenv local 3.8.18
pip install -r requirements.txt
pyinstaller main.py
```

Python 3.8 suporta Windows 7+.

---

## COMPARACAO COM OUTROS BUILD SYSTEMS

### PyInstaller vs PyOxidizer

| Aspecto | PyInstaller | PyOxidizer |
|---------|-------------|------------|
| Tamanho | 380 MB | 350 MB |
| Build Time | 2 min | 3 min (10 min primeira vez) |
| Startup | Rapido | Muito rapido |
| Complexidade | Baixa | Alta |
| Python Version | 3.13.12 | 3.10.9 fixo |
| Debugging | Facil | Dificil |
| Comunidade | Grande | Media |

**Recomendacao**: PyInstaller para maioria dos casos.

### PyInstaller vs Nuitka

| Aspecto | PyInstaller | Nuitka |
|---------|-------------|--------|
| Tamanho | 380 MB | 388 MB |
| Build Time | 2 min | 15 min |
| Performance | Normal | Nativa (C) |
| Startup | Rapido | Muito rapido |
| Compatibilidade | Alta | Media |
| Debugging | Facil | Medio |

**Recomendacao**: Nuitka se performance critica.

---

## REFERENCIAS

### Documentacao Oficial

- PyInstaller Manual: https://pyinstaller.org/en/stable/
- PyInstaller Hooks: https://github.com/pyinstaller/pyinstaller-hooks-contrib
- Spec File Reference: https://pyinstaller.org/en/stable/spec-files.html

### Ferramentas Uteis

- Dependency Walker: https://www.dependencywalker.com/
- UPX: https://upx.github.io/
- Resource Hacker: http://www.angusj.com/resourcehacker/
- PEiD: Detectar packers e compressores

### Comunidade

- PyInstaller Issues: https://github.com/pyinstaller/pyinstaller/issues
- Stack Overflow Tag: [pyinstaller]
- Reddit: r/learnpython

### Certificados Code Signing

- Digicert: https://www.digicert.com/signing/code-signing-certificates
- Sectigo: https://sectigo.com/ssl-certificates-tls/code-signing
- GlobalSign: https://www.globalsign.com/en/code-signing-certificate

---

## APENDICE A: Checklist Pre-Build

```
[ ] Python 3.8+ instalado
[ ] PyInstaller 6.16.0 instalado
[ ] Dependencias em requirements.txt instaladas
[ ] Antivirus exclusoes adicionadas
[ ] Builds anteriores removidos (build/, dist/)
[ ] Codigo testado e funcionando
[ ] Versao atualizada em version.py
[ ] Icon.ico presente (se usar)
[ ] version_info.txt presente (se usar)
[ ] Espaco em disco suficiente (500 MB+)
```

---

## APENDICE B: Checklist Pos-Build

```
[ ] Executavel existe em dist/
[ ] Tamanho razoavel (~380 MB)
[ ] Teste: --version mostra versao correta
[ ] Teste: --help mostra ajuda
[ ] Teste: --gui abre interface
[ ] _internal/ contem todos arquivos
[ ] config/ e data/ foram copiados
[ ] DLLs Qt presentes (Qt6Core.dll, etc.)
[ ] python313.dll presente
[ ] Copiar para launchers/dist/windows_amd64/ (canonico) ou builds/pyinstaller/ (historico)
[ ] Testar em outro computador (opcional)
[ ] Comprimir para distribuicao (opcional)
```

---

## APENDICE C: Template version_info.txt

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(4, 43, 0, 0),
    prodvers=(4, 43, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'SSA'),
        StringStruct(u'FileDescription', u'SSA Consulta Rapida'),
        StringStruct(u'FileVersion', u'4.43'),
        StringStruct(u'InternalName', u'SSA_Consulta_Rapida'),
        StringStruct(u'LegalCopyright', u'Copyright 2025'),
        StringStruct(u'OriginalFilename', u'SSA_Consulta_Rapida.exe'),
        StringStruct(u'ProductName', u'SSA Consulta Rapida'),
        StringStruct(u'ProductVersion', u'4.43')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

---

**Ultima atualizacao historica original**: 2025-11-14
**Versao do guia**: 1.0
**Autor**: Claude Code
**Status**: Completo e testado

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
