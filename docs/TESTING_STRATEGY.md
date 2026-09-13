# Estrategia de Testes

Este documento descreve a estrategia geral. O
[plano de validacao da auditoria](VALIDATION_PLAN.md) contem a passagem para a
rodada completa, comandos, casos de regressao e criterios de aceite.

Na rodada de implementacao, validacoes locais selecionadas nao substituem a
suite completa, scanners, desempenho e uso visual nos sistemas suportados.
Registrar resultados por comando e revisao do codigo; nao reutilizar contagens
de uma rodada anterior como aprovacao de alteracoes novas.

Ao selecionar por `-k`, conferir que os casos criticos aparecem na coleta.
`close_event` nao seleciona `test_forced_close_disconnects_pending_workers`;
para regressao conhecida, usar tambem o node ID completo indicado na passagem.
Registrar o retorno da ferramenta original, sem perde-lo em pipes para tail/tee.

## Regressao de operacoes substituidas e nova tentativa

A matriz de concorrencia deve exercitar uma operacao A seguida de B, incluindo
retornos atrasados de A. Verificar o estado de B antes e depois de cada retorno;
constatar apenas ausencia de excecao nao comprova isolamento.

- SAM API: progresso, previa, decisao, sucesso e erro de A nao alteram B. Se o
  dialogo de A permanecer aberto durante a troca, sua resposta nao deve ser
  entregue depois que B se torna ativa.
- Inicio da SAM API: falha em construtor, preparacao, conexao ou `start()` libera
  o registro da tentativa e permite iniciar outra. Sucesso seguido de falha de
  recarga deve manter mensagem objetiva, log e orientacao `Recarregar dados`.
- Derivadas: falha no construtor e no `start()` encerra o estado de execucao;
  conferir finalizacao da UI e inicio de uma nova tentativa.
- Compactacao e validacao de outro banco: exercitar as duas operacoes nas duas
  etapas de falha, construtor e `start()`. Conferir flag, referencia, status,
  menus e inicio de nova tentativa em cada combinacao. Esses casos estao em
  `tests/test_gui_menu_import_external.py`.
- Rescan: sucesso, erro e cancelamento de A podem finalizar seu dialogo, mas nao
  mudam status, carga ou referencias do worker e dialogo de B.
- Preferencias: diferenciar escrita que retorna falso, escrita que lanca excecao
  e escrita ainda em andamento. `flush` deve informar a falha e liberar quem
  espera quando a thread termina; uma nova escrita confirmada elimina o erro.
- Fechamento: falha ao salvar preferencias precisa aparecer no status e no log;
  o adiamento restaura o flag da janela. Manter tambem os casos do prazo de
  fechamento para a mesma operacao e para uma nova operacao.

Testes Qt com `QT_QPA_PLATFORM=offscreen` verificam sinais, callbacks e estado
sem janela nativa. Registrar separadamente o uso visual no host, incluindo
fechamento, dialogos e mensagens; a execucao sem tela nao comprova essa etapa.
Resultados de selecoes diferentes nao devem ser somados quando ha sobreposicao.
O resultado da suite completa depende de sua propria execucao concluida.

## Residuos A-E apos c30f87da

Os 2938 passed e 9 skipped da rodada S1-S8 pertencem ao codigo `0f239dac`, com
documentacao em `c30f87da`. O diff A-E exige resultado proprio, registrado em L4
de AUDIT_FIXES_REPORT.md. Nao somar resultados focados com casos em comum.

A selecao precisa incluir falhas de preparacao e sinais obrigatorios em rescan
e filtro, termino do escritor antes da escrita, entrega de DataFrame malformado,
retorno False da atualizacao visual e excecao de finalizadores. Em cada caso,
verificar estado liberado ou thread viva retida, mensagem correta e tentativa
seguinte concluida. Em D, verificar que a fachada de erro mostra a janela no
startup e preserva contexto/modal/retencao. Ausencia de excecao sozinha nao basta.

Para Qt, executar em subprocesso isolado o caso que possa abortar o processo.
A reproducao com duas colunas `numero_ssa` entregues por QTimer passou de
SIGABRT (-6) para retorno 0/busy=False. Nao instalar excepthook global para
transformar abortos em aprovacoes e nao usar dados/configuracoes de producao.
O teste offscreen confirma esse caminho, sem substituir captura nativa.

Para preferencias, usar a falha controlada de `Condition.wait` e conferir
flush=OSError com snapshot pendente, shutdown vazio valido e recuperacao apos
escrita posterior. O teste extremo nao mede incidencia real. Fsync tolerado
continua um limite da politica, nao um resultado validado de durabilidade.

