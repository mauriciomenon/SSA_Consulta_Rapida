# Dev Module Status (v3.11)

The repository now tracks a set of "_dev" modules that keep legacy or experimental
versions of core components so development can continue on multiple machines.
This document summarizes how each dev file relates to the production code that
ships with v3.11 and how you can resume work from another workstation.

| Dev file | Source snapshot (header) | Production counterpart | Notes / Recommended usage |
| --- | --- | --- | --- |
| `core/app_logic_dev.py` | `core/app_logic.py 20250725 103000 (v3.1 - Refatorado, Exceções, Logging)` | `core/app_logic.py` | Full snapshot of the pre-v3.11 CLI/GUI orchestration layer (≈1.8k LOC). Not referenced anywhere. Useful if you need to port behaviours that were removed/refactored in `core/app_logic.py`. Compare with `git diff core/app_logic_dev.py core/app_logic.py` before merging changes. |
| `core/config_manager_dev.py` | `core/config_manager.py 20250725 163000 (v2.1 - Melhorias de Erro, Logging)` | `core/config_manager.py` | Legacy configuration loader with simpler validation rules. Keeps the old default display mapping inline. Treat it as a reference when adjusting validation or backporting behaviour. |
| `extracao/extractor_dev.py` | `extracao/extractor.py 20250725 101500 (v6.4 - Melhorias de Tipo, Sanitizacao, Logging)` | `extracao/extractor.py` | Older extractor that predates the latest sanitisation work. Handy for A/B testing column-mapping changes. Remember it still imports the live `core.config_manager`. |
| `gui/gui_ssa_dev.py` | Minimal dev-only GUI stub (header comment) | `gui/gui_ssa.py` | Stand‑alone PyQt6 window to call the Itaipu API without touching the main GUI. No production imports refer to it; run with `python -m gui.gui_ssa_dev`. |

## General guidance

* None of the dev modules are imported by the shipping code path (search `rg app_logic_dev` etc.
  returns no hits). They are safe to modify without affecting runtime until you deliberately wire
  them in.
* To resume the dev work on another machine, pull the latest `main` and work directly in the
  `_dev` modules. When you are ready to merge a change back into production, diff the corresponding
  files and port the relevant sections.
* Keep the headers (timestamp/version) up to date if you take another snapshot—this makes it easier
  to see which release a dev file corresponds to.
* If you produce additional helper modules, list them here so the status stays current.

Happy hacking! If you need to promote one of these modules to production, the quickest workflow is:

```bash
# work in the dev file
vim core/app_logic_dev.py
# compare against production counterpart
git diff core/app_logic.py core/app_logic_dev.py
# merge the desired changes manually and run the relevant tests
```
