<!-- markdownlint-disable MD013 -->

# Builds Windows AMD64 e ARM64 em Windows 11 ARM64

Este documento separa os dois fluxos Windows no mesmo host VMware. O build AMD64 usa Python x64 sob emulacao do Windows ARM. O build ARM64 usa Python ARM64 nativo. Nenhum ambiente, pasta temporaria, metadata ou pacote e compartilhado entre as arquiteturas.

## Matriz de saida

| Arquitetura | Plataforma Python | Ambiente | Configuracao | Dist | Pacotes |
| --- | --- | --- | --- | --- | --- |
| AMD64 | `win-amd64` | `.venv-win` | `launchers/platforms/windows_amd64/` | `launchers/dist/windows_amd64/` | `builds/packages/windows_amd64/` |
| ARM64 | `win-arm64` | `.venv-win-arm64` | `launchers/platforms/windows_arm64/` | `launchers/dist/windows_arm64/` | `builds/packages/windows_arm64/` |

O branch de origem e `dev`. O comando ARM usa exclusivamente `-Platform windows_arm64 -Backend pyinstaller`. Nao copie arquivos do diretorio AMD64 para o diretorio ARM.

O fluxo foi concluido em 2026-09-10 para a versao 4.50, no commit `46f3fece45c99ba21973fc54198c17256231bafa`.

## Resultado confirmado

- Plataforma da VM: Windows 11 Pro ARM64.
- Interpretador de build: CPython 3.13.12 x64.
- Plataforma reportada pelo Python: `win-amd64`.
- PyInstaller: 6.22.2.
- Backend: PyInstaller, modo `onedir`.
- Executaveis gerados:
  - `SSA_CLI_v4.50_windows_amd64.exe`
  - `SSA_GUI_v4.50_windows_amd64.exe`
- Cabecalho PE dos dois executaveis: `0x8664` (AMD64).
- Build final: 160,73 s.
- Pacote ZIP: 108.454.127 bytes, 1.699 entradas.

A arquitetura ARM64 pertence ao sistema hospedeiro da VM. O executavel continua sendo AMD64 porque o interpretador x64 e o bootloader x64 foram usados durante o build.

## Fluxo AMD64

O PyInstaller nao e um cross-compiler geral. O bootloader e as extensoes empacotadas precisam ser resolvidos para o sistema alvo. Por isso, o build Windows foi executado em um Windows real dentro da VM, e nao no macOS ARM.

O Windows 11 ARM executa processos x64 por emulacao. Isso permite usar um Python Windows x64 e produzir um executavel AMD64 sem fingir a arquitetura por variaveis de ambiente.

O ponto de controle usado pelo builder e:

```powershell
python -c "import platform, sysconfig; print(platform.machine()); print(sysconfig.get_platform())"
```

A saida esperada para este fluxo e `ARM64` para a maquina do sistema e `win-amd64` para o interpretador selecionado. O builder interrompe o processo se o interpretador nao for `win-amd64`.

O script legado AMD64 e `dev_env/build/build_pyinstaller.bat`. Ele usa `.venv-win`, `launchers/platforms/windows_amd64/` e `builds/packages/windows_amd64/`. Este fluxo nao deve ser executado durante a entrega ARM.

## Fluxo ARM64 nativo

Use uma sessao separada do Python ARM64. O ambiente precisa reportar `win-arm64`; um Python x64 emulado nao atende este fluxo.

```powershell
Set-Location (Join-Path $env:USERPROFILE 'gitlab\ssa_consulta_rapida_pyqt6')
git switch dev
git status --short
$env:UV_PROJECT_ENVIRONMENT = '.venv-win-arm64'
uv sync --extra build --locked
& .\.venv-win-arm64\Scripts\python.exe -c "import platform, sysconfig; print(platform.machine()); print(sysconfig.get_platform())"
```

A saida deve conter `ARM64` e `win-arm64`. O build ARM executa somente:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\release.ps1 `
    -Target windows -Platform windows_arm64 -Backend pyinstaller `
    -SkipInstaller -Yes
```

O script dedicado e `dev_env/build/build_pyinstaller_windows_arm64.bat`. Seus artefatos ficam em `launchers/dist/windows_arm64/`, `builds/pyinstaller/windows_arm64/` e `builds/packages/windows_arm64/`. O relatorio fica em `builds/reports/release_report_windows_arm64.json`.

Confirme a arquitetura PE dos dois executaveis ARM64 com `Machine: 0xaa64` e a arquitetura dos dois executaveis AMD64 com `Machine: 0x8664`. O smoke da CLI e a abertura visual da GUI devem usar um runtime isolado fora do checkout.

## Pre-requisitos na VM

A VM precisa ter:

- Windows 11 ARM64 atualizado.
- Git for Windows.
- uv compativel com os dois interpretadores instalados.
- PowerShell 7.
- Acesso ao repositorio Git.
- Espaco temporario para o ambiente, PyInstaller e ZIP final.

A instalacao normal do PyInstaller usa bootloader precompilado e dependencias em wheels. Visual Studio Build Tools, LLVM e Windows SDK nao sao necessarios para esse caso. Eles so entram se for necessario reconstruir o bootloader ou alguma extensao nativa a partir do codigo-fonte.

Confirme as ferramentas em um console PowerShell novo:

```powershell
Get-Command git, uv, pwsh -CommandType Application -ErrorAction Stop |
    Select-Object Name, Source