## Piramide de Testes (Alvo)
- Unidade (rapidos, puros, sem IO pesado) ~60%
- Integracao (SQLite + scripts + normalizacao) ~30%
- End-to-End / Gates (run_quality_gates, smoke CLI/GUI) ~10%

## Classes de Testes Atuais
| Tipo | Exemplos | Observacoes |
|------|----------|-------------|
| Unidade | (a ser expandido) funcoes de normalizacao isoladas | Criar camada unit para `_normalize_numero_ssa_value` etc. |
| Integracao | `test_import_dtypes.py`, `test_db_upsert_integrity.py`, `test_normalization_rules.py` | Usam fixtures de DB temporario e DataFrames sinteticos |
| Governaca / Gates | `test_quality_gates_smoke.py`, `test_quality_gates_fail_paths.py` | Validam o pipeline de qualidade em ambos caminhos |
| Compatibilidade Legacy | `test_import_single_legacy_compat.py` | Substitui testes antigos ruidosos |
| Referencia Legacy (skipped) | `tests/legacy_tests/*` placeholders | Mantidos apenas por historico (skip module-level) |

## Fixtures Principais
- `temp_db`: cria banco SQLite isolado a partir de `config/schema.sql` (ou otimizado quando aplicavel)
- `sample_import_dataframe`: DataFrame sintetico base para casos de import
- `sample_upsert_batches`: Lotes ordenados para exercitar atualizacao condicional (upsert inteligente)
- `normalization_cases`: Casos parametrizados (entrada → saida) para normalizacao de `numero_ssa`

## Politica de Dtypes
Matriz centralizada em `tests/_helpers/dtypes_matrix.py` define:
- `expected_dtype`
- Flags (ex.: `required`, `normalized`)
Testes devem importar a matriz, nunca reescrever os tipos manualmente.

## Quality Gates
Scripts agregados por `run_quality_gates.py`:
- `validate_configs.py` (estrutura & semantica leve)
- `smoke_cli.py` (entrada CLI basica, marker `SSA_SMOKE_TEST`)
- `check_docs.py` (densidade minima + placeholders)

O agregador oferece JSON com `summary.overall_status` e lista de `gates`. Argumentos adicionais suportados:
```
uv run --no-sync python scripts/run_quality_gates.py --only smoke_cli
uv run --no-sync python scripts/run_quality_gates.py --extra-doc docs/README.md
uv run --no-sync python scripts/run_quality_gates.py --skip check_docs
```

## CI GitHub, GitLab e release Windows

Configuracao da rodada de 13/09/2026, posterior a `b9672334`:

- GitHub `minimal-ci`: push em main/dev, PR para main/dev e disparo manual.
  Os cinco grupos verificam autoria e selecionam validacoes conforme o diff.
  Um job impedido de iniciar por faturamento nao executou os testes.
- GitLab: MR, branch padrao, disparo web e push em `fix/`. Havendo MR aberto,
  o push da feature nao duplica sua pipeline de MR. Autoria, gates, suite
  completa e scanner de segredos sao bloqueantes. `pytest-full` deixou de
  ser manual/opcional; o limite do job e 40 minutos, com 45s por teste.
  A primeira execucao completa durou 29min43s; o limite anterior de 30min
  deixava apenas 17s de margem para variacoes do runner.
  O setup instala Git para os contratos de inventario e hooks do repositorio.
- Gates: `ci_quality_gates.sh` aceita `GATES_ARGS` com aspas, sem `eval`.
  Argumentos vazios e nomes com LF sao preservados no Bash 3.2 e 5.3.
  O parser usa NUL em temporario removido antes dos gates. Aspas invalidas encerram com
  codigo 2 antes dos gates/smoke; falha funcional encerra com codigo 1.
  O stdout/stderr capturado e exibido no log. O ultimo registro JSON continua
  em `quality_gates_output.jsonl`; no GitLab, e preservado mesmo em falha.
- Pytest no GitLab: modo full exibe cada nome e resultado; `--durations=20`
  registra os testes mais lentos. JUnit em `pytest-results.xml`, preservado em sucesso/falha
  por 14 dias. O arquivo so existe se pytest alcancar sua geracao; timeout do
  processo ou falha de setup nao equivalem a teste aprovado.
- Runner local: `run_tests.sh` valida aspas com shlex e deixa pytest consumir
  `PYTEST_ADDOPTS` pelo ambiente uma vez. Variavel vazia funciona no Bash 3.2;
  tokens vazios e LF sao preservados. Sintaxe invalida encerra com retorno 2.
  A precedencia e a nativa do pytest: opcoes explicitas do modo escolhido
  prevalecem sobre as do ambiente. Nao existe expansao via eval.
