# Comparação: build_simple.py vs build_multiplatform.py

Este documento sumariza as diferenças principais entre os scripts de build existentes em `launchers/` e explica para que cada um foi projetado, com foco especial em builds Windows.

Arquivos comparados:
- `launchers/build_simple.py`
- `launchers/build_multiplatform.py`

## Resumo rápido
- `build_simple.py`: script leve e rápido para gerar um executável de desenvolvimento (usa `dist_simple`, limpa automaticamente). Ideal para developers que querem validar um exe localmente em poucos segundos.
- `build_multiplatform.py`: sistema completo e robusto para builds reproduzíveis em múltiplas plataformas (Windows, macOS, Debian). Gerencia virtualenvs por plataforma, configurações por plataforma, pós-processamento (UPX), manifests e integração git/CI.

## Diferenças por categoria

### Propósito
- build_simple.py: build de triagem/desenvolvimento rápido. Não pretende ser usado em release automatizado.
- build_multiplatform.py: build oficial/CI para produzir artefatos distribuíveis para diferentes plataformas.

### Ambiente e dependências
- build_simple.py: usa o Python/ambiente atual e executa PyInstaller diretamente (sem criar venv isolado).
- build_multiplatform.py: cria e gerencia um `venv` por plataforma em `launchers/platforms/{platform}/venv` e instala `requirements.txt` específicos por plataforma.

### Configuração e parametrização
- build_simple.py: flags PyInstaller hardcoded (alguns `hidden-imports`) e nome fixo do executável (`SSA_CLI_v3.10_SIMPLES`).
- build_multiplatform.py: carrega `build_config.json` por plataforma (`launchers/platforms/{platform}/build_config.json`) e monta as flags dinamicamente (`pyinstaller_args`, `cli_config`, `gui_config`).

### Pós-processamento e metadados
- build_simple.py: não possui pós-processamento.
- build_multiplatform.py: compressão opcional com UPX, criação de `build_manifest.json` contendo metadados (tamanho, nome, versão), limpeza avançada e rotação de logs.

### Integração com git e CI
- build_simple.py: sem integração git automatizada.
- build_multiplatform.py: pode commitar/pushar artefatos e metadados (`--auto-git`), além de oferecer limpeza online de arquivos rastreados indevidamente.

### Limpeza de artefatos
- build_simple.py: `dist_simple` temporário é removido automaticamente (atexit).
- build_multiplatform.py: possui `cleanup_build_artifacts()` que remove caches, builds antigos, `dist_simple`, arquivos temporários e mantém apenas os últimos logs.

### Teste do executável
- build_simple.py: testa o exe gerado com `--help` e valida o retorno (quick smoke test).
- build_multiplatform.py: foca em gerar artefatos e manifest; integração de testes geralmente é feita no pipeline externo (mas o script pode ser estendido para isso).

## Comportamento específico no Windows
- `build_multiplatform.py` contém mapeamentos explícitos para `windows_amd64` (ex.: `python_exe = python.exe`, `executable_ext = .exe`) e usa caminhos Windows-aware (`venv\Scripts\python.exe`). Também detecta ausência de UPX e avisa.
- `build_simple.py` funciona em Windows desde que `pyinstaller` esteja disponível no PATH.

## Onde os artefatos Windows aparecem (exemplo no repositório)
- `launchers/dist/windows_amd64/SSA_CLI_v3.11_windows_amd64.exe`
- `launchers/dist/windows_amd64/SSA_GUI_v3.11_windows_amd64.exe`
- `launchers/dist/windows_amd64/build_manifest.json`

## Como usar (comandos exemplares)

Build rápido (desenvolvimento):
```powershell
python launchers/build_simple.py
```

Build Windows (reprodutível, plataforma atual):
```powershell
python launchers/build_multiplatform.py --platform windows_amd64
```

Build atual detectado (faz build para a plataforma atual):
```powershell
python launchers/build_multiplatform.py
```

Passos para CI / release recomendados:
1. Usar `build_multiplatform.py` em runner correspondente (Windows runner para windows_amd64, macOS runner para macos_arm64, etc.).
2. Habilitar `--auto-cleanup` e `--auto-git` se quiser que manifests e docs sejam committados automaticamente (cautela: script evita commitar executáveis).
3. Anexar `build_manifest.json` e executáveis ao GitHub Release (ex.: `gh release upload`).

## Recomendações de consolidação (opcional)
- Mantenha ambos: `build_simple.py` como wrapper rápido para dev, e `build_multiplatform.py` como sistema oficial de build/CI.
- Alternativa: transformar `build_simple.py` em um pequeno wrapper que chama internamente as funções de `build_multiplatform.py` com um perfil `dev` (gera `dist_simple`). Isso evita duplicação de lógica (construir comando PyInstaller).

## Observações finais
- `build_simple.py` é intencionalmente limitado (simplicidade e limpeza automática). `build_multiplatform.py` é mais complexo por design: venvs, configs por plataforma, pós-processamento e operações git.
- Antes de automatizar uploads de executáveis para releases, confirme política de versão e checagens de integridade (assinatura, checksums) se necessário.

---

Arquivo gerado automaticamente pelo agente em: `docs/BUILD_SCRIPTS_COMPARISON.md`
