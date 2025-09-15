# RESUMO DA ORGANIZAÇÃO FINAL DO PROJETO

Este documento resume o estado final (consolidado) da organização do repositório após as correções estruturais e padronizações recentes.

## 1. Objetivo
Fornecer visão sintética (<= 2 minutos de leitura) para qualquer pessoa validar rapidamente:
- Onde estão os componentes centrais.
- Quais diretórios são fonte de verdade para cada tipo de artefato.
- Quais áreas exigem maior cautela para alteração.

## 2. Mapa Macro de Diretórios
| Diretório | Papel | Observações |
|-----------|-------|-------------|
| `core/` | Lógica de orquestração e cache | Alterar com revisão prévia. |
| `armazenamento/` | Acesso e otimização de banco SQLite | Backup antes de mudanças. |
| `extracao/` | Processos de ingestão / parsing | Validar formatos antes de expandir. |
| `interface/` | CLI e interações textuais | Mantém paridade com GUI quando possível. |
| `gui/` | Implementação PyQt6 | Respeitar algoritmo de larguras. |
| `config/` | JSONs de mapeamento e preferências | Adicionar README explicando campos (pendente). |
| `scripts/` | Automação operacional / build | Não misturar com manutenção. |
| `scripts_manutencao/` | Diagnósticos e correções | Executar isoladamente. |
| `data/` | Banco e caches | Contém backups versionados. |
| `docs/` | Documentação técnica detalhada | Fonte primária da doc. |
| `launchers/` | Guias rápidos / status / quickstart | Voltado a operação. |
| `tests/` | Testes (GUI/CLI) | Expandir smoke + estabilidade. |

## 3. Fluxo Crítico Simplificado
1. Entrada (import) → `extracao/`
2. Processamento / normalização → `core/app_logic.py`
3. Persistência → `armazenamento/database(_optimized).py`
4. Cache / otimização → `core/cache_manager.py`
5. Exposição → CLI (`interface/`) ou GUI (`gui/`)

## 4. Convenções Essenciais
- Nomes de arquivos: snake_case, ASCII, sem acentos.
- Sem lógica de banco dentro de GUI diretamente.
- Mudança em mapeamentos → justificar em changelog.
- Documentos não podem permanecer vazios (placeholder deve ser marcado claramente).

## 5. Itens Sensíveis / Requerem Cautela
| Área | Risco | Mitigação |
|------|-------|-----------|
| `armazenamento/database.py` | Corrupção de dados | Backup + teste em cópia. |
| `config/*.json` | Quebra de importações | Validar chaves antes de commit. |
| `core/app_logic.py` | Fluxo central | Revisão dupla. |
| Cache (`core/cache_manager.py`) | Inconsistência de dados exibidos | Invalidar corretamente. |
| Otimizado (`database_optimized.py`) | Regressão performance | Benchmarks simples. |

## 6. Ações Recentes de Organização
- Remoção de placeholders vazios (ou preenchimento com conteúdo mínimo útil).
- Consolidação de navegação via `launchers/DOCUMENTACAO_CONSOLIDADA.md`.
- Criação de arquivos guia: onboarding, algoritmo de larguras, análise de problemas.
- Neutralização de ruído de lint para foco em erros reais.

## 7. Pendências Estruturais (Resumo)
| Pendência | Benefício | Prioridade |
|-----------|-----------|------------|
| README detalhado para cada grupo de JSON | Evita mau uso | Alta |
| Testes smoke mínimos (CLI + GUI) | Confiança em refactors | Alta |
| Auditor de placeholders em CI | Evita retorno de vazios | Média |
| Documentação fluxo de cache detalhada | Clareza performance | Média |

## 8. Critério de “Organização Estável”
Considera-se estável quando: (a) nenhum .md vazio em 2 releases, (b) testes smoke passam, (c) alterações em config sempre acompanhadas de justificativa documentada, (d) banco nunca alterado sem backup automático.

## 9. Como Evoluir sem Regressão
- Introduzir mudanças em camadas isoladas (feature branch focada).
- Atualizar sempre documento relacionado antes de merge.
- Adotar script de verificação pré-commit para nomes e placeholders.

## 10. Histórico
Arquivo criado para substituir placeholder vazio (12/09/2025). Atualizar ao concluir pendências ou alterar topologia.

