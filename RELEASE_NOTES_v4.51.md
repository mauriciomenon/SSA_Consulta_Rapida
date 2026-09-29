# Candidata local v4.51

Data do registro: 2026-09-24. Fonte: branch `dev` local.

Esta candidata consolida correcoes locais de importacao, cancelamento, armazenamento, derivadas, caches, CLI e GUI. A ultima release publicada e `v4.50`. Os tres alvos nativos foram reconstruidos com saidas limpas a partir de `a2954a489801fed52bc8b29eef43d51d2fc6e0f7`; nao ha tag, push, release ou CI remota nesse SHA. O PR #135 foi marcado como pronto para revisao, mas o GitHub ainda ve o commit antigo `3be4c350` e indica `BLOCKED`.

## Evidencia local ja obtida

- No tip de codigo `ba9ab08c`, antes da troca de metadados de versao, a suite completa terminou com 3377 testes aprovados, 9 ignorados e 11 subtestes aprovados (`QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q`, 1072,10 s).
- Apos a troca dos metadados para 4.51, os testes de versao e inicializacao terminaram com 34 aprovados. `uv lock --check` passou.
- O patch do builder macOS passou em `py_compile`, Ruff, Ty, Bandit, Vulture, Semgrep (0 achados), Gitleaks (0 vazamentos), detect-secrets (0) e TruffleHog (0); 46 testes focados do builder passaram. `pip-audit` sobre dependencias exportadas do lock nao encontrou vulnerabilidades conhecidas.
- A CLI empacotada expunha um defeito reproduzido em macOS e Windows: `--help` e `--version` entravam no loop interativo e podiam consultar um banco inexistente. O commit `a2954a48` faz essas opcoes encerrarem antes da carga do banco. `py_compile`, Ruff, Ty e os 35 testes de `tests/test_launcher_entry_runtime.py` passaram; os ZIPs finais foram testados novamente nos tres alvos.
- Uma revisao local do delta de build pelo CodeRabbit CLI terminou com zero achados; o review remoto do PR ainda nao cobriu o SHA local.
- A suite completa nao foi repetida depois das mudancas de versao, builder e CLI. Essas verificacoes focadas nao substituem a CI no commit exato da candidata.

## Pacotes locais v4.51

Somente os nove ZIPs sob `builds/packages/v4.51/` sao candidatos a upload futuro em uma release/tag. Nenhum arquivo foi enviado. Os ZIPs foram testados com `unzip -t` ou teste CRC equivalente, e os combinados Windows nao incluem banco, planilhas, `.env` ou codigo fonte. Os SHA-256 copiados da VM conferem com os do Mac. O DMG esta dentro do ZIP macOS e passou em `hdiutil verify` apos extracao.

Os diretorios de saida e temporarios dos tres alvos foram esvaziados por rename para backup antes do build final, sem apagar os pacotes 4.50. No Windows, os runtimes CPython 3.13.15 ARM64 e AMD64 foram instalados por `uv` em locais isolados, com venvs separados. A sessao de build acessou o checkout de outro perfil; o guard de `release.ps1` nao aceita essa combinacao. Por isso os ZIPs foram gerados pela sequencia equivalente builder PyInstaller, sincronizacao de saidas e `create_distribution`, sem alterar o guard nem o perfil do usuario. O checkout da VM ficou detached no SHA fonte; a ref `dev` anterior e os pacotes 4.50 foram preservados.

