# Histórico detalhado — últimos 50 commits (até 2025-10-03)

## Índice

- [Visão geral rápida](#visão-geral-rápida)
- [Topologia de branches (resumo)](#topologia-de-branches-resumo)
- [Branches, tags e remotes](#branches-tags-e-remotes)
- [Commits detalhados (últimos 50)](#commits-detalhados-últimos-50)
- [Mapeamento do código de temas (theming)](#mapeamento-do-código-de-temas-theming)
  - [utils/themes.py — paletas e normalização](#utilsthemespy--paletas-e-normalização)
  - [gui/gui_ssa.py — apply_theme(name: str)](#guigui_ssapy--apply_themename-str)
- [Decisões equivocadas e correções (aprendizados)](#decisões-equivocadas-e-correções-aprendizados)
- [TODOs e pendências objetivas](#todos-e-pendências-objetivas)
- [Conversa desta sessão — resumo didático](#conversa-desta-sessão--resumo-didático)
- [Apêndice: Comandos Git usados](#apêndice-comandos-git-usados)

Este documento consolida as mudanças realizadas nos últimos 50 commits, a topologia de branches, um mapeamento do código de temas (theming) na GUI, decisões equivocadas corrigidas, pendências (TODOs) e um resumo direto da nossa conversa para dar continuidade fora do ambiente.

## Visão geral rápida

- Janela de tempo: 2025-09-07 → 2025-10-02
- Branch principal: `main`
- Principais marcos durante o período:
  - v4.0.0 (documentação consolidada, logging robusto, otimizações)
  - v3.11 (filtros unificados e Streamlit)
- Áreas mais tocadas: GUI (temas, filtros, limpeza de estabilidade), documentação, automações CI e segurança (hooks/pre-commit), scripts utilitários.

## Topologia de branches (resumo)

```
$ git log --graph --decorate --oneline --all -n 120
* 82b114b (HEAD -> main, origin/main, origin/HEAD) gui usavel - to do melhorar contraste temas
*   13cf29b Merge PR #9: add Claude GitHub Actions workflows (no code changes)
|\
| * 84a99de (origin/add-claude-github-actions-1759346193101) "Claude Code Review workflow"
| * 23496df "Claude PR Assistant workflow"
| | *   a17fc7a (refs/stash) On main: pre-merge PR#9 add-claude-github-actions-1759346193101
| |/|\
|/| | |
| | | * 535e045 untracked files on main: 388e5dd fix(gui): enforce central widget bg for dark/gruvbox themes
| | * c9885a7 index on main: 388e5dd fix(gui): enforce central widget bg for dark/gruvbox themes; docs: note .emoji_backups
| |/  
|/|
* | 388e5dd fix(gui): enforce central widget bg for dark/gruvbox themes; docs: note .emoji_backups
|/
* 94fbeb4 chore(docs): remove emojis from docs; tools: add remove_emojis script; fix(logging): export setup_logging alias
* 90d6c06 docs: Atualização completa documentação para v4.0.0
* 8a7c8d9 (tag: v4.0.0) feat: Sistema de Logging Robusto + Otimizações Performance Completas
* 47807a2 melhorias
* 913f03a refatoracao em andamento ponto de mudanca
* f1412db Enhance GUI theme styling and filter controls
* 74c9c55 minimal
* 7a3c13f Adiciona análise de performance do Qwen3CLI
* e9d62c0 minimal
* 03e080a docs: add activation helpers usage for macOS/WSL and PowerShell
* 26533b5 chore(env): normalize .envrc line endings; add cross-platform activation helpers (activate_repo.sh, activate_repo.ps1) and .gitattributes
*   b44131f Merge branch 'main' of https://github.com/mauriciomenon/SSA_Consulta_Rapida
|\
| * 79b0972 docs: add dev module status
| * f61d396 chore: add dev helper modules
| * 94696b6 (tag: v3.11) release: v3.11 unified filters and streamlit
* | 00e1ec7 docs: remove tests summary report to keep max 5 new reports in this session
|/
* 7b2ace3 chore(dev): add _dev/_old copies for robust_importer; add Itaipu dev GUI and Streamlit app; docs reports; keep main importer at HEAD stable
* bfdd4df feat: update CLI pagination and schema configs
* 88fcc57 placeholders pass
* aae403f hook test
* 60b05e3 chore(security): add secret scan pre-commit hook with marker
* a757b24 docs: add session context snapshot 2025-09-15
* db219d5 chore(security): add hooks installer, gitleaks config & session log
* cdbde82 chore: stage refactors & security prep before history rewrite
* e138ba2 chore(quality-gates): habilita streaming do gate lint com --lint-stream e remove --quiet padrão
* a75cd44 chore(quality-gates): adiciona gate lint e pre-commit hooks
* 05fbb66 chore(lint): ajustes flake8 em robust_importer + config .flake8 e runner unificado
* 8045459 feat(importer,quality): hardened numero_ssa normalization, complementary merge mode, quality gates, perf & reporting tooling
* fc083ba fix(gui): defensiva em cleanup e instrumentação estabilidade (commit parcial sem hooks)
* b4a48d9 docs: adiciona log completo configuração Copilot com MCPs e OpenRouter - removido emojis
* d70f9a0 docs: adiciona log completo configuração Copilot com MCPs e OpenRouter
* 781b56f docs: Finaliza consolidação e limpeza de documentação
* a210201 docs: Adiciona guia de próximos passos pós-consolidação
* 520d34e docs: Consolidação completa da documentação fragmentada
* 3ce217d Conclusão da Phase 3: Consolidação completa docs_saida
* 6f5fcf8 Fase 3 completa - Limpeza e consolidação massiva
* 7c11ae6 Limpeza de linguagem não profissional e emojis - Fase 2
* 5bd69a0 Limpeza de linguagem não profissional e emojis - Fase 1
* 8d84a9f cleanup: corrigir referencias finais e remover duplicatas
* b94de0f refactor: corrigir referencias e organizar diretorios
* 149747a fix: limpar referencias historicas inadequadas
* 1a86423 organize: continuar limpeza e padronizacao de nomes
* 57ea069 security: proteger configuracoes pessoais e simplificar nomes
* 65b7a05 docs: profissionalizar documentacao e organizar estrutura
* ade3ce8 feat: organizar estrutura, remover arquivos temporarios e implementar limpeza automatica
```

Observações:
- A branch remota auxiliar `origin/add-claude-github-actions-1759346193101` foi criada e mergeada no PR #9 (apenas workflows do GitHub Actions, sem mudanças de código de app).
- Stash apontado no histórico durante o preparo para o merge.

## Branches, tags e remotes

- Branches locais/remotas:
  - `main` (HEAD atual)
  - `origin/main`
  - `origin/add-claude-github-actions-1759346193101`
- Tags (ordem decrescente): `v4.0.0`, `v3.11`, `v3.10`, `pre-ssa-rule`, `v3.0.7`, `v3.0.5`, `v3.0.3`, `v3.0.2`, `v3.0.1`, `v3.0.0`, `v2.4.1`, `v2.4.0`, `v2.2.0`, `v2.1.0`, `v2.0.0`.
- Remote: `origin` (push/fetch configurados no repositório GitHub do projeto).

## Commits detalhados (últimos 50)

Abaixo, cada entrada contém: hash, data, autor, assunto e shortstat (arquivos/linhas alteradas segundo `git --shortstat`).

- 82b114ba8eb18971646fbde9ad51f67bc488a6f2 | 2025-10-02 16:52:48 -0300 | MAURICIO MENON | gui usavel - to do melhorar contraste temas — 4 files changed, 272 insertions(+), 26 deletions(-)
- 13cf29b557ff6d9ca688969b8f2bd220c2b84485 | 2025-10-02 08:17:57 -0300 | MAURICIO MENON | Merge PR #9: add Claude GitHub Actions workflows (no code changes)
- 84a99de71bcb46dac4288cd17c95bc3a2777dcdd | 2025-10-01 16:16:37 -0300 | Maurício Menon | "Claude Code Review workflow" — 1 file changed, 57 insertions(+)
- 23496dfedb9bfb95b7f134caf28992c8f1881680 | 2025-10-01 16:16:35 -0300 | Maurício Menon | "Claude PR Assistant workflow" — 1 file changed, 50 insertions(+)
- 388e5dd9d1f634a548aae452f7c22cd9e10bde7e | 2025-09-29 16:38:14 -0300 | MAURICIO MENON | fix(gui): enforce central widget bg for dark/gruvbox themes; docs: note .emoji_backups — 2 files changed, 14 insertions(+)
- 94fbeb4d1a4b11278d49af3c6764e64e76d389c0 | 2025-09-29 12:58:58 -0300 | MAURICIO MENON | chore(docs): remove emojis from docs; tools: add remove_emojis script; fix(logging): export setup_logging alias — 61 files changed, 7766 insertions(+), 448 deletions(-)
- 90d6c062798dfa231d70f42283efb521dbae5f0f | 2025-09-26 16:48:19 -0300 | MAURICIO MENON | docs: Atualização completa documentação para v4.0.0 — 5 files changed, 175 insertions(+), 44 deletions(-)
- 8a7c8d948b41a77c399747778ef01e48daf1d513 | 2025-09-26 16:43:46 -0300 | MAURICIO MENON | feat: Sistema de Logging Robusto + Otimizações Performance Completas — 3 files changed, 29 insertions(+), 5 deletions(-)
- 47807a276f54819a829d7db0848ce2f9cb004139 | 2025-09-26 16:35:41 -0300 | MAURICIO MENON | melhorias — 27 files changed, 3451 insertions(+), 67 deletions(-)
- 913f03ad79c18dd58ad2a45f18bf061cebea4ad2 | 2025-09-26 15:30:00 -0300 | MAURICIO MENON | refatoracao em andamento ponto de mudanca — 2 files changed, 328 insertions(+), 30 deletions(-)
- f1412dbc6be82f7c2af2cf85e2d009c81994e399 | 2025-09-25 16:59:11 -0300 | MAURICIO MENON | Enhance GUI theme styling and filter controls — 1 file changed, 243 insertions(+), 44 deletions(-)
- 74c9c557ad8c0f5ac5b6c6cbdebd3057c0b0fc1b | 2025-09-25 14:06:49 -0300 | MAURICIO MENON | minimal — 11 files changed, 336 insertions(+), 7 deletions(-)
- 7a3c13f26fab79d12b56e7ddc7e2c16fe5320ac7 | 2025-09-25 10:24:56 -0300 | Maurício Menon | Adiciona análise de performance do Qwen3CLI — 1 file changed, 54 insertions(+)
- e9d62c088912f27bdd75537ef70c95e08e8a0030 | 2025-09-23 17:09:23 -0300 | MAURICIO MENON | minimal — 8 files changed, 256 insertions(+), 220 deletions(-)
- 03e080a8fbfbdbd4b2bd48f313e185eaa546004a | 2025-09-22 08:58:38 -0300 | MAURICIO MENON | docs: add activation helpers usage for macOS/WSL and PowerShell — 1 file changed, 56 insertions(+), 37 deletions(-)
- 26533b5089cd95b1c2680d41cdfd947b53403b23 | 2025-09-22 08:51:11 -0300 | MAURICIO MENON | chore(env): normalize .envrc line endings; add cross-platform activation helpers (activate_repo.sh, activate_repo.ps1) and .gitattributes — 4 files changed, 90 insertions(+)
- b44131f00ae1c080846bba823587a1b5008581d7 | 2025-09-22 07:56:45 -0300 | MAURICIO MENON | Merge branch 'main' of https://github.com/mauriciomenon/SSA_Consulta_Rapida
- 79b0972791f1091be79b24efd49dd65170fe4dde | 2025-09-22 06:05:34 -0300 | Maurício Menon | docs: add dev module status — 1 file changed, 35 insertions(+)
- f61d3968ff43d8b0ffd7099fe72cb897b09f56c7 | 2025-09-22 06:03:30 -0300 | Maurício Menon | chore: add dev helper modules — 4 files changed, 1890 insertions(+)
- 94696b6fa4ba1e4bc2b97960431ef43850941c12 | 2025-09-22 05:59:59 -0300 | Maurício Menon | release: v3.11 unified filters and streamlit — 12 files changed, 2788 insertions(+), 619 deletions(-)
- 00e1ec700260cd69690c9161aa895f664bf3002f | 2025-09-19 17:36:14 -0300 | MAURICIO MENON | docs: remove tests summary report to keep max 5 new reports in this session — 1 file changed, 9 deletions(-)
- 7b2ace38978db46c705fa2de42790560c2bb3c23 | 2025-09-19 17:35:18 -0300 | MAURICIO MENON | chore(dev): add _dev/_old copies for robust_importer; add Itaipu dev GUI and Streamlit app; docs reports; keep main importer at HEAD stable — 13 files changed, 1537 insertions(+)
- bfdd4df8f8b5ea45d05de9a9a171aad0d9be256c | 2025-09-17 20:24:20 -0300 | Maurício Menon | feat: update CLI pagination and schema configs — 17 files changed, 1022 insertions(+), 320 deletions(-)
- 88fcc57fd834e414fb27dcc884319ec92294c85a | 2025-09-16 11:45:43 -0300 | Maurício Menon | placeholders pass — 2 files changed, 81 insertions(+)
- aae403f337bb5c2a85049246bb9307a13e5d81eb | 2025-09-16 10:30:01 -0300 | Maurício Menon | hook test
- 60b05e3060dc00f86dd9446141a8b6fb654f2965 | 2025-09-16 10:15:52 -0300 | Maurício Menon | chore(security): add secret scan pre-commit hook with marker — 1 file changed, 1 insertion(+)
- a757b240e9d867fcd1e955f6a1102b07f2f1a012 | 2025-09-15 23:52:23 -0300 | Maurício Menon | docs: add session context snapshot 2025-09-15 — 1 file changed, 75 insertions(+)
- db219d5c451bca4666c63cb309fac0ec94d545fa | 2025-09-15 23:51:13 -0300 | Maurício Menon | chore(security): add hooks installer, gitleaks config & session log — 8 files changed, 371 insertions(+)
- cdbde826583db6b4d9ecc0c42050d5f03bb1cab1 | 2025-09-15 23:30:53 -0300 | Maurício Menon | chore: stage refactors & security prep before history rewrite — 161 files changed, 21376 insertions(+), 19832 deletions(-)
- e138ba285e73d1daa0435783e1ba5c95f6430e1d | 2025-09-14 23:12:10 -0300 | Maurício Menon | chore(quality-gates): habilita streaming do gate lint com --lint-stream e remove --quiet padrão — 1 file changed, 34 insertions(+), 2 deletions(-)
- a75cd44c4d71eb3578021bb3b26159b22b1e58d8 | 2025-09-14 23:03:40 -0300 | Maurício Menon | chore(quality-gates): adiciona gate lint e pre-commit hooks — 3 files changed, 28 insertions(+), 3 deletions(-)
- 05fbb666de0544f948a41496e06d735e1f6cbc93 | 2025-09-14 22:34:42 -0300 | Maurício Menon | chore(lint): ajustes flake8 em robust_importer + config .flake8 e runner unificado — 3 files changed, 137 insertions(+), 23 deletions(-)
- 8045459f8e2437dda26e20625e1471f7129ad9b5 | 2025-09-14 21:54:47 -0300 | Maurício Menon | feat(importer,quality): hardened numero_ssa normalization, complementary merge mode, quality gates, perf & reporting tooling — 169 files changed, 10251 insertions(+), 3013 deletions(-)
- fc083baefebbeaefe7b0743d8140eba600994f43 | 2025-09-13 07:40:45 -0300 | Maurício Menon | fix(gui): defensiva em cleanup e instrumentação estabilidade (commit parcial sem hooks) — 1 file changed, 77 insertions(+), 4 deletions(-)
- b4a48d9781e8f4c5a424c5d690c7d8e554dbb70c | 2025-09-07 23:44:45 -0300 | Maurício Menon | docs: adiciona log completo configuração Copilot com MCPs e OpenRouter - removido emojis — 1 file changed, 8 insertions(+), 8 deletions(-)
- d70f9a0a1de7b639c1187e8fb4843a63a9330813 | 2025-09-07 23:44:31 -0300 | Maurício Menon | docs: adiciona log completo configuração Copilot com MCPs e OpenRouter — 1 file changed, 184 insertions(+)
- 781b56f4a3c196c21cb3358e07b459511df4d3e9 | 2025-09-07 18:15:55 -0300 | Maurício Menon | docs: Finaliza consolidação e limpeza de documentação — 7 files changed, 893 deletions(-)
- a2102010a8f5c72848ac9b25e15f164216fb35e2 | 2025-09-07 17:18:10 -0300 | Maurício Menon | docs: Adiciona guia de próximos passos pós-consolidação — 1 file changed, 167 insertions(+)
- 520d34e219043fdc32e5d7a371cbad41a95df902 | 2025-09-07 17:12:10 -0300 | Maurício Menon | docs: Consolidação completa da documentação fragmentada — 39 files changed, 1754 insertions(+), 3987 deletions(-)
- 3ce217d3e8e823370b00a282511321e86cdee368 | 2025-09-07 15:24:06 -0300 | Maurício Menon | Conclusão da Phase 3: Consolidação completa docs_saida — 29 files changed, 3597 insertions(+), 1859 deletions(-)
- 6f5fcf8131c59315752168fa19b2ae382503bd12 | 2025-09-07 15:04:36 -0300 | Maurício Menon | Fase 3 completa - Limpeza e consolidação massiva — 65 files changed, 1828 insertions(+), 3852 deletions(-)
- 7c11ae69347c950803f2d52d7f2a82bf6d2fca23 | 2025-09-07 14:12:39 -0300 | Maurício Menon | Limpeza de linguagem não profissional e emojis - Fase 2 — 9 files changed, 85 insertions(+), 73 deletions(-)
- 5bd69a062c821c368a3c85f8aad905a642550998 | 2025-09-07 13:14:07 -0300 | Maurício Menon | Limpeza de linguagem não profissional e emojis - Fase 1 — 11 files changed, 775 insertions(+), 58 deletions(-)
- 8d84a9f6112bc87a713f5133de0a6236b14ad20e | 2025-09-07 13:05:13 -0300 | Maurício Menon | cleanup: corrigir referencias finais e remover duplicatas — 3 files changed, 2 insertions(+), 160 deletions(-)
- b94de0f9833762ed36a55fb7b0a516956656c52d | 2025-09-07 13:04:15 -0300 | Maurício Menon | refactor: corrigir referencias e organizar diretorios — 36 files changed, 987 insertions(+), 12690 deletions(-)
- 149747a4b9526062925722c16dd5c2c9b86dfdbc | 2025-09-07 12:57:31 -0300 | Maurício Menon | fix: limpar referencias historicas inadequadas — 1 file changed, 4 insertions(+), 4 deletions(-)
- 1a864235a3889d7c7909cccb4241a1545826db20 | 2025-09-07 12:55:19 -0300 | Maurício Menon | organize: continuar limpeza e padronizacao de nomes — 16 files changed, 320 insertions(+), 985 deletions(-)
- 57ea069cd5f0dc8943d84c165c21105a86a20d71 | 2025-09-07 12:46:46 -0300 | Maurício Menon | security: proteger configuracoes pessoais e simplificar nomes — 33 files changed, 162 insertions(+), 3845 deletions(-)
- 65b7a05dff365daffedb93b2a7050befc490b7a8 | 2025-09-07 12:34:07 -0300 | Maurício Menon | docs: profissionalizar documentacao e organizar estrutura — 45 files changed, 16828 insertions(+), 453 deletions(-)
- ade3ce8e8094cf4970263fb50ccf16fc046e2b74 | 2025-09-07 01:32:27 -0300 | Maurício Menon | feat: organizar estrutura, remover arquivos temporarios e implementar limpeza automatica — 38 files changed, 628 insertions(+), 498559 deletions(-)

## Mapeamento do código de temas (theming)

Arquivos-chave:
- `utils/themes.py`: define paletas para temas conhecidos e função `normalize_theme(name: str) -> str`.
- `gui/gui_ssa.py` (método `apply_theme`): aplica paleta no `QApplication` e injeta QSS para consistência de menus/tooltips/listviews.

### utils/themes.py — paletas e normalização

- Funções:
  - `get_palette(name: str) -> QPalette`
    - Retorna um `QPalette` com cores específicas por tema. Temas suportados: `grayscale` (light), `windows7`, `kde`, `gnome`, `gruvbox`, `one-dark`, `dracula`, `solarized-dark`, `solarized-light`, `tokyo-night`, `catppuccin`.
    - Fallback: tema `dark` padrão.
  - `normalize_theme(name: str) -> str`
    - Mapeia aliases para o nome canônico (ex.: "windows 7" → `windows7`, "one dark" → `one-dark`, etc.).

- Observações de design:
  - Paletas definem cores para `Window`, `Base`, `AlternateBase`, `Text`, `WindowText`, `Button`, `ButtonText`, `ToolTipBase`, `ToolTipText`, `Highlight`, `HighlightedText`, `Link`, `LinkVisited`.
  - Alguns temas são escuros (gruvbox, one-dark, dracula, solarized-dark, tokyo-night, catppuccin); `grayscale`, `windows7`, `gnome`, `solarized-light` são claros.

### gui/gui_ssa.py — apply_theme(name: str)

- Passos principais:
  - Normaliza o nome via `normalize_theme(name)`.
  - Obtém `QApplication.instance()` e constrói a paleta (via `get_palette` ou paleta padrão do estilo para grayscale quando disponível).
  - Em Windows, força estilo `Fusion` para temas customizados (não-sistema) quando disponível, visando consistência.
  - Aplica a paleta ao app inteiro (`app.setPalette(pal)`).
  - Injeta um bloco QSS com cores derivadas da paleta para padronizar visual de `QMenu`, separadores, itens selecionados, `QToolTip` e `QComboBox QAbstractItemView`.
  - Ajusta a paleta da janela corrente (`self.setPalette(pal)`).
  - Para temas escuros, força o background do `centralWidget` a acompanhar a cor de `Window` da paleta para evitar caixas brancas.
  - Ajusta header (`QHeaderView::section{font-weight: normal;}`).
  - Usa dinamicamente cores da paleta para estilizar a linha de "Pesquisa Geral" (label, placeholder, focus) respeitando Link/Visited/Highlight/WindowText.

- Anotações:
  - Não há alteração de larguras de coluna neste método; ele é focado em paleta/estilo/QSS.
  - A lista de temas exibida no menu inclui: Escala de cinza, Escuro, Gruvbox, One Dark Pro, Dracula, Solarized Dark/Light, Tokyo Night, Catppuccin, Windows 7, KDE, GNOME.

## Decisões equivocadas e correções (aprendizados)

- Escopo de UI além do solicitado em momento anterior:
  - Houve tentativas de ajustes em larguras de coluna/estilos fora do escopo; foram interrompidas e revertidas na abordagem atual. Diretriz vigente: não mexer em larguras de colunas e não mexer em temas/paletas exceto documentação e correções mínimas.
- Filtros por coluna — semântica de OU:
  - Sintaxe implícita ou cross-coluna chegou a ser cogitada; definição final: OU apenas dentro da mesma coluna, vírgula como armazenamento interno, interface insere e exibe " OU " (botão [+ OU]) apenas no campo daquela coluna.
- Global search — literais preservados:
  - Garantido que "svp" é literal; nenhuma inferência de `v` como operador.
- Threads (QThread) — warning de destruição:
  - Endereçado com limpeza robusta: finished→deleteLater, quit()+wait(), desconexão de sinais e limpeza de referências; pendente validar comportamento em loops de abrir/fechar na máquina do usuário.

## TODOs e pendências objetivas

- Validar empiricamente a ausência do warning "QThread: Destroyed while thread ... is still running" após ciclos de abrir/fechar GUI.
- Opcional: tooltip discreto para o botão [+ OU] (“Insere OU entre alternativas desta coluna”).
- Não alterar tamanhos de colunas nem temas/paletas (congelados por diretriz) — somente correções estritamente necessárias.
- Monitorar contraste em temas escuros (há nota de "to do melhorar contraste temas").

## Conversa desta sessão — resumo didático

- Objetivos firmados:
  - Não mexer em tamanhos de colunas; não mexer em temas/paletas além de manter o que já existe.
  - OU apenas dentro do filtro de uma mesma coluna; botão [+ OU] insere “ OU ” no cursor; ao aplicar, converte para vírgula apenas internamente naquela coluna.
  - Mostrar “OU” visualmente nas entradas, mantendo armazenamento por vírgula.
  - "svp" deve ser literal na busca geral; nada de OR implícito.
  - Manter linhas iniciais de filtros e “Remover linha” apenas oculta a linha.
  - Fortalecer limpeza de QThread para evitar warnings de destruição.
- Estado final reportado:
  - Entradas de filtro por coluna exibem “OU” e o botão [+ OU] está disponível; aplicação converte para vírgula internamente.
  - Testes de filtro da GUI passando no ambiente local.
  - Limpeza de threads reforçada; resta validar em uso contínuo.

---

Se algo aqui divergir do que você quer ver neste relatório, me diga exatamente o que ajustar (ex.: granularidade por arquivo/commit, mais métricas, incluir diffs selecionados, etc.).

## Apêndice: Comandos Git usados

Comandos executados para gerar este relatório:

```bash
git --no-pager log -n 50 --date=iso --pretty=format:"%H|%ad|%an|%s" --stat
git --no-pager log -n 50 --date=iso --pretty=format:"---%n%H%n%ad%n%an%n%s" --shortstat
git --no-pager log --graph --decorate --oneline --all -n 120
git --no-pager branch -a --verbose --no-abbrev
git --no-pager tag --list --sort=-creatordate
git remote -v
```