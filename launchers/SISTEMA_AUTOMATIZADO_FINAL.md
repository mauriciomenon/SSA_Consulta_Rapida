<!-- Documento de referência estratégica do ecossistema de automações -->
# SISTEMA AUTOMATIZADO FINAL – VISÃO INTEGRADA

Este documento consolida a visão do sistema de automações destinado a garantir
qualidade, repetibilidade, higiene e governança contínua do repositório
`SSA_Consulta_Rapida`. Serve como blueprint evolutivo: descreve o estado atual,
gates já efetivos, lacunas e o roadmap incremental para chegar a um pipeline
maduro e auditável.

---
## 1. Objetivos do Sistema de Automação
| Objetivo | Descrição | Métrica Indicativa |
|----------|-----------|--------------------|
| Higiene | Detectar e minimizar lixo (caches, artefatos obsoletos) | Nº diretórios pycache após limpeza = 0 |
| Confiança | Prevenir regressões básicas antes de release/tag | Teste smoke CLI/GUI passa 100% |
| Consistência Documental | Evitar docs vazios/placeholder silenciosos | 0 falhas em check_docs |
| Integridade de Configuração | JSONs válidos e esquemas coerentes | 0 erros validate_configs |
| Rastreabilidade | Histórico claro de ações automatizadas | Log consolidado por execução |
| Reprodutibilidade de Build | Geração de artefatos determinística | Hashes estáveis entre builds |

---
## 2. Componentes Atuais (Estado Implementado)
| Componente | Arquivo / Local | Função Principal | Tipo |
|------------|-----------------|------------------|------|
| Limpeza emergencial | `launchers/cleanup_emergency.py` | Remover rapidamente artefatos em situação crítica (dry-run padrão) | Script standalone |
| Limpeza abrangente | `launchers/cleanup_repository.py` | Plano completo com grupos, retenção e integração opcional sanitize | Script standalone |
| Saneamento/Nomes | `sanitize_project.py` | Auditoria de nomes, docs vazios, pycache, backups | Script raiz |
| Consolidação docs | `launchers/DOCUMENTACAO_CONSOLIDADA.md` | Índice referencia rápido de documentação | Doc índice |
| Status build v3.10 | `launchers/STATUS_BUILD_v3.10.md` | Snapshot de maturidade build | Relatório |
| Relatório testes | `launchers/RELATORIO_TESTES_FINAL.md` | Baseline de critérios e categorias de teste | Relatório |
| Resumo final versão | `launchers/RESUMO_FINAL_v3.10.md` | Contexto, riscos e próximos passos | Resumo executivo |
| Estrutura sintética | `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` | Navegação rápida da árvore | Doc guia |
| Governança docs | `launchers/README_DOCS.md` | Padrões e métricas de documentação | Guia |
| Pipeline proposto | `launchers/README_BUILD_AUTOMATIZADO.md` | Blueprint de fases CI/CD desejadas | Design |

---
## 3. Lacunas / Itens Planejados (Short Term)
| Item | Descrição | Prioridade | Alvo |
|------|-----------|------------|------|
| `scripts/check_docs.py` | Lint de documentação (linhas mínimas, anti-placeholder, JSON output) | Alta | Gate PR |
| `scripts/validate_configs.py` | Validar estrutura/consistência dos JSON em `config/` | Alta | Gate PR |
| Smoke CLI | Testar `python main.py --help` ou entry CLI para sair OK | Alta | Pipeline básico |
| Smoke DB | Verificar abertura sqlite + tabela chave | Média | Pipeline extendido |
| Check GUI Launch | Iniciar GUI headless (import + criação objeto) | Média | Pipeline extendido |
| Teste memória básica | Carregar dataset e medir limite aceitável | Baixa | Qualidade contínua |
| Tag Baseline | Marcar estado limpo pós-gates iniciais | Alta | Controle versões |

---
## 4. Fluxo Ideal de Execução (Curto Prazo)
```mermaid
flowchart TD
	A[Dev Commit] --> B[Pre-commit (futuro?) lint/format]
	B --> C[CI Stage 1: check_docs]
	C --> D[CI Stage 2: validate_configs]
	D --> E[CI Stage 3: smoke_cli]
	E --> F[CI Stage 4: sanitize dry-run]
	F --> G{Falhas?}
	G -- Sim --> H[Block + Report]
	G -- Não --> I[Empacotar Build]
	I --> J[Artefatos / Dist]
	J --> K[Tag / Release]
```

---
## 5. Política de Gates (Inicial)
| Gate | Critério de Aprovação | Ação em Falha |
|------|-----------------------|---------------|
| check_docs | 0 arquivos inválidos/vazios | Falha pipeline |
| validate_configs | Todos JSON parse + campos obrigatórios presentes | Falha pipeline |
| smoke_cli | Comando retorna código 0 e contém trecho esperado em STDOUT | Falha pipeline |
| sanitize (dry) | Sem nomes proibidos / docs vazias | Warning (elevar depois) |
| build (futuro) | Artefatos gerados sem erro | Falha pipeline |

Evolução: transformar warning de sanitize em falha após estabilização.

---
## 6. Métricas de Observabilidade (Propostas)
| Métrica | Origem | Objetivo |
|---------|--------|----------|
| docs_invalid_count | check_docs | Rumo a zero | 
| config_errors | validate_configs | Detectar regressão config |
| smoke_cli_duration_ms | smoke_cli | Monitor tempo de resposta |
| sanitize_warnings | sanitize_project (dry) | Redução contínua |
| build_size_bytes | build pipeline | Estabilidade / diffs inesperados |

