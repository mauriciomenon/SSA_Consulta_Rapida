# Guia de Distribuicao - SSA Consulta Rapida

## CURRENT TRUTH (v4.32)

- Sync deste guia: `2026-03-10 16:55 -0300`.
- Versao de referencia: `4.32` (arquivo `VERSION`).
- Fluxo canonico de build: `launchers/build_multiplatform.py`.
- Saida canonica de artefatos: `launchers/dist/<plataforma>/`.
- Empacotamento: `scripts/create_distribution.py`.
- Ferramentas historicas e caminhos legados (`build_*.bat`, `builds/*`) nao sao caminho principal neste baseline.
- Backends reconhecidos pelo parser do empacotador: `pyinstaller`, `nuitka`, `pyoxidizer`.
- Backend de release operacional neste baseline: `pyinstaller`.
- `pytoexe`/`py2exe`: nao suportados neste repositorio (fora das choices dos scripts atuais).

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

Evidencia local desta rodada:
- logs consolidados: `/tmp/ssa_pack_audit_20260310_1030/summary.log`
- artefato gerado: `dist_packages/SSA_Consulta_Rapida_v4.32_pyinstaller.zip`

## Visao Geral

Este guia descreve como gerar pacotes para distribuicao em Windows, macOS e Debian/Linux
usando o fluxo canonico atual.

Nota Debian:
- no baseline atual, Debian usa pacote ZIP canonico.
- AppImage/.deb ficam como trilha futura e nao sao etapa automatica do pipeline oficial.

## Build Canonico

### 1) Build da plataforma atual

```bash
python launchers/build_multiplatform.py --apps cli gui
```

### 2) Build de plataforma especifica

```bash
python launchers/build_multiplatform.py --platform windows_amd64 --apps cli gui
python launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui
python launchers/build_multiplatform.py --platform debian_amd64 --apps cli gui
```

### 3) Verificar saida do build

```bash
python launchers/test_complete.py
```

## Empacotamento para Distribuicao

### 1) Criar ZIP

```bash
python scripts/create_distribution.py --build-system pyinstaller --skip-installer
```

### 2) Criar instalador Windows (Inno Setup)

```bash
python scripts/create_distribution.py --build-system pyinstaller
```

Notas:
- O script tenta localizar Inno Setup por:
  1. `INNO_SETUP_COMPILER`
  2. `iscc` no PATH
  3. caminhos padrao do Windows
- Se Inno Setup nao estiver disponivel, o ZIP continua funcional.

### 3) Criar pacote de outros build systems (laboratorio)

```bash
python scripts/create_distribution.py --build-system nuitka --skip-installer
python scripts/create_distribution.py --build-system pyoxidizer --skip-installer
```

Importante:
- `nuitka` e `pyoxidizer` estao mantidos como trilha experimental neste ciclo.
- Para release operacional, usar PyInstaller como padrao.

## Estrutura Esperada dos Pacotes

Pacote ZIP:

```text
SSA_Consulta_Rapida_v<versao>_<build_system>/
├── <executavel_principal>
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

Politica operacional (v4.32+):
- build canonico nao embeda `data/` por padrao.
- se for necessario incluir dados locais para laboratorio, usar fluxo explicito e controlado:
  - `python scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data`
  - nunca usar isso para pacote de distribuicao geral.

## Distribuicao para Usuario Final

Texto sugerido:

```text
SSA Consulta Rapida v4.32

INSTALACAO
1. Baixe o arquivo ZIP.
2. Extraia para uma pasta local.
3. Entre na pasta extraida.
4. Execute o binario principal.

PRIMEIRO USO
1. Coloque arquivos de entrada em docs_entrada/.
2. Execute Atualizar Dados ou Reescaneamento Completo conforme o caso.

SUPORTE
- Logs em logs/ssa.log
- Guia de antivirus em docs/ANTIVIRUS_EXCLUSOES.md
```

## Checklist de Release

- [ ] Build canonico concluido em `launchers/dist/<plataforma>/`.
- [ ] `launchers/test_complete.py` sem erro bloqueante.
- [ ] ZIP gerado em `dist_packages/`.
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
python scripts/create_distribution.py --build-system pyinstaller --skip-installer
```

### Instalador nao gerado

1. Se log mostrar `Inno Setup nao encontrado`, instalar Inno Setup ou definir `INNO_SETUP_COMPILER`.
2. Se log mostrar `Falha na compilacao`, revisar saida de erro do ISCC e dependencias do build.
3. Opcional: definir compilador explicitamente:

```bash
set INNO_SETUP_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
python scripts/create_distribution.py --build-system pyinstaller
```

### Copia de dados locais para build

O script `scripts/copy_data_to_builds.py` exige confirmacao explicita:

```bash
python scripts/copy_data_to_builds.py --build-system pyinstaller --allow-local-data
```

Use somente em ambiente controlado.

## Historical Snapshot

- Referencias antigas a `build_*.bat`, `builds/*` e `pyoxidizer.bzl` existem em documentos de analise historica.
- No baseline atual, elas nao representam o caminho operacional principal.
