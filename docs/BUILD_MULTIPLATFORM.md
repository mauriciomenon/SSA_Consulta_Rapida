# Build System Multi-Plataforma

Sistema automatizado para criacao de executaveis SSA Consulta Rapida para Windows, macOS e Linux.

## CURRENT TRUTH (v4.33)

- Sync deste guia: `2026-03-11 23:35 -0300`.
- Relatorio consolidado deste ciclo:
  - `docs/BUILD_EXECUTION_AUDIT_20260311.md`
- Runbook operacional 3x3:
  - `docs/BUILD_3X3_RUNBOOK.md`
- Fluxo operacional padrao:
  1. build por backend com scripts em `dev_env/build/`
  2. distribuicao com `scripts/create_distribution.py`
- Backends ativos no ciclo:
  - `pyinstaller` (default de release)
  - `nuitka` (opcional)
  - `pyoxidizer` (opcional)
- Comandos canonicos (sempre via uv):
  - Windows:
    - `dev_env/build/build_pyinstaller.bat --silent`
    - `dev_env/build/build_nuitka.bat --silent`
    - `dev_env/build/build_pyoxidizer.bat --silent`
  - Debian via WSL:
    - `bash dev_env/build/build_pyinstaller_debian.sh --silent`
    - `bash dev_env/build/build_nuitka_debian.sh --silent`
    - `bash dev_env/build/build_pyoxidizer_debian.sh --silent`

## Local de saida e staging

- Artefatos finais:
  - PyInstaller:
    - `launchers/dist/<plataforma>/...`
    - `builds/pyinstaller/<plataforma>/...`
  - Nuitka:
    - `builds/nuitka/<plataforma>/...`
  - PyOxidizer:
    - `builds/pyoxidizer/<plataforma>/...`
- Instaladores e zips:
  - `dist_packages/`
- Staging temporario (nao versionar):
  - `build/pyoxidizer_stage_windows_amd64/`
  - `build/x86_64-pc-windows-msvc/`
  - `build/x86_64-unknown-linux-gnu/`
  - `launchers/platforms/*/temp/`

## Cleanup opcional (pos-build)

- Script canonico:
  - `uv run --python 3.13 scripts/cleanup_build_artifacts.py --scope temp`
- Escopo:
  - `temp`: remove apenas staging/temporarios.
  - `full`: remove tambem `builds/*`, `launchers/dist/*`, `dist_packages/*`.
- Scripts de build em modo nao silencioso perguntam no final se deve rodar cleanup `temp`.

## Nota de versao

Exemplos de nomes versionados neste documento (v3.10/v3.11) sao snapshots historicos.
No fluxo ativo, usar a versao corrente definida em `VERSION` e `config/version.json`.

## Estrutura de Build

```
launchers/
├── build_multiplatform.py      # Script principal de build
├── platforms/                  # Configuracoes por plataforma
│   ├── windows_amd64/
│   │   ├── venv/               # Ambiente virtual Windows
│   │   ├── requirements.txt    # Deps especificas Windows
│   │   └── build_config.json   # Config PyInstaller Windows
│   ├── macos_arm64/
│   │   ├── venv/               # Ambiente virtual macOS
│   │   ├── requirements.txt    # Deps especificas macOS
│   │   └── build_config.json   # Config PyInstaller macOS
│   └── debian_amd64/
│       ├── venv/               # Ambiente virtual Linux
│       ├── requirements.txt    # Deps especificas Linux
│       └── build_config.json   # Config PyInstaller Linux
├── dist/                       # Executaveis gerados
│   ├── windows_amd64/
│   │   ├── SSA_CLI_v3.10_windows_amd64.exe
│   │   └── SSA_GUI_v3.10_windows_amd64.exe
│   ├── macos_arm64/
│   │   ├── SSA_CLI_v3.10_macos_arm64
│   │   └── SSA_GUI_v3.10_macos_arm64.app
│   └── debian_amd64/
│       ├── SSA_CLI_v3.10_debian_amd64
│       └── SSA_GUI_v3.10_debian_amd64
└── resources/                  # Recursos compartilhados
    ├── app_icon.ico            # Icone Windows
    ├── app_icon.icns           # Icone macOS
    └── app_icon.png            # Icone Linux
```

## Uso

### Build Automatico (Detecta OS atual)
```bash
uv run --python 3.13 launchers/build_multiplatform.py
```

### Build especifico por Plataforma
```bash
uv run --python 3.13 launchers/build_multiplatform.py --platform windows_amd64
uv run --python 3.13 launchers/build_multiplatform.py --platform macos_arm64
uv run --python 3.13 launchers/build_multiplatform.py --platform debian_amd64
```

