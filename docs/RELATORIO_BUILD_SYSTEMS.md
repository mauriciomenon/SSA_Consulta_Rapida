# Relatório de Build Systems - SSA Consulta Rápida

**Data**: 2025-11-14
**Ambiente**: MSYS2 UCRT64 + Windows 11
**Python**: 3.13.7 (via pyenv)

## 1. Status dos Build Systems

### ✅ PyInstaller 6.16.0 - SUCESSO COMPLETO

**Status**: Build concluído e testado com sucesso

**Executável**: `dist/SSA_Consulta_Rapida/SSA_Consulta_Rapida.exe`

**Características**:
- Tempo de build: ~2 minutos
- Modo: `--onedir` (pasta com dependências)
- Console: `--windowed` (sem console)
- Tamanho: ~80-100MB total (pasta completa)

**Teste**: Executável testou OK e exibiu versão correta: `Pesquisa Rapida de SSAs 4.11.0`

**Script**: [build_pyinstaller.bat](../build_pyinstaller.bat)

---

### ⚠️ PyOxidizer 0.24.0 - BUILD COMPLETO, ERRO DE RUNTIME

**Status**: Build compilado com sucesso, mas erro ao executar

**Executável**: `build/x86_64-pc-windows-msvc/release/install/SSA_Consulta_Rapida.exe`

**Características**:
- Tempo de build: ~2-3 minutos (primeira vez: 10-30 minutos)
- Modo: Standalone nativo com Python embedado
- Python embutido: 3.10.9 (distribuição standalone do PyOxidizer)
- Tamanho: 3.4MB (exe) + 8.3MB total com DLLs

**Problema Identificado**:
```
Traceback (most recent call last):
  File "runpy", line 196, in _run_module_as_main
  File "runpy", line 86, in _run_code
  File "main", line 166, in <module>
  File "ntpath", line 566, in abspath
```

**Causa Raiz**: Erro no `ntpath.abspath()` - problema com paths relativos/absolutos quando executado fora do diretório de build.

**Configuração MSVC**:
```
LIB=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\lib\x64;...
INCLUDE=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\include;...
```

**Script**: [build_pyoxidizer.bat](../build_pyoxidizer.bat)
**Config**: [pyoxidizer.bzl](../pyoxidizer.bzl)

**Licenças Detectadas**: 14 SPDX licenses, incluindo BSD, MIT, Apache 2.0, MPL 2.0

---

### ❌ Nuitka 2.8.4 - BUILD INTERROMPIDO

**Status**: Processo killado durante compilação

**Problema Anterior** (RESOLVIDO):
```
FATAL: Error, malformed '--include-data-dir' value, must specify existing
source data directory, not 'themes' as in 'themes=themes'.
```
- **Causa**: Script tentava incluir diretório `themes/` inexistente
- **Correção**: Linha removida do [build_nuitka.bat](../build_nuitka.bat)

**Status Atual**: Build iniciado corretamente mas foi interrompido (killed)

**Última tentativa**:
```
Nuitka: Starting Python compilation with:
Nuitka:   Version '2.8.4' on Python 3.13 (flavor 'Unknown') commercial grade 'not installed'.
```

**Configuração**:
- Modo: `--standalone`
- Plugin: `--enable-plugin=pyqt6`
- Dados: `--include-data-dir=config=config`
- Compilador: MinGW64 (download automático na primeira vez)
- Tempo estimado: 5-15 minutos (primeira vez)

**Script**: [build_nuitka.bat](../build_nuitka.bat)

---

## 2. Instalações e Ferramentas

### Ferramentas Python Instaladas
```
Nuitka         2.8.4
PyInstaller    6.16.0
PyOxidizer     0.24.0
```

### PyOxidizer - Duplicação de Instalação
**Problema**: PyOxidizer instalado em 2 locais diferentes:
- `C:\Users\menon\.pyenv\pyenv-win\shims\pyoxidizer.bat` (via pyenv)
- `C:\Users\menon\scoop\shims\pyoxidizer.exe` (via scoop)

**Recomendação**: Usar apenas uma fonte (preferir pyenv para consistência com Python)

### Nuitka - PATH
**Status**: Instalado via pip, mas não há shim no PATH do Windows
- Executar via: `python -m nuitka`
- Funciona corretamente

---

## 3. Problemas de Ambiente MSYS2 UCRT

