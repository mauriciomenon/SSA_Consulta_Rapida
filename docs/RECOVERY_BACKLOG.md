# Pendencias de estabilizacao

Atualizado em 2026-09-09, HEAD 36706e77; commits de limpeza uv a3e7adb6 e 36706e77 enviados aos tres remotos configurados.
Documento local ignorado pelo Git.

- [x] Tratar origem do GitPython no ambiente GUI: Codeflash removido dos manifestos, dos dois ambientes locais encontrados, do cache e da configuracao do usuario. Dependencias compartilhadas preservadas. Pytest-timeout virou dependencia direta de testes. Detalhes e backups no controle da rodada.
- [x] Pip removido da .venv e reinsercao corrigida em nove scripts. Ativacao real repetida preservou o ambiente sem pip. 134 testes focados e 55 web aprovados; uma omissao opcional PyArrow. Backups e evidencias no controle da rodada.
- [x] Streamlit atualizado para 1.63 dentro do mesmo major; GitPython/gitdb/smmap e cadeia antiga sairam naturalmente do lock. pip-audit consultou 99 pares nome/versao do lock sem vulnerabilidades conhecidas nem pacotes ignorados.
- [x] GitLab pipeline 2834411660 aprovado para 36706e7784a44f060761bbfe35d070971ac571fc, etapas verify/security, 1m11; conferido no navegador autenticado.
- [ ] GitHub mauriciomenon: regularizar cobranca da conta para executar CI. Runs 34394997425, 34394997311 e 34394997494 do SHA 36706e7784a44f060761bbfe35d070971ac571fc encerraram sem etapas: sete jobs bloqueados e dois ignorados. Nenhum teste executou; nao e evidencia de falha de codigo.
- [ ] GitHub schottge-menon: conferir CI com sessao que tenha acesso. MCP/API e navegador autenticado retornaram 404. Push concluido; resultado do CI desconhecido.
- [ ] Renovar `.venv-linux` em host Linux quando necessario: metadata SSA 4.37.0 e tabulate antigo. Interpretador nao executavel neste macOS. Codeflash/idna/isort removidos por metadata; pip ausente. Restam 20 pacotes; nao declarar ambiente validado.
- [ ] Validar filtros, Preferencias e encerramento em Windows 11 amd64/arm64 e Linux amd64/arm64. Esta rodada validou macOS arm64.
- [x] Preservadas regras Ruff E4/E7/E9/F em pyproject.toml durante migracao 0.15.21 -> 0.16.6. O conjunto anterior e o atual sao identicos; os 175 avisos adicionais provinham da mudanca de defaults. Ruff passou no escopo ampliado sem alterar codigo da aplicacao. Avaliar adocao de novas regras somente em slice especifico.
- [ ] Medir novamente CPU/RSS e latencia com base representativa se a proxima rodada alterar carregamento, caches ou concorrencia. Esta rodada confirmou backlog constante sob IO bloqueado, sem benchmark amplo.
- [ ] Continuar a reducao localizada de responsabilidades da janela principal mediante plano especifico. Montagem de Preferencias ja foi extraida; demais blocos grandes continuam existentes.

Nao bloquear o fechamento da GUI indefinidamente por falha permanente de disco: o contrato atual registra falha de escrita e distingue thread ativa de thread encerrada. Uma eventual mudanca na notificacao ao usuario exige preservar esse comportamento e definir criterio de recuperacao.


## Rodada de estabilidade e PRs em dev - 2026-09-10

Solicitacao: verificar estabilidade de dev, outros branches exceto main/master e PRs; aceitar versoes de PyInstaller, ty, Ruff, pywin32 e pytest; avaliar uv group.

