# Mapa de Pedidos → Implementações (com commits)

Rastreamento dos pedidos feitos ao longo da conversa e os commits que os implementaram. Quando houve correções/ajustes posteriores (desfeito/refeito), eles também são listados.

Observação: datas e SHAs foram obtidos via `git log` local na branch `main`. Itens aplicados no workspace mas ainda não comitados aparecem como “pendente de commit”.

---

## 1) Formatação unificada (não exibir “.0”, esconder NaN/NaT/None, datas dd/mm/yyyy, semanas inteiras)
- Implementação principal: formatter compartilhado CLI/GUI (utils/formatting) + integração nas camadas de exibição.
- Commits (implementação):
  - 346ae53 (2025-08-14) — feat(formatting): shared formatter; ensure_indexes guards; integrar GUI; add tests.
- Status: concluído e coberto por testes.

## 2) Desempenho da GUI (debounce de filtros)
- Implementação principal: QTimer para aplicar filtros com atraso curto ao digitar.
- Commits (implementação e correções):
  - 5308681 (2025-08-14) — gui: add 250ms debounced filtering.
  - dfb451c (2025-08-14) — GUI: fix debounce indentation e refinamentos; DB init path.
  - fe5a408 (2025-08-14) — Merge da PR de debounce.
- Status: concluído.

## 3) “Integrar tudo” após merges (paridade de funcionalidades)
- Implementação: ajustes e sincronizações pós-merge (extractor, table_printer, database, testes).
- Commits (integração):
  - 066823d, 54f0cad, 8e30191, 24cac89 (2025-08-13/14) — integrações e acertos pós-merge.
- Status: concluído.

## 4) CLI — novos comandos e ajuda (-ordn/-ordni, -cols, -x)
- Implementação: ordenação por nome (interno/label), listagem de colunas, remoção de termo do filtro, prompts/ajuda.
- Commits (base e ampliações):
  - 5ae09bc, 4f233d1 (2025-07-15) — CLI inicial e filtros sucessivos.
  - 9d8ee41, 1ddf65f, 641ac77 (2025-07-15) — ordenação e header wrapping.
  - d2eb694 (2025-07-25) — alterações amplas incluindo `interface/cli.py` e `interface/table_printer.py`.
  - 346ae53 (2025-08-14) — polimento e testes.
- Status: concluído.

## 5) Paridade CLI/GUI de apresentação (labels, truncação, seleção por largura do terminal)
- Implementação: seleção adaptativa por largura; truncação só quando necessário; uso de labels e short_labels.
- Commits:
  - d2eb694 (2025-07-25) — lote amplo de display/CLI.
  - 066823d/54f0cad/8e30191 (2025-08-13) — refinamentos pós-merge.
  - 346ae53 (2025-08-14) — ajustes + testes.
- Status: concluído.

## 6) Resolver conflito do column_priority.json (usar versão detalhada)
- Implementação: adotar estrutura com `essential`, `always_visible`, `priority_order`, `fixed_widths`, `short_labels`; mesclar larguras com settings; respeitar visibilidade.
- Commits:
  - d2eb694 (2025-07-25) — inclui configs e table_printer.
  - 346ae53 (2025-08-14) — polimento e testes.
- Status: concluído.

## 7) Reconstruir CHANGELOG e README ricos
- Implementação: `docs_saida/CHANGELOG_IMPLEMENTACOES.md` completo; README recriado com instalação/uso/testes.
- Commits:
  - 346ae53 (2025-08-14) — inclui CHANGELOG na árvore.
  - README atual: pendente de commit (presente no workspace).
- Status: concluído (changelog) / pendente de commit (README).

## 8) Proteger lógica de “arquivo mais recente” (não considerar README/changelog/config)
- Implementação: `utils/file_metadata.py` ignora arquivos protegidos (readme.md, changelog_implementacoes.md, column_priority.json, display_mappings.json); empacotamento inclui arquivos críticos.
- Commits:
  - 346ae53 (2025-08-14) — utilitários de metadados e testes correlatos.
  - Ampliação da lista de protegidos: pendente de commit (aplicada no workspace).
- Status: concluído (parcial no git) e reforçado (pendente de commit).

## 9) Integrity check para configs (auto-recriar se ausente/inválido, com logging)
- Implementação: verificação + auto-recriação de `display_mappings.json` com defaults; suporte a `SSA_CONFIG_DIR`; logging de recuperação.
- Commits:
  - Pendente de commit — código já aplicado no workspace em `core/config_manager.py` (função `load_display_mappings_integrity()`); usado por `gui/gui_ssa.py` e `interface/command_handlers.py`.
- Status: pendente de commit.

