# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Estabilizacao (branch rev)

- Busca com regex (`~`): expressoes com mais de 3 repeticoes sem limite (`*`, `+`, `{n,}`), como `a*a*a*a*b`, passam a ser recusadas como as demais expressoes perigosas (aviso no log). Antes passavam pela guarda e podiam travar a busca dentro do motor de regex, sem como cancelar. Um `.*` no inicio da expressao e ignorado: o resultado e o mesmo e a busca fica ate 70 vezes mais rapida (19 s para 0,3 s em 100 mil descricoes no teste).

- Banco com texto em UTF-8 invalido (gravado pelo app C++ antigo no macOS, que deixava um byte `\xC2` solto em celulas com espaco nao separavel) nao derruba mais a carga na GUI e na CLI: antes a leitura parava com `Could not decode to UTF-8`. As celulas afetadas aparecem com o caractere de substituicao (U+FFFD) e o log avisa quantas sao, em quais colunas e exemplos de SSA. O banco nao e alterado; bancos sem esse defeito carregam como antes.

- Busca geral na GUI: refinar uma busca (acrescentar termos, ex.: "alfa" e depois "alfa dois") passa a filtrar so o resultado anterior, como foi projetado. Antes a GUI nunca soltava o worker da busca terminada, o refino nunca ligava e toda busca percorria a tabela inteira. O resultado anterior so e reaproveitado se os dados nao mudaram desde ele (recarga, edicao ou ordenacao voltam a buscar na tabela inteira).

- Preferencias da GUI: sairam "Carregar dados do banco ao iniciar", "Usar cache de filtros" e "Limpar cache ao recarregar dados", que nao mudavam nada. A GUI sempre carrega o banco ao abrir (a caixa vinha desmarcada e mostrava o contrario), o cache de filtros esta sempre ligado (o tamanho continua em "Cache de filtros") e toda recarga ja limpa o cache. O grupo passa a se chamar "Comportamento". Preferencias salvas com essas chaves continuam abrindo normalmente.

- `scripts/create_distribution.py`: sai a opcao `--include-sample-db` e o banco de exemplo `dist_assets/sample_db/ssas_example.db` (schema antigo, 82 colunas, sem uso). O pacote e o instalador nao tem mais `BancoExemplo/`; o `LEIA-ME-USUARIO.txt` perde a secao 6, e "Banco local escolhido explicitamente" passa a ser a 6. Para levar um banco junto, use `--include-local-db <caminho>`.

- Pasta `exportacao/` da pasta de runtime: nao e mais criada pelos builds, pelo pacote nem pelo setup, porque nenhum export grava nela (CSV/XLSX vao para `docs_saida`). O `.gitignore` deixa de ignorar `exportacao/`, que e o pacote de codigo do export: um arquivo novo ali ficava fora do Git sem aviso.

- Busca com regex (`~`) e filtros: com o pyarrow instalado (extra `web`/Streamlit), `\w`, `\s` e `\b` so reconheciam ASCII, e `~^\w+$` nao achava "ação", "niño", "straße" nem "garçon". Agora o texto usa sempre o armazenamento Python do pandas, e a busca da o mesmo resultado com ou sem pyarrow.

