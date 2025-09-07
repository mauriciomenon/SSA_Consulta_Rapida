# BUILD SETUP - SSA Consulta Rapida
# Analise inicial e estrutura para compilacao

## SITUACAO ATUAL

### ESTRUTURA IDENTIFICADA:
- main.py: Entry point principal
- gui/: Interface grafica PyQt6
- interface/cli.py: Interface linha comando
- resources/app_icon.svg: Icone disponivel (SVG)

### REQUISITOS ANALISADOS:

1. **ARQUIVOS PROTEGIDOS**: Viavel com --onefile + --noconsole
2. **DOIS EXECUTAVEIS**: Viavel - CLI e GUI separados
3. **BANCO COMPARTILHADO**: Viavel - mesma pasta data/
4. **ICONE**: Precisa converter SVG para ICO
5. **DOIS PYENVS**: Recomendado - dev + build

## ESTRUTURA PROPOSTA

### AMBIENTE BUILD:
```
/build_env/          # Python env apenas para build
├── requirements_build.txt
└── scripts/
    ├── build_cli.py
    ├── build_gui.py
    └── convert_icon.py
```

### OUTPUTS:
```
/dist/
├── SSA_CLI.exe      # Executavel CLI
├── SSA_GUI.exe      # Executavel GUI  
├── data/            # Pasta compartilhada
└── config/          # Configuracoes compartilhadas
```

## PROXIMOS PASSOS

1. Converter SVG para ICO
2. Criar requirements_build.txt
3. Criar scripts de build
4. Testar compilacao

**CONFIRMA ESTA ESTRUTURA ANTES DE IMPLEMENTAR?**
