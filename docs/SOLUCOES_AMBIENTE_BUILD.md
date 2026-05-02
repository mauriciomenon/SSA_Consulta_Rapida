# Solucoes para Problemas de Ambiente - Build Systems

## CURRENT TRUTH 2026-05-01 20h56

- Branch alvo: `dev`.
- HEAD validado: `55e2c4e2685099d672e05897f4631ca1af6b0175 2026-05-01 20:55:47 -0300 STABILITY_PATCH: deduplicate Debian target normalization`.
- PR #56: merged.
- `dev` contem correcoes de release v4.37 que ainda precisam chegar ao `main` antes do rebuild final.
- Artefatos v4.37 anteriores a este HEAD estao stale e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
- Orquestradores ativos:
  - Windows AMD64: `dev_env/build/release_windows.ps1`.
  - Debian AMD64: `dev_env/build/release_debian.sh`.
- Dry-run validado neste HEAD:
  - Windows: `release_windows.ps1 -Backend all -DryRun -Yes -SkipBuild -SkipPackage -SkipInstaller`.
  - Debian WSL: `release_debian.sh --backend all --package all --dry-run -y`.
- Protecao de codigo:
  - Nuitka e o backend preferencial para release protegido.
  - PyInstaller tem protecao parcial.
  - PyOxidizer so e aceitavel como protegido quando o pacote nao expuser `.py`/`.pyc` do app.
- Proximo passo operacional: sincronizar `main`, rebuildar Windows AMD64 e Debian AMD64 a partir deste HEAD, validar artefatos e so entao atualizar release v4.37.

## HISTORICAL SNAPSHOT 2025-11-14

Conteudo legado preservado apenas como referencia historica; o bloco `CURRENT TRUTH` acima e a fonte operacional atual.

**Autor**: Claude Code

## Problema 1: PyOxidizer - Erro `ntpath.abspath`

### Diagnostico
```
Traceback (most recent call last):
  File "main", line 166, in <module>
  File "ntpath", line 566, in abspath
TypeError: _getfullpathname: path should be string, bytes or os.PathLike, not NoneType
```

### Causa Raiz
No PyOxidizer, a variavel `__file__` retorna `None` em vez do caminho do script.
Linha problema: `project_root = os.path.dirname(os.path.abspath(__file__))`

### Solucao Implementada

Criada funcao robusta que detecta diferentes ambientes de build:

```python
def _get_project_root():
    """Retorna o diretorio raiz do projeto de forma robusta para diferentes builds."""
    # PyOxidizer
    if getattr(sys, 'oxidized', False):
        return os.path.dirname(sys.executable)
    # PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    # Nuitka
    if '__compiled__' in globals():
        return os.path.dirname(sys.executable)
    # Desenvolvimento
    try:
        if __file__ is not None:
            return os.path.dirname(os.path.abspath(__file__))
        else:
            return os.getcwd()
    except (NameError, TypeError):
        return os.getcwd()
```

### Arquivo Modificado
- [main.py](../main.py) linha 166-184

---

## Problema 2: Nuitka - Conflito com GCC do MSYS2

### Diagnostico
```
FATAL: Only this specific gcc is supported with Nuitka.
Make sure to allow downloading it when prompted.
```

### Causa Raiz
Nuitka requer seu proprio compilador MinGW64 especifico.
O GCC 15.2.0 do MSYS2 UCRT esta no PATH e interfere com o download automatico do Nuitka.

### Solucao Implementada

Criado script [build_nuitka_clean.bat](../build_nuitka_clean.bat) que:

1. Remove temporariamente MSYS2/MinGW do PATH
2. Mantem apenas Python e Scoop no PATH
3. Executa build Nuitka
4. Restaura PATH original

```batch
REM PATH limpo sem MSYS2
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\<usuario>\.pyenv\pyenv-win\bin;C:\Users\<usuario>\.pyenv\pyenv-win\shims;C:\Users\<usuario>\scoop\shims"

REM Build com Nuitka
python -m nuitka --standalone ...

REM Restaurar PATH
set "PATH=%PATH_BACKUP%"
```

### Arquivo Criado
- [build_nuitka_clean.bat](../build_nuitka_clean.bat)

---

## Problema 3: Duplicacao PyOxidizer

### Diagnostico
PyOxidizer instalado em 2 locais:
- `C:\Users\<usuario>\.pyenv\pyenv-win\shims\pyoxidizer.bat` (via pip)
- `C:\Users\<usuario>\scoop\shims\pyoxidizer.exe` (via scoop)

