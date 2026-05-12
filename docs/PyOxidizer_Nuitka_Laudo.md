# Laudo PyOxidizer e Nuitka

## Cenário Geral
- Objetivo: empacotar o SSA Consulta Rápida em executáveis nativos (PyOxidizer e Nuitka).
- Ambiente: Windows 11, Python 3.13.7 instalado via pyenv-win, Visual Studio 2022 Community, toolchain MSYS2/UCRT64 disponível.
- Situação atual: PyInstaller já gera artefato funcional (`dist/SSA_Consulta_Rapida/`), porém builds nativos falharam.

## PyOxidizer
1. **Estado Atual**
   - Configuração em `pyoxidizer.bzl` usa `default_python_distribution()` com `pip_install(["pandas","openpyxl","PyQt6"])`.
   - `pyoxidizer` está instalado em `~/.pyenv/pyenv-win/versions/3.13.7/Scripts/pyoxidizer.exe`, porém não está no PATH padrão.
2. **Problema Encontrado**
   - Runtime falha no import do `numpy` com mensagem “you should not try to import numpy from its source directory”.
   - Causa raiz: `pip_install()` não inclui o diretório oculto `numpy/.libs` (DLLs do OpenBLAS) e nenhum passo adiciona `config/`, `data/`, etc. ao bundle.
3. **Ações Requeridas**
   - Rodar `pyoxidizer` a partir de um *Developer PowerShell for VS 2022* (ou `pwsh` com `vcvars64.bat`) para garantir MSVC e Rust (`rustc 1.85.0`, `cargo 1.85.0`) no PATH.
   - Ajustar `pyoxidizer.bzl` para copiar manualmente `numpy/.libs` e os diretórios externos exigidos pelo app (config, data, docs_entrada, docs_saida, logs, themes).
   - Confirmar que `C:\msys64\ucrt64\bin` NÃO está no PATH quando invocar PyOxidizer (evita conflitos com DLLs MinGW).

## Nuitka
1. **Estado Atual**
   - Disponível via `python -m nuitka --version` (2.8.4). Script `build_nuitka.bat` prepara build standalone.
   - Toolchain MSYS2/UCRT64 possui `gcc 15.2.0`, `g++ 15.2.0`, `sed 4.9`.
2. **Problemas Encontrados**
   - Primeira execução falhou porque `--include-data-dir=themes=themes` apontava para diretório inexistente.
   - Após remover `themes`, Nuitka ficou travado aguardando download do MinGW64 interno (não havia `gcc` no PATH visível).
3. **Ações Requeridas**
   - Instalar/confirmar GCC suportado pelo Nuitka (`pacman -S mingw-w64-ucrt-x86_64-gcc` já feito, binários em `C:\msys64\ucrt64\bin`).
   - Iniciar build pelo perfil `MSYS2 UCRT64` ou exportar `set "PATH=C:\msys64\ucrt64\bin;%PATH%"` antes de `python -m nuitka ...`.
   - Garantir que Windows SDK e MSVC workloads estão presentes (confirmado via `vswhere`), caso se opte por backend MSVC.

## Shells Indicados
| Tarefa | Shell Recomendado | Motivo |
|--------|------------------|--------|
| PyOxidizer (`pyoxidizer.bat build --release`) | **Developer PowerShell for VS 2022** (abre `vcvars64.bat`, depois `pyoxidizer.bat`) | Garante MSVC, `cl.exe`, `link.exe` e toolchain Rust disponíveis |
| Nuitka com GCC MinGW | **MSYS2 UCRT64** (executável `C:\msys64\msys2_shell.cmd -defterm -here -no-start -ucrt64`) | Coloca `C:\msys64\ucrt64\bin` na frente do PATH para `gcc/g++/sed/make` |
| Ajustes Python/pip (PyInstaller, scripts) | **PowerShell (sem profile) ou `python` do pyenv** | Evita overhead do profile customizado e usa mesma instalação do projeto |

## Adicionando MSYS2 UCRT64 ao Windows Terminal
1. Abra Windows Terminal → `Settings`.
2. Clique em “Add a new profile” → “New empty profile”.
3. Preencha:
   - **Name:** `MSYS2 UCRT64`
   - **Command line:** `C:\msys64\msys2_shell.cmd -defterm -here -no-start -ucrt64`
   - **Starting directory:** `C:\Users\menon\git\SSA_Consulta_Rapida` (opcional).
   - **Icon:** `C:\msys64\msys2.ico` (se desejar).
4. Salve. Agora basta abrir esse perfil para executar comandos `pacman`, `gcc`, `ninja`, `make`, etc. no ambiente correto.

## Checklist Rápido
- [x] Python 3.13.7 + pip (pyenv-win)
- [x] PyInstaller 6.16.0
- [x] Nuitka 2.8.4 (necessita GCC/SDK configurados)
- [x] PyOxidizer 0.24.0 (executável fora do PATH por padrão)
- [x] Rust toolchain stable-x86_64-pc-windows-msvc
- [x] Visual Studio 2022 Community + VC Tools x64/x86
- [x] MSYS2 UCRT64 + gcc/g++ 15.2.0 + sed 4.9

## Próximos Passos
1. Atualizar `pyoxidizer.bzl` para embutir `numpy/.libs` e manifestar pastas externas.
2. Reexecutar `pyoxidizer.bat build --release` no Developer PowerShell.
3. Corrigir `build_nuitka.bat` (remover diretórios inexistentes, garantir PATH do GCC) e rodar via perfil MSYS2 UCRT64.
4. Validar executáveis resultantes apontando o `config/` e `data/` corretos.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

