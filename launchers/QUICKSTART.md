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
│   │   ├── requirements.txt        # dependências otimizadas
│   │   └── build_config.json       # Config PyInstaller
│   ├── macos_arm64/
│   │   ├── requirements.txt
│   │   └── build_config.json
│   └── debian_amd64/
│       ├── requirements.txt
│       └── build_config.json
```

### configuração Atual (macOS ARM64)

**Plataforma detectada**: macOS ARM64
**configuração ativa**: launchers/platforms/macos_arm64/

### Executar Build

```bash
# Navegar para o diretorio do projeto
cd /Users/menon/git/SSA_Consulta_Rapida

# Instalar dependências de build
pip install pyinstaller pillow cairosvg

# Executar build para plataforma atual
python launchers/build_multiplatform.py

# Ou especificar plataforma
python launchers/build_multiplatform.py --platform macos_arm64

# Listar plataformas disponiveis
python launchers/build_multiplatform.py --list-platforms

# Detectar plataforma atual
python launchers/build_multiplatform.py --detect-platform
```

### dependências Otimizadas (6 total)

- PyQt6==6.8.0
- pandas==2.2.3
- openpyxl==3.1.5
- Pillow==10.4.0
- packaging==24.2
- pyinstaller==6.0.0

### Outputs Esperados

Apos execucao bem-sucedida:

```
launchers/dist/macos_arm64/
├── SSA_CLI                         # executável CLI
├── SSA_GUI.app/                    # Bundle macOS GUI
```

### Configuracoes PyInstaller

**otimizações ativas**:
- `--onedir`: Build organizado em diretorio
- `--windowed`: Interface gráfica sem console (GUI)
- `--optimize=2`: Maxima otimização bytecode
- `--strip`: Remove simbolos de debug
- Exclusoes de modulos desnecessarios

### Proximos Passos

1. **Testar build**: Execute `python launchers/build_multiplatform.py`
2. **Verificar output**: Confira `launchers/dist/macos_arm64/`
3. **Testar executaveis**: Execute os binarios gerados
4. **Build outras plataformas**: Execute em Windows/Linux conforme necessario

### Troubleshooting

**Erro de dependências**:
```bash
pip install -r launchers/platforms/macos_arm64/requirements.txt
```

**Erro de icone**:
```bash
python launchers/convert_icon.py
```

**Logs detalhados**:
```bash
python launchers/build_multiplatform.py --verbose
```

### Status do Sistema

- ✅ Estrutura multi-plataforma criada
- ✅ Configuracoes otimizadas implementadas
- ✅ Sistema de build automatizado
- ✅ Documentacao completa
- ✅ GitIgnore atualizado
- ✅ Build CLI testado e funcionando
- 🔄 Build GUI em execucao
- ⏳ Pronto para producao

### Resultados Confirmados

**Build CLI (2025-09-06 20:18:52)**:
- ✅ executável gerado: `launchers/dist/macos_arm64/SSA_CLI_v3.10_macos_arm64/`
- ✅ Tempo de build: ~37 segundos
- ✅ otimizações aplicadas: onedir, console, optimize=2, strip
- ✅ Modulos excluidos: 10+ desnecessarios removidos
- ✅ dependências incluidas: pandas, openpyxl, PyQt6

**Build GUI (2025-09-06 20:21:51)**:
- 🔄 Em progresso: SSA_GUI_v3.10_macos_arm64
- 🔄 configuração: onedir, windowed, optimize=2, strip
- 🔄 Icone: app_icon.icns aplicado

### Documentacao Completa

Ver `BUILD_MULTIPLATFORM.md` para documentacao detalhada incluindo:
- configuração avancada
- Troubleshooting completo
- Integracao CI/CD
- distribuição multi-plataforma
