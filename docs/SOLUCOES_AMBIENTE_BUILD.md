# Solucoes para Problemas de Ambiente - Build Systems

## CURRENT TRUTH (2026-10-25, release v4.51 publicada; estabilizacao no branch rev)

- Fonte operacional completa: `docs/GUIA_DISTRIBUICAO.md`, bloco `CURRENT TRUTH`.
- Ultima release publicada: `v4.51` (tag -> `e2481cf4`, merge do PR #135 em 2026-09-29; release no GitHub em 2026-09-30; assets e SHA-256 em `RELEASE_NOTES_v4.51.md`).
- Em andamento: estabilizacao no branch `rev`, sem tag. O build do REL-01 e de teste de processo: sai do `rev` e o `build_info.json` registra branch e commit. O build oficial sai do `main`, depois do PR.
- Build e testes exigem ferramentas nativas e clone do proprio host; nao compartilhar checkout ou venv entre sistemas.
- Este documento registra solucoes de ambiente; nao deve duplicar a matriz completa de release.
- O PyOxidizer foi removido na v4.52: o pyoxidizer 0.24.0 esta sem manutencao desde 2022-12-30 e so embute CPython 3.10, que o projeto nao suporta mais.
- Em cada build, gerar artefatos no clone nativo a partir do mesmo commit confirmado para cada alvo; registrar o resultado real de cada build.
- Publicacao neste checkout: `origin` envia ao GitHub principal e ao GitLab; o push URL do espelho `schottge-menon` esta comentado em `.git/config` (conta suspensa). Conferir a configuracao antes de usar em outro clone.
- Os builds locais da candidata v4.51 (2026-09-24, a partir de `a2954a48`) nao sao os assets publicados: a release traz um pacote por alvo, inclusive Debian amd64 e arm64.

## HISTORICAL SNAPSHOT 2025-11-14

Conteudo legado preservado apenas como referencia historica; o bloco `CURRENT TRUTH` acima e a fonte operacional atual.


## Problema 1: Nuitka - Conflito com GCC do MSYS2

### Diagnostico
```
FATAL: Only this specific gcc is supported with Nuitka.
Make sure to allow downloading it when prompted.
```

### Causa Raiz
Nuitka requer seu proprio compilador MinGW64 especifico.
O GCC 15.2.0 do MSYS2 UCRT esta no PATH e interfere com o download automatico do Nuitka.

### Solucao Implementada

Historico: a primeira versao de
[build_nuitka_clean.bat](../dev_env/build/build_nuitka_clean.bat) montava um
PATH limpo sem MSYS2/MinGW antes do Nuitka.

O script atual nao altera o PATH. Ele roda sob `setlocal` (variaveis valem so
dentro do script), usa `uv run --python 3.13` com `UV_MANAGED_PYTHON=true` e o
ambiente `.venv-win`, e deixa o Nuitka baixar o proprio MinGW64.

### Arquivo Criado
- [build_nuitka_clean.bat](../dev_env/build/build_nuitka_clean.bat)

---

## Configuracao de Ambiente Atual

### Ferramentas Instaladas

| Ferramenta | Versao | Origem | Status |
|------------|--------|--------|--------|
| Python | 3.13.7 | pyenv | OK |
| PyInstaller | 6.16.0 | pip | OK |
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

### 2. build_nuitka.bat (antigo)
Status: **Problema com GCC**
- Falha devido ao GCC do MSYS2

### 3. build_nuitka_clean.bat (novo)
Status: **Pronto para teste**
- Remove MSYS2 do PATH temporariamente
- Permite Nuitka baixar seu proprio MinGW64

---

## Proximos Passos

### Prioridade ALTA
1. Executar build_nuitka_clean.bat
2. Verificar se Nuitka baixa MinGW64 corretamente

### Prioridade MEDIA
3. Comparar tamanhos finais dos 2 builds
4. Testar performance de startup
5. Documentar diferencas de comportamento

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

# Nuitka
./build/nuitka/main.dist/main.exe --version
```

---

## Resolucao de Problemas

### Nuitka: "Only this specific gcc is supported"
**Problema**: GCC do MSYS2 interferindo
**Solucao**: Usar build_nuitka_clean.bat

### PyInstaller: "Failed to execute script"
**Problema**: DLLs faltando
**Solucao**: Usar --onedir em vez de --onefile

---

**Ultima atualizacao**: 2026-09-25

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