| Alvo | Pacote em `builds/packages/v4.51/<alvo>/` | SHA-256 |
| --- | --- | --- |
| macos_arm64 | `SSA_CLI_v4.51_macos_arm64.zip` | `0d30df77fc16c97c0ca87774e32ac2f52379de7f13fb9368cffce559bf8ded5d` |
| macos_arm64 | `SSA_Consulta_Rapida_v4.51_macos_arm64_dmg.zip` | `8b3eadc77de3b3c56e8b17382a5bd5e2ec81da6eb799aa6eebc8e84c9243c69e` |
| macos_arm64 | `SSA_GUI_v4.51_macos_arm64_app.zip` | `526f98412522ab48b4e5485fc2c82d926a72f03afcbb3e4e5094945e6b641a12` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller.zip` | `482cd0e3b993f8751d83bb24c17aff08cf352e0e43acb5e6ad89dc42e0a2c37a` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller_cli.zip` | `0186b0015ebfdeac4ab3026fa0e0891f4be5ce8a6883d209666060f77af6185f` |
| windows_arm64 | `SSA_Consulta_Rapida_v4.51_windows_arm64_pyinstaller_gui.zip` | `2e16220c17d010658eed18330ee055c679cb160324d1619ed73f1022f54df835` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller.zip` | `63e838a05eacf0d5dc57ecd60d9b324b3ae6ec69f2742c0c69d4b41457725d98` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller_cli.zip` | `5924903ea2330bea6d28aea72b49783326358cff5a36dc07b6f91aa0847e9523` |
| windows_amd64 | `SSA_Consulta_Rapida_v4.51_windows_amd64_pyinstaller_gui.zip` | `728a54d10efb2dea7e753234276652681dd87a489a525b2668d544e6c4f5e136` |

Os executaveis macOS sao Mach-O ARM64, e os Windows sao PE ARM64 `0xaa64` e AMD64 `0x8664`. Os seis ZIPs Windows e os tres macOS passaram na verificacao CRC; o DMG passou em `hdiutil verify`. Todos os `build_info.json` inspecionados nos pacotes identificam `a2954a48`. Os ZIPs CLI/GUI macOS nao continham banco, XLSX, `.env` ou `.git`; os combinados Windows tambem excluem dados locais. Os hashes dos ZIPs Windows copiados ao Mac conferem com os da VM. Os pacotes anteriores foram preservados fora da pasta candidata.

### CLI e importacao empacotadas

| Verificacao no executavel extraido | macOS ARM64 | Windows ARM64 e AMD64 |
| --- | --- | --- |
| `--help`, `-h`, `--version`, sem banco | rc 0; ajuda/versao em stdout; stderr vazio | Mesmo resultado nos dois alvos |
| `--force-rescan` com XLSX sintetico fora da instalacao | rc 0; `status=updated`, 3 SSAs e 2 arestas ativas; raiz com 1 filho direto e 2 descendentes | rc 0; 3 SSAs e 2 arestas ativas em cada alvo |
| XLSX invalido | rc 1; stdout vazio; erro `candidate_incomplete` em stderr, sem traceback | rc 1; stdout vazio; erro `candidate_incomplete` em stderr |
| Menu de consulta com banco sintetico | Busca e saida `q` com rc 0 e stderr vazio | Busca interativa nao exercitada nesta rodada; a GUI nativa exibiu as 3 SSAs |

O utilitario `scripts/derivadas_cli.py` e separado do executavel interativo `SSA_CLI`; passar `--db ... parents` ao executavel empacotado nao chama esse utilitario. No checkout, `sync --require-consistency --report-json` manteve JSON em stdout, gravou o relatorio, e `children`, `info` e `scan` confirmaram a cadeia de tres SSAs; um destino de relatorio igual ao banco falhou com rc 1 sem sobrescreve-lo. No pacote, a importacao executou a sincronizacao de derivadas e a matriz/summary foram conferidas diretamente em SQLite.

Um limite de UX preexistente permanece: iniciar a CLI interativa sem banco ainda registra traceback da consulta inicial em stderr, embora mostre o prompt vazio, aceite `rescan` e encerre com rc 0. `--help`, `-h` e `--version` nao percorrem mais esse caminho. O caso nao altera banco nem impede a importacao explicita; uma mensagem inicial mais curta fica para uma correcao separada.

### GUI empacotada

