<!-- AUTOGERADO INICIALMENTE: pode editar manual; se script for criado, manter bloco START/END -->
# DOCUMENTAÇÃO CONSOLIDADA - SSA Consulta Rápida

Este documento centraliza referências rápidas aos principais materiais de documentação do projeto.
Objetivo: reduzir tempo de navegação entre múltiplos arquivos `.md` e servir de porta de entrada.

##  Índice Rápido
- [Visão Geral do Projeto](#visão-geral-do-projeto)
- [Arquitetura e Estrutura](#arquitetura-e-estrutura)
- [Mapeamentos e Configuração](#mapeamentos-e-configuração)
- [Fluxos Principais](#fluxos-principais)
- [Build & Distribuição](#build--distribuição)
- [Modo Optimized / Performance](#modo-optimized--performance)
- [Qualidade e Testes](#qualidade-e-testes)
- [Histórico e Changelog](#histórico-e-changelog)
- [Regras e Boas Práticas](#regras-e-boas-práticas)
- [Checklists Operacionais](#checklists-operacionais)
- [Diagnóstico / Troubleshooting](#diagnóstico--troubleshooting)
- [Estrutura Sintética / Navegação](#estrutura-sintética--navegação)
- [Governança da Documentação](#governança-da-documentação)
- [Scripts de Manutenção / Auditoria](#scripts-de-manutenção--auditoria)
- [Próximos Passos](#próximos-passos)

---
## Visão Geral do Projeto
- `README.md` (raiz) – visão resumida de execução.
- `docs/ESTRUTURA_PROJETO.md` – estrutura de diretórios e responsabilidades.
- `docs/RESUMO_ORGANIZACAO_FINAL.md` – consolidação pós-refatorações.

## Arquitetura e Estrutura
- Core: `core/app_logic.py`, `core/config_manager.py`.
- Banco: `armazenamento/database.py`, `armazenamento/database_optimized.py`.
- GUI: `gui/gui_ssa.py` (ou variante principal atual).
- CLI: diretório `interface/`.

## Mapeamentos e Configuração
- `config/column_mappings.json` – mapeamento de colunas origem → internas.
- `config/display_mappings.json` – nomes de exibição (não alterar DB).
- `config/column_priority.json` – ordem / prioridade de colunas.
- `config/default_settings.json` – parâmetros base.
- `config/version.json` – versão lógica do app.

## Fluxos Principais
1. Importação / atualização de SSA → `core/app_logic.py`
2. Carregamento otimizado → `armazenamento/database_optimized.py`
3. Filtro e exibição → GUI (camadas de busca + cache)
4. CLI / exportação simples → `interface/cli_main.py`

## Build & Distribuição
- `docs/BUILD_SYSTEM.md` – visão do sistema de build.
- `docs/BUILD_ANALYSIS.md` – análise técnica de build.
- `build/` scripts auxiliares.
- `launchers/README_BUILD_AUTOMATIZADO.md` – blueprint proposto de pipeline.
- `launchers/STATUS_BUILD_v3.10.md` – status detalhado da versão 3.10.

## Modo Optimized / Performance
- `docs/GUIA_MODO_OPTIMIZED.md` – instruções e trade-offs.
- `armazenamento/database_optimized.py` – implementação.
- Cache: `core/cache_manager.py`.

## Qualidade e Testes
- `launchers/RELATORIO_TESTES_FINAL.md` – relatório baseline de testes.
- `launchers/RESUMO_FINAL_v3.10.md` – resumo executivo da versão.
- `launchers/STATUS_FINAL.md` – visão de saúde e maturidade.
- `scripts/check_docs.py` – lint da documentação (mínimo de linhas, placeholders proibidos).
- `scripts/validate_configs.py` – validação estrutural e semântica básica dos JSONs em `config/`.
- `scripts/smoke_cli.py` – verificação rápida de integridade do entrypoint CLI.

## Histórico e Changelog
- `docs/HISTORICO_RELEASES.md` – releases detalhadas.
- `docs/HISTORICO_VERSOES.md` – evolução incremental.
- `docs/CHANGELOG_IMPLEMENTACOES.md` – mudanças implementadas.

## Regras e Boas Práticas
- `docs/REGRAS_DE_OURO.md` – o que nunca/sempre fazer.
- `docs/REGRA_NUMERO_SSA.md` – padrão de `numero_ssa` (sem acentos, snake_case etc.).
- Nomes internos: sempre snake_case, ASCII, sem espaços.

## Checklists Operacionais
- `docs/CHECKLIST_MASTER.md`
- `docs/CHECKLIST_ACOES_IMEDIATAS.md`
- `docs/CHECKLIST_PENDENCIAS_v3.10.md`
- `docs/CHECKLIST_PENDENCIAS_FUTURAS.md`

## Estrutura Sintética / Navegação
- `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` – mapa rápido de diretórios.

## Governança da Documentação
- `launchers/README_DOCS.md` – princípios, tipos e auditoria de docs.
- `launchers/BASELINE_TAG.md` – procedimento de criação de baseline tag.
- `launchers/GUIA_PRIVACIDADE_IMPLEMENTACAO.md` – diretrizes de privacidade e controles propostos.

## Scripts de Manutenção / Auditoria
- `launchers/cleanup_emergency.py` – limpeza emergencial (dry-run padrão).
- `launchers/cleanup_repository.py` – limpeza abrangente com retenção configurável.
- `launchers/cleanup_manual.py` – limpeza seletiva interativa / dry-run.
- `sanitize_project.py` – auditoria de nomes, docs vazios e estruturas.
- `scripts/check_docs.py` – valida documentação.
- `scripts/validate_configs.py` – valida JSONs de configuração.
- `scripts/smoke_cli.py` – smoke test CLI.

## Diagnóstico / Troubleshooting
- `docs/TROUBLESHOOTING.md`
- Scripts manutenção: `scripts_manutencao/`.
- Backups DB: `data/historico_backups/`.

## Próximos Passos
- `docs/PLANEJAMENTO_ROADMAP.md`
- `docs/PLANOS_MELHORIAS.md`
- `docs/PROXIMOS_PASSOS_POS_CONSOLIDACAO.md`
- (Futuro) Script agregador automático desta consolidação.

---
## Notas
- Este arquivo era originalmente vazio; preenchido em: $(date não dinâmico). Atualize manualmente conforme evoluções.
- Futuro script poderá regenerar esta consolidação automaticamente.
- Última atualização manual: 2025-09-12 (adição baseline, privacidade, smoke test, limpeza manual e validações configuracionais).

<!-- END CONSOLIDATED -->
