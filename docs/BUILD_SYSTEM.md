# BUILD SYSTEM - SSA Consulta Rapida v4.0.0

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
uv run --python 3.13 build/build_all.py
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
