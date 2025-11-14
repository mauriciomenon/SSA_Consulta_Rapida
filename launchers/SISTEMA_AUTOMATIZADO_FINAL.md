<!-- Documento de referencia estrategica do ecossistema de automacoes -->
# SISTEMA AUTOMATIZADO FINAL – VISAO INTEGRADA

Este documento consolida a visao do sistema de automacoes destinado a garantir
qualidade, repetibilidade, higiene e governanca continua do repositorio
`SSA_Consulta_Rapida`. Serve como blueprint evolutivo: descreve o estado atual,
gates ja efetivos, lacunas e o roadmap incremental para chegar a um pipeline
maduro e auditavel.

---
## 1. Objetivos do Sistema de Automacao
| Objetivo | Descricao | Metrica Indicativa |
|----------|-----------|--------------------|
| Higiene | Detectar e minimizar lixo (caches, artefatos obsoletos) | No diretorios pycache apos limpeza = 0 |
| Confianca | Prevenir regressoes basicas antes de release/tag | Teste smoke CLI/GUI passa 100% |
| Consistencia Documental | Evitar docs vazios/placeholder silenciosos | 0 falhas em check_docs |
| Integridade de Configuracao | JSONs validos e esquemas coerentes | 0 erros validate_configs |
| Rastreabilidade | Historico claro de acoes automatizadas | Log consolidado por execucao |
| Reprodutibilidade de Build | Geracao de artefatos deterministica | Hashes estaveis entre builds |

---
## 2. Componentes Atuais (Estado Implementado)
| Componente | Arquivo / Local | Funcao Principal | Tipo |
|------------|-----------------|------------------|------|
| Limpeza emergencial | `launchers/cleanup_emergency.py` | Remover rapidamente artefatos em situacao critica (dry-run padrao) | Script standalone |
| Limpeza abrangente | `launchers/cleanup_repository.py` | Plano completo com grupos, retencao e integracao opcional sanitize | Script standalone |
| Saneamento/Nomes | `sanitize_project.py` | Auditoria de nomes, docs vazios, pycache, backups | Script raiz |
| Consolidacao docs | `launchers/DOCUMENTACAO_CONSOLIDADA.md` | Indice referencia rapido de documentacao | Doc indice |
| Status build v3.10 | `launchers/STATUS_BUILD_v3.10.md` | Snapshot de maturidade build | Relatorio |
| Relatorio testes | `launchers/RELATORIO_TESTES_FINAL.md` | Baseline de criterios e categorias de teste | Relatorio |
| Resumo final versao | `launchers/RESUMO_FINAL_v3.10.md` | Contexto, riscos e proximos passos | Resumo executivo |
| Estrutura sintetica | `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` | Navegacao rapida da arvore | Doc guia |
| Governanca docs | `launchers/README_DOCS.md` | Padroes e metricas de documentacao | Guia |
| Pipeline proposto | `launchers/README_BUILD_AUTOMATIZADO.md` | Blueprint de fases CI/CD desejadas | Design |

---
## 3. Lacunas / Itens Planejados (Short Term)
| Item | Descricao | Prioridade | Alvo |
|------|-----------|------------|------|
| `scripts/check_docs.py` | Lint de documentacao (linhas minimas, anti-placeholder, JSON output) | Alta | Gate PR |
| `scripts/validate_configs.py` | Validar estrutura/consistencia dos JSON em `config/` | Alta | Gate PR |
| Smoke CLI | Testar `python main.py --help` ou entry CLI para sair OK | Alta | Pipeline basico |
| Smoke DB | Verificar abertura sqlite + tabela chave | Media | Pipeline extendido |
| Check GUI Launch | Iniciar GUI headless (import + criacao objeto) | Media | Pipeline extendido |
| Teste memoria basica | Carregar dataset e medir limite aceitavel | Baixa | Qualidade continua |
| Tag Baseline | Marcar estado limpo pos-gates iniciais | Alta | Controle versoes |

---
## 4. Fluxo Ideal de Execucao (Curto Prazo)
```mermaid
flowchart TD
	A[Dev Commit] --> B[Pre-commit (futuro?) lint/format]
	B --> C[CI Stage 1: check_docs]
	C --> D[CI Stage 2: validate_configs]
	D --> E[CI Stage 3: smoke_cli]
	E --> F[CI Stage 4: sanitize dry-run]
	F --> G{Falhas?}
	G -- Sim --> H[Block + Report]
	G -- Nao --> I[Empacotar Build]
	I --> J[Artefatos / Dist]
	J --> K[Tag / Release]
```

---
## 5. Politica de Gates (Inicial)
| Gate | Criterio de Aprovacao | Acao em Falha |
|------|-----------------------|---------------|
| check_docs | 0 arquivos invalidos/vazios | Falha pipeline |
| validate_configs | Todos JSON parse + campos obrigatorios presentes | Falha pipeline |
| smoke_cli | Comando retorna codigo 0 e contem trecho esperado em STDOUT | Falha pipeline |
| sanitize (dry) | Sem nomes proibidos / docs vazias | Warning (elevar depois) |
| build (futuro) | Artefatos gerados sem erro | Falha pipeline |

Evolucao: transformar warning de sanitize em falha apos estabilizacao.

---
## 6. Metricas de Observabilidade (Propostas)
| Metrica | Origem | Objetivo |
|---------|--------|----------|
| docs_invalid_count | check_docs | Rumo a zero | 
| config_errors | validate_configs | Detectar regressao config |
| smoke_cli_duration_ms | smoke_cli | Monitor tempo de resposta |
| sanitize_warnings | sanitize_project (dry) | Reducao continua |
| build_size_bytes | build pipeline | Estabilidade / diffs inesperados |

