# Build System Multi-Plataforma

Sistema automatizado para criacao de executaveis SSA Consulta Rapida para Windows, macOS e Linux.

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
python launchers/build_multiplatform.py
```

### Build especifico por Plataforma
```bash
python launchers/build_multiplatform.py --platform windows_amd64
python launchers/build_multiplatform.py --platform macos_arm64
python launchers/build_multiplatform.py --platform debian_amd64
```

### Build Completo (Todas as plataformas compativeis)
```bash
python launchers/build_multiplatform.py --all
```

### Opcoes Avancadas
```bash
python launchers/build_multiplatform.py --clean          # Limpa builds anteriores
python launchers/build_multiplatform.py --optimize       # Build otimizado (menor tamanho)
python launchers/build_multiplatform.py --debug          # Build com debug info
python launchers/build_multiplatform.py --release        # Build para release com versionamento
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

### Politica de dados locais no build (v4.32+)

- O build canonico nao inclui `data/` por padrao.
- Esta regra reduz risco de vazamento de DB local em artefato final.
- Para laboratorio controlado, use copia explicita apos build:

```bash
python scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
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
pip install --upgrade PyQt6 --force-reinstall
```

### Limpeza de Ambiente
```bash
python launchers/build_multiplatform.py --clean-all
```

Remove todos os ambientes virtuais e builds anteriores.

## Integracao CI/CD

### GitHub Actions
O script e compativel com workflows automatizados:

```yaml
- name: Build Executables
  run: python launchers/build_multiplatform.py --release --optimize
  
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
python launchers/build_multiplatform.py --debug --verbose
```

Gera logs detalhados para diagnostico de problemas.
