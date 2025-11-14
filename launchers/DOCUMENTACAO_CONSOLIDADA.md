<!-- AUTOGERADO INICIALMENTE: pode editar manual; se script for criado, manter bloco START/END -->
# DOCUMENTACAO CONSOLIDADA - SSA Consulta Rapida

Este documento centraliza referencias rapidas aos principais materiais de documentacao do projeto.
Objetivo: reduzir tempo de navegacao entre multiplos arquivos `.md` e servir de porta de entrada.

##  Indice Rapido
- [Visao Geral do Projeto](#visao-geral-do-projeto)
- [Arquitetura e Estrutura](#arquitetura-e-estrutura)
- [Mapeamentos e Configuracao](#mapeamentos-e-configuracao)
- [Fluxos Principais](#fluxos-principais)
- [Build & Distribuicao](#build--distribuicao)
- [Modo Optimized / Performance](#modo-optimized--performance)
- [Qualidade e Testes](#qualidade-e-testes)
- [Historico e Changelog](#historico-e-changelog)
- [Regras e Boas Praticas](#regras-e-boas-praticas)
- [Checklists Operacionais](#checklists-operacionais)
- [Diagnostico / Troubleshooting](#diagnostico--troubleshooting)
- [Estrutura Sintetica / Navegacao](#estrutura-sintetica--navegacao)
- [Governanca da Documentacao](#governanca-da-documentacao)
- [Scripts de Manutencao / Auditoria](#scripts-de-manutencao--auditoria)
- [Proximos Passos](#proximos-passos)

---
## Visao Geral do Projeto
- `README.md` (raiz) – visao resumida de execucao.
- `docs/ESTRUTURA_PROJETO.md` – estrutura de diretorios e responsabilidades.
- `docs/RESUMO_ORGANIZACAO_FINAL.md` – consolidacao pos-refatoracoes.

## Arquitetura e Estrutura
- Core: `core/app_logic.py`, `core/config_manager.py`.
- Banco: `armazenamento/database.py`, `armazenamento/database_optimized.py`.
- GUI: `gui/gui_ssa.py` (ou variante principal atual).
- CLI: diretorio `interface/`.

## Mapeamentos e Configuracao
- `config/column_mappings.json` – mapeamento de colunas origem → internas.
- `config/display_mappings.json` – nomes de exibicao (nao alterar DB).
- `config/column_priority.json` – ordem / prioridade de colunas.
- `config/default_settings.json` – parametros base.
- `config/version.json` – versao logica do app.

## Fluxos Principais
1. Importacao / atualizacao de SSA → `core/app_logic.py`
2. Carregamento otimizado → `armazenamento/database_optimized.py`
3. Filtro e exibicao → GUI (camadas de busca + cache)
4. CLI / exportacao simples → `interface/cli_main.py`

## Build & Distribuicao
- `docs/BUILD_SYSTEM.md` – visao do sistema de build.
- `docs/BUILD_ANALYSIS.md` – analise tecnica de build.
- `build/` scripts auxiliares.
- `launchers/README_BUILD_AUTOMATIZADO.md` – blueprint proposto de pipeline.
- `launchers/STATUS_BUILD_v3.10.md` – status detalhado da versao 3.10.

## Modo Optimized / Performance
- `docs/GUIA_MODO_OPTIMIZED.md` – instrucoes e trade-offs.
- `armazenamento/database_optimized.py` – implementacao.
- Cache: `core/cache_manager.py`.

## Qualidade e Testes
- `launchers/RELATORIO_TESTES_FINAL.md` – relatorio baseline de testes.
- `launchers/RESUMO_FINAL_v3.10.md` – resumo executivo da versao.
- `launchers/STATUS_FINAL.md` – visao de saude e maturidade.
- `scripts/check_docs.py` – lint da documentacao (minimo de linhas, placeholders proibidos).
- `scripts/validate_configs.py` – validacao estrutural e semantica basica dos JSONs em `config/`.
- `scripts/smoke_cli.py` – verificacao rapida de integridade do entrypoint CLI.

## Historico e Changelog
- `docs/HISTORICO_RELEASES.md` – releases detalhadas.
- `docs/HISTORICO_VERSOES.md` – evolucao incremental.
- `docs/CHANGELOG_IMPLEMENTACOES.md` – mudancas implementadas.

## Regras e Boas Praticas
- `docs/REGRAS_DE_OURO.md` – o que nunca/sempre fazer.
- `docs/REGRA_NUMERO_SSA.md` – padrao de `numero_ssa` (sem acentos, snake_case etc.).
- Nomes internos: sempre snake_case, ASCII, sem espacos.

## Checklists Operacionais
- `docs/CHECKLIST_MASTER.md`
- `docs/CHECKLIST_ACOES_IMEDIATAS.md`
- `docs/CHECKLIST_PENDENCIAS_v3.10.md`
- `docs/CHECKLIST_PENDENCIAS_FUTURAS.md`

## Estrutura Sintetica / Navegacao
- `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` – mapa rapido de diretorios.

## Governanca da Documentacao
- `launchers/README_DOCS.md` – principios, tipos e auditoria de docs.
- `launchers/BASELINE_TAG.md` – procedimento de criacao de baseline tag.
- `launchers/GUIA_PRIVACIDADE_IMPLEMENTACAO.md` – diretrizes de privacidade e controles propostos.

## Scripts de Manutencao / Auditoria
- `launchers/cleanup_emergency.py` – limpeza emergencial (dry-run padrao).
- `launchers/cleanup_repository.py` – limpeza abrangente com retencao configuravel.
- `launchers/cleanup_manual.py` – limpeza seletiva interativa / dry-run.
- `sanitize_project.py` – auditoria de nomes, docs vazios e estruturas.
- `scripts/check_docs.py` – valida documentacao.
- `scripts/validate_configs.py` – valida JSONs de configuracao.
- `scripts/smoke_cli.py` – smoke test CLI.

## Diagnostico / Troubleshooting
- `docs/TROUBLESHOOTING.md`
- Scripts manutencao: `scripts_manutencao/`.
- Backups DB: `data/historico_backups/`.

## Proximos Passos
- `docs/PLANEJAMENTO_ROADMAP.md`
- `docs/PLANOS_MELHORIAS.md`
- `docs/PROXIMOS_PASSOS_POS_CONSOLIDACAO.md`
- (Futuro) Script agregador automatico desta consolidacao.

---
## Notas
- Este arquivo era originalmente vazio; preenchido em: $(date nao dinamico). Atualize manualmente conforme evolucoes.
- Futuro script podera regenerar esta consolidacao automaticamente.
- Ultima atualizacao manual: 2025-09-12 (adicao baseline, privacidade, smoke test, limpeza manual e validacoes configuracionais).

<!-- END CONSOLIDATED -->