- [x] Workspace inicial e final limpos em dev. Base 10d0f92d; commit humano c52b42ab3718b9bb6ff5b30af68561b8ec14ecf3 publicado nos tres destinos configurados de origin. Nenhum novo branch/worktree/PR, nenhum merge ou alteracao em main/master.
- [x] Pywin32 311 -> 312: pyproject.toml, requirements_build.txt, launchers/platforms/windows_amd64/requirements.txt e uv.lock; limite >=312,<313 e marcador Windows preservado. Patch +25/-22; backups com timestamp em /tmp. Outros 99 registros do lock preservados, exceto metadata da dependencia no proprio projeto. Fonte PyPI preservada.
- [x] PRs #123 PyInstaller, #124 ty, #125 Ruff e #127 pytest ja atendidos pela base dev: 6.22.2, 0.0.79, 0.16.6 e 9.1.1. PR #126 atendido pelo commit desta rodada. Nao importar historicos antigos para reduzir versoes ou reintroduzir dependencias removidas.
- [x] PR #130 uv avaliado: Pillow 12.3.0 e setuptools 83.0.0 ja presentes; python-multipart 0.0.32 e Starlette 1.6.0 superiores ao PR; GitPython ja removido com sua cadeia. Integracao desnecessaria; mantido aberto.
- [ ] Encerramento sem merge dos PRs #123-127: solicitada autorizacao explicita, ainda pendente. Os cinco continuam abertos; nenhuma aprovacao/merge remoto foi publicado.
- [x] Inventario Git: 94 refs, das quais 45 existentes (12 locais + 33 heads remotos) e 49 historicas (37 tracking refs obsoletas + 12 Bitbucket sem remote configurado). Dos 33 heads remotos, 20 fora archive/ e 13 arquivados. Filtro excluiu ultimo segmento main/master/dev, inclusive archives. Nenhuma ref foi removida.
- [x] StepSecurity ja equivalente em dev; macOS signature e mypy lock sao ancestrais; backup_dulse contem apenas EOL. dev_feature, docs-update-4-42, fix-dependabot-uv-graph e CodSpeed possuem escopos amplos/duplicados e ficaram fora da integracao. Os 29 mauriciomenon-patch* de CI sao tracking refs obsoletas.
- [x] GitLab sem MRs abertos, conferido no navegador autenticado. PRs/CI do segundo GitHub indisponiveis por 404 em API e navegador; acesso Git SSH/push funciona.
- [x] Compilacao de 611 arquivos Python e Ruff em todos os arquivos Python versionados: passaram.
- [x] Suite nos 272 modulos do escopo de CI, com 62 modulos GUI em processos isolados: 2870 passaram, 8 ignorados, 2 falharam; 63 lotes, 484,4 s. Sem timeout. Exclusoes do CI preservadas: legacy_tests, gui_poc_smoke_test.py e main_test.py; nao declarar todo teste existente executado.
- [ ] Dois contratos de testes preexistentes: tests/test_docs_and_priority.py:10 exige titulo README antigo; tests/test_runtime_manifest_parity.py:83 exige literalmente filelock>=3.20.3, mas manifestos ja usam >=3.32.6,<4. Falhas confirmadas na base 10d0f92d e repetidas isoladamente; nao corrigidas nesta rodada.
- [ ] Ty: 6 erros e 6 avisos no escopo principal; erros em core/search_filter.py:533/561, gui/ssa/details_series_index.py:35, gui/workers/filter_worker.py:59 e interface/cli_enhancement_manager.py:258/267. Fonte funcional nao alterada pelo bump. Vulture: 3 candidatos preexistentes, sem remocao automatica.
- [x] pip-audit: 99 pares externos nome/versao do lock consultados, zero vulnerabilidades conhecidas e zero ignorados. Variantes NumPy/pandas auditadas em grupos sem nomes duplicados.
- [x] Semgrep: 1115 regras, 194 arquivos do escopo principal, zero resultados. Bandit: 63705 linhas, 6 avisos baixos, nenhum medio/alto; B110 em interface/cli_enhancement_manager.py:264 permanece para triagem.
- [x] Gitleaks e TruffleHog: zero segredos no intervalo recente 54be5259..dev; TruffleHog sem verificacao online. Detect-secrets em arquivos versionados: 10 candidatos preexistentes em baseline/exemplos/docs/testes; nenhuma mudanca nesses arquivos, nenhum candidato no patch.
- [ ] ShellCheck: 8 apontamentos preexistentes; PSScriptAnalyzer: 186 (160 avisos, 26 informativos), sem erros. Nao misturar limpeza ampla com bump de dependencia.
- [x] CodeRabbit: revisao da base recente gerou 8 issues (3 major, 5 minor); revisao focada dos quatro arquivos finais gerou zero issues, exit 0. Sugestao de exigir rtk no startup descartada por falta de defeito demonstrado e dependencia extra.
- [ ] Risco confirmado em PowerShell: scripts/env/setup_env.ps1:157 sobrescreve SSA_PYTHON_STABLE_VERSION ao selecionar free-threaded; depois stable pode selecionar 3.14-dev. Confirmado em processo PS 7.6.1 por funcoes/atribuicao extraidas do AST. Corrigir em slice especifico aprovado, com cobertura de troca de variante.
- [ ] dev_env/activate_repo.ps1:173 rejeita Python com patch diferente do alvo, incluindo patch superior; fallback pode criar ambiente com Python do PATH e rejeita-lo depois. Condicao confirmada; criacao Windows nativa nao reproduzida. Avaliar provisionamento da versao alvo, preservando politica estrita.
- [ ] scripts/env/setup_env.sh:183 tambem atribui a versao FT a variavel stable; impacto de sessao menor por executar como processo. tests/test_shell_ci_contracts.py:259 pressupoe ausencia de uv em /usr/bin:/bin; fragilidade em outras distros.
- [x] GUI macOS arm64, Qt offscreen: 5/5 registros sinteticos via SQLite/DataLoader reais, status pronto e fechamento normal 5,5 ms; imports ate dados 394,86 ms, RSS 174,83 MiB. Preferencias originais preservadas. Screenshot: /tmp/ssa_20260910_gui.png. Amostra unica pequena; nao e benchmark representativo.
- [ ] Filtros inferiores apresentam alguns titulos truncados/sobrepostos na captura offscreen; comparar em Cocoa antes de atribuir regressao. Nenhuma mudanca visual aplicada.
- [x] uv lock --check passou; dry-run do extra build passou para macOS arm64 e Windows amd64/arm64. Wheels pywin32 verificadas para CPython 3.10-3.14 nas duas arquiteturas Windows.
- [ ] Validacao nativa Windows/Linux e build completo continuam pendentes. Dry-run Linux exige glibc >=2.34 em amd64 e >=2.39 em arm64 pelo PyQt6-Qt6 6.11.2 atual; passou com esses alvos e falhou com alvo generico manylinux_2_28. Essa restricao ja existia antes do bump.

