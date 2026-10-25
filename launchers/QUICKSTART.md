# SSA Consulta Rapida - Quick Start Build System

## Sistema de Build Multi-Plataforma Configurado

### Estrutura Criada

```
launchers/
├── build_multiplatform.py          # Script principal de build
├── convert_icon.py                 # Conversao de icones
└── platforms/                      # Um diretorio por alvo
    ├── windows_amd64/              # requirements.txt + build_config.json (PyInstaller)
    ├── windows_arm64/
    ├── macos_arm64/
    ├── debian_amd64/
    └── debian_arm64/
```

### configuracao Atual (macOS ARM64)

**Plataforma detectada**: macOS ARM64
**configuracao ativa**: launchers/platforms/macos_arm64/

### Executar Build

```bash
# Navegar para o diretorio do projeto
cd caminho/para/SSA_Consulta_Rapida  # raiz do repositorio

# Instalar dependencias de build
uv sync --frozen --extra build

# Executar build para plataforma atual
uv run --no-sync launchers/build_multiplatform.py

# Ou especificar plataforma
uv run --no-sync launchers/build_multiplatform.py --platform macos_arm64

# Listar plataformas disponiveis
uv run --no-sync launchers/build_multiplatform.py --list-platforms

# Detectar plataforma atual
uv run --no-sync launchers/build_multiplatform.py --detect-platform
```

### Dependencias

As versoes vem do `pyproject.toml` e do `uv.lock` (extra `build`: PyInstaller,
Nuitka, Pillow, CairoSVG). `launchers/platforms/<alvo>/requirements.txt` repete
as mesmas faixas para o ambiente de build de cada alvo; nao instale versoes
fora do lock.

### Outputs Esperados

Apos execucao bem-sucedida:

```
launchers/dist/macos_arm64/
├── SSA_CLI_v<versao>_macos_arm64/                     # CLI (onedir)
├── SSA_GUI_v<versao>_macos_arm64.app/                 # Bundle macOS GUI
└── SSA_Consulta_Rapida_v<versao>_macos_arm64_pyinstaller.dmg
```

### Configuracoes PyInstaller

**otimizacoes ativas**:
- `--onedir`: Build organizado em diretorio
- `--windowed`: Interface grafica sem console (GUI)
- `--optimize=2`: Maxima otimizacao bytecode
- `--strip`: Remove simbolos de debug
- Exclusoes de modulos desnecessarios

### Proximos Passos

1. **Testar build**: Execute `uv run --no-sync launchers/build_multiplatform.py`
2. **Verificar output**: Confira `launchers/dist/macos_arm64/`
3. **Testar executaveis**: Execute os binarios gerados
4. **Build outras plataformas**: Execute em Windows/Linux conforme necessario

### Troubleshooting

**Erro de dependencias**:
```bash
uv run --no-sync launchers/build_multiplatform.py --platform macos_arm64 --clean-all  # limpa builds e recria os ambientes
```

**Erro de icone**:
```bash
uv run --no-sync launchers/convert_icon.py
```

**Logs detalhados**:
```bash
uv run --no-sync launchers/build_multiplatform.py --debug
```

### Status do Sistema

- Estrutura multi-plataforma criada
- Configuracoes otimizadas implementadas
- Sistema de build automatizado
- Documentacao completa
- GitIgnore atualizado
- Build CLI testado e funcionando
- Build GUI em execucao
- Pronto para producao

### Resultados Confirmados

**Build CLI (2025-09-06 20:18:52)**:
- executavel gerado: `launchers/dist/macos_arm64/SSA_CLI_v3.10_macos_arm64/`
- Tempo de build: ~37 segundos
- otimizacoes aplicadas: onedir, console, optimize=2, strip
- Modulos excluidos: 10+ desnecessarios removidos
- dependencias incluidas: pandas, openpyxl, PyQt6

**Build GUI (2025-09-06 20:21:51)**:
- Em progresso: SSA_GUI_v3.10_macos_arm64
- configuracao: onedir, windowed, optimize=2, strip
-  Icone: app_icon.icns aplicado

### Documentacao Completa

Fluxo de release e pacotes: `docs/GUIA_DISTRIBUICAO.md`. O detalhamento do
builder (`BUILD_MULTIPLATFORM.md`) e documento local, fora do repositorio.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

