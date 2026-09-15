# Builds Windows AMD64, Windows ARM64 e macOS ARM64

Este guia descreve o procedimento reproduzivel a partir de `dev`. Resultados,
hashes e commits de uma execucao pertencem aos metadados e ao relatorio daquela
entrega; a existencia deste guia nao comprova que um pacote foi gerado ou testado.

## Separacao por alvo

| Alvo | Host e interpretador | Ambiente do wrapper | Saida dos executaveis | Entrega no Mac |
| --- | --- | --- | --- | --- |
| `windows_amd64` | Windows 11, Python `win-amd64` | `.venv-win` | `launchers/dist/windows_amd64/` | `builds/packages/windows_amd64/` |
| `windows_arm64` | Windows 11 ARM64, Python `win-arm64` | `.venv-win-arm64` | `launchers/dist/windows_arm64/` | `builds/packages/windows_arm64/` |
| `macos_arm64` | macOS ARM64, Python ARM64 | Ambiente macOS local | `launchers/dist/macos_arm64/` | `launchers/dist/macos_arm64/` (DMG) |

O builder cria seu ambiente interno em `launchers/platforms/<alvo>/venv` e usa
configuracao e temporarios sob `launchers/platforms/<alvo>/`. Os ambientes do
wrapper e do builder sao distintos. Nao compartilhar venv, dist, temporarios,
metadados ou pacotes entre alvos. A sincronizacao Windows usa
`builds/pyinstaller/<alvo>/`.

Na VM VMware Windows 11 ARM64, o fluxo AMD64 usa Python x64 sob emulacao; o
resultado continua sendo PE AMD64. O fluxo ARM64 usa Python e dependencias
Windows ARM64 nativos. O macOS ARM64 e construido no Mac. Nao alterar firmware,
boot ou aceleracao grafica da VM para executar esses comandos.

Despertar a tela e usar o login ja fornecido quando a sessao estiver bloqueada.
Reutilizar SSH quando disponivel ou o console e a transferencia local existentes.
A senha de criptografia da VM, o PIN e a senha do Windows sao credenciais
distintas. Falha de acesso nao justifica alterar hardware virtual ou entrar no
firmware. Um reparo autorizado exige snapshot e backup da configuracao antes da
alteracao; registrar o responsavel e os efeitos confirmados no relatorio.

## Origem do codigo

Usar o checkout Windows local esperado pelo guard do projeto:

```powershell
Set-Location (Join-Path $env:USERPROFILE 'gitlab\ssa_consulta_rapida_pyqt6')
git branch --show-current
git status --short
git rev-parse HEAD
```

Confirmar `dev`, checkout limpo e o mesmo commit de origem nos tres builds antes
de iniciar. Atualizar o checkout pelo fluxo Git autorizado; nao selecionar um
commit antigo copiado da documentacao. Nao copiar ambientes do Mac para a VM.
Versao e commit devem vir do codigo e constar nos metadados e no About gerados.

## Windows AMD64

Executar em PowerShell no checkout Windows. O wrapper seleciona Python x64 para
PyInstaller e prepara `.venv-win`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\release.ps1 `
    -Target windows -Platform windows_amd64 -Backend pyinstaller `
    -SkipInstaller -Yes
```

O script de build e `dev_env/build/build_pyinstaller.bat`. Conferir o
interpretador usado pelo builder:

```powershell
& .\launchers\platforms\windows_amd64\venv\Scripts\python.exe -c "import sysconfig; print(sysconfig.get_platform())"
```

Resultado exigido: `win-amd64`. Os executaveis CLI e GUI devem ter PE Machine
`0x8664`. O relatorio fica em `builds/reports/release_report_windows_amd64.json`.

## Windows ARM64

Instalar CPython 3.13 ARM64 pelo instalador oficial do Python para Windows. O
fluxo usa esse interpretador local; nao depende de um download Windows ARM64
pelo catalogo de interpretadores gerenciados do uv.

O wrapper procura por padrao
`%LOCALAPPDATA%\Programs\Python\Python313-arm64\python.exe`. Para uma instalacao
em outro local, definir `SSA_WINDOWS_ARM64_PYTHON` com o caminho absoluto do
`python.exe` ARM64. O wrapper desativa a selecao de Python gerenciado pelo uv
neste alvo e exige `sysconfig.get_platform() == "win-arm64"` antes de preparar
o ambiente. Interpretador ausente ou de outra arquitetura interrompe o fluxo.

Executar em PowerShell na VM Windows 11 ARM64:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\release.ps1 `
    -Target windows -Platform windows_arm64 -Backend pyinstaller `
    -SkipInstaller -Yes
```

O script dedicado e `dev_env/build/build_pyinstaller_windows_arm64.bat`.
Conferir o interpretador usado pelo builder:

```powershell
& .\launchers\platforms\windows_arm64\venv\Scripts\python.exe -c "import sysconfig; print(sysconfig.get_platform())"
```