O app macOS extraido do ZIP com `ditto` passou em `SMOKE_GUI_OK v4.51`. A extracao comum por `zipfile` nao preservou links do bundle e falhou ao iniciar Python; repetir com `ditto` resolveu o problema do harness, sem mudanca no app. Na VM Windows desbloqueada, as GUIs ARM64 e AMD64 extraidas dos ZIPs abriram visualmente com titulo v4.51, exibiram as 3 SSAs sinteticas, os valores `Derivada de` e a hierarquia na aba Derivadas, sem erro de caminho. A coluna `Qtd. Derivadas` e a contagem do painel nao foram comparadas visualmente nessa rodada. A abertura visual do app macOS final com banco de teste tambem nao foi repetida.

A assinatura interna do app macOS final passou em `codesign --verify`; a avaliacao anterior com `spctl` rejeitou distribuicao automatica por falta de Developer ID e nao foi repetida apos este rebuild. Os quatro EXEs Windows finais aparecem como `NotSigned` em Authenticode. A distribuicao sem assinatura paga foi aceita pelo usuario nesta rodada e nao e tratada como defeito ou bloqueio de codigo.

## Ponto de desempenho pendente

Uma medicao anterior registrou **0,436 s** para um backup SQLite de **161 MiB**. O fluxo atual tem duas copias distintas: `stage_database_copy()` prepara o banco escolhido no worker; `snapshot_database_for_replace()` copia o banco que sera substituido durante `commit_staged_database_copy()`, chamado na thread GUI depois do check de `request_id`. Em chamadas diretas anteriores, um banco local de 161,1 MiB deu backup p50 **0,589 s** e p95 **0,662 s** (5 amostras), e staging p50 **0,305 s** e p95 **0,590 s** (10 amostras).

Agora o fluxo completo foi medido em tres execucoes no macOS ARM64 com `QApplication`, `SSAMainWindow`, selecao de banco alternativo, worker, promocao e recarga reais, mais `QTimer` de 20 ms. Origem e destino SQLite sinteticos tinham 169.197.568 bytes cada; a tabela principal continha uma SSA e uma tabela de preenchimento aumentava o arquivo. O staging no worker levou **175-199 ms** e permitiu 8-10 ticks; o backup do destino na thread GUI levou **217-296 ms**, com maior intervalo entre ticks de **240-321 ms** (p95 habitual dos ticks: 21 ms). A selecao ate entrega dos dados levou **433-514 ms**. As tres execucoes exibiram a SSA nova, sem erros ou staging pendente. O pico de RSS do processo ficou perto de 171 MiB, aumento de **1,4-1,8 MiB** sobre o inicio da selecao; esse indicador nao inclui cache do kernel.

A pausa da GUI durante o backup esta confirmada, mas estas tres amostras offscreen nao medem pintura visual, espera de dialogos nem recarga de uma tabela com dezenas de milhares de SSAs. A diferenca entre os tempos diretos e o fluxo sintetico depende do conteudo e do cache do filesystem; nao extrapolar um p95 de tres execucoes. O custo fica registrado como limite de desempenho conhecido desta candidata, sem alterar agora a protecao de dados. Medicao com base representativa e interacao visual continua sendo um aperfeicoamento posterior.

A promocao permanece na thread GUI para descartar resultados com `request_id` obsoleto antes de trocar o banco selecionado. Mover a promocao inteira para um worker sem novo protocolo permitiria que um resultado tardio substituisse uma selecao mais recente. Uma correcao futura precisa manter a verificacao de identidade da requisicao, cancelamento e descarte de resultado tardio, com teste de corrida.

## Condicao de release

O PR remoto continua bloqueado e ainda nao revisou o codigo local v4.51, pois nao houve push. Antes de merge, faltam os gates remotos no commit a publicar e a revisao correspondente. A suite completa nao foi repetida no SHA dos pacotes, conforme o escopo focal desta rodada. A ausencia de assinatura paga esta aceita; a pausa medida da GUI e os limites visuais acima permanecem documentados, sem serem apresentados como falha de integridade.
