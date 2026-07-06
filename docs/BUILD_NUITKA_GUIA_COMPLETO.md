# Guia Completo (Historico/Laboratorio) - Build com Nuitka

## CURRENT TRUTH (baseline v4.44 local / v4.36 published)

- Sync deste guia: `2026-07-06 09:45 -0300`.
- Baseline local ativo: `v4.44`; ultima tag publicada remota: `v4.36`.
- GitHub remoto esta bloqueado por HTTP 403; nao publicar release remota ate desbloqueio e nova comparacao de divergencia.
- Fluxo canonico Nuitka (sempre via uv wrappers):
  - Windows: `dev_env/build/build_nuitka.bat --silent`
  - Debian/WSL: `bash dev_env/build/build_nuitka_debian.sh --silent`
- Artefatos finais:
  - Windows GUI: `builds/nuitka/windows_amd64/gui_entry.dist/*`
  - Windows CLI: `builds/nuitka/windows_amd64/cli_entry.dist/*`
  - Debian (quando toolchain do host estiver completo): `builds/nuitka/debian_amd64/*`
- Pre-requisito Debian:
  - instalar `patchelf` no WSL com `sudo apt-get update && sudo apt-get install -y patchelf`
  - sem `patchelf`, o script falha no preflight por design.
- Pipeline oficial de release continua PyInstaller para pacote default.
- Nuitka permanece trilha opcional de hardening/performance.
- Nomes/versionamento exato de executavel dentro de `builds/nuitka/*` devem ser lidos do output do ciclo corrente, nao deste guia historico.

## HISTORICAL SNAPSHOT NOTICE

Este guia registra estudo detalhado de setup/tuning.
Quando houver conflito com docs operacionais, prevalece CURRENT TRUTH.

## ATENCAO OPERACIONAL

- ESTE ARQUIVO E REFERENCIA HISTORICA/LABORATORIAL.
- NAO USAR COMO FLUXO DE RELEASE.
- PARA RELEASE, USAR PYINSTALLER + `launchers/dist/*`.

**Data**: 2025-11-14
**Autor**: Claude Code
**Projeto**: SSA_Consulta_Rapida v4.43 (snapshot historico)
**Sistema Operacional**: Windows 10/11
**Ambiente**: CMD / PowerShell (PATH limpo)

---

## INDICE