Evidencias locais: /tmp/ssa_20260910_pytest_summary.json, /tmp/ssa_20260910_pytest_000.log, /tmp/ssa_20260910_ty.log, /tmp/ssa_20260910_audit_0.json, /tmp/ssa_20260910_audit_1.json, /tmp/ssa_20260910_audit_2.json, /tmp/ssa_20260910_platforms.json. Logs completos dos demais verificadores usam o mesmo prefixo.

CI final do SHA c52b42ab3718b9bb6ff5b30af68561b8ec14ecf3:

- [x] GitLab pipeline 2837511900 aprovado em 1m16s: quality-gates e secret-scan passaram; pytest-full permanece manual e nao foi executado. Conferido na UI autenticada: https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines/2837511900.
- [ ] GitHub runs 34489040397 (minimal-ci), 34489040430 (Secret Scan) e 34489040360 (CodeQL) bloqueados por faturamento. Sete jobs falharam com zero etapas; dois ignorados. Nenhum teste executou. Evidencia: https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34489040397.
- [x] Conferencia final por git ls-remote: origin, schottge e gitlab apontam dev para c52b42ab. Workspace versionado limpo; backlog local ignorado. PRs abertos #123-127 e #130 confirmados por API; estados e bases remotas nao alterados.

Status final: versoes solicitadas atendidas em dev; verificacao de estabilidade entregue com pendencias preexistentes; merge/encerramento dos PRs nao executado. Grupo uv avaliado e nao integrado por estar superado. Windows/Linux nativos e acesso aos PRs/CI Schottge parciais.