---
## 7. Design de Scripts (Padrões Recomendados)
1. Dry-run por padrão para scripts destrutivos.
2. Flag `--json` para integração CI.
3. Código de saída padronizado:
	 - 0 sucesso
	 - 1 falha de validação
	 - 2 erro interno/execução
4. Limitar saída humana (modo texto) e detalhar em JSON quando necessário.
5. Manter help (`-h/--help`) claro e com exemplos mínimos.

---
## 8. Roadmap Evolutivo (Macro)
| Fase | Conteúdo | Resultado Esperado |
|------|----------|--------------------|
| Fase 1 | check_docs, validate_configs, smoke_cli | Baseline qualidade mínima |
| Fase 2 | sanitize integrado no CI, smoke_db, smoke_gui | Confiança ampliada |
| Fase 3 | Testes unitários críticos (core, armazenamento) | Cobertura inicial |
| Fase 4 | Métricas + upload artefatos build | Observabilidade básica |
| Fase 5 | Hardening (coverage gates, mutation tests) | Qualidade robusta |
| Fase 6 | Otimizações performance automatizadas | Performance monitorada |

---
## 9. Checklist Pré-Tag Baseline (Inicial)
| Item | Status | Observação |
|------|--------|------------|
| Scripts core implementados | Parcial | Falta check_docs / validate_configs |
| Smoke CLI | Pendente | Implementar teste simples |
| Índice docs atualizado | OK | Atualizado 2025-09-12 |
| Limpeza/Organização (sanitize) | OK (manual) | Rodar dry-run no pipeline |
| Plano de gates documentado | OK | Este documento |
| Configs validadas | Pendente | Aguardando script |

---
## 10. Riscos & Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Falta de testes unitários | Regressões silenciosas | Priorizar Fase 3 pós baseline |
| Aumento de complexidade scripts | Manutenção difícil | Padronizar estilo + centralizar utilidades |
| Divergência entre docs e pipeline real | Confusão de estado | Regeneração periódica + revisão mensal |
| Volumes de logs não tratados | Espaço em disco | Políticas de retenção já implementadas |
| Backups excessivos | Espaço e lentidão | Retenção configurável em cleanup_repository |

---
## 11. Estrutura de Diretórios Relacionada
| Diretório | Propósito |
|-----------|-----------|
| `launchers/` | Scripts e relatórios de alto nível / blueprint |
| `scripts/` | (Em formação) utilidades de validação | 
| `scripts_manutencao/` | Scripts legados / manutenção específica |
| `data/historico_backups/` | Backups versionados do SQLite |
| `build/` | Entradas para processo de build futuro |

---
## 12. Próximas Ações Imediatas
1. Implementar `scripts/check_docs.py`.
2. Implementar `scripts/validate_configs.py`.
3. Adicionar teste smoke CLI.
4. Consolidar checklist Baseline Tag.
5. Ajustar pipeline futuro (GitHub Actions / outro) com estágios iniciais.

---
## 13. Convenções de Código para Scripts de Qualidade
| Convenção | Justificativa |
|-----------|--------------|
| `if __name__ == "__main__":` com `SystemExit(main())` | Códigos de saída explícitos |
| Uso de `argparse` | Interface consistente |
| Flag `--json` | Integração CI agnóstica |
| Sem dependências externas (fase 1) | Simplicidade / bootstrap rápido |
| Mensagens curtas no modo texto | Leitura humana em logs |

---
## 14. Evolução Planejada de Testes
| Etapa | Conteúdo | Ferramenta |
|-------|----------|-----------|
| Smoke | CLI help / DB open | Script custom |
| Unit Core | Funções críticas de `core/*` | pytest (futuro) |
| Unit DB | Operações CRUD mínimas | pytest |
| Integração | Fluxo ingestão → cache → busca | pytest + fixtures |
| Performance | Cenário dataset médio (tempo/memória) | harness custom |

---
## 15. Indicadores de Maturidade (Score Heurístico)
| Nível | Características |
|-------|-----------------|
| 1 (Atual) | Scripts de limpeza e saneamento básicos + docs consolidadas |
| 2 | Gates de docs, configs e smoke CLI ativos |
| 3 | Testes unitários iniciais + sanitize como gate hard |
| 4 | Cobertura monitorada + build distribuível verificável |
| 5 | Performance monitorada + artefatos assinados |
| 6 | Automação avançada (mutação, segurança, análise estática) |

---
## 16. Referências Relacionadas
| Documento | Contexto |
|-----------|---------|
| `launchers/README_BUILD_AUTOMATIZADO.md` | Pipeline proposto |
| `launchers/README_DOCS.md` | Governança documental |
| `launchers/STATUS_BUILD_v3.10.md` | Estado versão atual |
| `launchers/RELATORIO_TESTES_FINAL.md` | Estratégia de testes |
| `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` | Navegação rápida |
| `sanitize_project.py` | Auditoria e saneamento |
| `launchers/cleanup_repository.py` | Limpeza ampla |

---
## 17. Notas Finais
Este documento deve ser revisto a cada ciclo de versão ou ao introduzir novos
gates. Alterações estruturais no pipeline precisam atualizar simultaneamente:
1. Esta visão integrada
2. Índice consolidado
3. READMEs específicos (build / docs)

Versão inicial: 2025-09-12

