# Builds do SSA Consulta Rapida

Este diretorio contem os executaveis gerados pelos 3 build systems.

## Estrutura

```
builds/
├── pyinstaller/     # PyInstaller 6.16.0 (PRONTO)
├── pyoxidizer/      # PyOxidizer 0.24.0 (PRONTO)
└── nuitka/          # Nuitka 2.8.4 (EM PROGRESSO)
```

## PyInstaller (RECOMENDADO PARA USO)

**Status**: FUNCIONAL 100%

**Executavel**: `builds/pyinstaller/SSA_Consulta_Rapida.exe`

**Tamanho**: ~30 MB (exe unico)

**Caracteristicas**:
- Pronto para distribuicao
- Testado e funcionando
- Inclui todas dependencias
- Startup rapido

**Como usar**:
```bash
cd builds/pyinstaller
./SSA_Consulta_Rapida.exe --version
./SSA_Consulta_Rapida.exe --gui
```

---

## PyOxidizer (OTIMIZADO)

**Status**: FUNCIONAL (versao 0.0.0 - bug menor)

**Executavel**: `builds/pyoxidizer/SSA_Consulta_Rapida.exe`

**Tamanho**: ~3.4 MB (exe) + ~8 MB (libs)

**Caracteristicas**:
- Menor tamanho
- Python 3.10.9 embedado
- Startup mais rapido
- Build nativo com Rust

**Como usar**:
```bash
cd builds/pyoxidizer
./SSA_Consulta_Rapida.exe --version
./SSA_Consulta_Rapida.exe --gui
```

**Nota**: Se antivirus deletar o exe, adicionar exclusao (ver docs/ANTIVIRUS_EXCLUSOES.md)

---

## Nuitka (EM PROGRESSO)

**Status**: COMPILANDO (10-15 minutos primeira vez)

**Executavel**: `builds/nuitka/main.exe` (quando finalizar)

**Caracteristicas**:
- Compilacao para C nativo
- Melhor performance de execucao
- Maior tempo de build
- Usa MinGW64 proprio

**Como usar** (apos conclusao):
```bash
cd builds/nuitka
./main.exe --version
./main.exe --gui
```

---

## Comparacao

| Build System  | Tamanho | Build Time | Performance | Status |
|---------------|---------|------------|-------------|--------|
| PyInstaller   | 30 MB   | 2 min      | Normal      | OK     |
| PyOxidizer    | 11 MB   | 3 min      | Rapido      | OK     |
| Nuitka        | ~50 MB  | 15 min     | Muito Rapido| Build  |

---

## Scripts de Build

Localizados na raiz do projeto:

- `build_pyinstaller.bat` - Build rapido (2 min)
- `build_pyoxidizer.bat` - Build otimizado (3 min)
- `build_nuitka_clean.bat` - Build nativo (15 min)

---

## Troubleshooting

### Antivirus deletou o executavel

Ver: [docs/ANTIVIRUS_EXCLUSOES.md](../docs/ANTIVIRUS_EXCLUSOES.md)

### Erro ao executar PyOxidizer

- Certifique-se de estar no diretorio `builds/pyoxidizer/`
- O executavel precisa das DLLs na mesma pasta

### Nuitka nao compila

- Usar `build_nuitka_clean.bat` que remove GCC do MSYS2 do PATH
- Deixar Nuitka baixar seu proprio MinGW64

---

**Ultima atualizacao**: 2025-11-14