- Windows: a coleta de logs de falha vem depois da verificacao e do envio dos
  artefatos. Assim, uma falha na verificacao final tambem pode preservar os
  logs ja produzidos. YAML/PowerShell validos nao comprovam build executado.

Comandos locais de diagnostico (ambiente ja sincronizado):

```sh
actionlint
yamllint -d relaxed .github/workflows .gitlab-ci.yml
shellcheck scripts/ci_quality_gates.sh
PYTHON="$PWD/.venv/bin/python" QT_QPA_PLATFORM=offscreen bash scripts/ci_quality_gates.sh
QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest tests/test_shell_ci_contracts.py tests/test_quality_gates_fail_paths.py -q
uv run --no-sync python scripts/validate_git_authorship.py range origin/dev HEAD
```

Preserve o caminho `.venv/bin/python`; resolver o symlink ate o interpretador
base remove o contexto do ambiente e pode causar dependencias ausentes.
Conferir SHA, estado dos jobs e anexos antes de declarar aprovacao. O verificador
usa o HEAD real do PR/MR e o intervalo do evento; um push incremental aprovado
nao garante que o intervalo completo de uma PR esteja aprovado.

Referencia da simulacao de pipeline:
[CI Lint API](https://docs.gitlab.com/api/lint/).
Resultados desta rodada e limites do servidor estao na secao M do relatorio.

## Markers Pytest

Definidos em `pyproject.toml` (`tool.pytest.ini_options.markers`):

- `performance`
- `integration`
- `legacy`
- `slow`
- `smoke`
- `stress`

Uso rapido:
```
uv run --no-sync python -m pytest -m "integration and not slow" -q
uv run --no-sync python -m pytest -m smoke -q
```

## Limiar Progressivo de Qualidade (Roadmap)

Metas de evolucao; esta tabela nao comprova que uma regra esta ativa no CI ou
que a cobertura atual atingiu o percentual. Conferir a configuracao publicada
e o resultado da execucao antes de declarar um bloqueio efetivo.

| Fase | Criterios | Acao de Bloqueio |
|------|-----------|------------------|
| Fase 1 | >=5 testes core integracao (OK) + gates smoke passando | CI falha se <5 |
| Fase 2 | Cobertura >=30% modulos criticos (`armazenamento/`, `core/`) | CI marca warning se <30% |
| Fase 3 | Cobertura >=60%, + testes unit para normalizacao e cache | CI falha se <60% |
| Fase 4 | Cobertura >=80%, lint estrito (sem noqa novo) | PR bloqueado |

(Percentuais atuais ainda em medicao – primeira coleta manual via `pytest --cov`.)

## Proximos Incrementos Planejados
1. Adicionar testes unit para funcoes de normalizacao (sem criar DB).
2. Cobrir caminhos de erro de `insert_dataframe_with_smart_upsert` (linhas de regressao futuras).
3. Teste de idempotencia de `verify_database_integrity` em base consistente.
4. Cobrir `config_manager` leitura com mock de diretorio alternativo (`SSA_CONFIG_DIR`).
5. Integrar relatorio de cobertura ao pipeline CI (HTML opcional em artefatos).

## Convencoes
- Evitar `print` em testes novos (usar asserts). Legacy placeholders podem conter prints, mas estao skipped.
- Nunca depender de arquivos reais grandes em `docs_entrada/` para caminhos core.
- Em falhas de subprocessos, sempre exibir stdout/stderr no assert para diagnostico.

## Execucao Rapida
```
# Smoke + integracao basica (exclui legacy/slow)
uv run --no-sync python -m pytest -m "integration and not slow and not legacy" -q

# Gates (caminho feliz + falhas controladas)
uv run --no-sync python -m pytest -k quality_gates -q

# Cobertura inicial
uv run --no-sync python -m pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Politica de Migracao Legacy
Criterios (ja aplicados): fluxo suportado, assert nao redundante, sem dependencia obsoleta, tempo <2s. Testes fora dos criterios: convertidos em placeholder com `pytest.skip` no import modulo.

## Falhas Esperadas / Negative Paths
Documentados em `test_quality_gates_fail_paths.py` – nao remover sem adicionar substituto equivalentes de governanca.

---
Atualize este documento ao:
- Introduzir novo marcador ou fixture
- Elevar fase de cobertura
- Deprecar scripts de gate ou alterar saida JSON

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