Proxima atividade: tratar os dois contratos de testes e a troca de variante PowerShell em slices separados aprovados; resolver encerramento dos PRs apos autorizacao explicita e reexecutar GitHub CI apos regularizar faturamento.

## Correcao minima de estabilidade em dev - 2026-09-10

Solicitacao: identificar e corrigir as duas falhas README/filelock, eliminar erros de ty, corrigir selecao de Python no PowerShell e validar Windows/Linux nativos com codigo minimo, legivel e sem monkeypatch.

Entregas:

- Commits atomicos humanos publicados nos tres remotos de dev: 94cb0b39 (contratos), 62d86e14 (tipagem/lock) e 45e00ad53c41dae5c5f1efccffb5fbdad89fcafd (ambiente Python). Workspace versionado limpo e destinos conferidos por git ls-remote. Sem alteracao de main/master, branches novos, worktrees, PRs ou merges.

- README: test_readme_exists_and_has_core_sections exigia titulo antigo # SSA_Consulta_Rapida e secoes antigas Instalacao/Uso/Testes. Agora verifica os titulos publicados # SSA Consulta Rapida, Execucao, Dados e importacao e Distribuicao. README de produto preservado.
- filelock: test_filelock_version_floor_pinned_in_every_manifest exigia exatamente filelock>=3.20.3, mas os manifestos ja declaram >=3.32.6,<4. O novo teste compara com a declaracao canonica de pyproject.toml, incluindo limites inferior e superior. Nenhuma dependencia reduzida.
- Tipagem: contador de geracoes declarado int; reducao de mascaras booleanas usa np.any(axis=0); DetailsSeriesIndex usa Mapping.get herdado com o cache existente; imports de lock dependem de sys.platform; verificacoes de temporarios usam is not None; cast redundante removido. Sem supressoes novas e sem remover limpeza apos erro.
- Windows lock: erro em seek(0) agora chega ao tratamento existente; arquivo invalido nao segue para locking. Testes de backend usam arquivos temporarios reais e ha caso exclusivo Windows de falha de seek.
- Python: setup_env.ps1/setup_env.sh exportam a versao para a variante correta; activate_repo.ps1 cria o ambiente com uv venv --python alvo, valida versao e Py_GIL_DISABLED antes de ativar fallback, preserva venv existente e propaga falha do uv. Helper Invoke-Python removido. Backups /tmp/setup_env.ps1.20260910_114230.bak, /tmp/setup_env.sh.20260910_114230.bak, /tmp/activate_repo.ps1.20260910_114230.bak; CRLF preservado.
- Regressao: selecao FT nao contamina stable; pedido FT usa .venv_ft; versao incorreta e build sem FT falham antes de ativacao. Sem monkeypatch novo. Fixtures preexistentes de pytest preservadas.

Validacao local:

- Suite completa no mesmo recorte do CI: 272 modulos, 63 processos/lotes (62 modulos GUI isolados), 2.881 passaram, 9 pulados, 0 falhas, 491,9s. Excluidos legacy_tests, gui_poc_smoke_test.py e main_test.py conforme recorte estabelecido. Foram resolvidas as 2 falhas antigas e adicionados 9 casos aprovados mais 1 caso exclusivo Windows pulado no macOS. Resumo /tmp/ssa_fix_validation_summary.json; detalhes /tmp/ssa_fix_pytest_summary.json e logs /tmp/ssa_fix_pytest_000.log a _062.log.

