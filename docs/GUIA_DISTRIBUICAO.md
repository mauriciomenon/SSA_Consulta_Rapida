# Guia de Distribuicao - SSA Consulta Rapida

## CURRENT TRUTH (2026-10-25, release v4.51 publicada; estabilizacao no branch rev)

- Branch fonte local desta rodada: `rev`; `dev` segue como branch de fase (CD-22).
- Ultima release publicada: `v4.51` (tag -> `e2481cf4`, merge do PR #135 em 2026-09-29; release no GitHub em 2026-09-30; assets e SHA-256 em `RELEASE_NOTES_v4.51.md`).
- Em andamento: estabilizacao no branch `rev`, sem tag. O build do REL-01 e de teste de processo: sai do `rev` e o `build_info.json` registra branch e commit. O build oficial sai do `main`, depois do PR.
- Entradas operacionais primarias: `release.ps1` no Windows e `release.sh` no Debian/macOS.
- Comando canonico para build Windows: `.\release.ps1 -Target windows -Backend pyinstaller -Yes` (sem banco). `-IncludeRuntimeDb` embute o `data\ssas.db` operacional desta maquina no pacote: use so quando o pacote for para quem pode ver esses dados. Os ZIPs locais v4.51 desta rodada foram gerados sem banco operacional.
- Debian/macOS: `./release.sh` no clone nativo do proprio host; `dev_env/build/release_windows.ps1` continua implementacao interna do fluxo Windows.
- Nao compartilhar checkout ou venv entre Windows e WSL/Linux. Validacao Linux exige clone Linux proprio; build Windows usa ferramentas Windows nativas.
- Artefatos `v4.51` e anteriores sao historicos para a rodada `rev`.
- Publicacao neste checkout: `origin` envia ao GitHub principal e ao GitLab; o push URL do espelho `schottge-menon` esta comentado em `.git/config` (conta suspensa). Conferir a configuracao antes de usar em outro clone.
- Os builds locais da candidata v4.51 (2026-09-24, a partir de `a2954a48`) nao sao os assets publicados: a release traz um pacote por alvo, inclusive Debian amd64 e arm64.

## HISTORICAL SNAPSHOT 2026-06-11 11h

- Branch fonte: `dev`.
- Branch destino: `main`.
- Base minima sincronizada: `4705c2e5722c4f3a5266ac02a5d15a1928d5a223 2026-05-04T02:07:12-03:00 Merge PR #59: sync docs and required CI`; usar este commit ou sucessor sincronizado em `main`/`dev`.
- PR #58 e PR #59: merged; `main`, `dev`, `origin/main` e `origin/dev` devem estar sincronizados antes de qualquer rebuild.
- Artefatos v4.43 anteriores a base minima `4705c2e5722c4f3a5266ac02a5d15a1928d5a223` estao stale e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
  - Windows AMD64: `pyinstaller`, `nuitka` + `zip`.
  - Debian AMD64/ARM64: `pyinstaller`, `nuitka` + `deb`, `appimage`, `tar`.
  - macOS ARM64: `pyinstaller` + `dmg`.
- Interface operacional primaria:
  - Windows: `release.ps1`.
  - Debian/macOS: `release.sh`.
- Orquestradores ativos:
  - Local Windows + WSL: `dev_env/build/release_local.ps1`.
  - Windows AMD64: `dev_env/build/release_windows.ps1`.
  - Debian AMD64: `dev_env/build/release_debian.sh`.
  - Debian ARM64: `dev_env/build/release_debian_arm64.sh`.
  - macOS ARM64: `release.sh` -> `launchers/build_multiplatform.py`.
- Dry-run previamente validado para os orquestradores; depois do merge PR #58, o proximo ciclo deve rodar dry-run novamente antes de build real.
- Protecao de codigo:
  - Nuitka e o backend preferencial para release protegido.
  - PyInstaller tem protecao parcial.
- `setup_env.sh` e `setup_env.ps1` nao executam instalador remoto de pyenv sem opt-in e SHA256 explicitos.
- `dev_env/setup_msvc_path.ps1` e diagnostico/sessao; nao altera PATH permanente do usuario por padrao.
- Proximo passo operacional historico: rebuildar Windows AMD64, Debian AMD64, Debian ARM64 e macOS ARM64 a partir deste HEAD, validar conteudo/metadata/smoke e so entao atualizar release v4.43.

## Comandos Simples De Release

Use estes comandos como entrada primaria. Os scripts em `dev_env/build/` sao
implementacao interna e devem ser usados diretamente apenas para diagnostico.

Windows AMD64, PyInstaller com instalador, sem banco operacional:

```powershell
.\release.ps1 -Target windows -Backend pyinstaller -Yes
```

Opcional, embute o `data\ssas.db` desta maquina (dados operacionais) no pacote:

```powershell
.\release.ps1 -Target windows -Backend pyinstaller -IncludeRuntimeDb -Yes
```

Debian AMD64 em host/VM e clone Linux nativos:

```bash
./release.sh
```

macOS ARM64, default PyInstaller e DMG:

```bash
./release.sh
```

VM/host Debian remoto:

```bash
./release.sh --target debian --ssh-host user@host --ssh-repo /home/user/SSA_Consulta_Rapida --yes
```

macOS local + Debian AMD64/ARM64 remoto:

```bash
./release.sh --target all --ssh-host user@host --ssh-repo /home/user/SSA_Consulta_Rapida --yes
```

Dry-run macOS sem remoto Debian:

```bash
./release.sh --target all --dry-run --allow-missing-remote
```

## HISTORICAL SNAPSHOT (4.37 local automation)

- Sync deste guia: `2026-05-01 13:20 -0300`.
- Versao de referencia local: `4.37` (arquivo `VERSION`).
- Fluxo automatico local Windows + Debian AMD64: `dev_env/build/release_local.ps1`.
- Fluxo automatico Windows AMD64: `dev_env/build/release_windows.ps1`.
- Fluxo automatico Debian AMD64: `dev_env/build/release_debian.sh`.
- Saida de release Windows AMD64: `builds/packages/windows_amd64/` e `dist_packages/`.
- Saida de release Debian AMD64: `builds/packages/debian_amd64/`.
- Backends reconhecidos pelo parser do empacotador: `pyinstaller`, `nuitka`.
- Backends de release operacional neste baseline: `pyinstaller`, `nuitka`.
- O PyOxidizer foi removido na v4.52: o pyoxidizer 0.24.0 esta sem manutencao desde 2022-12-30 e so embute CPython 3.10, que o projeto nao suporta mais.
- `pytoexe`/`py2exe`: nao suportados neste repositorio (fora das choices dos scripts atuais).

## Release Automatico Local (historico)

O bloco abaixo preserva o fluxo antigo Windows + WSL para auditoria. Ele nao e permitido
na release v4.50 e nao deve ser executado.

```powershell
.\dev_env\build\release_local.ps1 -Backend all -DebianPackage all -Yes
```

Dry-run sem build/pacote:

```powershell
.\dev_env\build\release_local.ps1 -Backend all -DebianPackage all -Yes -DryRun
```

Somente Windows:

```powershell
.\dev_env\build\release_windows.ps1 -Backend all -Yes
```

Somente Debian AMD64 no clone Linux nativo:

```bash
cd "$HOME/gitlab_repo/ssa_consulta_rapida_pyqt6"  # no WSL esta pasta e obrigatoria; ~/gitlab e bloqueada
bash dev_env/build/release_debian.sh --backend all --package all -y
```

Contrato do fluxo:
- `-Yes`/`-y` e obrigatorio para execucao automatica sem prompt.
- `-DryRun`/`--dry-run` deve validar ambiente e plano sem build nem pacote.
- `release_windows.ps1` nao chama Bash/WSL.
- `release_debian.sh` nao chama PowerShell, `.bat` ou Inno Setup.
- `release_local.ps1` e legado e nao faz parte do fluxo permitido da v4.50.

## Validacao Operacional 2026-03-10 (host macOS arm64)

Status de ferramentas no host:
- `pyinstaller`: OK (`6.19.0`)
- `nuitka`: OK (`4.0.1`)
- `pyoxidizer`: OK (`0.24.0`)
- `iscc`: NOT_FOUND
- `pytoexe`: NOT_FOUND
- `py2exe`: NOT_FOUND

Resultado de tentativa de pacote (scripts/create_distribution.py):
- `pyinstaller --skip-installer`: OK (ZIP gerado)
- `pyinstaller` (com installer): ZIP OK, installer FAIL (origem Windows/Inno nao resolvida neste host)
- `nuitka --skip-installer`: FAIL (build ausente em `builds/nuitka`)
- `pyoxidizer --skip-installer`: FAIL (build ausente em `builds/pyoxidizer`)
- `pytoexe`: FAIL esperado (choice invalida)

Evidencia local desta publicacao:
- logs consolidados: `/tmp/ssa_pack_audit_20260310_1030/summary.log`
- artefato alvo desta publicacao: `dist_packages/SSA_Consulta_Rapida_v4.37_pyinstaller.zip`

## Visao Geral

Este guia descreve como gerar pacotes para distribuicao em Windows, macOS e Debian/Linux
usando o fluxo canonico atual.

Nota Debian:
- no baseline atual, Debian usa `.deb` como pacote padrao no wrapper de release.
- AppImage e tar continuam disponiveis por arquitetura quando suportados pela matriz.
- scripts disponiveis para AMD64 e ARM64 ficam em `dev_env/build/package_debian_*`.

## Build Canonico

### 1) Build da plataforma atual

```bash
uv run --no-sync launchers/build_multiplatform.py --apps cli gui
```

### 2) Build de plataforma especifica

```bash
uv run --no-sync launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui
uv run --no-sync launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui
uv run --no-sync launchers/build_multiplatform.py --platform debian_amd64 --apps cli gui
uv run --no-sync launchers/build_multiplatform.py --platform debian_arm64 --apps cli gui
```

### 3) Verificar saida do build

```bash
uv run --no-sync launchers/test_complete.py
```

## Empacotamento para Distribuicao

### 1) Criar ZIP

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller --skip-installer
```

Para incluir um banco local escolhido explicitamente:

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller --skip-installer --include-local-db data/ssas.db
```

### 2) Criar instalador Windows (Inno Setup)

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller
```

Para incluir um banco local escolhido explicitamente:

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller --include-local-db data/ssas.db
```

Notas:
- O script tenta localizar Inno Setup por:
  1. `INNO_SETUP_COMPILER`
  2. `iscc` no PATH
  3. caminhos padrao do Windows
- Se Inno Setup nao estiver disponivel, o ZIP continua funcional.
- O ZIP vai para `builds/packages/<plataforma>/`; o script `.iss` e o instalador, para `dist_packages/`.

### 3) Criar pacote de outros build systems (laboratorio)

```bash
uv run --no-sync scripts/create_distribution.py --build-system nuitka --skip-installer
```

Importante:
- Para Windows/Debian protegido, usar Nuitka como padrao.
- Para macOS ARM64, usar PyInstaller + DMG.

### 4) Criar .deb e AppImage Debian manualmente

Fluxo recomendado para Debian AMD64:

```bash
bash dev_env/build/release_debian.sh --backend pyinstaller,nuitka --package deb -y
```

Fluxo remoto por SSH:

```bash
bash dev_env/build/release_debian.sh --ssh-host user@host --ssh-repo /home/user/SSA_Consulta_Rapida --backend pyinstaller,nuitka --package deb -y
```

AppImage Debian AMD64:

```bash
bash dev_env/build/release_debian.sh --backend pyinstaller,nuitka --package appimage -y
```

O orquestrador valida workspace limpo, `config/build_info.json`,
`docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md`, conteudo de `.deb` e gera
`builds/reports/release_report_debian_amd64.json`.

Comandos manuais por wrapper continuam disponiveis:

```bash
bash dev_env/build/package_debian_amd64_deb.sh --build-system pyinstaller
bash dev_env/build/package_debian_amd64_appimage.sh --build-system pyinstaller --prepare-only
bash dev_env/build/package_debian_arm64_deb.sh --build-system pyinstaller
bash dev_env/build/package_debian_arm64_appimage.sh --build-system pyinstaller --prepare-only
```

Notas Debian:
- `.deb` aceita `pyinstaller` e `nuitka`.
- AppImage aceita `pyinstaller` e `nuitka`.
- Debian ARM64 requer host Debian ARM64 nativo; este fluxo nao faz cross-compilation.
- `--prepare-only` valida AppDir sem exigir `appimagetool`.
- Os pacotes finais removem residuos locais: `venv`, backups `.bak`, bancos, planilhas e `.env`.

## Mapa de Pastas de Build

### Pastas temporarias (nunca versionar)

- PyInstaller: `launchers/platforms/<plataforma>/temp/`
- Nuitka: `builds/nuitka/<plataforma>/*.build/`

### Artefatos linkados/intermediarios (nunca versionar)

- Tradicional (PyInstaller, canonico): `launchers/dist/<plataforma>/`
- Tradicional (equivalente/espelho): `builds/pyinstaller/<plataforma>/`
- Nuitka: `builds/nuitka/<plataforma>/<entry>.dist/`

### Artefatos finais de distribuicao (nunca versionar)

- ZIP final: `builds/packages/<plataforma>/`
- Instalador Inno Setup: `dist_packages/`
- `.deb` e AppImage Debian manual: `builds/packages/<plataforma>/`
- Script `.iss` gerado: `dist_packages/installer_<backend>.iss`

### Exes principais esperados (Windows)

- Tradicional (PyInstaller, onedir): `launchers/dist/windows_amd64/SSA_GUI_v<versao>_windows_amd64/SSA_GUI_v<versao>_windows_amd64.exe`
- Tradicional (equivalente/espelho): `builds/pyinstaller/windows_amd64/SSA_GUI_v<versao>_windows_amd64/SSA_GUI_v<versao>_windows_amd64.exe`
- Nuitka: `builds/nuitka/windows_amd64/gui_entry.dist/SSA_GUI_v<versao>_windows_amd64.exe`

### Exes principais esperados (Debian)

Use `<plataforma>` como `debian_amd64` ou `debian_arm64`.

- Tradicional (PyInstaller, onedir): `launchers/dist/<plataforma>/SSA_GUI_v<versao>_<plataforma>/SSA_GUI_v<versao>_<plataforma>`
- Tradicional (equivalente/espelho): `builds/pyinstaller/<plataforma>/SSA_GUI_v<versao>_<plataforma>/SSA_GUI_v<versao>_<plataforma>`
- Nuitka: `builds/nuitka/<plataforma>/gui_entry.dist/SSA_GUI_v<versao>_<plataforma>`

## Estrutura Esperada dos Pacotes

Pacote ZIP:

```text
SSA_Consulta_Rapida_v<versao>_<build_system>/
├── <executavel_principal>
├── BancoLocal/                    # opcional com --include-local-db
├── config/
├── docs/
├── LEIA-ME-USUARIO.txt
├── LEIA-ME.txt
└── VERSION.txt
```

No caminho canonico de empacotamento, diretorios de dados locais sensiveis nao entram no bundle:
- `data`
- `docs_entrada`
- `docs_saida`
- `logs`
- `reports`
- `exportacao`

Politica operacional (v4.43+):
- build canonico nao embeda `data/` por padrao.
- se for necessario incluir dados locais para laboratorio, usar fluxo explicito e controlado:
  - `uv run --no-sync scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data`
  - nunca usar isso para pacote de distribuicao geral.
- banco local da maquina que gerou o pacote continua bloqueado no empacotador.
- `--include-local-db <caminho>` libera apenas o arquivo `.db` indicado no parametro.
- com `--include-local-db`, o ZIP recebe esse arquivo em `BancoLocal/`.
- no instalador Windows, o banco local escolhido vai para `{userdocs}\\SSA Consulta Rapida\\BancoLocal`.

## Distribuicao para Usuario Final

Texto sugerido:

```text
SSA Consulta Rapida v<versao publicada>

INSTALACAO
1. Baixe o arquivo ZIP.
2. Extraia para uma pasta local.
3. Entre na pasta extraida.
4. Execute o binario principal.

PRIMEIRO USO
1. Coloque arquivos de entrada em docs_entrada/.
2. Execute Atualizar Dados ou Reescaneamento Completo conforme o caso.

BANCO LOCAL OPCIONAL
1. Se o pacote tiver sido gerado com `--include-local-db`, use o banco em `BancoLocal/`.
2. O empacotador inclui somente o caminho indicado no parametro.
3. Esse fluxo e intencional para quando voce realmente quiser distribuir um banco local escolhido conscientemente.

SUPORTE
- Logs em logs/ssa.log
- Guia de antivirus em docs/ANTIVIRUS_EXCLUSOES.md
```

## Checklist de Release

- [ ] Build canonico concluido em `launchers/dist/<plataforma>/`.
- [ ] `launchers/test_complete.py` sem erro bloqueante.
- [ ] ZIP gerado em `builds/packages/<plataforma>/`.
- [ ] Instalador (quando aplicavel) gerado em `dist_packages/`.
- [ ] Nome inclui versao e build system.
- [ ] Smoke manual: `--version`, `--help`, `--gui`.

## Troubleshooting Rapido

### ZIP nao gerado

1. Confirmar build em `launchers/dist/<plataforma>/`.
2. Confirmar que existe executavel primario no diretorio alvo (nao apenas manifesto/log).
3. Para PyInstaller, o empacotador agora valida executavel antes de aceitar o build canonico.
4. Em laboratorio, `canonical_dirs` pode ser configurado em `BUILD_SYSTEMS["pyinstaller"]`.
5. Executar novamente com log:

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller --skip-installer
```

### Instalador nao gerado

1. Se log mostrar `Inno Setup nao encontrado`, instalar Inno Setup ou definir `INNO_SETUP_COMPILER`.
2. Se log mostrar `Falha na compilacao`, revisar saida de erro do ISCC e dependencias do build.
3. Opcional: definir compilador explicitamente:

```bash
set INNO_SETUP_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller
```

### Copia de dados locais para build

O script `scripts/copy_data_to_builds.py` exige confirmacao explicita:

```bash
uv run --no-sync scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
```

Use somente em ambiente controlado.

### Banco local opcional

Se voce quer um pacote com um banco local especifico, use:

```bash
uv run --no-sync scripts/create_distribution.py --build-system pyinstaller --include-local-db data/ssas.db
```

Contrato dessa flag:
- inclui so o arquivo `.db` indicado no parametro
- o arquivo vai para `BancoLocal/` no ZIP
- no instalador Windows, o arquivo vai para `{userdocs}\\SSA Consulta Rapida\\BancoLocal`
- nao desbloqueia outros `.db` locais do build

## Historical Snapshot

- Referencias antigas a `build_*.bat`, `builds/*` e `pyoxidizer.bzl` existem em documentos de analise historica.
- No baseline atual, elas nao representam o caminho operacional principal.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