Resultado exigido: `win-arm64`. Os executaveis CLI e GUI devem ter PE Machine
`0xaa64`. O relatorio fica em `builds/reports/release_report_windows_arm64.json`.
Python x64 emulado nao atende este alvo. Nao forjar deteccao de arquitetura.

Os dois comandos Windows exigem Git, uv e PowerShell 7. `-SkipInstaller` dispensa
Inno Setup e entrega o fluxo ZIP. Nao incluir banco pessoal; a inclusao de dados
operacionais e uma opcao separada, `-IncludeRuntimeDb`.

## macOS ARM64

Na raiz do checkout `dev` no Mac, conferir branch, estado e commit como no
Windows. Executar com o ambiente nativo:

```bash
bash -c 'source scripts/env/direnv_common.sh &&
ssa_env::apply &&
ssa_native_guard_tools uv &&
uv run --no-sync python launchers/build_multiplatform.py --platform macos_arm64 --apps cli gui'
```

A configuracao e `launchers/platforms/macos_arm64/build_config.json`. O builder
gera CLI, GUI e DMG sob `launchers/dist/macos_arm64/`. Conferir que os executaveis
sao Mach-O ARM64 com `file` e verificar o DMG com `hdiutil verify`, passando os
caminhos efetivamente gerados. Nao executar limpeza de outro alvo.

## Validacao de cada entrega

Conferir os metadados dos dois executaveis contra o commit registrado por
`git rev-parse HEAD` no inicio do build, a versao
do codigo e o alvo solicitado. Validar tambem a arquitetura das bibliotecas
nativas empacotadas. Testes de scripts nao substituem a execucao do pacote.

Extrair o ZIP ou montar o DMG em uma area de teste e executar os binarios dali.
Usar runtime isolado fora do checkout, dentro do TEMP do usuario, com
`SSA_RUNTIME_ROOT` apontando para esse diretorio. Colocar a base sintetica em
`data/ssas.db` dentro dele: o launcher congelado redefine `SSA_CONFIG_DIR` para
`config/` e `SSA_DB_PATH` para `data/ssas.db` do runtime. Nao usar banco pessoal
nem liberar diretorios adicionais para contornar uma fixture mal posicionada.

Para a CLI, definir `SSA_SMOKE_TEST=1`, executar o launcher e exigir codigo zero
e o marcador de smoke. Remover essa variavel antes do teste visual da GUI.
Abrir a GUI, conferir About, redimensionamento, resposta da janela e encerramento.
Registrar quais interacoes foram verificadas e quais nao foram executadas.

Adicional obrigatorio apos o incidente de 14/09/2026: exercitar importacao e o
botao de derivadas com banco e planilhas em diretorio arbitrario do usuario
(ex.: `Downloads`), fora do diretorio de instalacao. O defeito de propagacao
de `extra_allowed_roots` (secao N de AUDIT_FIXES_REPORT.md) nao aparece quando
o banco esta dentro das raizes padrao; um pacote validado apenas com runtime
no TEMP nao cobre esse caminho. Resultado exigido: a fase de derivadas nao
emite `fora das bases permitidas` e nao retorna `blocking_derivadas_sync_error`.

## Entrega no sistema de arquivos do Mac

Copiar os ZIPs Windows finais da VM para os diretorios correspondentes da tabela.
Preservar a separacao entre AMD64 e ARM64 e conferir que cada ZIP contem CLI,
GUI e os metadados corretos. O DMG macOS permanece no diretorio do seu alvo.
Os nomes devem ser derivados da versao e do alvo da execucao, sem nomes de uma
entrega anterior fixados neste guia.

O release Windows gera ZIPs individuais e um ZIP combinado terminado em
`_pyinstaller.zip`, sem arquitetura no nome, dentro da pasta de cada alvo.
Entregar o combinado, identificando a arquitetura no nome da copia final.
Validar tambem esse ZIP: o relatorio automatico do release cobre os individuais.

Comparar SHA-256 antes e depois da transferencia: `Get-FileHash -Algorithm SHA256`
no Windows e `shasum -a 256` no Mac, com o caminho real de cada pacote. Conferir
que o arquivo de destino existe e pode ser lido antes de declarar a entrega.
Os artefatos ficam ignorados pelo Git; nao adicionar binarios ao repositorio.

Se o ZIP falhar com `WinError 206`, conferir o staging curto no TEMP usado por
`scripts/create_distribution.py`. Registrar a falha e corrigir sua causa; timeout
ou artefato de uma execucao anterior nao comprovam sucesso do build atual.

## Encerramento

Entregar quando os alvos solicitados tiverem pacote legivel, arquitetura e
metadados corretos, smoke com retorno zero, GUI aberta e copia no Mac com hash
conferido. Registrar os limites reais da verificacao visual. Suite completa e
scanners adicionais so entram por pedido ou por falha ou risco concreto.
Correcoes exclusivamente documentais posteriores nao invalidam os binarios:
preservar o commit de origem nos metadados e no relatorio, sem alterar o About
manualmente ou iniciar novas compilacoes apenas para acompanhar commits de docs.