---
## 7. Design de Scripts (Padroes Recomendados)
1. Dry-run por padrao para scripts destrutivos.
2. Flag `--json` para integracao CI.
3. Codigo de saida padronizado:
	 - 0 sucesso
	 - 1 falha de validacao
	 - 2 erro interno/execucao
4. Limitar saida humana (modo texto) e detalhar em JSON quando necessario.
5. Manter help (`-h/--help`) claro e com exemplos minimos.

---
## 8. Roadmap Evolutivo (Macro)
| Fase | Conteudo | Resultado Esperado |
|------|----------|--------------------|
| Fase 1 | check_docs, validate_configs, smoke_cli | Baseline qualidade minima |
| Fase 2 | sanitize integrado no CI, smoke_db, smoke_gui | Confianca ampliada |
| Fase 3 | Testes unitarios criticos (core, armazenamento) | Cobertura inicial |
| Fase 4 | Metricas + upload artefatos build | Observabilidade basica |
| Fase 5 | Hardening (coverage gates, mutation tests) | Qualidade robusta |
| Fase 6 | Otimizacoes performance automatizadas | Performance monitorada |

---
## 9. Checklist Pre-Tag Baseline (Inicial)
| Item | Status | Observacao |
|------|--------|------------|
| Scripts core implementados | Parcial | Falta check_docs / validate_configs |
| Smoke CLI | Pendente | Implementar teste simples |
| Indice docs atualizado | OK | Atualizado 2025-09-12 |
| Limpeza/Organizacao (sanitize) | OK (manual) | Rodar dry-run no pipeline |
| Plano de gates documentado | OK | Este documento |
| Configs validadas | Pendente | Aguardando script |

---
## 10. Riscos & Mitigacoes
| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Falta de testes unitarios | Regressoes silenciosas | Priorizar Fase 3 pos baseline |
| Aumento de complexidade scripts | Manutencao dificil | Padronizar estilo + centralizar utilidades |
| Divergencia entre docs e pipeline real | Confusao de estado | Regeneracao periodica + revisao mensal |
| Volumes de logs nao tratados | Espaco em disco | Politicas de retencao ja implementadas |
| Backups excessivos | Espaco e lentidao | Retencao configuravel em cleanup_repository |

---
## 11. Estrutura de Diretorios Relacionada
| Diretorio | Proposito |
|-----------|-----------|
| `launchers/` | Scripts e relatorios de alto nivel / blueprint |
| `scripts/` | (Em formacao) utilidades de validacao | 
| `scripts_manutencao/` | Scripts legados / manutencao especifica |
| `data/historico_backups/` | Backups versionados do SQLite |
| `build/` | Entradas para processo de build futuro |

---
## 12. Proximas Acoes Imediatas
1. Implementar `scripts/check_docs.py`.
2. Implementar `scripts/validate_configs.py`.
3. Adicionar teste smoke CLI.
4. Consolidar checklist Baseline Tag.
5. Ajustar pipeline futuro (GitHub Actions / outro) com estagios iniciais.

---
## 13. Convencoes de Codigo para Scripts de Qualidade
| Convencao | Justificativa |
|-----------|--------------|
| `if __name__ == "__main__":` com `SystemExit(main())` | Codigos de saida explicitos |
| Uso de `argparse` | Interface consistente |
| Flag `--json` | Integracao CI agnostica |
| Sem dependencias externas (fase 1) | Simplicidade / bootstrap rapido |
| Mensagens curtas no modo texto | Leitura humana em logs |

---
## 14. Evolucao Planejada de Testes
| Etapa | Conteudo | Ferramenta |
|-------|----------|-----------|
| Smoke | CLI help / DB open | Script custom |
| Unit Core | Funcoes criticas de `core/*` | pytest (futuro) |
| Unit DB | Operacoes CRUD minimas | pytest |
| Integracao | Fluxo ingestao → cache → busca | pytest + fixtures |
| Performance | Cenario dataset medio (tempo/memoria) | harness custom |

---
## 15. Indicadores de Maturidade (Score Heuristico)
| Nivel | Caracteristicas |
|-------|-----------------|
| 1 (Atual) | Scripts de limpeza e saneamento basicos + docs consolidadas |
| 2 | Gates de docs, configs e smoke CLI ativos |
| 3 | Testes unitarios iniciais + sanitize como gate hard |
| 4 | Cobertura monitorada + build distribuivel verificavel |
| 5 | Performance monitorada + artefatos assinados |
| 6 | Automacao avancada (mutacao, seguranca, analise estatica) |

---
## 16. Referencias Relacionadas
| Documento | Contexto |
|-----------|---------|
| `launchers/README_BUILD_AUTOMATIZADO.md` | Pipeline proposto |
| `launchers/README_DOCS.md` | Governanca documental |
| `launchers/STATUS_BUILD_v3.10.md` | Estado versao atual |
| `launchers/RELATORIO_TESTES_FINAL.md` | Estrategia de testes |
| `launchers/ESTRUTURA_FINAL_ORGANIZADA.md` | Navegacao rapida |
| `sanitize_project.py` | Auditoria e saneamento |
| `launchers/cleanup_repository.py` | Limpeza ampla |

---
## 17. Notas Finais
Este documento deve ser revisto a cada ciclo de versao ou ao introduzir novos
gates. Alteracoes estruturais no pipeline precisam atualizar simultaneamente:
1. Esta visao integrada
2. Indice consolidado
3. READMEs especificos (build / docs)

Versao inicial: 2025-09-12

