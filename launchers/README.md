# Sistema de Build - Launchers

## CURRENT TRUTH (v4.47 stable)

- Pipeline oficial de build: `launchers/build_multiplatform.py`.
- Release estavel ativa: `v4.47`; tag anterior: `v4.46`.
- `origin` (GitLab) e `bitbucket` estao operacionais; o HTTP 403 afeta somente `gh` (GitHub) e publicacoes naquele provedor.
- Plataformas ativas:
  - `windows_amd64`
  - `macos_arm64`
  - `debian_amd64`
- Saida canonica: `launchers/dist/<plataforma>/`.
- Integracao de distribuicao: `scripts/create_distribution.py`.
- Referencias antigas (`windows_x64`, `windows_x86`, `macos_x64`, `linux_x64`) sao historicas.

## Inicio Rapido

```bash
# Build para plataforma atual
uv run --python 3.13 launchers/build_multiplatform.py --apps cli gui

# Build para plataforma explicita
uv run --python 3.13 launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui

# Teste basico dos artefatos
uv run --python 3.13 launchers/test_complete.py
```

## Estrutura Relevante

```text
launchers/
├── build_multiplatform.py
├── build_complete.py
├── build_simple.py
├── test_complete.py
├── test_executables.py
├── platforms/
│   ├── windows_amd64/
│   │   ├── build_config.json
│   │   └── requirements.txt
│   ├── macos_arm64/
│   │   ├── build_config.json
│   │   └── requirements.txt
│   └── debian_amd64/
│       ├── build_config.json
│       └── requirements.txt
└── dist/
    ├── windows_amd64/
    ├── macos_arm64/
    └── debian_amd64/
```

## Fluxo Recomendado

1. Executar build canonico.
2. Rodar validacao com `launchers/test_complete.py`.
3. Empacotar com `scripts/create_distribution.py`.
4. Publicar artefatos apenas apos smoke local.

## UPX (Windows opcional)

Para compressao opcional no Windows:

```bash
scoop install upx
```

Se `upx` nao estiver no `PATH`, o build continua sem compressao.

## Troubleshooting

### Plataforma nao detectada

```bash
uv run --python 3.13 launchers/build_multiplatform.py --detect-platform
```

### Limpeza de artefatos

```bash
uv run --python 3.13 launchers/build_multiplatform.py --clean
uv run --python 3.13 launchers/build_multiplatform.py --clean-all
```

### Logs de build

- logs principais: `launchers/logs/`
- manifest por plataforma: `launchers/dist/<plataforma>/build_manifest.json`

## Historical Snapshot

- Este README substitui texto legado v3.10 com targets antigos.
- Estado oficial de runtime/build deste snapshot antigo foi substituido pelo bloco `CURRENT TRUTH`.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
