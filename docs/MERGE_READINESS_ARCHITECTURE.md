# Merge Readiness Architecture

## Current Truth 2026-05-20 23h14

- Branch alvo: `dev`.
- Baseline usado para este DOC_SYNC:
  - `2b8746564f64a11bf93fc70f030239260ec53059 2026-05-20 22:46:32 -0300 DOC_SYNC: update merge readiness handoff`.
- Este documento e documentacao apenas; confirmar o head operacional real com `git log -1`.
- Este documento e um mapa de revisao para PR/merge; nao substitui o estado real do PR/checks.

## Function Map

```mermaid
flowchart TD
    CLI["CLI / main.py"] --> AppLogic["core.app_logic"]
    AppLogic --> ImportSingle["core.import_single_file"]
    AppLogic --> ImportReport["core.import_run_report"]
    ImportSingle --> Extractor["extracao.extractor"]
    ImportSingle --> Validator["armazenamento.database_validation"]
    ImportSingle --> Upsert["armazenamento.database_upsert_logic"]
    Upsert --> DB["SQLite ssas.db"]
    AppLogic --> Derivadas["core derivadas sync"]

    GUI["gui.gui_ssa.SSAMainWindow"] --> GUIControllers["gui/ssa controllers"]
    GUIControllers --> Filters["filter controllers / mixins"]
    GUIControllers --> Details["details presenter/provider/model"]
    GUIControllers --> Workers["gui/workers"]
    Workers --> PaiWorker["gui/workers/pai_api_worker.py"]
    PaiWorker --> PaiScript["scripts/import_pai_api_xlsx.py"]
    PaiScript --> PaiNormalizer["core.pai_xlsx_normalizer"]
    PaiScript --> ImportSingle
    Filters --> CoreSearch["core.search_filter"]
    Details --> Derivadas
```

## Functionality Map

```mermaid
flowchart LR
    User["Usuario"] --> GUI["GUI PyQt6"]
    User --> CLI["CLI"]

    subgraph Importacao["Importacao XLS/XLSX"]
        LocalXLS["Arquivo local"] --> Extract["extracao.extractor"]
        Extract --> Validate["validacao"]
        Validate --> WriteDB["upsert DB"]
    end

    subgraph API["API PAI"]
        SectorConfig["setores priorizados"] --> Fetch["scrap_report sam-api-flow"]
        Fetch --> NormalizeXLSX["normalizar XLSX"]
        NormalizeXLSX --> Preview["preview / confirmacao"]
        Preview --> WriteDB
    end

    subgraph DBLayer["Banco de dados"]
        WriteDB --> Integrity["integridade"]
        Integrity --> Cache["cache"]
        Cache --> Query["consulta tabela"]
    end

    subgraph Filtragem["Filtragem e busca"]
        Query --> GeneralSearch["busca geral"]
        Query --> ColumnFilters["filtros por coluna"]
        Query --> AdvancedFilters["filtros avancados"]
        GeneralSearch --> Undo["undo"]
        ColumnFilters --> Undo
        AdvancedFilters --> Undo
    end

    subgraph GUIFlow["Exibicao GUI"]
        Filtragem --> Table["tabela"]
        Table --> DetailsPanel["detalhes SSA"]
        DetailsPanel --> Graph["derivadas grafo/arvore/mermaid"]
    end

    CLI --> Importacao
    GUI --> Importacao
    GUI --> API
    GUI --> GUIFlow
```

## Merge Readiness Gates

- Verde no baseline `2b874656`: `minimal-ci`, `CodeQL`, `Secret Scan`, `Automatic Dependency Submission`; revalidar o head atual apos qualquer novo DOC_SYNC.
- Local verde no slice runtime mais recente: `py_compile`, `ruff`, `ty`, `pytest` focado, `bandit`, `semgrep`, `detect-secrets`, `gitleaks`.
- Ferramentas externas com limitacao:
  - `CodeRabbit` local timeoutou sem findings em duas tentativas.
  - `Clawpatch` corrigiu achados reais aplicaveis, mas a revisao completa ainda teve timeout/provider.
  - `Qwen` headless foi validado com `glm-5-turbo`; modelos `qwen3.x` e `glm-5` ainda dependem de estabilidade do plano/modelo.

## Known Residuals

- `gui/mixins/filter_gui_ssa_mixin.py` ainda esta acima da meta de tamanho.
- `gui/gui_ssa.py` ainda e god class medio/alto, embora menor que ciclos anteriores.
- `tests/test_gui_filter_logic.py` ainda e arquivo de teste monolitico.
- `DatabaseAnalyzer` ainda mistura estrutura, sanidade de dominio e relatorio Markdown.
- Build/smoke macOS ainda nao foi executado neste ciclo; e bloqueante somente para release de artefato.