- 611 arquivos Python: py_compile e Ruff sem falhas.
- ty no escopo main.py armazenamento core gui exportacao utils interface: zero diagnosticos em macOS e no alvo estatico win32. Resultado estatico nao equivale a execucao nativa Windows.
- Testes focados: 125 passaram/1 pulado em filtros, cancelamento, cache e locks; 20 passaram em gravacao atomica/concorrencia; 83 passaram em scripts de ambiente. Apos revisao, 9 casos PowerShell passaram com .venv_ft real no harness.
- Comparacao da reducao OR: resultados identicos em 0, 1.000 e 100.000 linhas, 12 colunas. Em 100 mil linhas: 59,28 us antes e 59,60 us depois; pico tracemalloc 1.301.017 / 1.301.369 bytes. Amostra sintetica, sem crescimento relevante de custo. Evidencia: /tmp/ssa_stability_filter_benchmark.json. Semantica NumPy: https://numpy.org/doc/stable/reference/generated/numpy.any.html.
- pip-audit: 99 combinacoes nome/versao do lock, zero vulnerabilidades nas tres particoes.
- Gitleaks, TruffleHog e detect-secrets: zero achados no diff/arquivos alterados. TruffleHog sem verificacao remota.
- Bandit: zero medio/alto, cinco avisos baixos preexistentes (antes eram seis; removido except vazio do lock). Vulture: tres candidatos preexistentes fora do patch.
- ShellCheck warning+ sem achados; tres SC2016 informativos preexistentes. PSScriptAnalyzer sem erros, seis avisos preexistentes nos dois scripts PowerShell.
- CodeRabbit: nenhum problema de producao; unica observacao de teste FT corrigida e revalidada.
- Semgrep: zero achados em 194 arquivos/1115 regras Python e multilinguagem. Uma regra atingiu timeout em gui/gui_ssa.py na primeira passagem; repeticao desse arquivo com limite de 30s concluiu sem erros ou achados.
- Linux Ubuntu 26.04 ARM64: 248 testes passaram, 9 pulados (1 Windows/msvcrt e 8 PowerShell ausente), 0 falhas. Python 3.13.12 e dependencias Linux isolados em /tmp, checkout ro, nenhum ambiente macOS compartilhado. Ty completo Linux sem diagnosticos; Ruff, py_compile e bash -n aprovados no escopo. Evidencias copiadas ao host e conferidas por SHA256. Lima desligada graciosamente, estado Stopped restaurado. Resumo: /tmp/ssa_fix_linux_summary.txt.
- GUI macOS Cocoa nativo: SQLite/DataLoader com 12 linhas, busca assincrona 6 resultados, filtro combinado/exclusao 3, lookup fora do filtro e painel de detalhes corretos; limpeza voltou a 12. Captura /tmp/ssa_fix_gui.png; preferencias reais preservadas por hash e zero avisos/erros nos logs. Inicializacao 530,62ms, busca 112,14ms, lookup 16,87ms, fechamento 8,25ms; RSS 192,91MiB ao carregar/256,14MiB apos interacoes; CPU 1,73% em amostra curta. Nao e benchmark representativo nem comparavel ao backend offscreen anterior. Sobreposicoes de texto do screenshot offscreen anterior nao reproduzidas em Cocoa. Relatorio /tmp/ssa_fix_gui_report.json; harness /tmp/ssa_fix_gui_probe.py.

Pendencias e limites:

- Windows 11 ARM64 existente esta na configuracao inicial OOBE. Sem desktop autenticado ou terminal nativo disponivel. Nao foi avancada configuracao de conta nem fornecida senha.
- Linux validado em Ubuntu 26.04 ARM64 via VM existente; nao representa certificacao de Debian/Artix, AMD64 ou Windows AMD64.
- GitHub CI continua bloqueado por faturamento no novo SHA; sete jobs nao iniciaram. CI GitLab automatico aprovado, pytest-full remoto manual nao executado. Validacao local completa registrada acima.

