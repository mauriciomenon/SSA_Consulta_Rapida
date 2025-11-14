# Plano de Limpeza, Retencao e Higiene Operacional

Este plano define a estrategia padronizada para manter o repositorio **SSA_Consulta_Rapida** enxuto, integro e previsivel, reduzindo entropia operacional e prevenindo crescimento descontrolado de artefatos temporarios.

---
## 1. Objetivos
| Objetivo | Motivacao | Metrica Indicativa |
|----------|-----------|--------------------|
| Reduzir lixo tecnico | Evitar poluicao de commits / diffs | No diretorios `__pycache__` apos cleanup = 0 |
| Controlar crescimento de backups | Manter espaco previsivel | No backups > limite | 
| Garantir reprodutibilidade | Evitar dependencia de arquivos temporarios | Build limpa executa sem erros |
| Acelerar inspecao | Menos ruido em buscas globais | Tempo medio grep reduzido |
| Preparar baseline confiavel | Tag segura exige higienizacao | Baseline sem artefatos obsoletos |

---
## 2. Escopo
| Categoria | Incluido | Exemplos | Exclusoes |
|-----------|----------|----------|-----------|
| Cache Python | Sim | `__pycache__/` | Arquivos fonte |
| Build / Distribuicao | Sim | `build/`, `dist/` | Scripts de build versionados |
| Logs Antigos | Sim | `logs/*.log` | Logs < janela de retencao |
| Backups Antigos | Sim | `data/historico_backups/ssas.db.backup_*` | Ultimos N (config) |
| Temporarios | Sim | `tmp/`, `temp/`, `*.tmp` | Dados permanentes |
| Relatorios Gerados | Sim | `reports/*.csv|xlsx|txt` | Documentacao fonte |
| Exportacoes Usuario | Opcional | `exportacao/*.xlsx` | Ultimo export relevante (manual) |
| DB Principal | Nao remove | `data/ssas.db` | - |

---
## 3. Scripts Envolvidos
| Script | Finalidade | Intensidade |
|--------|-----------|-------------|
| `launchers/cleanup_emergency.py` | Remocao rapida focada (seguro) | Leve |
| `launchers/cleanup_repository.py` | Limpeza abrangente (grupos + retencao) | Completo |
| `launchers/cleanup_manual.py` | Selecao interativa e granular | Custom |
| `sanitize_project.py` | Auditoria de estrutura / docs / nomes | Preventivo |
| (Futuro) `retention_policy.py` | Aplicar politica unificada de retencao | Evolucao |

---
## 4. Decisao de Uso (Matriz)
| Situacao | Script Recomendado | Parametros |
|----------|--------------------|------------|
| Antes de criar baseline | `cleanup_repository.py` + `sanitize_project.py` | `--dry-run` depois `--apply` |
| Espaco em disco critico | `cleanup_emergency.py` | Padrao (dry-run -> aplicar) |
| Analise seletiva (so logs) | `cleanup_manual.py` | `--logs --days-logs 21` |
| Rotina semanal | `cleanup_repository.py` | `--apply` |
| Investigar lixo oculto | `sanitize_project.py` | `--dry-run` |

---
## 5. Politica de Retencao
| Artefato | Regra | Script Principal | Notas |
|----------|------|------------------|-------|
| Backups DB | Manter ultimos 5 (padrao) | `cleanup_repository.py` | Ajustavel via flag |
| Logs | Remover > 14 dias | `cleanup_manual.py` | Parametro `--days-logs` |
| Relatorios / reports | Remover sempre que obsoletos | `cleanup_repository.py` | Regeraveis |
| Cache Python | Sempre remover | Todos | Regenera automaticamente |
| Build/Dist | Remover antes de rebuild | `cleanup_repository.py` | Evita residuos antigos |
| Exportacoes | Manual (boa pratica: limpar apos uso) | - | Usuario decide |