- Guia de instalacao, "Executar Testes Automatizados": os comandos apontavam para `tests\test_imports.py` e `tests\teste_sistema_completo.py`, que nao testavam nada (um so imprimia, o outro estava vazio). Agora: `scripts\smoke_cli.py --json`, `pytest tests\test_database.py` e a suite completa. Sairam de `tests/` 39 scripts que nunca rodavam no pytest (manuais, de diagnostico ou vazios).
- `scripts/check_docs.py --paths X`: um caminho inexistente ou que nao e Markdown agora e erro (codigo 2, `{"error": ...}` no `--json`); antes era ignorado e o gate passava com 0 arquivos verificados. `run_quality_gates.py --extra-doc` passa a somar o arquivo aos docs do repositorio, como a ajuda dizia; antes checava so o extra.
- Importacao com `docs_entrada` em pen drive ou disco FAT/exFAT no Windows: mover a planilha importada para `processadas` passa a copiar e apagar a origem quando o sistema de arquivos recusa hard link com `EINVAL` (como ja acontecia com `EXDEV`/`EPERM`/`EACCES`/`ENOTSUP`). Antes esse erro interrompia o pos-processamento.
- Removidos `requirements_ci.txt` e `requirements_clean.txt`: nenhum CI, script ou guia os usava (o segundo nem tinha dependencias). Para o ambiente de desenvolvimento e CI use `uv sync --frozen`; para build, `uv sync --frozen --extra build`.
- Build Nuitka Debian: sairam os ramos para clone em `/mnt/*` e as variaveis `SSA_NUITKA_NATIVE_ROOT`, `SSA_NUITKA_VENV_DIR`, `SSA_NUITKA_WORK_ROOT` e `KEEP_NUITKA_WORK_DIR`, que so valiam nesses ramos. A guarda nativa ja bloqueava `/mnt/*` antes, entao nunca tinham efeito. O Nuitka grava direto em `builds/nuitka/<alvo>`, como ja acontecia: uma falha no build deixa o alvo sem `.dist`.
- Guia de antivirus (`docs/ANTIVIRUS_EXCLUSOES.md`, tambem no pacote): as exclusoes indicadas passam a ser as pastas onde os builds gravam (`launchers\dist`, `launchers\platforms`, `builds`, `dist_packages`). Antes o guia mandava excluir `build\` e `dist\` da raiz, que os builds nao usam, e o falso positivo continuava.
- `scripts/append_profile_snippet.ps1`: o trecho gravado no `$PROFILE` procurava `activate_repo.ps1` na raiz do repositorio, onde ele nao existe, e a ativacao automatica nunca acontecia (sem aviso). Agora aponta para `dev_env\activate_repo.ps1`. Quem ja rodou o script deve trocar o caminho no proprio `$PROFILE` (ou apagar o trecho antigo e rodar de novo).
- DMG do macOS com o nome do backend, como os demais pacotes: `SSA_Consulta_Rapida_v<versao>_macos_arm64_pyinstaller.dmg` (antes `..._macos_arm64.dmg`). Ao publicar a release, o arquivo e renomeado sem o sufixo, como os demais.
- Builds Debian: um script por backend (`dev_env/build/build_nuitka_debian.sh`, `build_pyinstaller_debian.sh`, `build_pyoxidizer_debian.sh`), com `--platform debian_amd64` (padrao) ou `--platform debian_arm64`; um alvo diferente para com codigo 2 antes de qualquer passo de build. Saem `build_nuitka_debian_arm64.sh`, `build_pyinstaller_debian_arm64.sh` e `build_pyoxidizer_debian_arm64.sh`, que eram copias do amd64 com outro nome de alvo; `release_debian_arm64.sh` ja chama o novo formato. Quem rodava um `_arm64.sh` direto deve usar, por exemplo, `bash dev_env/build/build_nuitka_debian.sh --platform debian_arm64`.
- Guia de migracao (Windows): o clone passa a ser feito em `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`. Antes o guia mandava clonar em `C:\Users\<usuario>\git\SSA_Consulta_Rapida`, e o passo seguinte (`.\dev_env\activate_env.ps1`) era bloqueado pela guarda nativa. No guia de distribuicao, o exemplo Debian usava `~/gitlab`, pasta que a guarda bloqueia no Linux; agora usa `~/gitlab_repo/ssa_consulta_rapida_pyqt6`.
- README, nova secao "Pasta do clone (guarda nativa)": a pasta exigida em cada sistema pelos scripts de ambiente, testes, hooks e build (Windows: `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`; WSL: `~/gitlab_repo/ssa_consulta_rapida_pyqt6` em ext4; Linux e macOS: qualquer pasta fora de `/mnt/*` e `~/gitlab`). Antes a regra so aparecia na mensagem de bloqueio.
- **Python minimo passa a 3.11** (antes 3.10; CI e builds ja usavam 3.13): exigido pelas correcoes de seguranca abaixo. Motivos: o Python 3.10 chega ao fim de suporte em 10/2026; o pandas 3 exige 3.11, e em 3.10 o lock resolvia o pandas 2.3, com o qual as correcoes de datas e extracao nunca foram testadas. `dev_env/bootstrap.sh`, `dev_env/bootstrap.ps1` e `launchers/build_multiplatform.py` nao caem mais para 3.10 quando nao acham 3.13/3.12/3.11.
- Dependencias atualizadas e auditadas (OSV e data de publicacao de cada versao do lock): Pillow 13.0.0 (corrige 41 avisos, 5 criticos, da 12.3.0), filelock 4.2.1 (corrige 1 aviso alto), certifi 2026.10.19 (aviso critico), virtualenv 21.14.13 (aviso alto), urllib3 2.8.0, pandas 3.0.6, numpy 2.5.4, PyInstaller 6.22.3, Nuitka 4.3.1, Streamlit 1.66.1, ruff 0.17.1, ty 0.0.89, entre outras. Nenhum aviso de pacote malicioso. setuptools 84.2.1 (25/10) corrige o ultimo aviso (baixo, GHSA-xmj3-9gf7-h52w); o build do projeto tambem passa a exigir setuptools 84.2.1 ou mais novo. pip-audit sobre todos os extras: nenhuma vulnerabilidade conhecida. Lock gerado com o mesmo uv 0.9.30 das imagens de CI, sem mudar o formato do `uv.lock`.
- Carencia de dependencias: `[tool.uv] exclude-newer = "7 days"` impede resolver versoes publicadas ha menos de 7 dias (janela tipica de release comprometida). Excecoes so para correcao de seguranca verificada (OSV limpo e provenance do PyPI do repositorio oficial), registradas no `pyproject.toml`.
- Os usos de `inplace=` e de `ExcelFile.parse`, depreciados no pandas 3.1, foram trocados. Sai o extra `dev` duplicado: as ferramentas de desenvolvimento vem do grupo `dev`; quem usava `uv sync --frozen --extra dev` (inclusive os CIs, ja ajustados) deve usar `uv sync --frozen`.
- `launchers/build_simple.py` roda o PyInstaller pelo mesmo Python do projeto e para logo com a instrucao `uv run --extra build python launchers/build_simple.py` quando ele nao esta instalado. Antes chamava o `pyinstaller` do PATH, que pode ser outro Python sem pandas/tabulate/filelock: o executavel saia quebrado (a CLI nao iniciava).
- `launchers/build_simple.py` deixa de embutir a pasta `data/` (banco e backups) no executavel e leva de `config/` so os arquivos versionados, como os demais builds. Antes levava a pasta inteira da maquina do build, inclusive preferencias locais.
- Removido `utils/robust_importer.py`: o programa importa planilhas pelo extractor, e a sincronizacao de derivadas passa a ler a aba diretamente (mesmo resultado). Sairam junto as variaveis `SSA_IMPORT_DEBUG` e `SSA_MAX_HEADER_SCAN`, a gravacao de `reports/last_import_stats.json` na pasta corrente e os scripts de desempenho que mediam esse importador (`scripts/run_import_perf.sh`, `run_perf_analysis.sh`, `run_perf_no_direnv.sh`, `analyze_perf_history.py`).
- Removidos `scripts/optimize_database_indexes.py` (criava 6 indices fora do schema, no banco relativo a pasta corrente) e `scripts_manutencao/cleanup_emergency.py` (tratava `ssas` como tabela; no schema atual e uma VIEW). Nenhum fluxo do programa os usava.
- Builds e pacotes: a copia do banco para o pacote (`create_distribution.py`, inclusive o banco de runtime do PyOxidizer, antes copiado com `copy2`; `build_multiplatform.py`; `copy_data_to_builds.py`) segue uma regra so: origem aberta so leitura (inclusive em caminho de rede UNC), temporario de nome unico, `quick_check`, lock no destino e recusa se o destino tiver `-wal`/`-shm`/`-journal`. Antes so `copy_data_to_builds.py` fazia tudo isso; os outros podiam substituir um banco aberto.
- SAM API (GUI e `scripts/import_pai_api_xlsx.py`): importar para um banco fora das pastas padrao do programa (por exemplo, com `SSA_DB_PATH` apontando para outra pasta) passa a funcionar como em "Importar arquivos" e na reanalise. Antes a importacao do SAM API recusava esse banco por seguranca de caminho e nao gravava nada.
- SAM API: a GUI passa a respeitar `SSA_SCRAP_REPORT_RUNNER` (`uv` ou `pythonpath`), pela mesma regra de `scripts/import_pai_api_xlsx.py`; antes usava sempre `uv`. Sem a variavel nada muda.
- App empacotado: quando o programa substitui `SSA_DB_PATH`, `SSA_CONFIG_DIR` ou `SSA_RUNTIME_ROOT` definidos pelo usuario pelas pastas do runtime, o log registra um aviso com o valor ignorado e o usado. Antes a troca era silenciosa. O comportamento nao muda: no pacote, essas pastas continuam sendo as do runtime (o PyOxidizer tambem ignora `SSA_RUNTIME_ROOT`).
- Removidos `utils/fallback/emergency_import.py` e `utils/fallback/main_simple.py`. Apesar do nome, a "importacao de emergencia" nao importava planilhas: criava um banco de schema antigo com 2 SSAs de teste e, com `--force`, arquivava o banco real e publicava esse no lugar. O CLI simplificado so contava registros desse banco. Para recuperar o banco, veja "Recuperacao do banco" no README (a importacao restaura o snapshot valido mais recente).
- CLI: sairam os comandos `debug` e `toggle-debug`, que so trocavam uma flag sem efeito, e a variavel `SSA_CLI_ENHANCEMENTS_PATH` (o arquivo fica na pasta de config). `config/cli_enhancements.json` tem so `enhanced_table_printer` (ligado por `enhanced-on`/`enhanced-off`); as flags `unified_column_config`, `improved_ssa_normalization`, `word_wrap_in_cli` e `debug_output` nunca mudavam nada e `status-cli` deixa de lista-las. Um arquivo antigo com essas chaves continua sendo lido.
- Arquivos de `config/` achados por uma regra so (`SSA_CONFIG_DIR` valido, senao `config/` da raiz do programa): a CLI le `column_priority.json`, `display_mappings.json`, `gui_main_preferences.json` e `cli_enhancements.json`, e a GUI le `filter_aliases.json`, dessa pasta. Antes a CLI lia `column_priority.json` da pasta corrente (iniciada fora da raiz, perdia as prioridades sem aviso) e, no pacote, editar esses arquivos na pasta de config do usuario nao tinha efeito; o comando de debug da CLI gravava dentro do pacote.
- Configuracoes da CLI e da importacao: `config/settings.json` passa a sobrepor `config/default_settings.json` por secao e por chave, em vez de substitui-lo inteiro. Assim `import_settings` do arquivo padrao vale mesmo com `settings.json` presente (antes so valia sem ele). Ao salvar pela CLI, o `settings.json` grava as configuracoes efetivas completas. Sairam as larguras de coluna com rotulos que a CLI nao usa (`Emi.`, `Exe.`, `Emissor`, `Executor`, `Sem.\nCadastro`, `Data\nCadastro`), que nunca tinham efeito.
- Removidas as variaveis `SSA_DERIVADAS_ACTOR` e `SSA_SYNC_ACTOR`: o autor gravado em cada sincronizacao de derivadas e o usuario do sistema (`USER`/`USERNAME`), como ja era quando nenhuma das duas estava definida.
- Removida a variavel `SSA_EXTRA_DIRS`: a criacao das pastas no inicio usa so a lista fixa do programa e nao cria nem exige pastas extras indicadas pelo ambiente.
- Filtro avancado de "Divisao" removido de vez: ja nao aparecia na tela, mas um filtro salvo antigo com essa chave ainda era aplicado sem aparecer (e herdando a divisao do setor emissor). Agora a chave salva e ignorada, com aviso no log. A macro "SSA Executadas Divisao" e a ordenacao dos setores nao mudam.
- SAM API (GUI e `scripts/import_pai_api_xlsx.py`): a pasta do `scrap_report` e achada pela mesma regra. A GUI passa a respeitar `SSA_SCRAP_REPORT_ROOT` (a mensagem de erro ja mandava defini-la), e o script passa a procurar a pasta irma do projeto por padrao, como a GUI; `SSA_ALLOW_SIBLING_SCRAP_REPORT=0` desliga essa busca nos dois.
- Removido `config/logging.json`: o programa nunca o lia (niveis, arquivos e formato de log vem de `utils/robust_logging.py`). Editar esse arquivo nao tinha efeito.
- Interface web (Streamlit): o cache de filtros usa o mesmo limite por item da GUI (16 MB sem `SSA_CACHE_MAX_MB`; `0` = sem limite); antes, sem a variavel, nao havia limite.
- `SSA_NON_INTERACTIVE` tem uma leitura so: liga com `1`, `true`, `yes` ou `on`; `0`, `false`, `no`, `off` ou vazio desligam. Antes a paginacao da CLI e a confirmacao de limpeza da GUI tratavam qualquer valor (ate `0`) como ligado.
- Exportacao da CLI em JSON: se dois campos tiverem o mesmo nome de exibicao, as chaves saem como "Nome (coluna_interna)" em vez de o JSON falhar; CSV e XLSX continuam com os nomes de exibicao.
- CLI: `exportar <nome>` grava o arquivo com o nome como foi digitado (antes era forcado a minusculas, ex.: `Relatorio_MEL4` virava `relatorio_mel4`).
- Sincronizacao de derivadas: quando uma familia e mais funda que o limite da closure (32 niveis), o log avisa quantas SSAs tiveram descendentes fora da contagem; antes o corte era silencioso.
- Janela de detalhes da SSA: as "SSAs derivadas diretas" e as outras relacoes diretas voltam a ser links clicaveis; antes apareciam como texto simples nessa janela.
- Filtros de coluna da GUI: desativar um filtro que fazia parte de um grupo OU (mesmo termo em varias colunas) desfaz o grupo; ao reativar uma dessas colunas sozinha ela nao volta a combinar com as outras.
- Exportacao do grafo de derivadas (PNG, SVG, Mermaid) e filtros salvos da GUI: a gravacao vai para um temporario e so substitui o arquivo no fim, com os dados ja no disco; uma falha ou queda de energia no meio nao deixa mais o arquivo anterior truncado ou vazio.
- Filtros de setor da GUI (executor/emissor, subset por setor e macro) comparam o setor sem diferenca de maiusculas e espacos: a opcao "MEL4" alcanca tambem linhas gravadas como "mel4" ou "MEL4 ".
- Filtro avancado "Ano Emissao" (GUI): o ano passa a ser o ano ISO da semana de cadastro, o mesmo das faixas de semana; sem semana, vale o ano ISO da data de cadastro. As SCC/ADI/ASE sem data, que tem semana, passam a aparecer no filtro de ano, e SSAs de inicio de janeiro que caem na ultima semana do ano anterior (ex.: 01/01/2022 = semana 202152) contam no mesmo ano da semana.
- CLI: o numero da SSA aparece como esta gravado. Antes, um valor vindo como "202512345.0" era mostrado como "025123450" ou "2025123450", e numeros longos eram truncados (ex.: "2025123456789" virava "512345678").
- Situacao no formato "COD - DESCRICAO" (como o SAM API manda, ex.: "STE - SERVICO TERMINADO") vale como o codigo tambem no filtro avancado de situacao, na excecao de SSA sem data de cadastro da importacao (SCC/ADI/ASE) e na cor dos links de SSA relacionadas nos detalhes.
- O resumo de cada importacao (`import_run_*.json`) fica sempre na mesma pasta do `ssa.log`. Antes, com `SSA_RUNTIME_ROOT` fora das pastas permitidas, ele caia em `logs/` do programa e a poda apagava os relatorios de la.
- Reanalise pela CLI interativa: o resumo final mostra arquivos processados/candidatos e arquivos com erro (mesma contagem do executavel da CLI) e o caminho real do log. Antes dois dos tres contadores nunca subiam (procuravam texto com acento que o importador nao escreve) e a mensagem citava `logs/app.log`, que nao existe.
- Ajuda da linha de comando (`main.py --help`) fiel ao que o programa faz: `--force-rescan` explica que recria o banco so com as planilhas presentes e onde fica o banco anterior (citava o `.last_import`, que nao existe); `--optimized` aparece como sem efeito; `--standard` deixa de prometer "ate 90% mais lento" e logs extras. Sai a referencia ao inexistente `GUIA_MODO_OPTIMIZED.md`.
- Guia de instalacao so com uv: saem os fluxos alternativos com `python -m venv`, `pip` e `python main.py` sem uv, e a recomendacao de `--optimized`.
- `scripts/check_docs.py` checa os Markdown que o git conhece (versionados e novos nao ignorados): arquivos locais ignorados pelo `.gitignore` (`.remember/`, `tmp/`, docs locais) nao derrubam mais os quality gates, e `dev_env/build/*.md`, antes pulado pela pasta `build`, passa a ser checado. Fora de um repositorio git o script sai com erro (codigo 2).
- `release.ps1` (build Windows) exige PowerShell 7 (`pwsh`) e para logo no inicio com a instrucao de uso. No Windows PowerShell 5.1 ele abortava com "Dependencias de build ausentes" sempre que o uv escrevia no stderr ("Using CPython ...").
- `main.py --force-rescan` sai com codigo 1 quando a importacao falha (status bloqueante, importador ocupado ou rodada parcial com arquivos com erro), pela mesma regra do executavel da CLI; antes saia 0 e scripts nao percebiam a falha.
- A CLI abre o banco somente para leitura ao carregar e recarregar a base (nunca escreve no `ssas.db`).
- `launchers/build_multiplatform.py` e `launchers/build_complete.py` nao tem mais `--auto-git`, `--git-message`, `--cleanup-online` e `--cleanup-only`: o build nao faz `git add`/commit/push nem `git rm` por conta propria.
- Novo `dev_env/build/BUILD_WINDOWS_VM_SSH.md`: build Windows numa VM pelo ssh com snapshot raso do commit, cache e Python do uv dentro de uma pasta do usuario, recuperacao dos ZIPs com conferencia de SHA-256 e limpeza completa da VM.
- Removidas as variaveis `SSA_LEGACY_SETUP_MODULE` e `SSA_ALLOW_EXTERNAL_LEGACY_SETUP_MODULE`: a criacao das pastas no inicio nao executa mais um arquivo Python indicado por variavel de ambiente.
- Uma unica definicao de SSA encerrada: STE e SES (encerramento normal), SCA e SCC (anormal). Na GUI, "Ocultar encerradas (STE/SES/SCA/SCC)" passa a esconder tambem as SCC; a macro "SSAs para baixar" lista mae ainda aberta (inclusive SAD, antes excluida por engano) com todas as filhas encerradas, contando SCA/SCC como concluidas; o filtro "Derivadas encerradas" segue a mesma regra; a ordem padrao da GUI e da CLI poe todas as encerradas no fim (antes so STE). Situacao no formato "STE - Servico Terminado" e reconhecida. Catalogo de nomes corrigido pelo Manual G05: ALE e ASL (no lugar de AIP/ASI, que nao existem no SAM) e SCC "Cancelada no Cadastramento". A importacao (o que e congelado no upsert) nao muda.
- Guia de instalacao, secao "Banco Corrompido": o procedimento antigo (`--force-rescan`, depois `--reset-db`) falha com o banco corrompido ("file is not a database"). O guia agora manda usar "Atualizar dados" na GUI, que restaura o ultimo snapshot valido, e, sem snapshot, tirar o `ssas.db` do lugar antes do `--force-rescan`.
- Guia de instalacao (tambem embutido no pacote): a secao "Reimportacao Completa" dizia que `--force-rescan` reimporta "sem zerar o banco". Agora avisa que ele recria o banco so com as planilhas presentes em `docs_entrada` (SSAs de planilhas retiradas da pasta somem), que o banco anterior fica em `data\ssas.db.full_rescan_backup_<data_hora>` e que, para so acrescentar planilhas, o caminho e "Atualizar dados" na GUI.
- CI: pushes e PRs em `dev` e `rev` tambem disparam as verificacoes (GitHub e GitLab); fora do `main` uma falha aparece sem reprovar a execucao, exceto o secret scan, que bloqueia em qualquer branch.
- Quando a importacao encontra o banco corrompido ou ausente e o restaura automaticamente do ultimo snapshot de integridade (`data/historico_backups/ssas.db.integrity_*.db`), isso agora e avisado: a GUI conclui "com Ressalvas" citando o snapshot e onde o banco anterior foi preservado, a reanalise da CLI imprime "AVISO: banco restaurado automaticamente do snapshot ..." e o `logs/import_run_*.json` ganha `integrity.restored_from_snapshot` e `integrity.restored_snapshot`. Antes a rodada aparecia so como atualizada, sem dizer que alteracoes gravadas depois do snapshot nao estavam mais no banco.
- Pacotes Nuitka (Windows amd64 e Debian amd64/arm64) levam so os arquivos versionados de `config/`; antes levavam a pasta inteira da maquina do build, inclusive preferencias da GUI (`gui_main_preferences.json`, com a configuracao do PAI), filtros salvos, estado do Streamlit, `hypercorn.toml` e backups `.bak`. Sem esses arquivos o programa usa os padroes e cria as preferencias no primeiro uso, como no pacote PyInstaller.
- `scripts/derivadas_cli.py` sem `--db` usa `SSA_DB_PATH` ou `<SSA_RUNTIME_ROOT ou pasta do programa>/data/ssas.db`; antes usava o `data/ssas.db` da pasta corrente e podia sincronizar derivadas no banco errado.
- `main.py --force-rescan` rodando pelo codigo-fonte respeita `SSA_RUNTIME_ROOT`: `docs_entrada`, `data` (banco padrao quando `SSA_DB_PATH` nao esta definido) e as pastas criadas no inicio vem dessa raiz, como na GUI, no `cli_entry` e no `rescan` interativo; antes importava as planilhas do `docs_entrada` do repositorio. O executavel empacotado nao muda.
- Rodando pelo codigo-fonte (`python /caminho/main.py`, `uv run --project ...`, GUI de desenvolvimento, scripts) a partir de outra pasta: as configuracoes (`settings.json`, mapeamentos de colunas, preferencias e filtros salvos da GUI) vem sempre da pasta `config/` do programa; antes valiam as da pasta corrente, e arquivos de config eram criados nela. `SSA_CONFIG_DIR` e o executavel empacotado nao mudam.
- Ajuda de busca da CLI e do Streamlit: o exemplo para tirar as SSAs terminadas passa a ser `!=ste` (situacao diferente de STE). O exemplo antigo `!ste` exclui qualquer linha que contenha "ste" em qualquer coluna ("ajuste", "este", "poste") e escondia cerca de 1/3 das SSAs abertas. A ajuda do Streamlit tambem deixa de dizer que `OU`/`OR` e espacos separam termos: sao texto literal; use virgula.
- Linux com mais de um usuario na mesma maquina: o segundo usuario nao recebe mais "Diretorio de locks inseguro" ao importar ou gravar; cada usuario usa o proprio diretorio de lock em `/tmp` (`ssa_consulta_rapida-<uid>`).
- `Tempo Excedido` aparece na GUI (tabela, detalhes, copiar lista) e nos detalhes/listagens da CLI no formato do SAM ("1a, 9m, 22d 5h : 47mi"); o banco continua guardando ISO 8601 ("P1Y9M22DT5H47M"), que segue sendo o valor usado por ordenacao, filtros e exportacao CSV/XLSX/JSON.
- Resumo da importacao separa "atualizadas" (algum valor da SSA mudou) de "verificadas" (mesmos dados; so o arquivo de origem foi atualizado), como no app C++; o relatorio `logs/import_run_*.json` ganha `ssa_verified`/`ssa_verified_total`. O banco grava o mesmo de antes.
- `main.py --force-rescan` (modo otimizado) nao troca mais o banco para o modo WAL do SQLite; o banco fica no modo padrao ("delete"), o mesmo da GUI, sem os arquivos `-wal`/`-shm` (WAL e inseguro em pasta de rede/OneDrive e a copia so do `ssas.db` podia perder dados). Um banco ja convertido continua em WAL ate ser recriado.
- `numero_desvios` nao recebe mais o rotulo "Desvio #N" das planilhas "SSAs com Desvio" (texto numa coluna de contagem; 3.545 linhas no banco atual): o rotulo fica vazio e a contagem vem de "Numero de Desvios", como no app C++. Valores ja gravados so mudam ao reimportar.
- Removidos de `scripts_manutencao/` 9 scripts de debug sem uso que consultavam o schema legado (`debug_*.py`, `diagnostico_rapido.py`, `diagnosticar_problemas.py`, `teste_debug_excel.py`) e `reorganizar_projeto.py`, que movia `.py` da pasta corrente.
- `import_pai_api_xlsx.py --source-xlsx ... --cleanup-manifest` nao apaga mais o XLSX de origem informado pelo usuario.
- `verificar_instalacao.ps1` usa o mesmo banco efetivo do app (`SSA_DB_PATH` ou `data\ssas.db`) e nunca reseta um banco existente; erros do reset ficam visiveis.
- Removido `scripts_manutencao/parar_importacao_e_diagnostico.py`: consultava a tabela legada `ssas` e, por isso, sempre encerrava qualquer processo Python com "import", "main.py", "ssa" ou "excel" na linha de comando, inclusive de outros projetos.
- Importacao de datas: planilhas com formatos misturados (`01/02/2026` e `03/02/2026 15:30:00`) nao trocam mais dia e mes; datas gravadas como numero serial do Excel (ex.: `45205`) viram a data correta em vez de 1970.
- Importacao de arquivos com varias abas: abas que usam nomes diferentes para a mesma coluna (ex.: `Data Cadastro` numa aba e `Emitida Em` em outra) nao perdem mais a data das linhas da segunda aba.
- Sync de derivadas: uma planilha cujas colunas de SSA pai/filho nao sao reconhecidas agora e recusada antes de gravar, com o nome do arquivo na mensagem; antes ela desativava as derivadas ja existentes e o erro so aparecia depois. Planilha com cabecalho correto e sem linhas continua significando "sem derivadas".
- `Tempo Excedido`: anos e meses nao sao mais descartados (`1a, 9m, 22d 5h : 47mi` era gravado como `P22DT5H47M`; agora `P1Y9M22DT5H47M`). Valores com trecho nao reconhecido ficam como o texto original. Os valores ja gravados so sao corrigidos ao reimportar (`--force-rescan`).
- Colunas repetidas `Desde`/`Ate`: quando uma ocorrencia vinha toda vazia (ex.: o `Ate` do Tempo Excedido), a seguinte era gravada no lugar dela (o `Ate` do Tempo Total aparecia como `ate_1`). Cada ocorrencia agora fica na sua posicao; os valores ja gravados so sao corrigidos ao reimportar.
- Copia de planilhas para `docs_entrada` que falha no meio (disco cheio, permissao) nao deixa mais um arquivo parcial para ser importado depois.
- Exportacao CSV/XLSX/JSON grava num temporario e troca no final: uma falha no meio mantem a exportacao anterior intacta em vez de deixar um arquivo truncado.
- Planilha substituida enquanto a importacao roda nao e mais marcada como importada: fica fora do cache e entra na proxima rodada. O relatorio `logs/import_run_*.json` passa a registrar `source_signature` (caminho, tamanho, mtime) de cada arquivo importado.
- Consolidacao de `docs_entrada`: recusa o relatorio de uma importacao nao concluida (candidato nao promovido, cancelado) em vez de arquivar planilhas cujos dados nao foram gravados, e deixa pendente a planilha substituida depois da importacao (mesmo nome, outro conteudo).
- CLI: o comando de exportar nao imprime mais "Exportação concluída." quando nenhum formato foi gravado, e grava em `docs_saida` da pasta de dados (`SSA_RUNTIME_ROOT`), a mesma usada pelo rescan, em vez da pasta do programa.
- Cabecalhos de planilha com outra caixa, sem acento ou com espacos extras (`NÚMERO DA SSA`, `descricao da ssa`, `Emitida   Em`) sao reconhecidos; antes a importacao falhava com colunas obrigatorias ausentes.
- `main.py --force-rescan` (modo otimizado): planilha com coluna extra de nome invalido para SQL (ex.: `Categoría`) nao aborta mais o arquivo; a coluna e saneada como no modo padrao da GUI.
- Executavel empacotado: ao abrir com um marcador de seed sem manifesto (deixado por outro backend no mesmo perfil), os arquivos ja existentes em `data`/`config` (inclusive `ssas.db`) nao sao mais sobrescritos pelos do pacote; arquivos ausentes continuam sendo copiados.
- Planilha com titulo na coluna A acima do cabecalho (ex.: "Relatorio de SSAs - exportado em ...") e importada: o cabecalho e a linha com mais nomes de coluna conhecidos, em vez da primeira celula preenchida da coluna A.
- Filtro avancado de reprogramacoes "menor ou igual": SSAs sem informacao de reprogramacao nao entram mais no resultado (antes contavam como -1), como no app C++.
- GUI: as colunas voltam a ser redimensionaveis depois de reexibir a mesma pagina; e uma importacao em que parte das planilhas nao pode ser copiada para `docs_entrada` termina "com Ressalvas", com o aviso de quantas ficaram de fora, em vez de "Concluido com sucesso".
- GUI, busca e filtros: alternar "excluir STE/SCA" durante uma busca refaz a busca em andamento (antes mostrava o resultado anterior sob o rotulo da busca nova); erro na busca volta o rotulo para o resultado exibido; o fim de uma busca nao cancela mais a busca que o usuario esta digitando; a ordenacao escolhida no cabecalho e mantida ao refazer filtros; o filtro pelo menu do cabecalho funciona em colunas agrupadas (OR) e `!MEL4`/termo parcial no setor executor nao zeram mais o resultado.

### v4.51 - 2026-09-30 (publicada; registro da candidata de 2026-09-24)

- Consolida correcoes locais de importacao, cancelamento, armazenamento e GUI ainda em validacao.
- Registra evidencia, riscos e condicoes de promocao em `RELEASE_NOTES_v4.51.md`.
- Builds locais macOS arm64, Windows arm64 e Windows amd64 da candidata concluidos a partir de `a2954a48`. A release publicada (tag `v4.51` -> `e2481cf4`, merge do PR #135) tem outros assets: ver `RELEASE_NOTES_v4.51.md`.

## [v4.50] - 2026-09-08

- Corrige paridade de importacao, isolamento de resultados e recarga apos gravacao parcial.
- Preserva cancelamento, limpeza de busca e desfazer.
- Limita caches por memoria e evita reter DataFrames filtrados nos detalhes.
- Publica fontes; evidencias e limites no doc local `docs/RELEASE_NOTES_v4.50.md` (fora do repositorio).


## [v4.47] - 2026-08-09

### Changed
- Quick executor-sector selector now shows `...` when more than one sector is active.
- Quick status include/exclude/neutral state now remains synchronized with active, column and advanced filters.
- Search cache is active on the real GUI DataFrame and survives visual-only refreshes.
- Nullable exact-search and range masks are normalized before boolean composition.
- SQLite recovery preserves the canonical SSA table, functional columns and auxiliary tables.
- Runtime/build snapshots use the SQLite backup API and include active WAL data.
- Fully rejected imports now receive deterministic classification across direct and rescan paths.
- Windows release orchestration is native-only; Linux release uses a native Linux clone.
- SQLite connections in active and maintenance paths close on exceptional exits.
- Runtime and package metadata now identify stable release `4.47`.
- Functional CLI smoke now closes its verification connection before removing the temporary Windows database.
- Exact SSA search now treats nullable Arrow values as non-matches instead of aborting the filter.

### Notes
- No database schema, application filter-operator or layout change.
- This release consolidates the stable fixes introduced after `v4.45.2`, including the `v4.46` status-filter cycle.
- No dependency jump was made without a reproduced security need.

### Security
- Updated locked `gitpython` from `3.1.57` to `3.1.58`, `python-multipart` from `0.0.28` to `0.0.31`, `setuptools` from `82.0.1` to `83.0.0` and `starlette` from `1.0.1` to `1.3.1`.
- These are the minimum versions that clear the advisories reported by `pip-audit` in build, development and web dependency paths.

### Validation
- Critical database, import, release, filter, nullable and cache groups passed on native Windows.
- `uv lock --check` and `pip-audit` passed without a known vulnerability.
- Consolidated final suite, scanners and real packaged smoke are recorded before tagging.

## [v4.46] - 2026-08-09

### Changed
- Quick SSA status buttons cycle through included, excluded (`!STATUS`) and neutral states.
- Status-button state remains synchronized with active and advanced filter views.
- Windows activation and test scripts received native path and portability hardening.

### Dependency update cycle - 2026-07-15
- Created local checkpoint tag `v4.45.1` at commit `d8c4033c6828f1ecde05f4f3140f137ee43d496f` before the dependency update slice. The tag is not published.
- Completed the dependency audit with `uv tree --outdated`, `pip-audit`, Safety, `pip check`, and `uv lock --check`.
- Current `uv.lock` contains PyPI artifact URLs only. Future lock regeneration must isolate the private Safety index configured outside the lock.
- The audit found 69 distinct update candidates across runtime, build, development, web, and transitive dependencies. Updates will be applied in controlled slices, excluding major or high-risk pre-1.0 jumps.
- Completed the first controlled lock slice in commit `afcc46da32874d93c7a6ecb8f263f35a04c34aae` (`STABILITY_PATCH: update selected dependency lock`, 2026-07-15 12:26:56 -0300). Direct updates cover `idna`, PyQt6, Nuitka, PyInstaller, Black, Filelock, Isort, Mypy, Pytest, Ruff, and Virtualenv.
- Mypy and Virtualenv required the transitive updates `ast-serialize 0.6.0`, `librt 0.13.0`, `pyinstaller-hooks-contrib 2026.6`, and `python-discovery 1.4.4`. Click `8.4.2` and Pillow `12.3.0` are also present from the previous authorized lock update.
- Full validation passed: `2526 passed, 6 skipped, 2 warnings, 11 subtests passed`; all lock, type, lint, package integrity, security, import, PyInstaller, and Nuitka checks passed.
- Remaining major, high-risk pre-1.0, and Streamlit-discrepancy candidates remain deferred.

## [v4.45] - 2026-07-11 - HARDENING PYQT6 (ESTABILIZACAO RECUPERADA)

### Recovery and stabilization - 2026-07-12
- Archived and removed the interrupted, uncommitted Cycle 4 mixin/XLSX patch before applying any forward fix.
- Kept Theme/Event/Display mixin extraction deferred; event, resize, theme and headless behavior remain in the stable implementation.
- Window close now remains refused until every owned or retired worker has actually stopped; native Qt deletion is classified without forced termination.
- PaiApi cancellation is terminal through staging and SQLite import, with ownership retained until native thread completion and no success signal after cancel.
- SQLite progress cancellation is classified with `SQLITE_INTERRUPT=9`; DataLoader distinguishes expected cancellation from callback or startup failures.
- AdvancedOptions rejects stale generations and does not rebuild controls while a user selection is waiting for the apply timer.
- Derivadas completion is exactly once, including timeout followed by a late result.
- XLSX limits are canonical across extractor, staging, PAI, robust importer, Derivadas, CLI and trusted full rescan: 64 external files, 128 MiB per file, 1 GiB per batch and 1 GiB expanded ZIP content per file.
- Details refresh uses a bounded fingerprint sample when a data revision token is available, while preserving the exact full hash path without a token.
- Global filter clear now synchronizes quick status buttons; silent fallback failures in touched runtime paths are logged.
- Dead-code review removed only the obsolete Derivadas lock allocation; Qt callbacks, slots, eventFilter, resize and dynamic theme binding were retained.

### Changed
- Promoted local baseline to `4.45` as start of hardening PyQt6 refactor cycle.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.

### P0 - Critical races fixed (4 HOTFIX_BLOCKER commits)
- `97c70fee` Explicit shutdown() prevents QThread destroyed warning and PaiApi use-after-free.
- `77da4621` SQLite progress_handler cancellation makes long queries interruptible.
- `33ab54a4` PaiApiRefreshWorker cancel() + cleanup stops ThreadPoolExecutor and subprocesses on close.
- `32688ed4` Advanced filter options computation moved off GUI thread (was blocking event loop).

### P1 - Performance/cancel/dedup (6 STABILITY_PATCH + 1 HOTFIX_BLOCKER)
- `f7be4429` ListExportWorker cancellable on shutdown.
- `1753b897` FilterWorker snapshots df_completo (shallow copy) to prevent pandas data race.
- `161f6355` busy_timeout=5000 on read connections prevents database locked under schema changes.
- `a415a9df` Unified 5 duplicate _quote_identifier copies into shared identifier_utils.quote_identifier.
- `cf6ee9d4` XLSX import limits enforced (64 files, 128 MiB each, 1 GiB batch).
- `28773ef3` Fixed derivadas_sync timeout-vs-delivery race (late results no longer lost).

### P2 - Cleanup (5 commits)
- `5f0f52b6` Removed 10 confirmed dead files (1119 lines deleted).
- `389cb892` Removed dead rescan_button widget.
- `76f4c025` Removed 4 empty debug placeholders from tests/.
- `02d1e22c` Documented retrocompat shims as removal candidates.
- `ae55f60c` Narrowed except Exception to RuntimeError/AttributeError in shutdown paths.
- `33dc6837` Replaced silent except pass in PaiApi cancel with logged RuntimeError (bandit B110).

### P3 - God Class decomposition - DEFERRED
- Extraction of Theme/Event/Display mixins degenerated into local patchwork
  (8+ module-global dependencies per mixin). Deferred by user decision.

### Deferred items (with technical justification)
- Slice 2.5/2.6 (unify SSA normalization / date parsing): 3 sources have different
  contracts (storage strict vs display compat). Requires product decision.
- Slice 3.3 (consolidate v1/v2 scripts): v1 referenced by test_stream_log_wrapper_guards.
- Slice 3.4 (unify Qt stubs): qt_stubs.py and headless_qt_stubs.py are complementary,
  not duplicates. Broad refactor of 7+ modules.
- Full except Exception triage (770 occurrences): only critical paths narrowed.

### Validation
- `ruff check .`: All checks passed.
- `ty check`: All checks passed (on touched files).
- `semgrep` p/python + p/owasp-top-ten: 0 findings on 15 touched files.
- `bandit`: 0 issues on touched files (1 B110 fixed).
- Focused pytest: 1000+ tests passed across database, GUI, PaiApi, filter, derivadas suites.
- XLSX focused validation: 137 tests passed; trusted preflight scanned 1767 files / 538283881 bytes in 0.378 s with no material RSS increase.
- AdvancedOptions/Derivadas caller validation: 588 tests passed and 1 skipped.
- Real GUI smoke loaded 96028 rows and validated pagination, simple/advanced filters, clear, details, links, Derivadas graph, theme, resize and native close.
- Five-run medians after the GUI performance fix: render 0.278 s, simple filter 0.238 s, advanced filter 0.238 s, details 0.011 s; RSS improved by about 29 MiB.
- `pip-audit`, gitleaks and verified-only trufflehog: no vulnerabilities or verified leaks.
- Preserved `v4.36` as the latest published remote tag.

## [v4.44] - 2026-07-06

### Changed
- Promoted local active baseline to `4.44`.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.
- Fixed local validation gates for the v4.44 baseline:
  - `scripts/run_tests.sh` no longer depends on Bash `mapfile`, preserving macOS system Bash compatibility.
  - `tests/test_gui_stability.py` now accepts official `data_cadastro` header variants.
- Preserved `v4.36` as the latest published remote tag.

### Validation
- `bash -n scripts/run_tests.sh`
- `shellcheck scripts/run_tests.sh`
- `ruff check .`
- `pytest -q tests`: `2455 passed, 6 skipped, 2 warnings, 11 subtests passed`

## [v4.43+ local] - 2026-06-27

### Changed
- Local top on `dev` after baseline `4.43`:
  - Advanced filter option refresh now skips the cache helper entirely on clean cache hits, while dirty refresh still recomputes values.
  - Filter worker cancel/race coverage now includes a real `QThread` cancel while `apply_general_search_terms()` is running.
  - Advanced filter mask failures now keep the displayed dataframe and `filtered_status_label` count in sync instead of showing `0 de 0 SSAs`.
  - Runtime metadata, packaging test expectations and active documentation now point to `4.43`.
  - Persistent saved filters materialize visible advanced filter selections before deduplication.
  - Deleted Qt `FilterWorker` shutdown is treated as benign cleanup instead of a warning.
  - Previous local-top notes after `4.37` remain historical context below.
  - SSA detail popup keeps lower derivadas/relacionadas area with more usable height.
  - fallback graph without DB now includes the direct parent, avoiding incomplete local hierarchy rendering.
  - local detail navigation keeps `ssa:` clicks in the details context without rewriting global search text.
- GUI status contract split:
  - `filtered_status_label` now shows only `Status: X de Y SSAs`.
  - `status_label` now shows search and zero-result notices.
- Windows column widths synchronized across runtime defaults and versioned GUI preferences.
- GUI filter tests updated to use a realistic 50-row sanitized fixture and assert the split status behavior.
- Derivadas sync agora roda por padrao ao final de qualquer adicao valida de SSAs:
  - importacao diff
  - reescaneamento completo
  - importacao explicita por arquivo
- GUI agora recarrega os dados automaticamente apos alteracao valida do banco em importacao ou reescaneamento.

### Deferred
- Deep-copy reduction in filter caches remains deferred because current contracts require mutation isolation for cached and returned dataframes.
- Derivadas tree vectorization remains deferred: the tested vectorized attempt was slower than the existing `itertuples()` path on the local 50k-row benchmark.
- `has_post_search_filters` naming/semantics remains deferred because current tests intentionally distinguish terminal-only refresh from general-search sort deferral.

### Validation
- Filtros/cache/GUI validation on the local `v4.43+` cycle:
  - `tests/test_scenario_filter_refresh_mixin_qt.py`: `8 passed`
  - `tests/test_contract_filter_worker_cancel_race.py`: `6 passed`
  - advanced options cache/dirty suite: `41 passed`
  - performance smoke: `4 passed, 1 deselected`
  - combined non-performance slice smoke: `17 passed, 4 deselected`
- Runtime visual checks executed with programmatic PyQt rendering:
  - popup details
  - derivadas/relacionadas graph
  - lower details panel
- Focused local validation recently green on affected slices:
  - `py_compile`
  - `ruff`
  - `ty`
  - focused `pytest` on GUI detail navigation, popup graph, and import-trigger contracts

## [v4.43] - 2026-06-27

### Changed
- Promoted local active baseline to `4.43`.
- Synchronized runtime metadata in `VERSION`, `config/version.json`, `pyproject.toml` and `uv.lock`.
- Aligned active docs and packaging-related tests to versioned names `v4.43`.
- Reserved local tag `v4.43` before functional GUI/filter/cache stabilization slices.

## [v4.42] - 2026-06-11

### Changed
- Promoted local active baseline to `4.42`.
- Synchronized runtime metadata in `VERSION`, `config/version.json` and `pyproject.toml`.
- Aligned active docs and packaging-related tests to versioned names `v4.42`.
- Saved filters now capture pending advanced UI selections before duplicate detection.
- Filter worker shutdown no longer logs benign deleted Qt wrapper errors as warnings.

## [v4.37] - 2026-04-01

### Changed
- Promoted local active baseline to `4.37` while preserving `v4.36` as the latest published GitHub tag.
- Hardened GUI state contracts around:
  - general search ownership
  - header reorder/sort/resize persistence
  - details preservation across refreshes
  - derivadas navigation and details rendering
- Consolidated derivadas/details popup with graph export, tree view, platform width handling, and active-screen clamping.
- Extended import/storage hardening:
  - anti-downgrade protection for `situacao` on same-date updates
  - explicit single-file import path
  - DB repair/recreate flows for invalid or incomplete databases

### Notes
- `4.37` is the active local baseline in runtime and docs.
- `v4.36` remains the latest published GitHub tag at this time.

## [v4.36] - 2026-04-01

### Changed
- Centralized `numero_ssa` storage normalization and aligned simple insert/storage sanitization.
- Stabilized simplified filter contracts and derivadas alias preflight.
- Closed a focused `pytest`/`ty`/`bandit` min-fix slice to support the tag transition.

## [v4.35] - 2026-03-24

### Changed
- Closed nullable/filter/display regressions tied to full rescan and DB readback.
- Hardened async jump-to-SSA and details rendering behavior in the GUI.
- Normalized related SSA identifiers during import and preserved canonical text storage.
- Reduced local noise from `docs_entrada` and cleaned explicit DB option packaging for local operation.

## [v4.29] - 2026-03-02

### Changed
- Release `4.29` com estabilizacao de tema/legibilidade na GUI:
  - padronizacao de popup/menu/checkbox com roles de tema;
  - texto de selecao em botoes de multiselect mostra conteudo completo quando cabe;
  - truncamento por largura util, sem corte fixo arbitrario;
  - ajustes de robustez para evitar acesso a widget Qt invalido em relayout.
- Metadados de versao sincronizados para `4.29` em `VERSION` e `config/version.json`.

## [v4.27] - 2026-03-01

### Changed
- Runtime/documentation moved to uv-first usage with explicit command priority:
  - `uv run --python 3.13 ...` as first option.
  - fallback order documented: 3.12 -> 3.11 -> 3.10.
- `requires-python` updated to `>=3.10` to keep compatibility without dropping 3.13 priority.
- `dev_env/bootstrap.sh` and `dev_env/bootstrap.ps1` now prefer 3.13 and fallback to 3.12/3.11/3.10.
- `gui/gui_ssa.py` fallback for open folder now checks executable availability (`explorer`, `open`, `xdg-open`) before spawning.
- `interface/cli_enhancement_manager.py` applies POSIX-specific chmod/fsync steps only on POSIX.

### Validation
- Multi-version isolated matrix completed with uv envs:
  - Python 3.10.18: pass
  - Python 3.11.14: pass
  - Python 3.12.11: pass
  - Python 3.13.12: pass
- Focused checks per version:
  - `py_compile`, `ruff`, `ty`
  - `pytest -q tests/test_open_docs_folder_nonblocking.py tests/test_cli_enhancement_manager_lock_usage.py tests/test_cli_enhancement_manager_atomic_save.py`

## [Historical Unreleased] - 2025-11-10

### Fixed
- **Missing imports in mixins**: Fixed NameError when accessing format_search_display and GUI_MAIN_PREFERENCES in gui/mixins/filter_gui_ssa_mixin.py
- **Desynchronized progress callbacks**: Synchronized events between core/app_logic.py and RescanWorker (file_start, file_success, file_error)
- **Record counting**: _import_single_file now returns actual number of processed records
- **Single-instance lock**: Removed buggy mechanism via TCP socket that caused hangs

### Changed
- main.py: Removed single-instance check code
- core/app_logic.py: Function _import_single_file returns tuple[bool, int] instead of just bool
- GUI allows multiple simultaneous instances (real lock is in SQLite)

### Added
- **Verification script**: verify_integrity.py for general system validation
- **Specialized script**: verify_mixin_imports.py to detect missing imports in mixins
- **Documentation**: docs/VERIFICACAO_INTEGRIDADE.md with complete technical details

### Technical Details
- Callbacks now report: start (file_start), success with count (file_success), and errors (file_error)
- Import shows real-time progress in GUI
- SQLite uses WAL mode + busy timeout for concurrency control

---

## [v4.10.0] - 2025-11-10
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.10.0

### Contexto historico
Serie 4.0 apresentou problemas persistentes em dois eixos principais: filtros e temas. Em filtros houve interpretacao incorreta de conectivos visuais, divergencia entre GUI e CLI em casos com OU encadeado e regressao em cache que permitia exibicao parcial sem aplicacao correta de exclusoes com prefixo !. Em temas houve inconsistencias na aplicacao de papeis de cor para quadros resumo, indicadores laterais e tags de filtros salvos causando contraste irregular e legibilidade reduzida em alguns sistemas.

### Correcoes
- Unificacao de parsing de conectivos OU entre GUI CLI e streamlit sem substituicao visual ambigua
- Remocao de normalizacao tardia que gerava estado intermediario incoerente nos testes de filtros
- Ajuste de cache de filtros garantindo invalidacao quando conectivos OU ou negativos sao adicionados ou removidos
- Revisao de mapeamento de papeis de tema para quadros indicadores e tags garantindo aplicacao de chave unica centralizada
- Inclusao de chaves de tema ausentes herdadas da serie 4.0 para impedir fallback silencioso

### Impacto
- Fluxo de busca retorna resultados consistentes entre interfaces
- Filtros negativos nao sao ignorados em combinacoes com OU
- Temas aplicam cores previsiveis sem variar entre plataformas
- Registro explicito do historico evita reintroducao das falhas

### Notas
- Sem alteracao de schema de banco
- Sem mudanca em formatos de exportacao
- Versao marca encerramento das falhas iniciadas na serie 4.0

---

## [v4.0.3] - 2025-10-09
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.0.3

### Highlights
- Theming: all GUI accents (frames, indicators, tag buttons, macOS contrast) now consume centralized theme roles, with new role entries for summary frames and indicator text across every theme.
- UX: global search box normalizes visual connectors, so inputs like `A || B` are displayed as `A OU B`, matching per-column behaviour and keeping the tests green.
- Consistency: summary badges, saved-filter tags, and column-filter widgets share the same palette-driven styling on both Windows and macOS.

### Notes
- No data or schema changes.
- New theme keys (`summary_*`, `indicator_text_color`) default gracefully; custom themes should extend `utils/themes.py` accordingly.

---

## [v4.0.1] - 2025-10-03
Released: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v4.0.1

### Highlights
- GUI: added "[+ OU]" per-column UI button to compose OR conditions in a single column (UI-only; storage unchanged).
- Robustness: explicit cleanup of QThreads to eliminate thread-destruction warnings.
- Documentation: `docs/HISTORICO_ULTIMOS_50_COMMITS.md` added with a navigable index and appendices.

### Notes
- No database schema changes.
- No filter syntax changes.

---

For the full technical changelog and implementation details, see `docs_saida/CHANGELOG_IMPLEMENTACOES.md`. (`docs/HISTORICO_ULTIMOS_50_COMMITS.md` was removed in e36d54c0, 2025-11-11.)

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
