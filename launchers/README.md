# Sistema de Build - Launchers

## CURRENT TRUTH (2026-10-25, release v4.51 publicada; estabilizacao no branch rev)

- Pipeline oficial de build: `launchers/build_multiplatform.py`.
- Ultima release publicada: `v4.51` (tag -> `e2481cf4`, merge do PR #135 em 2026-09-29; release no GitHub em 2026-09-30; assets e SHA-256 em `RELEASE_NOTES_v4.51.md`).
- Em andamento: estabilizacao no branch `rev`, sem tag. O build do REL-01 e de teste de processo: sai do `rev` e o `build_info.json` registra branch e commit. O build oficial sai do `main`, depois do PR.
- Plataformas ativas (`build_multiplatform.py --list-platforms`; cada build roda no host do alvo):
  - `windows_amd64`
  - `windows_arm64`
  - `macos_arm64`
  - `debian_amd64`
  - `debian_arm64`
- Saida canonica: `launchers/dist/<plataforma>/`.
- Integracao de distribuicao: `scripts/create_distribution.py`.
- Referencias antigas (`windows_x64`, `windows_x86`, `macos_x64`, `linux_x64`) sao historicas.
- Publicacao neste checkout: `origin` envia ao GitHub principal e ao GitLab; o push URL do espelho `schottge-menon` esta comentado em `.git/config` (conta suspensa). Conferir a configuracao antes de usar em outro clone.
- Os builds locais da candidata v4.51 (2026-09-24, a partir de `a2954a48`) nao sao os assets publicados: a release traz um pacote por alvo, inclusive Debian amd64 e arm64.

## Inicio Rapido

```bash
# Build para plataforma atual
uv run --no-sync launchers/build_multiplatform.py --apps cli gui

# Build para plataforma explicita
uv run --no-sync launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui

# Teste basico dos artefatos
uv run --no-sync launchers/test_complete.py
```

## Estrutura Relevante

```text
launchers/
├── build_multiplatform.py
├── build_complete.py
├── build_simple.py
├── test_complete.py
├── test_executables.py
├── platforms/                      # build_config.json + requirements.txt por alvo
│   ├── windows_amd64/
│   ├── windows_arm64/
│   ├── macos_arm64/
│   ├── debian_amd64/
│   └── debian_arm64/
└── dist/                           # mesmo nome de alvo: launchers/dist/<plataforma>/
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
uv run --no-sync launchers/build_multiplatform.py --detect-platform
```

### Limpeza de artefatos

```bash
uv run --no-sync launchers/build_multiplatform.py --clean
uv run --no-sync launchers/build_multiplatform.py --clean-all
```

### Logs de build

- logs principais: `launchers/logs/`
- manifest por plataforma: `launchers/dist/<plataforma>/build_manifest.json`

## Historical Snapshot

- Este README substitui texto legado v3.10 com targets antigos.
- Estado oficial de runtime/build deste snapshot antigo foi substituido pelo bloco `CURRENT TRUTH`.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