1. [Introducao](#introducao)
2. [Pre-requisitos](#pre-requisitos)
3. [Instalacao do Nuitka](#instalacao-do-nuitka)
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

Nuitka e um compilador Python-para-C que transforma codigo Python em codigo C nativo, compilando-o com GCC ou MSVC. O resultado e um executavel verdadeiramente nativo com performance superior ao Python interpretado.

### O que e Nuitka?

Nuitka compila Python em C:
1. **Analisa** codigo Python (.py)
2. **Transforma** em codigo C equivalente
3. **Compila** C com compilador nativo (GCC/MSVC)
4. **Link** com Python embedado e bibliotecas
5. **Gera** executavel nativo Windows (.exe)

### Por que Nuitka?

**Vantagens**:
- **Performance**: Executavel C nativo (10-30% mais rapido)
- **Startup**: Instantaneo (sem descompressao)
- **Compatibilidade**: Usa Python do sistema (3.13.12)
- **Otimizacoes**: Compilador aplica otimizacoes agressivas
- **Standalone**: Tudo em um diretorio

**Desvantagens**:
- **Build Time**: 10-15 minutos (compila 1500+ arquivos C)
- **Tamanho**: Maior que outros (388 MB)
- **Complexidade**: Configuracao avancada
- **Debugging**: Mais dificil (codigo compilado)
- **Requer**: Compilador C especifico

### Quando Usar Nuitka

Use Nuitka quando:
- Performance maxima e critico
- Precisa de startup instantaneo
- Quer usar Python 3.11+ features
- Pode esperar 15 minutos de build
- Precisa de codigo verdadeiramente nativo

### Quando NAO Usar Nuitka

Evite Nuitka quando:
- Precisa de builds rapidos (< 5 min)
- Tamanho e critico (< 100 MB)
- Tem prazos apertados
- Nao pode configurar compilador C
- Codigo usa muitas extensoes C complexas

---

## PRE-REQUISITOS

### Sistema Operacional

- **Windows**: 10 ou 11 (64-bit)
- **Permissoes**: Usuario padrao (nao precisa admin)
- **Espaco em Disco**: 2 GB para build + 1 GB para MinGW64

### Python

```
Versao: 3.13.12 (recomendado) ou 3.8-3.13
Gerenciador: pyenv-win (recomendado)
Localizacao: C:\Users\menon\.pyenv\pyenv-win\
```

**IMPORTANTE**: Nuitka USA o Python do sistema (diferente de PyOxidizer).

**Verificacao**:
```bash
python --version
# Saida esperada: Python 3.13.12

python -c "import sys; print(sys.executable)"
# Saida: C:\Users\menon\.pyenv\pyenv-win\versions\3.13.12\python.exe
```

### Compilador C (CRITICO)

Nuitka requer compilador C especifico. **NAO use GCC do MSYS2**.

#### Opcao 1: MinGW64 via Nuitka (Recomendado)

Nuitka baixa seu proprio MinGW64 automaticamente:

```bash
python -m nuitka --assume-yes-for-downloads --version
```

- **Download**: ~200 MB
- **Instalacao**: Automatica em cache
- **Versao**: MinGW64 11.2.0 (especifica para Nuitka)
- **Cache**: `%LOCALAPPDATA%\Nuitka\Cache\downloads\`

#### Opcao 2: MSVC 2022

Alternativa (nao testado neste projeto):

```bash
python -m nuitka --msvc=latest --version
```

Requer Visual Studio 2022 instalado.

#### O que NAO funciona

- **GCC do MSYS2**: Versao incompativel
- **MinGW standalone**: Nao e o MinGW do Nuitka
- **Clang**: Nao suportado no Windows

### Dependencias Python do Projeto

Mesmas que PyInstaller:

```bash
pip install -r requirements.txt
```

Pacotes principais:
- pandas>=2.0.0
- openpyxl>=3.1.0
- PyQt6>=6.5.0
- streamlit>=1.28.0
- plotly>=5.18.0

---

## INSTALACAO DO NUITKA

### Metodo 1: Via pip (Recomendado)

```bash
pip install nuitka==2.8.4
```

### Metodo 2: Via requirements_build.txt

```bash
pip install -r requirements_build.txt
```

Conteudo:
```
nuitka==2.8.4
ordered-set>=4.1.0
zstandard>=0.21.0
```

### Metodo 3: Development Version

```bash
pip install -U https://github.com/Nuitka/Nuitka/archive/develop.zip
```

### Verificacao da Instalacao

```bash
python -m nuitka --version
# Saida: 2.8.4

which nuitka
# Saida: /c/Users/menon/.pyenv/pyenv-win/shims/nuitka
```

### Primeira Execucao (Download MinGW64)

```bash
python -m nuitka --assume-yes-for-downloads --version
```

Primeira vez:
- Download MinGW64: ~200 MB
- Extracao: ~500 MB
- Tempo: 5-10 minutos
- Cache: Reusado em builds futuros

---

## CONFIGURACAO DO AMBIENTE

### PATH Limpo (CRITICO)

Nuitka e **MUITO sensivel** a GCC no PATH.

**Problema**: GCC 15.2.0 do MSYS2 UCRT conflita com MinGW64 do Nuitka.

**Erro tipico**:
```
FATAL: Only this specific gcc is supported with Nuitka.
Make sure to allow downloading it when prompted.
```

**Solucao**: PATH limpo sem MSYS2:

```batch
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims;C:\Users\menon\scoop\shims"
```

**Remover do PATH**:
- C:\msys64\ucrt64\bin (GCC 15.2.0)
- C:\msys64\mingw64\bin
- Qualquer outro GCC/MinGW

### Verificar PATH

```bash
# Deve NAO encontrar gcc
which gcc
# Erro esperado: which: no gcc in (...)

# Deve encontrar Python
which python
# OK: /c/Users/menon/.pyenv/pyenv-win/shims/python
```

### Script build_nuitka_clean.bat

Automatiza configuracao de PATH limpo:

```batch
@echo off
REM Salvar PATH original
set "PATH_BACKUP=%PATH%"

REM PATH limpo
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims;C:\Users\menon\scoop\shims"

REM Build
python -m nuitka ...

REM Restaurar PATH
set "PATH=%PATH_BACKUP%"
```

### Configuracao do Antivirus

Mesmas exclusoes que outros builds:

```powershell
# PowerShell Admin
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\build"
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\builds"
Add-MpPreference -ExclusionPath "%LOCALAPPDATA%\Nuitka"
```

**Importante**: Antivirus pode bloquear cache do Nuitka.

**Sintoma**: Warning sobre cache nao gravavel.

---

## ESTRUTURA DO PROJETO

### Arvore de Diretorios

```
SSA_Consulta_Rapida/
|
|-- main.py                      # Entry point
|-- build_nuitka_clean.bat       # Script de build
|
|-- core/
|-- gui/
|-- extracao/
|-- exportacao/
|-- config/
|-- data/
|
|-- build/                       # Temporario Nuitka
|   |-- nuitka/
|       |-- main.build/          # Arquivos C intermediarios
|       |-- main.dist/           # Build final
|           |-- main.exe         # Executavel (142 MB!)
|           |-- *.dll            # DLLs Python e dependencias
|           |-- config/          # Dados copiados
|           |-- data/
|
|-- builds/                      # Build organizado
    |-- nuitka/
        |-- main.exe             # 142 MB
        |-- *.dll
        |-- config/
        |-- data/
```

### Modulos Criticos

Mesmos que PyInstaller/PyOxidizer, com funcao `_get_project_root()`:

```python
def _get_project_root():
    # Nuitka
    if '__compiled__' in globals():
        return os.path.dirname(sys.executable)
    # Outros...
```

**Linha 166-184 de main.py**: Funcao robusta para todos builds.

---

## ARQUIVO DE CONFIGURACAO

### Script build_nuitka_clean.bat

Conteudo completo:

```batch
@echo off
REM Build script para Nuitka 2.8.4 sem gcc do MSYS2 no PATH
REM Autor: Claude Code
REM Data: 2025-11-14

echo Removendo MSYS2/MinGW do PATH temporariamente...
echo.

REM Salvar PATH original
set "PATH_BACKUP=%PATH%"

REM PATH limpo sem MSYS2
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

echo PATH limpo configurado
echo.

REM Limpar build anterior se existir
if exist build\nuitka rmdir /s /q build\nuitka

echo Iniciando build com Nuitka...
echo Nuitka vai baixar seu proprio compilador MinGW64 na primeira vez.
echo Isso vai demorar 5-15 minutos na primeira vez.
echo.

REM Build com Nuitka
python -m nuitka ^
    --standalone ^
    --assume-yes-for-downloads ^
    --windows-console-mode=force ^
    --enable-plugin=pyqt6 ^
    --include-data-dir=config=config ^
    --output-dir=build\nuitka ^
    --company-name="SSA" ^
    --product-name="SSA Consulta Rapida" ^
    --file-version=4.0.0 ^
    --product-version=4.0.0 ^
    --follow-imports ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo Executavel em: build\nuitka\main.dist\main.exe
    echo.
    echo Copiando para builds/nuitka/
    if not exist builds\nuitka mkdir builds\nuitka
    xcopy /E /I /Y build\nuitka\main.dist\* builds\nuitka\
    echo.
    echo Executavel final: builds\nuitka\main.exe
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

REM Restaurar PATH original
set "PATH=%PATH_BACKUP%"
echo.
echo PATH restaurado

pause
```

### Parametros Explicados

**--standalone**
- Cria diretorio com exe + todas dependencias
- Equivalente ao --onedir do PyInstaller
- Alternativa: --onefile (experimental)

**--assume-yes-for-downloads**
- Aceita download automatico de MinGW64
- Sem interacao do usuario
- Essencial para scripts automatizados

**--windows-console-mode=force**
- Abre console Windows (para ver prints/erros)
- Alternativas:
  - `disable`: Modo windowed (sem console)
  - `attach`: Anexa a console existente
  - `force`: Sempre cria nova console

**--enable-plugin=pyqt6**
- Ativa plugin especifico para PyQt6
- Detecta DLLs e plugins Qt automaticamente
- Outros plugins: numpy, tkinter, multiprocessing

**--include-data-dir=config=config**
- Sintaxe: `origem=destino`
- Copia pasta config/ para build
- Repeticao: Multiplos --include-data-dir

**--output-dir=build\nuitka**
- Define diretorio de saida
- Padrao: main.build/ e main.dist/ no diretorio atual

**--company-name="SSA"**
- Metadata do executavel
- Visivel em propriedades do arquivo

**--file-version=4.0.0**
- Versao do arquivo (4 numeros: major.minor.patch.build)

**--follow-imports**
- Segue todas importacoes recursivamente
- Inclui todos modulos usados
- Alternativa: --nofollow-imports (so modulo principal)

### Opcoes Adicionais Uteis

```batch
REM Otimizacao maxima
--lto=yes

REM Remover console (GUI mode)
--windows-console-mode=disable

REM Icon
--windows-icon-from-ico=icon.ico

REM Threads paralelos (build mais rapido)
--jobs=8

REM Debug
--debug

REM Verbose
--verbose
```

---

## PROCESSO DE BUILD PASSO A PASSO

### Passo 1: Preparacao

```bash
# Navegar para diretorio
cd c:/Users/menon/git/SSA_Consulta_Rapida

# Verificar Python
python --version
# Esperado: 3.13.12

# Verificar Nuitka
python -m nuitka --version
# Esperado: 2.8.4

# Verificar que GCC NAO esta no PATH
which gcc
# Esperado: erro "not found"
```

### Passo 2: Limpeza de Builds Anteriores

```bash
# Remover build anterior
rm -rf build/nuitka

# Ou Windows
rmdir /s /q build\nuitka
```

### Passo 3: Primeira Execucao (Download MinGW64)

**Somente primeira vez**:

```bash
python -m nuitka --assume-yes-for-downloads --version
```

Saida:
```
Nuitka will make use of Dependency Walker (https://dependencywalker.com) to
analyze the dependencies of Python extension modules.

Is it OK to download and put it in
"%LOCALAPPDATA%\Nuitka\Cache\downloads\depends\x86_64"? [Yes]/No

Downloading from https://...
[========================================] 100% (1.2 MB)

Extracting...
Done.
```

**Cache em**: `%LOCALAPPDATA%\Nuitka\Cache\`

Conteudo:
- MinGW64 compiler (gcc 11.2.0)
- Dependency Walker
- Ccache (cache de compilacao)

### Passo 4: Executar Build

**Via Script (Recomendado)**:
```batch
build_nuitka_clean.bat
```

**Via Linha de Comando**:
```bash
# Com PATH limpo
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

python -m nuitka --standalone --assume-yes-for-downloads --enable-plugin=pyqt6 --include-data-dir=config=config main.py
```

### Passo 5: Monitorar Progresso

Nuitka mostra fases:

**Fase 1: Analise (1 min)**
```
Nuitka: Starting Python compilation with Nuitka ...
Nuitka: Analyzing main.py
Nuitka: Processing import of 'core'
Nuitka: Processing import of 'gui'
Nuitka: Processing import of 'pandas'
Nuitka: Processing import of 'PyQt6'
...
Nuitka: Found 1512 modules to compile
```

**Fase 2: Geracao C (2 min)**
```
Nuitka: Generating C source code...
[   1%] Generating code for module '__main__'
[   5%] Generating code for module 'pandas'
[  10%] Generating code for module 'PyQt6'
...
[ 100%] Generated 1512 C files
```

**Fase 3: Compilacao C (10 min)**
```
Nuitka: Compiling C source code...
[   1%] Compiling __main__.c
[   2%] Compiling pandas.core.frame.c
[   3%] Compiling PyQt6.QtWidgets.c
...
[ 100%] Compiled 1512 C files

Using clcache (MSVC cache) or ccache (GCC cache)
```

**Fase 4: Linking (1 min)**
```
Nuitka: Linking...
Nuitka: Copying required DLLs...
Nuitka: Copying data files (config/, data/)...
Nuitka: Creating main.dist directory...
Done.
```

**Tempo Total**:
- **Primeira build**: 15-20 minutos
- **Builds subsequentes**: 10-15 minutos (ccache acelera)

### Passo 6: Verificar Saida

```bash
# Listar build
ls -lh build/nuitka/main.dist/

# Tamanho do exe
ls -lh build/nuitka/main.dist/main.exe
# Esperado: 142 MB (!)

# Tamanho total
du -sh build/nuitka/main.dist/
# Esperado: 388 MB
```

### Passo 7: Copiar para builds/

```bash
# Criar estrutura
mkdir -p builds/nuitka

# Copiar
cp -r build/nuitka/main.dist/* builds/nuitka/

echo "Nuitka copiado para builds/nuitka/"
```

### Passo 8: Testar Executavel

```bash
cd builds/nuitka

# Teste 1: Versao
./main.exe --version
# Esperado: 4.43

# Teste 2: Help
./main.exe --help

# Teste 3: GUI
./main.exe --gui
```

---

## ANALISE DA SAIDA

### Estrutura de build/nuitka/main.dist/

```
main.dist/
|
|-- main.exe                     # Executavel (142 MB!)
|
|-- python313.dll                # Python embedado (4 MB)
|-- _socket.pyd                  # Extensoes C
|-- _ssl.pyd
|-- _sqlite3.pyd
|
|-- Qt6Core.dll                  # PyQt6 DLLs (30 MB)
|-- Qt6Gui.dll                   # (25 MB)
|-- Qt6Widgets.dll               # (20 MB)
|
|-- pandas/                      # Bibliotecas Python compiladas
|-- openpyxl/
|-- PyQt6/
|-- numpy/
|
|-- config/                      # Dados copiados
|   |-- schema.sql
|   |-- settings.json
|
|-- data/
    |-- ssas.db
```

### Por que main.exe e tao Grande?

**142 MB** porque contem:
- Codigo Python compilado para C (embedado)
- Python stdlib compilado
- Metadados de todos modulos
- Tabelas de importacao

**Comparacao**:
- PyInstaller exe: 25 MB (bytecode Python)
- PyOxidizer exe: 3.4 MB (loader Rust + bytecode)
- Nuitka exe: 142 MB (C compilado nativo)

**Trade-off**: Tamanho vs Performance

### Tamanhos Detalhados

```bash
cd build/nuitka/main.dist

# Executavel
du -sh main.exe
# 142 MB

# DLLs Python e Qt
du -sh *.dll *.pyd
# 150 MB

# Bibliotecas Python
du -sh pandas/ numpy/ PyQt6/
# 80 MB

# Outros
# 16 MB

# Total: 388 MB
```

### Arquivos Criticos

**Nao podem ser removidos**:
- main.exe
- python313.dll
- Qt6*.dll
- *.pyd (extensoes C)
- Pastas pandas/, numpy/, PyQt6/
- config/, data/

---

## OTIMIZACOES APLICADAS

### 1. PATH Limpo

**Problema**: GCC do MSYS2 interferindo

**Solucao**: build_nuitka_clean.bat remove MSYS2 do PATH

**Impacto**: Build funciona vs falha fatal

### 2. Ccache / Clcache

Nuitka usa cache de compilacao:
- **Ccache** (MinGW64)
- **Clcache** (MSVC)

**Primeira build**: 15 minutos
**Builds subsequentes**: 10 minutos (30% mais rapido)

**Cache em**: `%LOCALAPPDATA%\Nuitka\Cache\ccache\`

**Limpar cache**:
```bash
python -m nuitka --clean-cache
```

### 3. LTO (Link-Time Optimization)

Habilitar otimizacao entre modulos:

```batch
python -m nuitka --lto=yes ...
```

**Vantagens**:
- Exe 10-15% menor
- Performance 5-10% melhor

**Desvantagens**:
- Build 20-30% mais lento

**Nao usado neste projeto** (build ja lento).

### 4. Follow-Imports Seletivo

```batch
REM Atual (segue tudo)
--follow-imports

REM Alternativa (so modulos usados)
--follow-import-to=core,gui,extracao
```

**Trade-off**:
- Menos imports = Build mais rapido
- Risco: Modulo faltando em runtime

### 5. Jobs Paralelos

```batch
--jobs=8
```

Compila 8 arquivos C em paralelo (usa 8 cores CPU).

**Impacto**: Build 30-40% mais rapido em CPU multi-core.

**Padrao**: Detecta automaticamente numero de cores.

---

## ERROS COMUNS E SOLUCOES

### Erro 1: "Only this specific gcc is supported"

**Sintoma**:
```
FATAL: Only this specific gcc is supported with Nuitka.
Make sure to allow downloading it when prompted.
```

**Causa**: GCC do MSYS2 (15.2.0) no PATH

**Solucao**: Usar build_nuitka_clean.bat que limpa PATH

```batch
REM Verificar que gcc NAO esta no PATH
where gcc
REM Deve retornar erro

REM Build
build_nuitka_clean.bat
```

### Erro 2: "Failed to download MinGW64"

**Sintoma**:
```
Error downloading from https://github.com/...
Connection timeout
```

**Causa**: Firewall ou proxy bloqueando

**Solucao**:

1. Download manual:
   https://github.com/Nuitka/Nuitka-gcc-binaries/releases

2. Extrair para:
   `%LOCALAPPDATA%\Nuitka\Cache\downloads\gcc\x86_64-11.2.0-win32\`

3. Re-executar build

### Erro 3: "Antivirus warning about cache"

**Sintoma**:
```
Warning: Could not write to cache file ...
Antivirus software may be interfering
```

**Causa**: Windows Defender bloqueando cache

**Solucao**:
```powershell
# PowerShell Admin
Add-MpPreference -ExclusionPath "%LOCALAPPDATA%\Nuitka"
```

### Erro 4: Qt Platform Plugin Error

**Sintoma**:
```
This application failed to start because no Qt platform plugin could be initialized.
```

**Causa**: Plugin PyQt6 nao habilitado

**Solucao**:
```batch
python -m nuitka --enable-plugin=pyqt6 ...
```

### Erro 5: "ModuleNotFoundError" em Runtime

**Sintoma**:
```
ModuleNotFoundError: No module named 'pandas.core.computation'
```

**Causa**: Import dinamico nao seguido

**Solucao**:

1. Adicionar import explicito:
```python
# No main.py
import pandas.core.computation
```

2. Ou forcar seguir:
```batch
--follow-import-to=pandas.core.computation
```

### Erro 6: "Out of Memory"

**Sintoma**:
```
gcc: fatal error: Killed signal terminated program cc1
```

**Causa**: RAM insuficiente (compilacao usa ~8 GB)

**Solucao**:

1. Reduzir jobs paralelos:
```batch
--jobs=2
```

2. Compilar modulos menores (excluir grandes):
```batch
--nofollow-import-to=plotly
```

3. Aumentar RAM virtual (pagefile)

### Erro 7: "Permission Denied"

**Sintoma**:
```
PermissionError: [WinError 5] Access is denied: 'build\\nuitka\\main.dist\\main.exe'
```

**Causa**: Executavel ainda rodando

**Solucao**:
```bash
# Matar processo
taskkill /F /IM main.exe

# Ou fechar manualmente
```

---

## LICOES APRENDIDAS

### 1. GCC do MSYS2 e Incompativel

**Descoberta critica**: Nuitka requer seu proprio MinGW64.

GCC 15.2.0 do MSYS2 UCRT causa:
```
FATAL: Only this specific gcc is supported
```

**Solucao permanente**: build_nuitka_clean.bat

### 2. Build e LENTO (10-15 min)

Nuitka compila:
- 1512 arquivos C
- 150.000+ linhas de codigo C gerado
- Link com 200+ bibliotecas

**Aceitar**: Build lento e inevitavel.

**Mitigar**:
- Ccache (30% mais rapido em rebuilds)
- Jobs paralelos (--jobs=8)
- Excluir modulos nao usados

### 3. Executavel e GRANDE (142 MB)

Codigo C compilado e maior que bytecode Python.

**Comparacao**:
- Bytecode: 10 MB
- C compilado: 142 MB

**Trade-off**: Tamanho vs Performance

**Nao tem solucao**: E caracteristica do Nuitka.

### 4. Primeira Build Baixa MinGW64

Primeira build:
1. Download MinGW64 (200 MB)
2. Download Dependency Walker (1 MB)
3. Setup ccache

**Tempo adicional**: +10 minutos primeira vez

**Cache permanente**: Reusado em todos projetos

### 5. Performance Gain e Modesto

**Esperado**: 200-300% mais rapido (C vs Python)

**Real**: 10-30% mais rapido

**Por que?**:
- Codigo passa tempo em bibliotecas (pandas, PyQt6)
- Bibliotecas ja sao C (nao beneficiam de compilacao)
- Gargalos sao I/O, nao CPU

**Vale a pena?**: Depende. Se startup critico, sim.

### 6. Compatibilidade e Excelente

Nuitka usa Python do sistema (3.13.12):
- Todas features do Python 3.13
- Compatibilidade maxima com bibliotecas
- Sem restricoes de versao

**Vantagem sobre PyOxidizer** (Python 3.10.9 fixo).

### 7. Debugging e Dificil

Codigo compilado = sem traceback claro.

**Erro Python**:
```
File "main.py", line 100, in func
```

**Erro Nuitka**:
```
In compiled code (main.c:12453)
```

**Solucao**: Debug em Python normal primeiro, depois compilar.

### 8. Antivirus Reclama Mais

Nuitka gera muitos arquivos temporarios (~1500 .c files).

Antivirus escaneia todos = build lento + warnings.

**Solucao**: Exclusoes obrigatorias.

### 9. Cache Acelera Rebuilds

Ccache armazena .o compilados.

**Primeira build**: 15 min
**Rebuild (sem mudancas)**: 2 min
**Rebuild (mudancas pequenas)**: 5 min

**Cache em**: `%LOCALAPPDATA%\Nuitka\Cache\ccache\`

**Tamanho**: ~500 MB apos varios builds

**Limpar**:
```bash
python -m nuitka --clean-cache
```

### 10. --onefile e Experimental

```batch
python -m nuitka --onefile main.py
```

Cria um unico .exe (como PyInstaller --onefile).

**Status**: Experimental, nao recomendado.

**Problemas**:
- Extrai para TEMP (como PyInstaller)
- Startup lento
- Alguns bugs conhecidos

**Use --standalone** (testado e confiavel).

---

## TROUBLESHOOTING AVANCADO

### Debug Build Process

Habilitar logs verbose:

```batch
python -m nuitka --verbose --standalone main.py
```

Saida inclui:
- Cada modulo encontrado
- Decisoes de seguir imports
- Comandos gcc executados
- Caminhos de bibliotecas

### Analisar Tempo de Build

Profile de tempo:

```batch
python -m nuitka --show-progress --show-modules --standalone main.py
```

Mostra:
- Tempo por modulo
- Modulos mais lentos
- Bottlenecks de compilacao

### Verificar MinGW64

Script de diagnostico:

```batch
@echo off
echo Verificando MinGW64 do Nuitka...

set NUITKA_CACHE=%LOCALAPPDATA%\Nuitka\Cache\downloads\gcc

if exist "%NUITKA_CACHE%" (
    echo OK: Cache Nuitka existe
    dir /B "%NUITKA_CACHE%"
) else (
    echo AVISO: Cache Nuitka nao encontrado
    echo Execute: python -m nuitka --assume-yes-for-downloads --version
)

echo.
echo Verificando gcc no PATH...
where gcc > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo PROBLEMA: gcc encontrado no PATH
    where gcc
    echo REMOVA do PATH antes de build Nuitka
) else (
    echo OK: gcc nao esta no PATH
)
```

### Reduzir Tamanho do Exe

Tecnicas experimentais:

**1. Strip symbols**:
```batch
strip build\nuitka\main.dist\main.exe
```

Reducao: 142 MB -> 120 MB

**2. UPX compression**:
```batch
upx --best build\nuitka\main.dist\main.exe
```

Reducao: 120 MB -> 50 MB

**ATENCAO**: UPX com exe grande (> 100 MB) pode nao funcionar.

**3. Excluir stdlib nao usado**:
```batch
--nofollow-import-to=unittest,pydoc,email
```

### Otimizacoes Agressivas

Para producao (nao usado neste projeto):

```batch
python -m nuitka ^
    --standalone ^
    --lto=yes ^
    --clang ^
    --jobs=8 ^
    --optimize-pythonbytecode ^
    --assume-yes-for-downloads ^
    main.py
```

**Flags**:
- `--lto=yes`: Link-time optimization
- `--clang`: Usar clang em vez de gcc (se disponivel)
- `--optimize-pythonbytecode`: Pre-compilar .py em .pyc

**Trade-off**: Build ainda mais lento (20 min).

---

## COMPARACAO COM OUTROS BUILD SYSTEMS

### Nuitka vs PyInstaller

| Aspecto | Nuitka | PyInstaller |
|---------|--------|-------------|
| Tamanho Exe | 142 MB | 25 MB |
| Tamanho Total | 388 MB | 385 MB |
| Build Time | 15 min | 2 min |
| Performance | C nativo | Python normal |
| Startup | Instantaneo | Rapido |
| Debugging | Dificil | Facil |
| Compatibilidade | Alta | Muito Alta |

**Recomendacao**:
- PyInstaller para desenvolvimento
- Nuitka para producao com performance critica

### Nuitka vs PyOxidizer

| Aspecto | Nuitka | PyOxidizer |
|---------|--------|------------|
| Tamanho Total | 388 MB | 343 MB |
| Exe Size | 142 MB | 3.4 MB |
| Build Time | 15 min | 3 min |
| Performance | C nativo | Python 3.10 normal |
| Python Version | 3.13.12 | 3.10.9 fixo |
| Complexidade | Alta | Muito Alta |

**Recomendacao**:
- PyOxidizer para tamanho otimizado
- Nuitka para performance maxima

### Tabela Consolidada

| Criterio | PyInstaller | PyOxidizer | Nuitka |
|----------|-------------|------------|--------|
| Build Time | 2 min | 3 min | 15 min |
| Exe Size | 25 MB | 3.4 MB | 142 MB |
| Total Size | 385 MB | 343 MB | 388 MB |
| Startup | Rapido | Muito rapido | Instantaneo |
| Performance | Normal | Normal | 10-30% melhor |
| Python Ver | 3.13.12 | 3.10.9 | 3.13.12 |
| Debugging | Facil | Dificil | Dificil |
| Complexidade | Baixa | Alta | Alta |

**Recomendacao Final**:
- **Desenvolvimento**: PyInstaller
- **Producao balanceada**: PyOxidizer
- **Producao performance**: Nuitka

---

## REFERENCIAS

### Documentacao Oficial

- Nuitka Manual: https://nuitka.net/doc/user-manual.html
- Nuitka Plugins: https://nuitka.net/doc/plugins.html
- Nuitka FAQ: https://nuitka.net/pages/faq.html

### Repositorio

- GitHub: https://github.com/Nuitka/Nuitka
- Issues: https://github.com/Nuitka/Nuitka/issues
- Releases: https://github.com/Nuitka/Nuitka/releases

### Compiladores

- MinGW64 do Nuitka: https://github.com/Nuitka/Nuitka-gcc-binaries
- MSVC: https://visualstudio.microsoft.com/

### Comunidade

- Reddit: r/Nuitka
- Stack Overflow Tag: [nuitka]
- Discussions: https://github.com/Nuitka/Nuitka/discussions

---

## APENDICE A: Checklist Pre-Build

```
[ ] Python 3.8+ instalado
[ ] Nuitka 2.8.4 instalado
[ ] MinGW64 baixado (primeira vez)
[ ] GCC NAO esta no PATH (verificar com: where gcc)
[ ] PATH limpo configurado
[ ] Antivirus exclusoes adicionadas
[ ] Dependencias instaladas (pip install -r requirements.txt)
[ ] build_nuitka_clean.bat criado
[ ] Espaco em disco: 2 GB livres
[ ] RAM disponivel: 8 GB (para compilacao)
[ ] Tempo disponivel: 15-20 minutos
```

---

## APENDICE B: Checklist Pos-Build

```
[ ] Build completou sem erros (ERRORLEVEL 0)
[ ] Executavel em build/nuitka/main.dist/main.exe
[ ] Tamanho exe: ~142 MB
[ ] Tamanho total: ~388 MB
[ ] python313.dll presente
[ ] Qt6*.dll presentes
[ ] config/ e data/ copiados
[ ] Teste: main.exe --version (mostra 4.43)
[ ] Teste: main.exe --help (mostra ajuda)
[ ] Teste: main.exe --gui (abre interface)
[ ] Startup e instantaneo (< 1 segundo)
[ ] Copiar para builds/nuitka/
[ ] Testar em outro PC (opcional)
```

---

## APENDICE C: Comparacao Startup Time

Medido com time command:

```bash
# PyInstaller
time ./builds/pyinstaller/SSA_Consulta_Rapida.exe --version
# Real: 2.3s

# PyOxidizer
time ./builds/pyoxidizer/SSA_Consulta_Rapida.exe --version
# Real: 0.8s

# Nuitka
time ./builds/nuitka/main.exe --version
# Real: 0.3s
```

**Nuitka e 7x mais rapido que PyInstaller no startup**.

---

## APENDICE D: Estrutura de Cache do Nuitka

```
%LOCALAPPDATA%\Nuitka\
|
|-- Cache\
    |
    |-- downloads\
    |   |-- gcc\
    |   |   |-- x86_64-11.2.0-win32\   # MinGW64 (~500 MB)
    |   |       |-- bin\gcc.exe
    |   |       |-- lib\
    |   |       |-- include\
    |   |
    |   |-- depends\
    |       |-- x86_64\               # Dependency Walker
    |           |-- depends.exe
    |
    |-- ccache\                        # Cache de compilacao (~500 MB)
        |-- 0\
        |-- 1\
        |-- ...
        |-- f\
```

**Limpar cache**:
```bash
python -m nuitka --clean-cache
```

**Tamanho tipico**: 1 GB apos varios builds

---

**Ultima atualizacao**: 2025-11-14
**Versao do guia**: 1.0
**Autor**: Claude Code
**Status**: Completo e testado

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
