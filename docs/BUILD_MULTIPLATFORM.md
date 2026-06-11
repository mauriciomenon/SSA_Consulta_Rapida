# Build System Multi-Plataforma

Sistema automatizado para criacao de executaveis SSA Consulta Rapida para Windows, macOS e Linux.

## CURRENT TRUTH (4.42 local release candidate)

- Sync deste guia: `2026-05-22 09:22 -0300`.
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
  - Debian AMD64:
    - `bash dev_env/build/build_pyinstaller_debian.sh --silent`
    - `bash dev_env/build/build_nuitka_debian.sh --silent`
    - `bash dev_env/build/build_pyoxidizer_debian.sh --silent`
  - Debian ARM64:
    - `bash dev_env/build/build_pyinstaller_debian_arm64.sh --silent`
    - `bash dev_env/build/build_nuitka_debian_arm64.sh --silent`
    - `bash dev_env/build/build_pyoxidizer_debian_arm64.sh --silent`

## Local de saida e staging

- Artefatos finais:
  - PyInstaller via `launchers/build_multiplatform.py`:
    - `launchers/dist/<plataforma>/...`
  - PyInstaller via scripts legados em `dev_env/build/`:
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

Exemplos de nomes versionados neste documento usam v4.42 como baseline atual.
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
│   ├── debian_amd64/
│   │   ├── venv/               # Ambiente virtual Linux AMD64
│   │   ├── requirements.txt    # Deps especificas Linux AMD64
│   │   └── build_config.json   # Config PyInstaller Linux AMD64
│   └── debian_arm64/
│       ├── venv/               # Ambiente virtual Linux ARM64
│       ├── requirements.txt    # Deps especificas Linux ARM64
│       └── build_config.json   # Config PyInstaller Linux ARM64
├── dist/                       # Executaveis gerados
│   ├── windows_amd64/
│   │   ├── SSA_CLI_v4.42_windows_amd64.exe
│   │   └── SSA_GUI_v4.42_windows_amd64.exe
│   ├── macos_arm64/
│   │   ├── SSA_CLI_v4.42_macos_arm64
│   │   └── SSA_GUI_v4.42_macos_arm64.app
│   └── debian_amd64/
│       ├── SSA_CLI_v4.42_debian_amd64
│       └── SSA_GUI_v4.42_debian_amd64
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
uv run --python 3.13 launchers/build_multiplatform.py --platform debian_arm64
```

### Build de todos os apps da plataforma atual
```bash
uv run --python 3.13 launchers/build_multiplatform.py --current-platform
```

Observacao:
- `--current-platform` neste launcher nao faz cross-compilation.
- O efeito pratico e construir todos os apps (`cli` + `gui`) apenas para a plataforma detectada no host atual.

### Signing macOS

- `launchers/platforms/macos_arm64/build_config.json` usa `post_build.sign=true`.
- O builder atualiza `Info.plist`, assina novamente o `.app` e valida com `codesign --verify --deep --strict` antes de criar o DMG.
- A identidade padrao e assinatura ad-hoc (`-`). Para Developer ID, definir `MACOS_CODESIGN_IDENTITY`.

### Opcoes Avancadas
```bash
uv run --python 3.13 launchers/build_multiplatform.py --clean          # Limpa builds anteriores
uv run --python 3.13 launchers/build_multiplatform.py --clean-all      # Limpa builds e ambientes
uv run --python 3.13 launchers/build_multiplatform.py --debug          # Build com debug info
uv run --python 3.13 launchers/build_multiplatform.py --current-platform # Todos os apps da plataforma atual
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

**Debian AMD64/ARM64:**
- PyInstaller 6.0+
- Nuitka 4.0+ para trilha Nuitka
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
- `SSA_CLI_v4.42_windows_amd64.exe`
- `SSA_GUI_v4.42_macos_arm64.app`
- `SSA_CLI_v4.42_debian_amd64`

### Empacotamento Debian no baseline atual

- Saida operacional oficial para Debian continua sendo ZIP pelo pipeline canonico.
- `.deb` e AppImage existem como etapa manual de release por arquitetura, fora do `build_multiplatform.py`.
- Scripts disponiveis:
  - `dev_env/build/package_debian_amd64_deb.sh`
  - `dev_env/build/package_debian_amd64_appimage.sh`
  - `dev_env/build/package_debian_arm64_deb.sh`
  - `dev_env/build/package_debian_arm64_appimage.sh`
- Os scripts removem residuos locais do pacote final: `venv`, `.bak`, bancos locais, planilhas e `.env`.
- AppImage suporta `--prepare-only` para validar o AppDir quando `appimagetool` nao esta instalado.

### Manifesto de Build
Cada build gera um `build_manifest.json` dentro da pasta da plataforma:
```json
{
  "platform": "macos_arm64",
  "version": "4.42",
  "build_date": "2026-05-22T12:00:00.000000",
  "executables": [
    {
      "name": "SSA_GUI_v4.42_macos_arm64.app",
      "kind": "directory",
      "size_mb": 42.1,
      "path": "macos_arm64/SSA_GUI_v4.42_macos_arm64.app"
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

`--clean` e `--clean-all` removem `launchers/dist/`, `venv/` e `temp/` de todas as plataformas.
`--clean --platform <plataforma>` limita a remocao de `dist/`, `venv/` e `temp/` a plataforma informada.

## Integracao CI/CD

### GitHub Actions
O script e compativel com workflows automatizados:

```yaml
- name: Build Executables
  run: uv run --python 3.13 launchers/build_multiplatform.py --current-platform
  
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

<!-- DOC_SYNC_MAC: 2026-05-22 host-agnostic paths, continue from repo root on macOS -->
