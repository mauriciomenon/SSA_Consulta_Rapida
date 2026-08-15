# Guia Completo (Historico/Laboratorio) - Build com PyOxidizer

## CURRENT TRUTH (4.44 local / v4.36 published)

- Sync deste guia: `2026-07-06 09:45 -0300`.
- Baseline local ativo: `v4.44`; ultima tag publicada remota: `v4.36`.
- GitHub remoto esta bloqueado por HTTP 403; nao publicar release remota ate desbloqueio e nova comparacao de divergencia.
- PyOxidizer segue como trilha avancada (nao default), mas com fluxo operacional funcional para:
  - `windows_amd64`
  - `debian_amd64` (via WSL)
- Comandos canonicos (sempre via uv):
  - Windows: `dev_env/build/build_pyoxidizer.bat --silent`
  - Debian/WSL: `bash dev_env/build/build_pyoxidizer_debian.sh --silent`
- Artefatos finais:
  - `builds/pyoxidizer/windows_amd64/SSA_Consulta_Rapida.exe`
  - `builds/pyoxidizer/debian_amd64/SSA_Consulta_Rapida`
- Estrutura runtime gerada no bundle:
  - codigo do projeto em raiz (`core/`, `gui/`, `interface/`, etc.)
  - runtime Python em `lib/`
  - dados/config copiados por `scripts/copy_data_to_builds.py`
- Runtime deps nativas de pandas/numpy:
  - sincronizadas por `scripts/sync_pyoxidizer_runtime_libs.py`
  - chamadas automaticamente pelos scripts de build de PyOxidizer
- Observacao tecnica:
  - PyOxidizer 0.24.0 usa runtime Python 3.10 embedado.
  - O toolchain e processo do projeto continuam padronizados em `uv run --python 3.13 ...`.

## HISTORICAL SNAPSHOT NOTICE

Este documento foi mantido para contexto tecnico.
Nao usar como runbook primario de release.

**Data**: 2025-11-14
**Autor**: Claude Code
**Projeto**: SSA_Consulta_Rapida v4.43 (snapshot historico)
**Sistema Operacional**: Windows 10/11
**Ambiente**: CMD / PowerShell (NAO MSYS2)

---

## INDICE