### Diferenças MSYS2 UCRT vs CMD

**MSYS2 UCRT64**:
- Emula ambiente Unix no Windows
- PATH usa separador `:` (Unix-style)
- Comandos Unix disponíveis (ls, grep, etc.)
- Conversão automática de paths Windows <-> Unix

**CMD/PowerShell**:
- Ambiente Windows nativo
- PATH usa separador `;` (Windows-style)
- Comandos Windows nativos
- Melhor compatibilidade com ferramentas Windows (MSVC, etc.)

### Recomendações

1. **Para PyOxidizer**: Usar CMD ou PowerShell Developer Prompt do Visual Studio
   - Configuração MSVC mais confiável
   - Evita problemas de path conversion

2. **Para PyInstaller**: Funciona bem em ambos ambientes

3. **Para Nuitka**: Preferir CMD
   - MinGW64 integra melhor
   - Menos problemas com paths

---

## 4. Estrutura de Diretórios de Build

```
build/
├── nuitka/              # Nuitka output
│   ├── main.build/     # Arquivos intermediários
│   └── main.dist/      # Distribuição final (vazio - build incompleto)
├── SSA_Consulta_Rapida/ # Provavelmente PyInstaller antigo
└── x86_64-pc-windows-msvc/  # PyOxidizer output
    └── release/
        └── install/
            ├── SSA_Consulta_Rapida.exe  (3.4MB)
            ├── python310.dll            (4.3MB)
            ├── lib/                     # Módulos Python
            └── *.dll                    # Runtime DLLs

dist/
└── SSA_Consulta_Rapida/  # PyInstaller output (~80-100MB)
    ├── SSA_Consulta_Rapida.exe
    ├── _internal/         # Dependências e módulos Python
    └── config/            # Configurações copiadas
```

---

## 5. Próximos Passos Recomendados

### Prioridade ALTA

1. **Corrigir PyOxidizer** - Problema de `ntpath.abspath()`
   - Investigar `main.py:166`
   - Possivelmente relacionado a `config/` ou `data/` paths
   - Solução: usar `os.path.dirname(__file__)` ou sys._MEIPASS equivalente

2. **Completar build Nuitka**
   - Executar em ambiente limpo
   - Monitorar processo completo (15 minutos)
   - Verificar saída em `build/nuitka/main.dist/`

### Prioridade MÉDIA

3. **Remover duplicação PyOxidizer**
   ```bash
   scoop uninstall pyoxidizer
   # Ou: pyenv uninstall pyoxidizer
   ```

4. **Testar builds em CMD nativo**
   - Comparar resultados MSYS2 vs CMD
   - Documentar diferenças

5. **Criar documentação de troubleshooting**
   - Problemas comuns
   - Soluções conhecidas
   - Guia de ambiente

---

## 6. Comparação de Tamanhos (Estimado)

| Build System  | Tamanho Aprox. | Tempo Build | Status      |
|---------------|----------------|-------------|-------------|
| PyInstaller   | ~100MB         | 2 min       | ✅ Funcional |
| PyOxidizer    | ~10MB          | 2-30 min    | ⚠️ Runtime erro |
| Nuitka        | ~50-80MB       | 5-15 min    | ❌ Incompleto |

---

## 7. Recomendação Final

**Para produção**: Usar **PyInstaller**
- Mais maduro e testado
- Melhor compatibilidade com Python 3.13
- Funciona imediatamente
- Fácil debug e troubleshoot

**Para otimização futura**: Resolver **PyOxidizer**
- Menor tamanho final
- Melhor performance (Python embedado)
- Build reproducível
- Requer correção do bug de paths

**Para performance máxima**: Completar **Nuitka**
- Compila para C nativo
- Melhor performance de execução
- Maior tempo de build
- Requer MinGW64 configurado

---

## 8. Logs de Erros Detalhados

### PyOxidizer - Erro de Runtime
```
Traceback (most recent call last):
  File "runpy", line 196, in _run_module_as_main
  File "runpy", line 86, in _run_code
  File "main", line 166, in <module>
  File "ntpath", line 566, in abspath
```

### Nuitka - Erro de Diretório (RESOLVIDO)
```
FATAL: Error, malformed '--include-data-dir' value, must specify existing
source data directory, not 'themes' as in 'themes=themes'.
```

---

**Gerado por**: Claude Code
**Última atualização**: 2025-11-14
