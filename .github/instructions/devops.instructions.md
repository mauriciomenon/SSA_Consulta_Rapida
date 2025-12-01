---
applyTo: '**/Dockerfile,**/*.yaml,**/*.yml,**/docker-compose*,**/.github/workflows/**,**/ci/**'
description: Instrucoes para CI/CD com GoReleaser, Docker, Sentry
---

# DevOps e CI/CD

## Ferramentas MCP Disponiveis

### GoReleaser (`io.github.goreleaser/mcp`)

```
Build e release automatizado:
- Binarios multiplataforma
- Checksums automaticos
- Upload para GitHub Releases
- Changelog automatico
```

### Docker MCPs

```
Servidores que rodam em Docker:
- SonarQube: Analise de codigo
- Elasticsearch: Busca full-text
- Sentry: Monitoramento de erros
```

### Sentry (`getsentry/sentry-mcp`)

```
Monitoramento em producao:
- Rastreamento de exceptions
- Performance monitoring
- Release tracking
```

## Estrutura CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements_dev.txt

      - name: Run tests
        run: pytest --cov=.

      - name: Run Codacy Analysis
        uses: codacy/codacy-analysis-cli-action@master

  build:
    needs: test
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build with PyInstaller
        run: |
          pip install -r requirements_build.txt
          pyinstaller SSA_Consulta_Rapida.spec
```

### Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: ./build_pyinstaller.bat

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

## Docker Compose

### Ambiente de Desenvolvimento

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  sonarqube:
    image: mcp/sonarqube
    ports:
      - "9000:9000"
    environment:
      - SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true

  elasticsearch:
    image: docker.elastic.co/mcp/elasticsearch
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node

  sentry:
    image: getsentry/sentry
    ports:
      - "9001:9000"
```

## Monitoramento com Sentry

### Configuracao Python

```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://xxx@sentry.io/yyy",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment="production",
    release="ssa-consulta@1.0.0",
)
```

### Captura de Erros

```python
try:
    processar_ssa(numero)
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise
```

### Contexto Adicional

```python
with sentry_sdk.push_scope() as scope:
    scope.set_tag("ssa_numero", numero)
    scope.set_context("ssa", {"tipo": tipo, "status": status})
    sentry_sdk.capture_message("SSA processada")
```

## Build Multiplataforma

### PyInstaller (Windows)

```batch
@echo off
REM build_pyinstaller.bat
pyinstaller ^
    --onefile ^
    --windowed ^
    --name SSA_Consulta_Rapida ^
    --icon resources/icon.ico ^
    main.py
```

### Nuitka (Performance)

```batch
@echo off
REM build_nuitka.bat
python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    main.py
```

## Checklist de Release

```
Pre-release:
[ ] Todos os testes passando
[ ] Codacy sem issues criticos
[ ] Snyk sem vulnerabilidades altas
[ ] Changelog atualizado
[ ] Versao incrementada

Build:
[ ] Build Windows OK
[ ] Executavel testado
[ ] Tamanho aceitavel

Release:
[ ] Tag criada
[ ] GitHub Release criado
[ ] Binario anexado
[ ] Release notes escritas

Pos-release:
[ ] Sentry release registrado
[ ] Monitoramento ativo
[ ] Usuarios notificados
```

## Integracao MCPs no CI

### Analise automatica:

```yaml
- name: Security Scan
  run: |
    snyk test
    snyk code test

- name: Code Quality
  run: |
    codacy-analysis-cli analyze
```

### Verificacao de dependencias:

```yaml
- name: Dependency Check
  run: |
    pip-audit
    snyk test --all-projects
```
