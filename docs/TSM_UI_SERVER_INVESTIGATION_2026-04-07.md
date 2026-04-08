# TSM UI Server Investigation - 2026-04-07

Status: local only

Objetivo
- Investigar os warnings `TSMSendMessageToUIServer: CFMessagePortSendRequest FAILED(-1)` vistos ao executar a GUI no macOS.
- Separar ruido de infraestrutura de um possivel problema real de foco/input na GUI.

Escopo
- Diagnostico e instrumentacao minima.
- Nenhuma correcao funcional definitiva aplicada neste ciclo.
- Nenhum commit ou push nesta rodada.

Sintoma observado
- Ao executar `uv run main.py --gui`, surgem bursts de:

```text
TSMSendMessageToUIServer: CFMessagePortSendRequest FAILED(-1) to send to port com.apple.tsm.uiserver
```

- O warning aparece em grupos de 6 linhas e pode voltar em momentos diferentes da sessao.

Logs paralelos vistos na mesma sessao
- `Banco de dados nao encontrado`
- warnings de importacao/extracao como:
  - `.xls legado(s) ignorado(s)`
  - `registros invalidos sem identidade`
  - `duplicidade exata no export`

Leitura inicial descartada
- O warning nao deve ser tratado automaticamente como "culpa do macOS" sem reproducao.
- O historico do projeto indica que a GUI ja rodou muitas vezes sem esse ruido.

Hipotese de trabalho
- O warning esta mais ligado a eventos de foco/input method da GUI real do que ao importer ou ao banco.

Codigo relevante
- Busca principal:
  - `gui/gui_ssa.py` `search_input`
- Troca de abas:
  - `gui/gui_ssa.py` `_on_tab_changed`
- Filtros avancados:
  - `gui/ssa/gui_filters_advanced_ui.py` `adv_week_emissao_start`
  - `gui/ssa/gui_filters_advanced_ui.py` `adv_week_execucao_start`
- Dialogos exercitados:
  - `gui/widgets/column_filter_dialog.py`
  - `gui/ssa/gui_theme.py`

Verificacao de fluxo principal
- Leitura de `main.py` mostrou que `main.py --gui` sozinho nao deveria acionar o pipeline principal de importacao.
- Conclusao:
  - logs de `core.app_logic` vistos junto com `TSMSend...` indicam outra acao adicional na sessao, nao apenas startup puro da GUI.

Testes executados fora do repo
- Harnesses temporarias criadas em `/tmp`:
  - `/tmp/ssa_tsm_probe_suite.py`
  - `/tmp/ssa_tsm_probe_quick.py`
  - `/tmp/ssa_tsm_debug_probe.py`
  - `/tmp/ssa_tsm_debug_probe_dialogs.py`
  - `/tmp/ssa_tsm_theme_probe.py`

Casos que NAO reproduziram de forma isolada
- `QWidget` puro
- `QLineEdit` puro com foco
- `QDialog` simples com `QLineEdit`
- `QMessageBox.warning()` simples
- `SSAMainWindow` abrindo e fechando sem interacao
- `search_input` sozinho
- troca de aba isolada
- foco isolado em `adv_week_emissao_start`
- `ColumnFilterDialog` isolado
- dialogo de tema isolado

Achado forte anterior
- Uma sequencia combinada da GUI real reproduziu o warning uma vez:
  1. foco em `search_input`
  2. troca para aba `Filtros`
  3. foco em `adv_week_emissao_start`
  4. mais mudancas de foco na mesma janela

Instrumentacao minima aplicada temporariamente no base
- Guardada por `SSA_TSM_DEBUG=1`
- Logs adicionados para:
  - `focus_in`
  - `focus_out`
  - `input_method`
  - `input_method_query`
  - `show`
  - `hide`
  - `tab_changed`
  - abertura do dialogo de filtro por coluna
  - abertura do dialogo de tema

Validacao tecnica do patch de instrumentacao
- `py_compile` em `gui/gui_ssa.py`: OK
- `ruff check gui/gui_ssa.py`: OK
- `ty check gui/gui_ssa.py`: OK
- `pytest -q tests/smoke_test_gui.py tests/test_main_gui_fallback.py`: `5 passed`

Resultado do kluster no patch de instrumentacao
- 1 finding
- severidade: HIGH
- conteudo: `SSAMainWindow` e uma God Class
- classificacao:
  - debt estrutural antiga
  - fora do escopo do slice de instrumentacao
- nenhum finding novo do slice foi reportado

Probes com `SSA_TSM_DEBUG=1`
- Startup real com:

```bash
SSA_TSM_DEBUG=1 QT_QPA_PLATFORM=offscreen uv run --python 3.13 python main.py --gui
```

- Resultado:
  - startup sem traceback
  - logs `TSM_DEBUG` iniciais de `show`
  - sem reproducao do `TSMSend...` em `offscreen`

Sequencia automatizada mais util
- Probe repetido 5x:
  1. foco em `tab0.search_input`
  2. digitacao
  3. troca para aba `filters`
  4. foco em `tab1.adv_week_emissao_start`
  5. digitacao
  6. foco em `tab1.quick_setor_executor_combo`

Padrao de log observado repetidamente
- `focus_in` em `tab0.search_input`
- varios `input_method_query` em `tab0.search_input`
- `tab_changed index=1 kind=filters`
- `focus_in` em `tab1.adv_week_emissao_start`
- varios `input_method_query` em `tab1.adv_week_emissao_start`
- `focus_in` e `focus_out` no combo rapido depois

Dialogos exercitados com instrumentacao
- Filtro por coluna:
  - logou `open_column_filter_dialog`
- Tema:
  - logou `open_theme_dialog`

Interpretacao tecnica atual
- Nao ha evidencia suficiente para culpar:
  - importer
  - banco
  - `QComboBox`
  - dialogo de tema
  - dialogo de filtro por coluna

- Os suspeitos principais agora sao os `QLineEdit` na cadeia de foco:
  - busca principal
  - campo avancado de semana na aba de filtros

Conclusao atual
- O warning parece ligado a:
  - foco/input method
  - troca entre abas
  - transicao de foco entre `QLineEdit` da busca e `QLineEdit` dos filtros avancados

- O problema segue:
  - real
  - intermitente
  - nao deterministico em `offscreen`

O que ainda NAO esta provado
- Qual widget exato dispara o primeiro envio que falha no macOS real
- Se o problema depende de:
  - IME/input source do sistema
  - estado de foco anterior
  - timing especifico da troca de abas
  - sessao grafica real vs `offscreen`

Proximo passo recomendado
- Rodar a GUI no ambiente real com:

```bash
SSA_TSM_DEBUG=1 uv run main.py --gui
```

- Quando o `TSMSend...` aparecer:
  - capturar as ultimas linhas `[TSM_DEBUG]` imediatamente anteriores
  - verificar se o padrao bate com:
    1. `tab0.search_input`
    2. `tab_changed ... filters`
    3. `tab1.adv_week_emissao_start`

Se isso se confirmar de novo
- o proximo slice deve focar apenas em:
  - lifecycle de foco dos `QLineEdit`
  - diferir ou reduzir transicoes de foco entre abas
  - evitar tocar importer, banco ou layout