## 10) Banco/ingestão robustos (reset granular, índices idempotentes, upsert com desempate por data)
- Implementação: `armazenamento/database.py` com resets, `ensure_indexes` protegido, upsert por `numero_ssa` (desempate por `data_cadastro`), normalização de SSA na extração.
- Commits:
  - a737a57, 7f74f2e (2025-07-15) — extrair/salvar em SQLite.
  - 066823d, 9e6569d (2025-08-13) — refinamentos.
  - 346ae53 (2025-08-14) — guards de índices e testes.
- Status: concluído.

---

### Apêndice — Linha do tempo (resumo)
- 2025-08-14 — 346ae53 feat(formatting) + testes; integração GUI.
- 2025-08-14 — dfb451c corrigir debounce; 5308681 adicionar debounce; 3738a44 ajustes de CI/deps.
- 2025-08-13/14 — 066823d, 54f0cad, 8e30191, 24cac89 integrações pós-merge.
- 2025-07-25 — d2eb694 lote amplo: configs/CLI/display/testes/schema.
- 2025-07-21 — bb9add6, c941992 exibição e criação de settings.
- 2025-07-15 — série CLI/display/db/extractor/export.

---

### Como validar
- Conferir arquivos de cada commit: `git show <sha> --name-only`.
- Executar a suíte: `pytest` (55 testes passando localmente).
- Verificar existência/estado de configs e docs conforme “Status”.

---

Última atualização: 2025-08-15

---

## 11) Cabeçalhos: preferir labels de exibição em terminais largos; fallback para short_labels só quando necessário
- Implementação: `interface/table_printer.py` passou a usar rótulos de exibição (display_mappings) quando a largura do terminal permite. Em terminais estreitos ou quando explicitamente configurado, cai para `short_labels`.
- Commits:
  - 346ae53 (2025-08-14) — atualizações no `table_printer` e testes correlatos.
  - Ajustes adicionais: aplicados no workspace e cobertos por testes (55), pendente de commit.
- Status: concluído, coberto por testes.

## 12) Colunas “sempre visíveis” e seleção para terminais estreitos
- Implementação: colunas marcadas como `always_visible` em `column_priority.json` nunca são descartadas. Estimativa de largura usa `short_labels` para maximizar fit. Truncação com reticências só quando houve truncamento real.
- Commits:
  - 346ae53 (2025-08-14) — lógica de seleção/truncação e testes.
- Status: concluído.

## 13) Filtros: listar/limpar e estado no prompt (-f/-filtros, -clear, -clearall)
- Implementação: comandos para visualizar pilha de filtros e limpar filtros do usuário ou da sessão; prompt mostra o estado dos filtros; banners com versão curta/longa.
- Commits:
  - 346ae53 (2025-08-14) — comandos e testes.
- Status: concluído.

## 14) Versão dinâmica e banner
- Implementação: `utils/version.py` lê `config/version.json` e imprime versão curta e longa no banner da CLI; GUI/CLI compartilham a mesma origem de versão.
- Commits:
  - 346ae53 (2025-08-14) — inclui `config/version.json` e integrações.
- Status: concluído.

## 15) Alias e comandos de manutenção
- Implementação: alias e comandos úteis na CLI: `-rescan`/`--rescan` para forçar revarredura; melhorias de mensagens de ajuda e de erro.
- Commits:
  - d2eb694 (2025-07-25) — inclui comandos e help; integrações em 346ae53.
- Status: concluído.

## 16) Integridade do column_priority.json (auto-restauração e logging)
- Implementação: verificação de integridade e restauração do `column_priority.json` para valores canônicos quando vazio/ausente/inválido; logging explícito do evento; suporte a `SSA_CONFIG_DIR`.
- Commits:
  - Pendente de commit — aplicado no workspace (coberto por testes). Parte do polimento de 346ae53.
- Status: concluído (pendente de commit público).

## 17) Integridade do display_mappings.json (auto-restauração e logging)
- Implementação: `core/config_manager.load_display_mappings_integrity()` carrega/restaura o arquivo com defaults; GUI e CLI passaram a usar essa função; suporte a `SSA_CONFIG_DIR`.
- Commits:
  - Pendente de commit — alterações em `core/config_manager.py`, `gui/gui_ssa.py`, `interface/command_handlers.py`.
- Status: concluído (pendente de commit público).

## 18) Empacotamento e preservação de artefatos
- Implementação: garantir inclusão de `config/column_priority.json`, README e changelogs nos artefatos; restaurar versões canônicas em caso de falta; proteger arquivos críticos contra heurística de “mais recente”.
- Commits:
  - Parte presente em 346ae53; reforços de empacotamento e proteção aplicados no workspace (pendente de commit).
- Status: concluído (parcial no git) e reforçado (pendente de commit).

## 19) Proteções adicionais em “arquivo mais recente”
- Implementação: `utils/file_metadata.PROTECTED_FILENAMES` inclui `display_mappings.json`, além de `readme.md`, `changelog_implementacoes.md` e `column_priority.json`.
- Commits:
  - Pendente de commit — alteração em `utils/file_metadata.py` aplicada no workspace.
- Status: concluído (pendente de commit público).
