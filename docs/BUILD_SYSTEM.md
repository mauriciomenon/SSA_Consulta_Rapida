# BUILD SYSTEM - SSA Consulta Rapida v4.0.0

## CURRENT TRUTH (4.44 local / v4.36 published)

- Sync deste guia: `2026-07-06 09:45 -0300`.
- Este arquivo e historico e nao representa o fluxo atual de release.
- Baseline local ativo: `v4.44`; ultima tag publicada remota: `v4.36`.
- GitHub remoto esta bloqueado por HTTP 403; nao publicar nem reconstruir release remota ate desbloqueio.
- Fluxo atual:
  - `docs/BUILD_MULTIPLATFORM.md`
  - `docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md`
  - `docs/BUILD_NUITKA_GUIA_COMPLETO.md`
  - `docs/BUILD_PYOXIDIZER_GUIA_COMPLETO.md`
- Todos os comandos operacionais devem usar uv (`uv run --python 3.13 ...`).
- Nao usar comandos antigos deste arquivo com `pip`/`python` direto como fonte primaria.

##  **BUILD SYSTEM OTIMIZADO PARA v4.0.0**

###  **PERFORMANCE APRIMORADA NO BUILD:**
- Sistema de logging robusto integrado nos executaveis
- Cache inteligente para builds mais rapidos
- Otimizacoes automaticas aplicadas por padrao

## ESTRUTURA CRIADA

### ARQUIVOS BUILD:
```
build/
├── setup_build_env.sh      # Cria ambiente build
├── build_all.py            # Script principal build
├── convert_icon.py         # Converte SVG->ICO
├── cli_entry.py            # Entry point CLI
└── gui_entry.py            # Entry point GUI

requirements_build.txt       # Deps apenas build
```

### OUTPUT ESPERADO:
```
dist/
├── SSA_CLI.exe             # Executavel CLI
├── SSA_GUI.exe             # Executavel GUI
├── config/                 # Configs compartilhadas
└── data/                   # Banco compartilhado
```

## COMO USAR

### 1. SETUP AMBIENTE BUILD:
```bash
./build/setup_build_env.sh
```

### 2. ATIVAR E COMPILAR:
```bash
source build_env/bin/activate
uv run --python 3.13 launchers/build_multiplatform.py
```

### 3. TESTAR:
```bash
./dist/SSA_CLI.exe --help
./dist/SSA_GUI.exe
```

## CARACTERISTICAS

### SEGURANCA:
- Arquivos Python protegidos (onefile)
- Nao expostos ao usuario final
- Dificil de reverter engenharia

### TAMANHO:
- CLI: ~50MB (console)
- GUI: ~60MB (windowed)
- Compartilham data/ e config/

### COMPATIBILIDADE:
- Sem alertas antivirus (PyInstaller confiavel)
- Executaveis independentes
- Sem instalacao necessaria

**PRONTO PARA TESTAR!**

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
