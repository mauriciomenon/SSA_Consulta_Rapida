# ESTRUTURA FINAL ORGANIZADA (VISÃO RÁPIDA)

Guia ultra-resumido para localizar rapidamente componentes e entender a responsabilidade de cada área. Leitura alvo < 60 segundos.

## 1. Núcleos Principais
| Área | Diretório / Arquivo | Responsabilidade | Observações |
|------|---------------------|------------------|-------------|
| Lógica Central | `core/app_logic.py` | Orquestra fluxo de atualização / consulta | Evitar acoplamento com GUI |
| Cache | `core/cache_manager.py` | Estratégia de cache de consultas | Ajustar TTL futuro |
| Banco (camada base) | `armazenamento/database.py` | Operações CRUD principais | Usar antes de otimizações |
| Banco otimizado | `armazenamento/database_optimized.py` | Rotinas de carga / índices / tuning | Validar impacto antes de mudar |
| Configurações | `config/*.json` | Mapeamentos e preferências persistidas | Adicionar validator (pendente) |
| GUI | `gui/` | Interface PyQt6 | Respeitar algoritmo de larguras |
| CLI | `interface/` | Comandos e interação textual | Manter paridade funcional com GUI |
| Scripts gerais | `scripts/` | Automação operacional | Não misturar manutenção |
| Scripts manutenção | `scripts_manutencao/` | Correções, diagnóstico | Executar isoladamente |

## 2. Fluxo de Dados (Simplificado)
Entrada → `extracao/` → Normalização → `core/app_logic.py` → Persistência (`armazenamento/`) → Cache (`core/cache_manager.py`) → Exposição (CLI `interface/` ou GUI `gui/`).

## 3. Documentação Chave (Entrada Rápida)
| Necessidade | Arquivo |
|-------------|---------|
| Visão global | `docs/RESUMO_ORGANIZACAO_FINAL.md` |
| Navegação geral | `launchers/DOCUMENTACAO_CONSOLIDADA.md` |
| Larguras GUI | `docs/ALGORITMO_LARGURAS_GUI_CRITICO.md` |
| Onboarding dev | `docs/TEMPLATE_ONBOARDING_DESENVOLVEDORES.md` |
| Status build | `launchers/STATUS_BUILD_v3.10.md` |
| Testes baseline | `launchers/RELATORIO_TESTES_FINAL.md` |
| Resumo versão | `launchers/RESUMO_FINAL_v3.10.md` |

## 4. Padrões Essenciais
- Nomes: snake_case ASCII.
- Sem lógica de banco na GUI.
- Alterou mapeamento? Registrar e justificar.
- Documento não pode ficar vazio (usar placeholder TODO claro se incompleto).

## 5. Áreas Sensíveis (Revisão Obrigatória)
| Área | Motivo | Requisito para Alterar |
|------|--------|------------------------|
| `core/app_logic.py` | Impacta fluxo global | Análise de impacto |
| `armazenamento/database_optimized.py` | Performance / índices | Medir antes/depois |
| `config/*.json` | Afeta comportamento | Validar com schema (quando existir) |
| `gui/` largura | Usabilidade | Manter algoritmo documentado |

## 6. Próximos Passos (Qualidade)
1. Adicionar validator de JSON.
2. Introduzir smoke CLI.
3. Adicionar script de checagem de docs.
4. Criar primeiros testes unit core.

## 7. Estado Atual (Checklist Rápida)
- [x] Documentação consolidada
- [x] Padronização de nomes
- [x] Script limpeza emergencial
- [ ] Validator config
- [ ] Smoke CLI
- [ ] Testes unit core

---
Atualizado em: 2025-09-12