uv --version
pwsh --version
```

## Preparar o checkout

Use um clone separado para o build Windows. O checkout precisa estar versionado e limpo para que o relatorio de release consiga associar os binarios ao commit correto.

```powershell
$repo = Join-Path $env:USERPROFILE 'gitlab\ssa_consulta_rapida_pyqt6'
Set-Location $repo
git fetch --depth 3 --no-tags origin dev
git checkout 46f3fece45c99ba21973fc54198c17256231bafa
git status --short
```

O ultimo comando deve nao imprimir arquivos modificados. Nao copie `.env`, preferencias pessoais, bancos de dados de usuario ou arquivos do OneDrive para o checkout de build.

## Selecionar Python x64 com uv no fluxo AMD64

O projeto usa um ambiente separado para Windows:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-win'
uv python install cpython-3.13.12-windows-x86_64-none
uv sync --extra build --locked
& .\.venv-win\Scripts\python.exe -c "import platform, sysconfig; print(platform.machine()); print(sysconfig.get_platform())"
```

O ambiente `.venv-win` deve apontar para Python x64 e nao deve ser compartilhado com um ambiente macOS ou Linux. O builder tambem verifica a arquitetura antes de instalar dependencias e antes de chamar o PyInstaller.

No fluxo ARM, use `.venv-win-arm64`. Nunca altere `UV_PYTHON` do script AMD64 para produzir ARM. O script ARM ja seleciona Python `3.13` e rejeita qualquer interpretador que reporte `win-amd64`.

## Executar o release

O comando usado para gerar CLI, GUI e o relatorio de release foi:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\release.ps1 `
    -Target windows `
    -Backend pyinstaller `
    -SkipInstaller `
    -Yes
```

`-SkipInstaller` gera os artefatos PyInstaller sem exigir o Inno Setup. O instalador pode ser tratado em uma etapa separada quando houver uma maquina Windows com essa ferramenta instalada.

O release gera os executaveis em:

```text
launchers/dist/windows_amd64/
```

E o pacote de distribuicao em uma pasta de build ignorada pelo Git. O manifesto incluido no ZIP declara `platform: windows_amd64`, versao `4.50` e os dois diretorios de executaveis.

## Evitar falha de caminho longo no ZIP

Dependencias como NumPy e lxml criam caminhos profundos. A montagem de distribuicao usa uma pasta temporaria curta com prefixo `ssa_pkg_*` e remove essa pasta em um unico bloco `finally`. Isso evita staging dentro de uma cadeia profunda do repositorio e reduz o risco de `WinError 206`.

Se aparecer falha de caminho longo:

1. Confirme que `scripts/create_distribution.py` usa o TEMP do sistema para o staging.
2. Remova somente a pasta temporaria criada pelo build que falhou.
3. Nao remova o checkout, o perfil do usuario ou dados de aplicacoes.
4. Repita o release a partir de um checkout limpo.

## Validacao feita no Windows

A validacao nativa executou os arquivos de build e os testes de contrato, sem modificar o codigo do produto:

```powershell
python -m py_compile scripts/create_distribution.py tests/test_create_distribution.py `
    launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py `
    tests/test_dev_env_build_scripts.py tests/test_release_entrypoints.py `
    tests/test_release_windows_script.py

uv run --no-sync ruff check scripts/create_distribution.py tests/test_create_distribution.py `
    launchers/build_multiplatform.py tests/test_build_multiplatform_manifest.py `
    tests/test_dev_env_build_scripts.py tests/test_release_entrypoints.py `
    tests/test_release_windows_script.py

uv run --no-sync ty check main.py armazenamento core gui exportacao utils interface `
    launchers/build_multiplatform.py

uv run --no-sync pytest -q -ra -p no:cacheprovider `
    tests/test_create_distribution.py `
    tests/test_build_complete.py `
    tests/test_build_multiplatform_manifest.py `
    tests/test_dev_env_build_scripts.py `
    tests/test_release_artifact_guard.py `
    tests/test_release_debian_script.py `
    tests/test_release_docs_contract.py `
    tests/test_release_entrypoints.py `
    tests/test_release_local_script.py `
    tests/test_release_windows_script.py `
    tests/test_runtime_manifest_parity.py `
    tests/test_cli_enhancement_manager_lock_usage.py
```

Resultado registrado no build final:

- 225 testes passaram.
- 1 teste foi ignorado por exigir candidato Python POSIX.
- Ruff, ty e `py_compile` passaram.
- O teste de lock usou dois processos Windows reais: uma tentativa concorrente foi rejeitada e a aquisicao ocorreu depois do fechamento do primeiro lock.
- Os dois executaveis foram lidos e conferidos como PE AMD64 (`0x8664`).

## Smoke test da CLI

A CLI normal e interativa. Portanto, executar apenas `SSA_CLI...exe --help` em um subprocesso pode esperar entrada e atingir timeout. Isso nao e um teste valido de inicializacao do launcher.

O launcher possui um marcador de smoke test:

```powershell
$env:SSA_SMOKE_TEST = '1'
$env:SSA_RUNTIME_ROOT = 'C:\Temp\ssa-runtime-smoke'
$env:SSA_CONFIG_DIR = "$env:SSA_RUNTIME_ROOT\config"
$env:SSA_DB_PATH = "$env:SSA_RUNTIME_ROOT\test.db"
& .\launchers\dist\windows_amd64\SSA_CLI_v4.50_windows_amd64\SSA_CLI_v4.50_windows_amd64.exe
```

O processo deve retornar codigo zero e imprimir o marcador de smoke com a versao. No build documentado, o smoke terminou em 0,21 s.

## Smoke visual da GUI

Para abrir a GUI com um runtime isolado, use um banco de teste fora do checkout:

```powershell
$env:SSA_RUNTIME_ROOT = 'C:\Temp\ssa-runtime-gui'
$env:SSA_CONFIG_DIR = "$env:SSA_RUNTIME_ROOT\config"
$env:SSA_DB_PATH = "$env:SSA_RUNTIME_ROOT\test.db"
Start-Process '.\launchers\dist\windows_amd64\SSA_GUI_v4.50_windows_amd64\SSA_GUI_v4.50_windows_amd64.exe'
```

A verificacao visual deve confirmar que a janela `Consulta Rapida de SSAs v4.50` abre, responde e fecha normalmente. O teste documentado confirmou a abertura e o encerramento. A interacao completa com filtros e carga de registros deve ser executada em uma rodada GUI dedicada.

## Copiar o artefato para o host

Depois de fechar os executaveis, copie o ZIP para o caminho local por arquitetura:

```text
builds/packages/windows_amd64/
```

Nome usado neste build:

```text
SSA_Consulta_Rapida_v4.50_windows_amd64_pyinstaller.zip
```

Valide a integridade antes de distribuir:

```bash
shasum -a 256 builds/packages/windows_amd64/SSA_Consulta_Rapida_v4.50_windows_amd64_pyinstaller.zip
git check-ignore -v builds/packages/windows_amd64/SSA_Consulta_Rapida_v4.50_windows_amd64_pyinstaller.zip
```

O repositorio ignora `builds/*`, `launchers/dist/` e `*.exe`. Binarios de release nao devem ser adicionados ao Git. O codigo-fonte, os scripts de build, os testes e este documento permanecem versionados.

No fluxo usado nesta rodada, a transferencia VM-host foi feita por um canal temporario local e o hash do ZIP foi comparado nos dois lados. O canal foi encerrado ao final e nenhum segredo ou credencial foi salvo no repositorio.

## Diagnostico rapido

### O builder rejeita a arquitetura

Verifique se o Python ativo e x64:

```powershell
python -c "import sysconfig; print(sysconfig.get_platform())"
```

A saida precisa ser `win-amd64`. Nao resolva isso alterando `platform.machine()` ou forjando variaveis de ambiente.

### A CLI fica esperando e o teste expira

Use `SSA_SMOKE_TEST=1` para testar o launcher. A CLI sem esse marcador inicia o loop interativo e espera comandos do usuario.

### O ZIP falha com `WinError 206`

Confirme o staging curto em TEMP e repita o pacote a partir de um checkout limpo. Nao aumente o timeout como substituto para corrigir o caminho de staging.

### O executavel abre e nao encontra o banco

Defina `SSA_RUNTIME_ROOT`, `SSA_CONFIG_DIR` e `SSA_DB_PATH` para um runtime isolado. Nao aponte o teste para o banco pessoal do usuario.

## Limites do processo

- O build AMD64 depende de executar o PyInstaller em Windows.
- Windows 11 ARM e adequado para esse fluxo porque executa Python e aplicativos x64 por emulacao.
- O resultado AMD64 e um binario x64 executado por emulacao no Windows ARM. O resultado ARM64 exige Python ARM64 e wheels ARM64 compativeis; os dois resultados sao publicados em diretorios distintos.
- O pacote ZIP e um artefato local ignorado pelo Git. A publicacao deve usar o mecanismo de release definido pelo projeto.
- A validacao visual feita nesta rodada cobre abertura e encerramento da GUI, nao uma certificacao completa de todos os filtros.
