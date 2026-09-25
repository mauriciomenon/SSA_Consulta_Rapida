# Candidata local v4.51

Data do registro: 2026-09-24. Fonte: branch `dev` local.

Esta candidata consolida correcoes locais de importacao, cancelamento, armazenamento, derivadas, caches e GUI. A ultima release publicada e `v4.50`. Os tres alvos nativos foram construidos localmente a partir de `b613fb16820bac49bf4d06c941520a3e0d6f3b62`; nao ha tag, push, release ou CI remota nesse SHA. O PR #135 foi marcado como pronto para revisao, mas o GitHub ainda ve o commit antigo `3be4c350` e indica `BLOCKED`.

## Evidencia local ja obtida

- No tip de codigo `ba9ab08c`, antes da troca de metadados de versao, a suite completa terminou com 3377 testes aprovados, 9 ignorados e 11 subtestes aprovados (`QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q`, 1072,10 s).
- Apos a troca dos metadados para 4.51, os testes de versao e inicializacao terminaram com 34 aprovados. `uv lock --check` passou.
- O patch do builder macOS passou em `py_compile`, Ruff, Ty, Bandit, Vulture, Semgrep (0 achados), Gitleaks (0 vazamentos), detect-secrets (0) e TruffleHog (0); 46 testes focados do builder passaram. `pip-audit` sobre dependencias exportadas do lock nao encontrou vulnerabilidades conhecidas.
- Uma revisao local do delta de build pelo CodeRabbit CLI terminou com zero achados; o review remoto do PR ainda nao cobriu o SHA local.
- Essas verificacoes nao substituem a medicao completa de desempenho nem a CI no commit exato da candidata.

## Pacotes locais v4.51

Somente os nove ZIPs sob `builds/packages/v4.51/` sao candidatos a upload futuro em uma release/tag. Nenhum arquivo foi enviado. Os ZIPs foram testados com `unzip -t` ou teste CRC equivalente, e os combinados Windows nao incluem banco, planilhas, `.env` ou codigo fonte. Os SHA-256 copiados da VM conferem com os do Mac. O DMG esta dentro do ZIP macOS e passou em `hdiutil verify` apos extracao.

Os diretorios de saida e temporarios dos tres alvos foram esvaziados por rename para backup antes do build final, sem apagar os pacotes 4.50. No Windows, os runtimes CPython 3.13.15 ARM64 e AMD64 foram instalados por `uv` em locais isolados, com venvs separados. A sessao de build acessou o checkout de outro perfil; o guard de `release.ps1` nao aceita essa combinacao. Por isso os ZIPs foram gerados pela sequencia equivalente builder PyInstaller, sincronizacao de saidas e `create_distribution`, sem alterar o guard nem o perfil do usuario. O checkout da VM ficou detached no SHA fonte; a ref `dev` anterior e os pacotes 4.50 foram preservados.

| Alvo | Pacote em `builds/packages/v4.51/<alvo>/` | SHA-256 |
| --- | --- | --- |
| macos_arm64 | `SSA_CLI_v4.51_macos_arm64.zip` | `ee13378e52aa0cec2248ca730848737bd38a146ab2a5e3792ced3fed351ecd38` |
| macos_arm64 | `SSA_Consulta_Rapida_v4.51_macos_arm64_dmg.zip` | `e560158f5ee55e956f819500b81efaf1f1bd6e980dccd3b72c8b8d891f448083` |
| macos_arm64 | `SSA_GUI_v4.51_macos_arm64_app.zip` | `c6cda8a50485dd438972280e913986caa2ebbf506593379b05fbdccaa9ace722` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller.zip` | `c72eeb01482d0cb8927aa8aacc81feaddaa1eecf6a1cdae8d47fa44446215bdd` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller_cli.zip` | `968a5dbb1738702d036350128a25bc7d429409a56443148f04bb43425b1d7175` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller_gui.zip` | `1f3a9d70804bdb081ce49ab0ba12e3e43ec7a23c6ed0f97ba3dbd629a337e29b` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller.zip` | `f1191865a464550a026f084801eff16d61d86636841d9c778cb03b102b33cd30` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller_cli.zip` | `66f0ac2b1e1c5041d85e4312b7427a83bb84ec808cd5258b613a81a705a9c9a8` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller_gui.zip` | `357dbbf21636e636de0a673e581be945562aedbc1d886c758043186bd626e615` |

Os executaveis macOS sao Mach-O ARM64; CLI extraida do ZIP respondeu `SMOKE_CLI_OK v4.51`. A GUI extraida abriu com titulo `Consulta Rapida de SSAs v4.51`; sem banco de teste configurado, exibiu erro de carga, portanto importacao e derivadas nao foram validadas visualmente nesse pacote. Na VM, os EXEs sao PE ARM64 `0xaa64` e AMD64 `0x8664`; a CLI extraida importou uma linha em cada alvo, e a GUI passou no smoke `SMOKE_GUI_OK v4.51` e permaneceu ativa por 10 s em Qt offscreen. A abertura visual Windows nao foi observada porque a sessao grafica permanece bloqueada.

A assinatura interna macOS passou em `codesign --verify`, mas `spctl` rejeitou o app: esta maquina nao possui identidade Developer ID valida para distribuicao automatica. Os quatro EXEs Windows retornaram `NotSigned` em Authenticode. Esses limites precisam ser resolvidos ou aceitos explicitamente antes de publicar binarios para usuarios finais.

## Ponto de desempenho pendente

Uma medicao anterior registrou **0,436 s** para um backup SQLite de **161 MiB**. O fluxo atual tem duas copias distintas: `stage_database_copy()` prepara o banco escolhido no worker; `snapshot_database_for_replace()` copia o banco que sera substituido durante `commit_staged_database_copy()`, chamado na thread GUI depois do check de `request_id`. Esta segunda copia pode pausar a interface. Em uma copia local de 161,1 MiB no macOS ARM64, cinco chamadas diretas a `snapshot_database_for_replace()` deram **p50 0,589 s**, **p95 0,662 s** e faixa **0,562-0,665 s**. Dez chamadas separadas ao staging deram p50 0,305 s e p95 0,590 s. As amostras sao pequenas, sem simulacao da GUI nem carga de outras plataformas; nao estabelecem limite de aceitacao ou pico de memoria do fluxo completo.

Antes de promover a candidata, medir o fluxo completo de selecao de banco em bancos reais de tamanhos representativos, com repeticoes em cada plataforma alvo. Registrar latencias **p50 e p95** do staging e da promocao, pico e variacao de memoria do processo, e responsividade da GUI durante a operacao. Definir limites de aceitacao com esses dados. Se a pausa ou o uso de memoria excederem os limites, a candidata permanece pendente ate a correcao ser implementada e revalidada.

A promocao permanece na thread GUI para descartar resultados com `request_id` obsoleto antes de trocar o banco selecionado. Mover a promocao inteira para um worker sem novo protocolo permitiria que um resultado tardio substituisse uma selecao mais recente. Uma correcao futura precisa manter a verificacao de identidade da requisicao, cancelamento e descarte de resultado tardio, com teste de corrida.

## Condicao de release

Fechar a revisao dos achados, medir responsividade real da GUI e memoria no fluxo de selecao de banco, validar visualmente Windows e o caminho de importacao/derivadas no pacote, decidir a politica de assinatura e executar os gates remotos no commit exato a publicar. O PR remoto continua bloqueado e ainda nao revisou o codigo local v4.51.