---
## 6. Fluxo Recomendado Pre-Tag
```mermaid
digraph CLEAN_FLOW {
	A[Dry-run sanitize] --> B[Dry-run cleanup_repository]
	B --> C[Aplicar cleanup]
	C --> D[Verificar backups]
	D --> E[Rodar validacoes]
	E --> F[Baseline Tag]
}
```

---
## 7. Sequencia Operacional Padronizada
1. `python sanitize_project.py --dry-run`
2. `python launchers/cleanup_repository.py --dry-run`
3. Se OK: `python launchers/cleanup_repository.py --apply`
4. (Opcional) Ajuste seletivo: `python launchers/cleanup_manual.py --logs --days-logs 21 --apply`
5. Validar backups restantes (`ls -1 data/historico_backups | wc -l`)
6. Executar gates de qualidade (docs/configs/smoke)
7. Prosseguir para baseline/tag

---
## 8. Metricas de Higiene
| Metrica | Meta | Coleta |
|---------|------|--------|
| No diretorios `__pycache__` | 0 pos-limpeza | `find . -name __pycache__` |
| Backups retidos | <= limite configurado | `ls data/historico_backups` |
| Tamanho total reports | Tendencia decrescente | `du -sh reports/` |
| Tamanho build/ + dist/ | ~0 antes de rebuild | `du -sh build dist` |
| Tempo execucao cleanup completo | < 10s (medio) | Cronometrar |

---
## 9. Riscos & Mitigacoes
| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Remocao acidental de artefato util | Media | Sempre rodar dry-run antes |
| Backup insuficiente apos limpeza | Alta | Verificar contagem > 0 depois |
| Execucao em diretorio errado | Alta | Validar caminho root (ex: sentinel .git) |
| Logs uteis apagados cedo demais | Baixa | Ajustar `--days-logs` conforme necessidade |

---
## 10. Padroes de Implementacao (Scripts)
| Aspecto | Padrao |
|---------|--------|
| Dry-run | Default verdadeiro (sem `--apply`) |
| Saida JSON | Para integracao CI: suportar `--json` |
| Codigos de Saida | 0 sucesso / 1 warnings→erro se promovidos / 2 falha interna |
| Logging | Verbose somente se `--verbose` (futuro) |
| Interatividade | Permitida apenas via flags explicitas |

---
## 11. Integracao com Qualidade / Gates
Apos limpeza e sanitizacao, executar:
```
python scripts/check_docs.py --fail-on-issues
python scripts/validate_configs.py --fail-on-warn
python scripts/smoke_cli.py
```
Falhas bloqueiam baseline.

---
## 12. Roadmap Evolutivo
| Fase | Entrega | Valor |
|------|---------|-------|
| 1 | Padronizacao scripts (atual) | Base consistente |
| 2 | Script unificado `run_quality_gates.py` | Automacao sequencial |
| 3 | Workflow CI (GitHub Actions) | Regressao preventiva |
| 4 | `retention_policy.py` (consolidacao) | Centralizacao regras |
| 5 | Metricas automaticas (JSON artifact) | Observabilidade |
| 6 | Diff hygiene vs baseline anterior | Evolucao mensuravel |

---
## 13. Anexos (Comandos Uteis)
```bash
# Listar backups ordenados do mais recente
ls -1t data/historico_backups | head -n 10

# Ver total de espaco ocupado por backups
du -sh data/historico_backups

# Encontrar todos os __pycache__
find . -type d -name __pycache__

# Simular limpeza completa
python launchers/cleanup_repository.py --dry-run

# Limpeza seletiva de logs (>21 dias)
python launchers/cleanup_manual.py --logs --days-logs 21 --apply
```

---
## 14. TL;DR
1. Sempre dry-run antes de apagar.
2. Limpar + validar + gate → so entao baseline.
3. Conservar ultimos 5 backups.
4. Nao commitar artefatos regeneraveis.
5. Evoluir para automacao CI ASAP.

> Higiene consistente reduz custo cognitivo e acelera releases seguras.

