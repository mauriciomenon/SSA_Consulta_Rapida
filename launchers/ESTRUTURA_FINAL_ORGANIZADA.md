# ESTRUTURA FINAL ORGANIZADA (VISAO RAPIDA)

Guia ultra-resumido para localizar rapidamente componentes e entender a responsabilidade de cada area. Leitura alvo < 60 segundos.

## 1. Nucleos Principais
| Area | Diretorio / Arquivo | Responsabilidade | Observacoes |
|------|---------------------|------------------|-------------|
| Logica Central | `core/app_logic.py` | Orquestra fluxo de atualizacao / consulta | Evitar acoplamento com GUI |
| Cache | `core/cache_manager.py` | Estrategia de cache de consultas | Ajustar TTL futuro |
| Banco (camada base) | `armazenamento/database.py` | Operacoes CRUD principais | Usar antes de otimizacoes |
| Banco otimizado | `armazenamento/database_optimized.py` | Rotinas de carga / indices / tuning | Validar impacto antes de mudar |
| Configuracoes | `config/*.json` | Mapeamentos e preferencias persistidas | Adicionar validator (pendente) |
| GUI | `gui/` | Interface PyQt6 | Respeitar algoritmo de larguras |
| CLI | `interface/` | Comandos e interacao textual | Manter paridade funcional com GUI |
| Scripts gerais | `scripts/` | Automacao operacional | Nao misturar manutencao |
| Scripts manutencao | `scripts_manutencao/` | Correcoes, diagnostico | Executar isoladamente |

## 2. Fluxo de Dados (Simplificado)
Entrada → `extracao/` → Normalizacao → `core/app_logic.py` → Persistencia (`armazenamento/`) → Cache (`core/cache_manager.py`) → Exposicao (CLI `interface/` ou GUI `gui/`).

## 3. Documentacao Chave (Entrada Rapida)
| Necessidade | Arquivo |
|-------------|---------|
| Visao global | `docs/RESUMO_ORGANIZACAO_FINAL.md` |
| Navegacao geral | `launchers/DOCUMENTACAO_CONSOLIDADA.md` |
| Larguras GUI | `docs/ALGORITMO_LARGURAS_GUI_CRITICO.md` |
| Onboarding dev | `docs/TEMPLATE_ONBOARDING_DESENVOLVEDORES.md` |
| Status build | `launchers/STATUS_BUILD_v3.10.md` |
| Testes baseline | `launchers/RELATORIO_TESTES_FINAL.md` |
| Resumo versao | `launchers/RESUMO_FINAL_v3.10.md` |

## 4. Padroes Essenciais
- Nomes: snake_case ASCII.
- Sem logica de banco na GUI.
- Alterou mapeamento? Registrar e justificar.
- Documento nao pode ficar vazio (usar placeholder TODO claro se incompleto).

## 5. Areas Sensiveis (Revisao Obrigatoria)
| Area | Motivo | Requisito para Alterar |
|------|--------|------------------------|
| `core/app_logic.py` | Impacta fluxo global | Analise de impacto |
| `armazenamento/database_optimized.py` | Performance / indices | Medir antes/depois |
| `config/*.json` | Afeta comportamento | Validar com schema (quando existir) |
| `gui/` largura | Usabilidade | Manter algoritmo documentado |

## 6. Proximos Passos (Qualidade)
1. Adicionar validator de JSON.
2. Introduzir smoke CLI.
3. Adicionar script de checagem de docs.
4. Criar primeiros testes unit core.

## 7. Estado Atual (Checklist Rapida)
- [x] Documentacao consolidada
- [x] Padronizacao de nomes
- [x] Script limpeza emergencial
- [ ] Validator config
- [ ] Smoke CLI
- [ ] Testes unit core

---
Atualizado em: 2025-09-12