CI final do SHA 45e00ad53c41dae5c5f1efccffb5fbdad89fcafd:

- GitLab pipeline 2837648683 aprovado em 1m19s (46s em fila): quality-gates e secret-scan aprovados. pytest-full continua manual e nao foi executado remotamente; a suite completa foi executada localmente. https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines/2837648683
- GitHub minimal-ci 34492582228, CodeQL 34492582273 e Secret Scan 34492582294 encerrados com bloqueio de faturamento. Sete jobs falhos com zero etapas e anotacao individual confirmando billing; dois jobs ignorados. Nenhum teste remoto GitHub executou. https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34492582228
- Remotos origin, schottge e gitlab conferidos em 45e00ad5; workspace versionado limpo. CI Schottge nao acessivel com a integracao atual; publicacao por SSH confirmada. Nenhuma reexecucao, mutacao de PR ou mudanca de configuracao de CI realizada.

Status: contratos, tipagem, selecao Python e Linux ARM64 entregues; Windows nativo parcial por OOBE; nenhum item ignorado. Relatorio local ignorado pelo Git.

Proxima atividade: concluir configuracao inicial/login da VM Windows e executar selecao/provisionamento Python e locks no Windows nativo; repetir CI GitHub quando o bloqueio externo for resolvido.

## Windows ARM e PyInstaller AMD64 - 2026-09-10

Solicitacao original: preparar a VM w11arm para desenvolvimento, gerar executaveis Windows AMD64 com PyInstaller, validar e documentar.

Status por pedido:

- Entregue: configuracao inicial da VM concluida; Windows 11 Pro ARM64, build 26200, 2 CPUs virtuais e 4 GiB RAM.
- Entregue: clone nativo em C:\Users\mauri\gitlab\ssa_consulta_rapida_pyqt6, branch dev. Ferramentas portateis em %LOCALAPPDATA%\SSADev: MinGit 2.55.0.5 x64, uv 0.12.12 x64 e PowerShell 7.6.6 x64, com SHA256 conferido nas fontes oficiais. Python 3.13.12 AMD64 e dependencias do lock instalados em .venv-win.
- Entregue: selecao explicita de Python Windows x64, verificacao da arquitetura do interprete e isolamento/restauracao de .venv-win no fluxo PyInstaller. Commit 29e8e232ecfc297be78b4da5e36112d96b0784f2.
- Entregue localmente: staging ZIP encurtado no TEMP do sistema e tres limpezas consolidadas em um unico finally, com falhas de remocao visiveis. Commit 08a298f9. Validacao desse ajuste na VM ainda pendente.
- Entregue: guia atualizado em docs/BUILD_PYINSTALLER_GUIA_COMPLETO.md. Commit 46f3fece45c99ba21973fc54198c17256231bafa. Tres commits humanos publicados nos tres remotos; sem criacao de branch ou PR e sem merge.
- Parcial: CLI e GUI foram gerados na VM a partir de 29e8e232. O fluxo encerrou em 274.55s com falha posterior no ZIP: WinError 206/3 em caminhos profundos de lxml e licencas NumPy. O novo staging corrige esse caso nos testes locais, mas o ZIP final ainda nao foi repetido no Windows.
- Parcial: leitura dos cabecalhos PE, teste CLI --help, abertura/interacao da GUI e suite Windows preparados, ainda nao executados. O Mac bloqueou a sessao; duas tentativas de captura informaram necessidade de desbloqueio manual. Usuario avisado. Nenhum pedido ignorado.

Validacao e evidencias:

