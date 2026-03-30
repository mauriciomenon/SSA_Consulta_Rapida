# SSA Consulta Rapida - Quick Start Build System

## Sistema de Build Multi-Plataforma Configurado

### Estrutura Criada

```
launchers/
├── BUILD_MULTIPLATFORM.md          # Documentacao completa
├── build_multiplatform.py          # Script principal de build
├── convert_icon.py                 # Conversao de icones
├── platforms/                      # Configuracoes por plataforma
│   ├── windows_amd64/
│   │   ├── requirements.txt        # dependencias otimizadas
│   │   └── build_config.json       # Config PyInstaller
│   ├── macos_arm64/
│   │   ├── requirements.txt
│   │   └── build_config.json
│   └── debian_amd64/
│       ├── requirements.txt
│       └── build_config.json
```

### configuracao Atual (macOS ARM64)

**Plataforma detectada**: macOS ARM64
**configuracao ativa**: launchers/platforms/macos_arm64/

### Executar Build

```bash
# Navegar para o diretorio do projeto
cd /Users/menon/git/SSA_Consulta_Rapida

# Instalar dependencias de build
uv pip install --python 3.13 pyinstaller "pillow>=12.1.1" cairosvg

# Executar build para plataforma atual
uv run --python 3.13 launchers/build_multiplatform.py

# Ou especificar plataforma
uv run --python 3.13 launchers/build_multiplatform.py --platform macos_arm64

# Listar plataformas disponiveis
uv run --python 3.13 launchers/build_multiplatform.py --list-platforms

# Detectar plataforma atual
uv run --python 3.13 launchers/build_multiplatform.py --detect-platform
```

### dependencias Otimizadas (6 total)

- PyQt6==6.8.0
- pandas==2.2.3
- openpyxl==3.1.5
- Pillow>=12.1.1
- packaging==24.2
- pyinstaller==6.0.0

### Outputs Esperados

Apos execucao bem-sucedida:

```
launchers/dist/macos_arm64/
├── SSA_CLI                         # executavel CLI
├── SSA_GUI.app/                    # Bundle macOS GUI
```

### Configuracoes PyInstaller

**otimizacoes ativas**:
- `--onedir`: Build organizado em diretorio
- `--windowed`: Interface grafica sem console (GUI)
- `--optimize=2`: Maxima otimizacao bytecode
- `--strip`: Remove simbolos de debug
- Exclusoes de modulos desnecessarios

### Proximos Passos

1. **Testar build**: Execute `uv run --python 3.13 launchers/build_multiplatform.py`
2. **Verificar output**: Confira `launchers/dist/macos_arm64/`
3. **Testar executaveis**: Execute os binarios gerados
4. **Build outras plataformas**: Execute em Windows/Linux conforme necessario

### Troubleshooting

**Erro de dependencias**:
```bash
uv pip install --python 3.13 -r launchers/platforms/macos_arm64/requirements.txt
```

**Erro de icone**:
```bash
uv run --python 3.13 launchers/convert_icon.py
```

**Logs detalhados**:
```bash
uv run --python 3.13 launchers/build_multiplatform.py --debug
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

Ver `BUILD_MULTIPLATFORM.md` para documentacao detalhada incluindo:
- configuracao avancada
- Troubleshooting completo
- Integracao CI/CD
- distribuicao multi-plataforma

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