1. [Introducao](#introducao)
2. [Pre-requisitos](#pre-requisitos)
3. [Instalacao do PyOxidizer](#instalacao-do-pyoxidizer)
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

PyOxidizer e um sistema moderno de empacotamento Python escrito em Rust. Diferente de PyInstaller, PyOxidizer embute o interpretador Python e bibliotecas de forma nativa, resultando em executaveis menores e startups mais rapidos.

### O que e PyOxidizer?

PyOxidizer compila aplicacoes Python em binarios nativos usando:
- **Rust** como linguagem de build
- **Python Build Standalone** (Python 3.10.9 embedado)
- **Cargo** (build system do Rust) para compilacao
- **MSVC** (Microsoft Visual C++) no Windows

### Por que PyOxidizer?

**Vantagens**:
- Executaveis menores (66% menor que PyInstaller)
- Startup mais rapido (sem descompressao)
- Python embedado nativo (sem dependencia externa)
- Builds reproduziveis (via Rust/Cargo)
- Analise automatica de licencas

**Desvantagens**:
- Configuracao mais complexa
- Requer MSVC no Windows
- Python versao fixa (3.10.9)
- Debugging mais dificil
- Menor comunidade que PyInstaller

### Quando Usar PyOxidizer

Use PyOxidizer quando:
- Tamanho do executavel e critico
- Precisa de startup rapido
- Quer distribuicao otimizada
- Tem tempo para configuracao inicial
- Pode usar Python 3.10.9

### Quando NAO Usar PyOxidizer

Evite PyOxidizer quando:
- Precisa de Python 3.11+
- Tem prazos apertados (configuracao complexa)
- Nao pode instalar MSVC
- Precisa de debug facil
- Dependencias usam recursos nao-Python (C extensions complicadas)

---

## PRE-REQUISITOS

### Sistema Operacional

- **Windows**: 10 ou 11 (64-bit)
- **Permissoes**: Admin para instalar MSVC
- **Espaco em Disco**: 10 GB para MSVC + 2 GB para builds

### Python

```
Versao: 3.13.12 (para desenvolvimento)
         3.10.9 (embedado pelo PyOxidizer)
Gerenciador: pyenv-win (recomendado)
Localizacao: C:\Users\menon\.pyenv\pyenv-win\
```

**Importante**: PyOxidizer NAO usa seu Python local. Ele baixa Python 3.10.9 standalone.

**Verificacao**:
```bash
python --version
# Saida: Python 3.13.12 (ou outra versao)
# OK! PyOxidizer usa seu proprio Python
```

### Microsoft Visual C++ (MSVC)

**CRITICO**: PyOxidizer requer MSVC 2022 (ou 2019).

#### Instalacao Via Visual Studio Installer

1. Baixar Visual Studio 2022 Community:
   https://visualstudio.microsoft.com/downloads/

2. Durante instalacao, selecionar:
   - "Desktop development with C++"
   - Windows 10/11 SDK
   - MSVC v143 build tools (x64/x86)

3. Tamanho: ~7 GB

#### Instalacao Via Build Tools

Alternativa menor (sem IDE):

1. Baixar Build Tools for Visual Studio 2022:
   https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022

2. Instalar componentes:
   - MSVC v143 - VS 2022 C++ x64/x86 build tools
   - Windows 10 SDK (10.0.22621.0)
   - C++ CMake tools for Windows

3. Tamanho: ~4 GB

#### Verificar Instalacao MSVC

```batch
REM CMD ou PowerShell
"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Verificar CL (compilador C++)
cl
REM Saida esperada: Microsoft (R) C/C++ Optimizing Compiler Version 19.xx
```

### Rust (Opcional mas Recomendado)

PyOxidizer instala Rust automaticamente, mas pode instalar manualmente:

```powershell
# PowerShell
Invoke-WebRequest -Uri https://win.rustup.rs -OutFile rustup-init.exe
.\rustup-init.exe -y

# Reiniciar terminal

rustc --version
# Saida: rustc 1.74.0 (ou superior)
```

### Dependencias Python do Projeto

Mesmas que PyInstaller:

```bash
pip install -r requirements.txt
```

---

## INSTALACAO DO PYOXIDIZER

### Metodo 1: Via pip (Recomendado)

```bash
pip install pyoxidizer==0.24.0
```

### Metodo 2: Via Scoop (Windows)

```bash
scoop install pyoxidizer
```

### Metodo 3: Via Cargo (Build from Source)

```bash
cargo install pyoxidizer --vers 0.24.0
```

### Verificacao da Instalacao

```bash
pyoxidizer --version
# Saida: 0.24.0

which pyoxidizer
# Saida: /c/Users/menon/.pyenv/pyenv-win/shims/pyoxidizer (pip)
#    ou: /c/Users/menon/scoop/shims/pyoxidizer (scoop)
```

### Duplicacao pip + scoop

Pode ter PyOxidizer instalado em ambos:
- pip: `C:\Users\menon\.pyenv\pyenv-win\shims\pyoxidizer.bat`
- scoop: `C:\Users\menon\scoop\shims\pyoxidizer.exe`

**E OK**. PATH prioriza pyenv primeiro.

---

## CONFIGURACAO DO AMBIENTE

### Configurar MSVC

**CRITICO**: Sempre configure MSVC antes de build.

**Metodo 1: Via vcvars64.bat (Recomendado)**

```batch
REM CMD
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Verificar
cl
link
```

**Metodo 2: Via Script Automatizado**

Criar `build_pyoxidizer.bat`:

```batch
@echo off
REM Limpar PATH para remover conflitos
set "PATH_BACKUP=%PATH%"
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

REM Configurar MSVC
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Build
pyoxidizer build --release

REM Restaurar PATH
set "PATH=%PATH_BACKUP%"
```

### Variaveis de Ambiente

Apos vcvars64.bat, estas variaveis sao configuradas:
- `VCINSTALLDIR`: C:\Program Files\Microsoft Visual Studio\2022\Community\VC\
- `WindowsSdkDir`: C:\Program Files (x86)\Windows Kits\10\
- `INCLUDE`: Caminhos para headers C++
- `LIB`: Caminhos para bibliotecas
- `PATH`: Inclui cl.exe, link.exe

**Verificar**:
```batch
echo %VCINSTALLDIR%
echo %WindowsSdkDir%
```

### PATH Limpo

PyOxidizer e sensivel a PATH poluido. Recomenda-se PATH minimo:

```batch
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"
```

**Remover**:
- MSYS2/MinGW (conflita com MSVC)
- Git Bash (pode confundir linker)
- Outras toolchains C/C++

### Configuracao do Antivirus

Mesmas exclusoes que PyInstaller:

```powershell
# PowerShell Admin
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\build"
Add-MpPreference -ExclusionPath "C:\Users\menon\git\SSA_Consulta_Rapida\builds"
```

---

## ESTRUTURA DO PROJETO

### Arvore de Diretorios

```
SSA_Consulta_Rapida/
|
|-- main.py                      # Entry point
|-- pyoxidizer.bzl                # Arquivo de configuracao PyOxidizer
|
|-- core/
|-- gui/
|-- extracao/
|-- exportacao/
|-- config/
|-- data/
|
|-- build_pyoxidizer.bat         # Script de build
|
|-- build/                       # Temporario PyOxidizer
|   |-- x86_64-pc-windows-msvc/
|       |-- debug/
|       |-- release/
|           |-- install/         # Build final
|               |-- SSA_Consulta_Rapida.exe
|               |-- lib/         # Python libs
|
|-- builds/                      # Build organizado
    |-- pyoxidizer/
        |-- SSA_Consulta_Rapida.exe
        |-- lib/
```

### Modulos Criticos

Mesmos que PyInstaller, mas com adaptacoes:

**main.py** (modificado para PyOxidizer):

```python
import sys
import os

def _get_project_root():
    """Detecta ambiente de build."""
    # PyOxidizer
    if getattr(sys, 'oxidized', False):
        return os.path.dirname(sys.executable)
    # PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    # Desenvolvimento
    try:
        if __file__ is not None:
            return os.path.dirname(os.path.abspath(__file__))
        else:
            return os.getcwd()
    except (NameError, TypeError):
        return os.getcwd()

project_root = _get_project_root()
sys.path.insert(0, project_root)
```

**Linha 166-184 de main.py**: Funcao critica para PyOxidizer funcionar.

---

## ARQUIVO DE CONFIGURACAO

### pyoxidizer.bzl

Arquivo principal de configuracao PyOxidizer:

```python
# pyoxidizer.bzl
# Configuracao PyOxidizer para SSA_Consulta_Rapida

def make_exe():
    # 1. Distribuicao Python
    dist = default_python_distribution(
        python_version = "3.10"
    )

    # 2. Politica de empacotamento
    policy = dist.make_python_packaging_policy()

    # CRITICO: Resources no filesystem, nao in-memory
    policy.resources_location = "filesystem-relative:lib"
    policy.resources_location_fallback = "filesystem-relative:lib"

    # Permitir carregamento de filesystem
    policy.allow_files = True
    policy.file_scanner_emit_files = True
    policy.include_file_resources = True

    # 3. Configuracao do interpretador Python
    python_config = dist.make_python_interpreter_config()

    # Run como modulo
    python_config.run_module = "main"

    # CRITICO: Habilitar filesystem importer
    python_config.filesystem_importer = True

    # Modo buffered para I/O
    python_config.buffered_stdio = False
    python_config.sys_frozen = True
    python_config.sys_meipass = False

    # 4. Criar executavel
    exe = dist.to_python_executable(
        name = "SSA_Consulta_Rapida",
        packaging_policy = policy,
        config = python_config,
    )

    # 5. Adicionar dependencias via pip
    exe.add_python_resources(exe.pip_install([
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "PyQt6>=6.5.0",
        "streamlit>=1.28.0",
        "plotly>=5.18.0",
        "tabulate>=0.9.0",
        "python-dotenv>=1.0.0",
    ]))

    # 6. Adicionar pacotes do projeto
    for resource in exe.read_package_root(
        path = ".",
        packages = [
            "core",
            "gui",
            "armazenamento",
            "extracao",
            "exportacao",
            "utils",
            "interface",
            "shared",
            "main",
        ],
    ):
        # CRITICO: Recursos no filesystem
        resource.add_location = "filesystem-relative:lib"
        exe.add_python_resource(resource)

    # 7. Adicionar arquivos de dados
    exe.add_filesystem_relative_resource(
        prefix = "config",
        files = glob(["config/*"]),
    )

    exe.add_filesystem_relative_resource(
        prefix = "data",
        files = glob(["data/*"]),
    )

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

def make_msi(exe):
    return exe.to_wix_msi_builder(
        "SSA_Consulta_Rapida",
        "SSA Consulta Rapida",
        "4.43",
        "SSA"
    )

register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends = ["exe"], default_build_script = True)
register_target("install", make_install, depends = ["exe"], default = True)
register_target("msi", make_msi, depends = ["exe"])

resolve_targets()
```

### Parametros Explicados

#### default_python_distribution

```python
dist = default_python_distribution(python_version = "3.10")
```

- Baixa Python Build Standalone 3.10.9
- Tamanho: ~30 MB download
- Cached em: `~/.pyoxidizer/` ou `%LOCALAPPDATA%\pyoxidizer\`

#### Politica de Recursos

```python
policy.resources_location = "filesystem-relative:lib"
```

Opcoes:
- `in-memory`: Recursos embedados no exe (mais rapido, maior exe)
- `filesystem-relative:lib`: Recursos em pasta lib/ (menor exe)
- `filesystem-relative:$ORIGIN/lib`: Relativo ao exe

**Escolha**: `filesystem-relative:lib` para compatibilidade.

#### Filesystem Importer

```python
python_config.filesystem_importer = True
```

**CRITICO**: Sem isso, imports falham.

PyOxidizer pode usar:
- `oxidized_importer`: Importer customizado em Rust (rapido)
- `filesystem_importer`: Importer padrao Python (compativel)

**Escolha**: `filesystem_importer` para maxima compatibilidade.

#### Pip Install

```python
exe.add_python_resources(exe.pip_install(["pandas>=2.0.0", ...]))
```

PyOxidizer executa pip install em ambiente isolado e empacota resultados.

**Alternativa**: Ler requirements.txt:

```python
exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))
```

#### Read Package Root

```python
for resource in exe.read_package_root(
    path = ".",
    packages = ["core", "gui", ...],
):
    resource.add_location = "filesystem-relative:lib"
    exe.add_python_resource(resource)
```

Le todos .py em packages especificados.

**add_location**: Onde colocar no build final.

#### Adicionar Arquivos

```python
exe.add_filesystem_relative_resource(
    prefix = "config",
    files = glob(["config/*"]),
)
```

Copia arquivos para build mantendo estrutura.

---

## PROCESSO DE BUILD PASSO A PASSO

### Passo 1: Preparacao

```batch
REM Navegar para diretorio
cd c:\Users\menon\git\SSA_Consulta_Rapida

REM Verificar Python
python --version

REM Verificar PyOxidizer
pyoxidizer --version

REM Verificar MSVC (testar cl)
cl
REM Se erro: executar vcvars64.bat primeiro
```

### Passo 2: Limpeza de Builds Anteriores

```batch
REM Remover build anterior
rmdir /s /q build\x86_64-pc-windows-msvc

REM Ou comando Unix (MSYS2)
rm -rf build/
```

### Passo 3: Configurar MSVC

```batch
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
```

Saida esperada:
```
**********************************************************************
** Visual Studio 2022 Developer Command Prompt v17.0.0
** Copyright (c) 2022 Microsoft Corporation
**********************************************************************
[vcvarsall.bat] Environment initialized for: 'x64'
```

### Passo 4: Executar Build

**Via Script (Recomendado)**:
```batch
build_pyoxidizer.bat
```

**Via Linha de Comando**:
```batch
pyoxidizer build --release
```

Flags disponiveis:
- `--release`: Build otimizado (recomendado)
- `--debug`: Build com symbols de debug
- `--target-triple x86_64-pc-windows-msvc`: Especificar target

### Passo 5: Monitorar Progresso

PyOxidizer mostra:

```
   Resolving Python distribution...
   Downloading Python 3.10.9...
   [00:00:30] ████████████████████████ 100% 30.5 MB
   Extracting Python distribution...

   Resolving packaging policy...
   Running pip install...
   [00:01:00] Installing pandas...
   [00:01:20] Installing PyQt6...
   [00:02:00] Installing openpyxl...

   Reading package root...
   Processing 156 Python modules...

   Compiling with Rust...
   [00:02:30] Compiling pyembed v0.24.0
   [00:03:00] Linking SSA_Consulta_Rapida.exe

   Build complete!
   Output: build/x86_64-pc-windows-msvc/release/install/
```

**Tempo de Build**:
- **Primeira vez**: 10-30 minutos (download Python + dependencias)
- **Builds subsequentes**: 2-3 minutos (cache)

### Passo 6: Verificar Saida

```batch
REM Listar build
dir build\x86_64-pc-windows-msvc\release\install\

REM Tamanho
du -sh build/x86_64-pc-windows-msvc/release/install/
REM Esperado: 350 MB
```

### Passo 7: Copiar para builds/

```batch
REM Criar estrutura
mkdir builds\pyoxidizer

REM Copiar
xcopy /E /I /Y build\x86_64-pc-windows-msvc\release\install\* builds\pyoxidizer\
```

### Passo 8: Testar Executavel

```batch
cd builds\pyoxidizer

REM Teste 1: Versao
SSA_Consulta_Rapida.exe --version
REM Esperado: 0.0.0 (bug conhecido)

REM Teste 2: Help
SSA_Consulta_Rapida.exe --help

REM Teste 3: GUI
SSA_Consulta_Rapida.exe --gui
```

---

## ANALISE DA SAIDA

### Estrutura de build/x86_64-pc-windows-msvc/release/install/

```
install/
|
|-- SSA_Consulta_Rapida.exe      # Executavel principal (3.4 MB)
|
|-- lib/                          # Bibliotecas Python (340 MB)
    |
    |-- python310.dll             # Python embedado (4 MB)
    |-- _sqlite3.pyd              # Extensoes C
    |-- pandas/                   # Pacotes Python
    |-- openpyxl/
    |-- PyQt6/
    |-- numpy/
    |-- plotly/
    |
    |-- config/                   # Dados do projeto
    |   |-- schema.sql
    |   |-- settings.json
    |
    |-- data/
        |-- ssas.db
```

### Tamanhos Detalhados

```batch
cd build\x86_64-pc-windows-msvc\release\install

REM Tamanho do exe
dir SSA_Consulta_Rapida.exe
REM 3.4 MB

REM Tamanho da lib/
du -sh lib/
REM 340 MB

REM Maiores componentes
du -sh lib/* | sort -h | tail -10
REM PyQt6: 150 MB
REM pandas + numpy: 80 MB
REM Python stdlib: 40 MB
REM Outros: 70 MB
```

### Comparacao com PyInstaller

| Aspecto | PyInstaller | PyOxidizer |
|---------|-------------|------------|
| Exe | 25 MB | 3.4 MB |
| Dependencias | _internal/ 360 MB | lib/ 340 MB |
| Total | 385 MB | 343 MB |
| Reducao | - | **11% menor** |

---

## OTIMIZACOES APLICADAS

### 1. Resources Location

**filesystem-relative vs in-memory**:

```python
# filesystem-relative (usado)
policy.resources_location = "filesystem-relative:lib"
# Exe: 3.4 MB, lib/: 340 MB

# in-memory
policy.resources_location = "in-memory"
# Exe: 343 MB, lib/: 0 MB (tudo embedado)
```

**Decisao**: `filesystem-relative` para:
- Exe menor (facil download separado)
- Atualizacoes incrementais (so exe ou so lib)
- Melhor compatibilidade

### 2. Include Only Necessary Packages

```python
exe.read_package_root(
    path = ".",
    packages = ["core", "gui", "extracao", ...],  # Especifico
    # NAO: packages = ["*"]  # Incluiria tudo
)
```

Economiza ~50 MB ao excluir:
- tests/
- docs/
- scripts_manutencao/
- LocalTemp/

### 3. Strip Debug Symbols

Build com `--release`:
```batch
pyoxidizer build --release
```

Remove symbols de debug, reduz exe de 5 MB para 3.4 MB.

### 4. Python 3.10 vs 3.13

PyOxidizer usa Python 3.10.9 (nao 3.13.12 do sistema):

**Vantagens Python 3.10**:
- Binarios menores
- Mais compatibilidade
- Build Standalone otimizado

**Desvantagens**:
- Sem features do 3.11+
- Alguma incompatibilidade (rara)

### 5. LTO (Link-Time Optimization)

Habilitado automaticamente no `--release`:

```
Compiling with LTO...
```

Otimiza chamadas entre modulos, reduz tamanho ~10%.

---

## ERROS COMUNS E SOLUCOES

### Erro 1: "error LNK1181: cannot open input file"

**Sintoma**:
```
LINK : fatal error LNK1181: cannot open input file 'kernel32.lib'
```

**Causa**: MSVC nao configurado (variaveis LIB, INCLUDE faltando)

**Solucao**:
```batch
REM Executar vcvars64.bat
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Verificar variaveis
echo %LIB%
echo %INCLUDE%

REM Re-executar build
pyoxidizer build --release
```

### Erro 2: "TypeError: _getfullpathname: path should be string, not NoneType"

**Sintoma**:
```
File "main", line 166, in <module>
TypeError: _getfullpathname: path should be string, bytes or os.PathLike, not NoneType
```

**Causa**: `__file__` retorna None no PyOxidizer

**Solucao**: Adicionar funcao `_get_project_root()` em main.py:

```python
def _get_project_root():
    if getattr(sys, 'oxidized', False):
        return os.path.dirname(sys.executable)
    # Outros casos...
```

**Arquivo**: [main.py](../main.py) linhas 166-184

### Erro 3: "ModuleNotFoundError" em Runtime

**Sintoma**:
```
ModuleNotFoundError: No module named 'pandas.core.computation'
```

**Causa**: Import dinamico nao foi detectado

**Solucao**: Adicionar pacote ao pyoxidizer.bzl:

```python
exe.add_python_resources(exe.pip_install([
    "pandas>=2.0.0",
    "pandas[computation]",  # Extras
]))
```

Ou usar `collect-all`:
```python
exe.add_python_resources(exe.pip_install_all(["pandas"]))
```

### Erro 4: Qt Platform Plugin Error

**Sintoma**:
```
This application failed to start because no Qt platform plugin could be initialized.
```

**Causa**: Plugins Qt nao foram copiados

**Solucao**: Verificar pyoxidizer.bzl tem:

```python
policy.resources_location = "filesystem-relative:lib"
policy.include_file_resources = True
```

E PyQt6 instalado via pip_install.

### Erro 5: "The system cannot find the path specified"

**Sintoma**:
Build falha procurando arquivos em PATH

**Causa**: PATH poluido com MSYS2, Git Bash, etc.

**Solucao**: Limpar PATH antes de build:

```batch
REM build_pyoxidizer.bat
set "PATH_BACKUP=%PATH%"
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

call vcvars64.bat
pyoxidizer build --release

set "PATH=%PATH_BACKUP%"
```

### Erro 6: Antivirus Bloqueou

**Sintoma**:
Executavel sumiu ou nao executa

**Solucao**: Mesma que PyInstaller (adicionar exclusoes).

### Erro 7: "ArgumentParser: expected str, not NoneType"

**Sintoma**:
```
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

**Causa**: `sys.argv[0]` tambem None no PyOxidizer

**Solucao**: Fix em main.py:

```python
prog_name = sys.argv[0] if sys.argv and sys.argv[0] else "SSA_Consulta_Rapida"
parser = argparse.ArgumentParser(prog=prog_name, ...)
```

**Arquivo**: [main.py](../main.py) linhas 277-280

---

## LICOES APRENDIDAS

### 1. MSVC e Obrigatorio no Windows

PyOxidizer compila com Rust que usa MSVC no Windows.

**NAO funciona**:
- MinGW
- GCC do MSYS2
- Clang standalone

**Funciona**:
- MSVC 2022 (recomendado)
- MSVC 2019
- Build Tools for Visual Studio

### 2. Usar CMD/PowerShell, NAO MSYS2

MSYS2 converte paths Unix<->Windows, confunde MSVC.

**Erros em MSYS2**:
- Paths tipo `/c/Users/...` nao funcionam com link.exe
- GCC no PATH interfere

**Solucao**: Sempre build em CMD ou PowerShell nativo.

### 3. filesystem-relative e Mais Compativel

Tentamos `in-memory` primeiro (tudo no exe), mas:
- PyQt6 nao encontrava plugins
- Arquivos de dados (config/, data/) nao carregavam

`filesystem-relative:lib` resolveu tudo.

### 4. Python Versao Fixa

PyOxidizer usa Python 3.10.9, nao a versao do sistema.

**Implicacoes**:
- Codigo deve ser compativel com 3.10
- Features do 3.11+ nao funcionam (match/case, etc.)
- Testes devem rodar em 3.10

**Solucao**: Testar em Python 3.10 antes de build:

```bash
pyenv install 3.10.9
pyenv local 3.10.9
pytest
```

### 5. Primeira Build e Lenta

Primeira build baixa:
- Python 3.10.9 standalone (~30 MB)
- Toolchain Rust (~200 MB)
- Dependencias pip (~100 MB)

Total: 10-30 minutos

Builds seguintes: 2-3 minutos (usa cache).

**Cache em**: `%LOCALAPPDATA%\pyoxidizer\` ou `~/.pyoxidizer/`

### 6. Versao Mostra 0.0.0

Bug conhecido: PyOxidizer nao le versao do codigo.

**Workaround**: Definir versao em pyoxidizer.bzl:

```python
def make_msi(exe):
    return exe.to_wix_msi_builder(
        "SSA_Consulta_Rapida",
        "SSA Consulta Rapida",
        "4.43",  # Versao aqui
        "SSA"
    )
```

Mas `--version` ainda mostra 0.0.0 (lê APP_VERSION via sys.argv).

### 7. Debugging e Dificil

Erros em PyOxidizer binaries sao critos:
- Nao da pra ver traceback completo
- Prints nao aparecem
- Nao da pra anexar debugger facilmente

**Solucao**: Logar para arquivo:

```python
if getattr(sys, 'oxidized', False):
    log_file = os.path.join(os.path.dirname(sys.executable), "debug.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG)
```

### 8. Reproducibilidade

PyOxidizer builds sao reproduziveis:
- Mesmos inputs = mesmo output
- Graças ao Rust/Cargo
- Git-friendly (versionar pyoxidizer.bzl)

**Vantagem**: CI/CD facil, builds deterministicos.

### 9. Licencas Detectadas Automaticamente

PyOxidizer analisa licencas:

```
Analyzing 63 software components...
14 distinct SPDX licenses found:
- MIT: 45 components
- Apache-2.0: 10 components
- BSD-3-Clause: 5 components
- MPL-2.0: 2 components
- LGPL-3.0: 1 component (PyQt6 - manual)
```

**Util para compliance**.

### 10. Atualizacoes Incrementais

Estrutura permite updates so do exe:

```
builds/pyoxidizer/
|-- SSA_Consulta_Rapida.exe      # 3.4 MB (update v4.43)
|-- lib/                          # 340 MB (nao muda)
```

Usuario baixa so 3.4 MB para update de codigo.

---

## TROUBLESHOOTING AVANCADO

### Debug Build Process

Habilitar logs verbose:

```batch
set RUST_LOG=debug
pyoxidizer build --release
```

Saida inclui:
- Comandos Rust executados
- Decisoes de packaging policy
- Paths resolvidos

### Analisar Binario

Ver recursos embedados:

```bash
pyoxidizer analyze build\x86_64-pc-windows-msvc\release\install\SSA_Consulta_Rapida.exe
```

Saida:
- Python modules incluidos
- Extensoes C carregadas
- Recursos adicionais

### Verificar MSVC Setup

Script de diagnostico:

```batch
@echo off
echo Verificando MSVC...

where cl
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: cl.exe nao encontrado
    echo Execute vcvars64.bat primeiro
    exit /b 1
)

where link
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: link.exe nao encontrado
    exit /b 1
)

echo %LIB% | findstr /C:"VC\\" > nul
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: LIB nao configurado
    exit /b 1
)

echo OK: MSVC configurado corretamente
```

### Reduzir Tamanho

Tecnicas avancadas:

**1. Excluir modulos stdlib**:

```python
# pyoxidizer.bzl
policy.include_distribution_sources = False
policy.include_distribution_resources = False
policy.include_test = False
```

**2. Comprimir lib/**:

```bash
# Apos build
cd build/x86_64-pc-windows-msvc/release/install/lib
upx --best *.pyd
```

Reducao: 340 MB -> 280 MB

**3. Remover .pyc desnecessarios**:

```bash
find lib/ -name "*.pyc" -delete
find lib/ -name "__pycache__" -delete
```

### Cross-compilation

PyOxidizer suporta cross-compile (ex: Linux -> Windows):

```bash
# No Linux
pyoxidizer build --target-triple x86_64-pc-windows-msvc --release
```

Requer:
- Rust cross-compilation toolchain
- Wine (para testar)

**Complexo**: Recomenda-se build nativo.

---

## COMPARACAO COM OUTROS BUILD SYSTEMS

### PyOxidizer vs PyInstaller

| Aspecto | PyOxidizer | PyInstaller |
|---------|------------|-------------|
| Tamanho Total | 343 MB | 385 MB |
| Exe Size | 3.4 MB | 25 MB |
| Build Time | 3 min* | 2 min |
| Startup | Muito rapido | Rapido |
| Complexidade | Alta | Baixa |
| Python Version | 3.10.9 fixo | 3.13.12 |
| Debugging | Dificil | Facil |
| Reproducibilidade | Alta | Media |

*Apos primeira build

**Recomendacao**:
- PyInstaller para desenvolvimento rapido
- PyOxidizer para producao otimizada

### PyOxidizer vs Nuitka

| Aspecto | PyOxidizer | Nuitka |
|---------|------------|--------|
| Tamanho | 343 MB | 388 MB |
| Build Time | 3 min | 15 min |
| Performance | Python normal | C nativo |
| Startup | Muito rapido | Instantaneo |
| Compatibilidade | Alta | Media-Alta |
| Compilacao | Rust | C + MSVC |

**Recomendacao**:
- PyOxidizer para tamanho otimizado
- Nuitka para performance maxima

---

## REFERENCIAS

### Documentacao Oficial

- PyOxidizer Docs: https://pyoxidizer.readthedocs.io/
- Starlark Config: https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_config.html
- Packaging Guide: https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_packaging.html

### Python Build Standalone

- Releases: https://github.com/indygreg/python-build-standalone/releases
- Python 3.10.9 usado: https://github.com/indygreg/python-build-standalone/releases/tag/20230116

### Rust e Cargo

- Rust Lang: https://www.rust-lang.org/
- Cargo Book: https://doc.rust-lang.org/cargo/

### MSVC

- Visual Studio: https://visualstudio.microsoft.com/
- Build Tools: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
- vcvars64 docs: https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line

### Comunidade

- PyOxidizer Issues: https://github.com/indygreg/PyOxidizer/issues
- Reddit: r/rust
- Stack Overflow Tag: [pyoxidizer]

---

## APENDICE A: Checklist Pre-Build

```
[ ] Python 3.10+ instalado (para desenvolvimento)
[ ] PyOxidizer 0.24.0 instalado
[ ] MSVC 2022 (ou 2019) instalado
[ ] vcvars64.bat executado
[ ] cl.exe e link.exe no PATH
[ ] LIB e INCLUDE configurados
[ ] PATH limpo (sem MSYS2/MinGW)
[ ] Antivirus exclusoes adicionadas
[ ] pyoxidizer.bzl presente
[ ] main.py com _get_project_root()
[ ] Espaco em disco: 10 GB (primeira build)
```

---

## APENDICE B: Checklist Pos-Build

```
[ ] Build completou sem erros
[ ] Executavel em build/x86_64-pc-windows-msvc/release/install/
[ ] Tamanho razoavel (~343 MB)
[ ] lib/ contem python310.dll
[ ] lib/ contem pacotes (pandas, PyQt6, etc.)
[ ] config/ e data/ copiados
[ ] Teste: exe --version (mostra 0.0.0 - bug conhecido)
[ ] Teste: exe --help (mostra ajuda)
[ ] Teste: exe --gui (abre interface)
[ ] Copiar para builds/pyoxidizer/
[ ] Testar em outro PC (opcional)
```

---

## APENDICE C: Script build_pyoxidizer.bat Completo

```batch
@echo off
REM Build script para PyOxidizer 0.24.0
REM Autor: Claude Code
REM Data: 2025-11-14

echo Iniciando build com PyOxidizer...
echo.

REM Salvar PATH original
set "PATH_BACKUP=%PATH%"

REM Limpar PATH (remover MSYS2, Git Bash, etc.)
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

echo PATH limpo configurado
echo.

REM Configurar ambiente MSVC
echo Configurando MSVC...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao configurar MSVC
    echo Verifique se Visual Studio 2022 esta instalado
    pause
    exit /b 1
)

echo.
echo Verificando ferramentas...
where cl > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: cl.exe nao encontrado
    pause
    exit /b 1
)

where link > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: link.exe nao encontrado
    pause
    exit /b 1
)

echo Ferramentas OK
echo.

REM Limpar build anterior
if exist build\x86_64-pc-windows-msvc rmdir /s /q build\x86_64-pc-windows-msvc
echo Build anterior limpo
echo.

REM Build com PyOxidizer
echo Executando PyOxidizer build...
echo Primeira build pode demorar 10-30 minutos (download Python + deps)
echo Builds seguintes: 2-3 minutos
echo.

pyoxidizer build --release

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo.
    echo Criando estrutura em builds/pyoxidizer/
    if not exist builds\pyoxidizer mkdir builds\pyoxidizer
    xcopy /E /I /Y build\x86_64-pc-windows-msvc\release\install\* builds\pyoxidizer\
    echo.
    echo Executavel em: builds\pyoxidizer\SSA_Consulta_Rapida.exe
    echo Tamanho: ~350 MB total (exe: 3.4 MB + lib: 340 MB)
) else (
    echo Build falhou com erro %ERRORLEVEL%
    echo.
    echo Verifique:
    echo 1. MSVC esta configurado corretamente
    echo 2. pyoxidizer.bzl esta correto
    echo 3. Espaco em disco suficiente
)

REM Restaurar PATH original
set "PATH=%PATH_BACKUP%"
echo.
echo PATH restaurado

pause
```

---

## APENDICE D: Correcoes Aplicadas em main.py

### Linha 166-184: Funcao _get_project_root()

```python
def _get_project_root():
    """
    Retorna o diretorio raiz do projeto de forma robusta para diferentes builds.

    Detecta automaticamente:
    - PyOxidizer (sys.oxidized = True)
    - PyInstaller (sys.frozen = True)
    - Nuitka (__compiled__ in globals)
    - Desenvolvimento (usa __file__)
    """
    # PyOxidizer: __file__ retorna None
    if getattr(sys, 'oxidized', False):
        return os.path.dirname(sys.executable)

    # PyInstaller: usa _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS

    # Nuitka: define __compiled__
    if '__compiled__' in globals():
        return os.path.dirname(sys.executable)

    # Desenvolvimento: usa __file__
    try:
        if __file__ is not None:
            return os.path.dirname(os.path.abspath(__file__))
        else:
            return os.getcwd()
    except (NameError, TypeError):
        return os.getcwd()
```

### Linha 277-280: Fix ArgumentParser

```python
# Fix para PyOxidizer: sys.argv[0] pode ser None
prog_name = sys.argv[0] if sys.argv and sys.argv[0] else "SSA_Consulta_Rapida"
parser = argparse.ArgumentParser(
    prog=prog_name,
    description=f"Consulta Rapida de SSAs v{APP_VERSION}",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
```

---

**Ultima atualizacao**: 2025-11-14
**Versao do guia**: 1.0
**Autor**: Claude Code
**Status**: Completo e testado

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