### Build Completo (Todas as plataformas compativeis)
```bash
uv run --python 3.13 launchers/build_multiplatform.py --all
```

### Opcoes Avancadas
```bash
uv run --python 3.13 launchers/build_multiplatform.py --clean          # Limpa builds anteriores
uv run --python 3.13 launchers/build_multiplatform.py --debug          # Build com debug info
uv run --python 3.13 launchers/build_multiplatform.py --all            # Build para plataforma atual
```

## configuracao de Ambiente

### Primeira Execucao
O script automaticamente:
1. Detecta a plataforma atual
2. Cria ambiente virtual especifico
3. Instala dependencias otimizadas
4. Configura PyInstaller
5. Gera executaveis

### dependencias por Plataforma

**Windows AMD64:**
- PyInstaller 6.0+
- Pandas (otimizado)
- PyQt6
- UPX (compressao opcional)

**macOS ARM64:**
- PyInstaller 6.0+
- Pandas (Apple Silicon)
- PyQt6 (ARM64)

**Debian AMD64:**
- PyInstaller 6.0+
- Pandas
- PyQt6
- Bibliotecas sistema (libGL, libX11)

## otimizacoes de Tamanho

### Tecnicas Aplicadas
1. **Exclusao de modulos desnecessarios**: Remove bibliotecas nao utilizadas
2. **Compressao UPX (quando disponivel)**: Pode reduzir tamanho em 50-70% (principalmente Windows/Linux)
3. **Strip symbols**: Remove informacoes de debug
4. **Shared libraries**: Reutiliza bibliotecas do sistema
5. **Tree shaking**: Inclui apenas codigo usado

### Politica de dados locais no build (v4.33+)

- O build canonico nao inclui `data/` por padrao.
- Esta regra reduz risco de vazamento de DB local em artefato final.
- Para laboratorio controlado, use copia explicita apos build:

```bash
uv run --python 3.13 scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
```

### Tamanhos Esperados
- **CLI**: 15-25 MB por plataforma
- **GUI**: 35-50 MB por plataforma

## Estrutura de Release

### Versionamento
Os executaveis seguem o padrao:
```
SSA_{CLI|GUI}_v{versao}_{plataforma}_{arquitetura}.{extensao}
```

Exemplo:
- `SSA_CLI_v3.10_windows_amd64.exe`
- `SSA_GUI_v3.10_macos_arm64.app`
- `SSA_CLI_v3.10_debian_amd64`

### Empacotamento Debian no baseline atual

- Saida operacional oficial para Debian: ZIP.
- AppImage/.deb nao sao gerados automaticamente pelo pipeline canonico atual.
- Se necessario, tratar AppImage/.deb como etapa manual/laboratorio fora do fluxo padrao.

### Manifesto de Release
Cada build gera um `release_manifest.json`:
```json
{
  "version": "3.10",
  "build_date": "2025-09-06T15:30:00Z",
  "platforms": [
    {
      "name": "windows_amd64",
      "cli_size": "18.5 MB",
      "gui_size": "42.1 MB",
      "python_version": "3.13.7",
      "dependencies": ["pandas==2.3.2", "PyQt6==6.9.1", ...]
    }
  ]
}
```

## Troubleshooting

### Problemas Comuns

**Erro de permissao (macOS/Linux):**
```bash
chmod +x launchers/build_multiplatform.py
```

**dependencias ausentes (Linux):**
```bash
sudo apt-get install python3-dev libgl1-mesa-dev libx11-dev
```

**PyQt6 nao encontrado (Windows):**
```bash
uv pip install --python 3.13 --upgrade PyQt6 --force-reinstall
```

### Limpeza de Ambiente
```bash
uv run --python 3.13 launchers/build_multiplatform.py --clean-all
```

Remove todos os ambientes virtuais e builds anteriores.

## Integracao CI/CD

### GitHub Actions
O script e compativel com workflows automatizados:

```yaml
- name: Build Executables
  run: uv run --python 3.13 launchers/build_multiplatform.py --all
  
- name: Upload Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: executables
    path: launchers/dist/
```

## Logs e Debug

### Localizacao dos Logs
- **Build logs**: `launchers/logs/build_{plataforma}_{timestamp}.log`
- **PyInstaller logs**: `launchers/platforms/{plataforma}/build.log`
- **Error logs**: `launchers/logs/errors_{timestamp}.log`

### Modo Debug
```bash
uv run --python 3.13 launchers/build_multiplatform.py --debug
```

Gera logs detalhados para diagnostico de problemas.