- Windows real: platform.machine() = ARM64, sysconfig.get_platform() = win-amd64, PROCESSOR_ARCHITECTURE = AMD64 dentro do Python x64. PyInstaller 6.22.2 selecionou Windows-64bit-intel sem alterar artificialmente a arquitetura. Evidencia: /tmp/ssa-win-native.IFL7As/architecture.json e toolchain.log.
- Build nativo: log /tmp/ssa-win-native.IFL7As/build.log confirma geracao dos dois executaveis e falha na montagem do ZIP. Na VM: launchers/dist/windows_amd64/SSA_CLI_v4.50_windows_amd64 e SSA_GUI_v4.50_windows_amd64. Nao foram copiados ao host nem qualificados para distribuicao.
- Testes macOS: 167 passaram e 3 exclusivos de Windows foram ignorados no conjunto de build/release; 46 passaram no packager. Total de casos distintos: 213 aprovados, 3 ignorados. Contratos de documentacao revalidados separadamente: 4 aprovados, ja incluidos no conjunto anterior.
- py_compile, Ruff e ty aprovados no escopo; ty tambem conferido para Windows e Linux no slice de arquitetura. PSScriptAnalyzer sem erros; 8 avisos e 12 informativos preexistentes nos wrappers. Nenhum shell script alterado.
- Semgrep 1115 regras: zero achados nos arquivos alterados. Vulture, Gitleaks, TruffleHog e detect-secrets: zero achados no escopo. pip-audit: 47 dependencias instaladas, zero vulnerabilidades; dependencias nao mudaram nesta rodada.
- Bandit: sem novo achado de producao. Alertas novos restritos a asserts e subprocess controlados nos testes; o packager mantem dois alertas baixos preexistentes.
- CodeRabbit fechou os achados de criacao interna fora do try e limpeza no cancelamento. O finally foi validado pela estrutura e testes de sucesso/falha; nao houve teste nativo de sinal/cancelamento.
- Logs de verificacao: /tmp/ssa_win_* e /tmp/ssa_win_package_*. Evidencia visual disponivel nesta rodada: desktop Windows, ferramentas e arquitetura. Ainda nao ha captura da GUI Windows.
- Memoria e desempenho: VM observada com 2 vCPUs/4 GiB; build concluido sem timeout. Nao houve medicao de RSS/CPU ou tempo de abertura da GUI Windows. Nao representa certificacao em hardware Windows AMD64 nem comparacao de desempenho com macOS/Linux.

Riscos preexistentes registrados pela revisao:

- _create_package_zip grava diretamente no ZIP final. Uma falha durante a compressao pode deixar pacote parcial ou substituir o anterior. Slice futuro: gravar temporario no mesmo destino e publicar por os.replace, com teste de preservacao do pacote anterior.
- Falha na alocacao inicial do TEMP continua propagando excecao, como a criacao inicial anterior. Avaliar mensagem/contrato em slice separado, preservando falhas visiveis.

Proxima atividade:

1. Desbloquear o Mac para restabelecer CUA. Nao reutilizar credenciais de outro sistema.
2. Sincronizar o clone Windows com 46f3fece e repetir release completo. Assert-BuildInfo exige commit do binario igual ao HEAD; nao editar metadados nem reaproveitar binarios de outro commit por SkipBuild.
3. Executar a suite Windows, verificar PE 0x8664 e CLI, testar GUI com 12 registros sinteticos, busca/filtros/detalhes/redimensionamento, fechar normalmente e recolher o ZIP/relatorios.
4. Registrar o resultado nativo final aqui. O guia versionado contem os comandos de preparacao e release.

Contas de navegador: GitHub schottge-menon usa Safari; GitHub mauriciomenon usa Edge. O resultado anterior de acesso Schottge nao comprova indisponibilidade do CI na conta correta.

CI final e estado do workspace em 46f3fece:

