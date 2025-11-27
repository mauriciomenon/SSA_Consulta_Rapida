---
applyTo: '**/build*.bat,**/build*.py,**/*.spec,**/pyproject.toml,**/requirements*.txt'
description: Instrucoes para build e empacotamento do projeto
---

# Build e Empacotamento

## Sistemas de Build Disponiveis

| Sistema | Arquivo | Uso |
|---------|---------|-----|
| PyInstaller | `build_pyinstaller.bat` | Producao - recomendado |
| Nuitka | `build_nuitka.bat` | Performance maxima |
| PyOxidizer | `build_pyoxidizer.bat` | Experimental |

## PyInstaller (Principal)

### Executar build
```batch
build_pyinstaller.bat
```

### Arquivos gerados
```
dist/SSA_Consulta_Rapida/
├── SSA_Consulta_Rapida.exe
├── config/                    # Configs copiadas
└── [dependencias]

builds/pyinstaller/            # Copia final
```

### Spec file
O arquivo `SSA_Consulta_Rapida.spec` controla o build.

## Dependencias

### requirements.txt (Producao)
```
pandas>=2.0.0
openpyxl>=3.1.0
PyQt6>=6.5.0
```

### requirements_dev.txt (Desenvolvimento)
```
pytest>=7.0.0
mypy>=1.0.0
ruff>=0.1.0
```

### requirements_build.txt (Build)
```
pyinstaller>=6.0.0
nuitka>=2.0.0
```

## Ferramentas MCP para Build

### Sonatype
Antes de adicionar dependencia:
```
getRecommendedComponentVersions - Verificar melhor versao
getComponentVersion - Verificar CVEs
```

### Snyk
Apos build:
```
snyk_test - Verificar vulnerabilidades
snyk_container_scan - Se usar Docker
```

### Codacy
Apos editar scripts de build:
```
codacy_cli_analyze - Verificar qualidade
```

## Checklist Pre-Build

1. [ ] Atualizar VERSION se necessario
2. [ ] Rodar testes: `pytest`
3. [ ] Verificar dependencias: Sonatype
4. [ ] Limpar builds anteriores
5. [ ] Executar build
6. [ ] Testar executavel gerado
7. [ ] Verificar se config/ foi copiado

## Troubleshooting

### Hidden imports
Se faltar modulo no executavel:
```
--hidden-import=modulo_faltando
```

### Data files
Se faltar arquivo de dados:
```
--add-data="caminho;destino"
```

### Antivirus falso positivo
PyInstaller pode gerar falsos positivos. Opcoes:
- Assinar executavel
- Usar Nuitka (menos deteccoes)
- Adicionar excecao no AV

## Versioning

### Arquivo VERSION
```
1.2.3
```

### Atualizar versao
1. Editar `VERSION`
2. Atualizar `CHANGELOG.md`
3. Commit com tag: `git tag v1.2.3`