### Solucao
Manter ambas instalacoes esta OK porque:
1. pyenv tem prioridade no PATH
2. Scoop serve como backup
3. Diferentes contextos podem precisar de cada uma

**Nenhuma acao necessaria**

---

## Configuracao de Ambiente Atual

### Ferramentas Instaladas

| Ferramenta | Versao | Origem | Status |
|------------|--------|--------|--------|
| Python | 3.13.7 | pyenv | OK |
| PyInstaller | 6.16.0 | pip | OK |
| PyOxidizer | 0.24.0 | pip + scoop | OK |
| Nuitka | 2.8.4 | pip | OK |
| GCC | 15.2.0 | MSYS2 UCRT | OK |
| Bazel | 8.4.2 | scoop | OK |
| MSVC | 2022 (17.0) | Visual Studio | OK |

### PATH no MSYS2 UCRT
```
C:\msys64\ucrt64\bin          # GCC e ferramentas Unix
C:\Windows\System32
C:\Windows
C:\Users\<usuario>\.pyenv\pyenv-win\bin
C:\Users\<usuario>\.pyenv\pyenv-win\shims
C:\Users\<usuario>\scoop\shims
```

---

## Scripts de Build Criados/Modificados

### 1. build_pyinstaller.bat
Status: **Funcional**
- Build rapido (2 min)
- Sem problemas de ambiente

### 2. build_pyoxidizer.bat
Status: **Funcional com main.py corrigido**
- Configura MSVC via vcvars64.bat
- PATH limpo para evitar conflitos
- Requer rebuild apos correcao do main.py

### 3. build_nuitka.bat (antigo)
Status: **Problema com GCC**
- Falha devido ao GCC do MSYS2

### 4. build_nuitka_clean.bat (novo)
Status: **Pronto para teste**
- Remove MSYS2 do PATH temporariamente
- Permite Nuitka baixar seu proprio MinGW64

---

## Proximos Passos

### Prioridade ALTA
1. Aguardar conclusao rebuild PyOxidizer
2. Testar executavel PyOxidizer corrigido
3. Executar build_nuitka_clean.bat
4. Verificar se Nuitka baixa MinGW64 corretamente

### Prioridade MEDIA
5. Comparar tamanhos finais dos 3 builds
6. Testar performance de startup
7. Documentar diferencas de comportamento

---

## Diferencas de Ambiente: MSYS2 vs CMD

### MSYS2 UCRT64
**Vantagens**:
- Ferramentas Unix (ls, grep, sed, etc.)
- GCC moderno nativo
- Ambiente familiar para Linux

**Desvantagens**:
- PATH complexo com conversoes Unix/Windows
- Pode interferir com ferramentas Windows nativas
- Comportamento diferente em redirecionamento

### CMD / PowerShell
**Vantagens**:
- Ambiente Windows nativo
- Melhor compatibilidade com MSVC
- PATH mais simples

**Desvantagens**:
- Sem ferramentas Unix
- Sintaxe de batch mais limitada

### Recomendacao
**Para builds de producao**: Usar CMD com MSVC configurado
**Para desenvolvimento**: MSYS2 UCRT64 esta OK

---

## Comandos Uteis

### Verificar Ambiente
```bash
# Verificar ferramentas
which python && python --version
which pyoxidizer && pyoxidizer --version
python -m nuitka --version
which gcc && gcc --version

# Verificar PATH
echo $PATH | tr ':' '\n' | grep -v "^$"
```

### Limpar Builds Antigos
```bash
rm -rf build/
rm -rf dist/
rm -rf *.spec
```

### Testar Executaveis
```bash
# PyInstaller
./dist/SSA_Consulta_Rapida/SSA_Consulta_Rapida.exe --version

# PyOxidizer
./build/x86_64-pc-windows-msvc/release/install/SSA_Consulta_Rapida.exe --version

# Nuitka
./build/nuitka/main.dist/main.exe --version
```

---

## Resolucao de Problemas

### PyOxidizer: "error LNK1181"
**Problema**: Linker nao encontra bibliotecas
**Solucao**: Executar vcvars64.bat antes do build

### Nuitka: "Only this specific gcc is supported"
**Problema**: GCC do MSYS2 interferindo
**Solucao**: Usar build_nuitka_clean.bat

### PyInstaller: "Failed to execute script"
**Problema**: DLLs faltando
**Solucao**: Usar --onedir em vez de --onefile

---

**Ultima atualizacao**: 2025-11-14

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