- Remotos origin, schottge e gitlab conferidos por SSH no mesmo SHA 46f3fece45c99ba21973fc54198c17256231bafa. Branch dev e workspace versionado limpo.
- GitHub mauriciomenon: minimal-ci 34500158678, CodeQL 34500158607 e Secret Scan 34500158608 encerraram com bloqueio de faturamento confirmado nas anotacoes dos sete jobs falhos; zero etapas executadas e dois jobs ignorados. Nenhum teste remoto executou. https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34500158678
- GitLab: consulta de API sem autenticacao retornou 404. Schottge: CI ainda nao consultado no Safari autenticado. Esses limites nao demonstram ausencia nem falha de CI; consulta visual pendente do desbloqueio do Mac.
- Servidor temporario de transferencia entre host e VM encerrado antes da pausa. Arquivos de retomada e logs preservados em /tmp/ssa-win-native.IFL7As; VM mantida no estado existente.


## 2026-09-13 - Reteste da auditoria depois da implementacao

Estado: codigo commitado e publicado nos tres destinos da branch
fix/audit-surgical-fixes ate 1ef9edaf. Base da implementacao: ca542fb5.
A documentacao segue em commit posterior. Este registro substitui as entradas
locais de 12/09 desta auditoria; o historico de outras entregas acima foi preservado.

Resolvidos: exportacao JSON/CSV/TSV na CLI e GUI, API/stdout preservados, F3/F4,
N7/N8/N11, coordenacao A7/Z-A15/Z-C1/Z-C5, C2 e cinco casos de feedback D7.
Inclui flush de preferencias sem parar fila, prazo novo apos preferencias, WAL
canonico com symlink e revalidacao depois do segundo dialogo de exportacao.
Hooks de autoria instalados; CI publicada em c49dbac7, sem execucao remota comprovada.

A passagem completa esta em [VALIDATION_PLAN.md](VALIDATION_PLAN.md): hashes,
comandos, casos de regressao e criterios de aceite. Evidencia local detalhada
em [AUDIT_FIXES_REPORT.md](AUDIT_FIXES_REPORT.md), secao I1. py_compile/Ruff/ty
passaram nos 22 Python; selecoes existentes passaram. Nao somar selecoes
sobrepostas. Nenhum caso novo de teste foi escrito nesta implementacao.

Pendencias reais para o proximo modelo:

1. Suite completa e scanners amplos; classificar regressao, passivo anterior,
   falha de ferramenta e timeout separadamente. Registrar SHA/ambiente/comandos.
2. Reproducoes da matriz da passagem, incluindo N8 A-expira/B-pronto/A-tardio,
   N7 preferencias/timers e N11 Qt/derivadas depois de preferencias.
3. Uso nativo e capturas em plataformas acessiveis; medir CPU/RSS/tempo dos
   fluxos alterados com dados comparaveis. Offscreen nao substitui teste visual.
4. Sistemas de arquivos sem hard link, caminhos protegidos e corrida de destino
   sem sobrescrita. A falha deve continuar explicita e preservar arquivos.
5. Autoria: 16 mensagens antigas em e62a85bf..ca542fb5 possuem credito Devin.
   Novos commits sao humanos e sem creditos. Nao reescrever sem autorizacao
   especifica; a simulacao antiga nao inclui descendentes desta implementacao.
6. Bloqueio nativo online completo indisponivel nos planos/tipos consultados.
   Hooks podem ser contornados; CI nao recusa todo push. Nao alegar equivalencia.
7. D1: cancelamento dentro da leitura de uma planilha nao implementado. C3:
   literais/aliases antigos preservados. D5/inventario F2: nenhuma exclusao de
   APIs/compatibilidade. Demais alegacoes D7 nao foram revalidadas individualmente.
8. Triar avisos GitHub da branch padrao mostrados no push (45 mauriciomenon,
   5 schottge); nao sao resultados novos de auditoria das dependencias do patch.

Proxima atividade: executar VALIDATION_PLAN.md no HEAD recebido e publicar laudo
com antes/depois, resultados comprovados, limites e pendencias. Esta passagem nao
autoriza mudar politica, criar branch/PR/worktree, aplicar merge ou reescrever Git.
