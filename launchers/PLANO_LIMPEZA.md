# Plano de Limpeza, Retenção e Higiene Operacional

Este plano define a estratégia padronizada para manter o repositório **SSA_Consulta_Rapida** enxuto, íntegro e previsível, reduzindo entropia operacional e prevenindo crescimento descontrolado de artefatos temporários.

---
## 1. Objetivos
| Objetivo | Motivação | Métrica Indicativa |
|----------|-----------|--------------------|
| Reduzir lixo técnico | Evitar poluição de commits / diffs | Nº diretórios `__pycache__` após cleanup = 0 |
| Controlar crescimento de backups | Manter espaço previsível | Nº backups > limite | 
| Garantir reprodutibilidade | Evitar dependência de arquivos temporários | Build limpa executa sem erros |
| Acelerar inspeção | Menos ruído em buscas globais | Tempo médio grep reduzido |
| Preparar baseline confiável | Tag segura exige higienização | Baseline sem artefatos obsoletos |

---
## 2. Escopo
| Categoria | Incluído | Exemplos | Exclusões |
|-----------|----------|----------|-----------|
| Cache Python | Sim | `__pycache__/` | Arquivos fonte |
| Build / Distribuição | Sim | `build/`, `dist/` | Scripts de build versionados |
| Logs Antigos | Sim | `logs/*.log` | Logs < janela de retenção |
| Backups Antigos | Sim | `data/historico_backups/ssas.db.backup_*` | Últimos N (config) |
| Temporários | Sim | `tmp/`, `temp/`, `*.tmp` | Dados permanentes |
| Relatórios Gerados | Sim | `reports/*.csv|xlsx|txt` | Documentação fonte |
| Exportações Usuário | Opcional | `exportacao/*.xlsx` | Último export relevante (manual) |
| DB Principal | Não remove | `data/ssas.db` | - |

---
## 3. Scripts Envolvidos
| Script | Finalidade | Intensidade |
|--------|-----------|-------------|
| `launchers/cleanup_emergency.py` | Remoção rápida focada (seguro) | Leve |
| `launchers/cleanup_repository.py` | Limpeza abrangente (grupos + retenção) | Completo |
| `launchers/cleanup_manual.py` | Seleção interativa e granular | Custom |
| `sanitize_project.py` | Auditoria de estrutura / docs / nomes | Preventivo |
| (Futuro) `retention_policy.py` | Aplicar política unificada de retenção | Evolução |

---
## 4. Decisão de Uso (Matriz)
| Situação | Script Recomendado | Parâmetros |
|----------|--------------------|------------|
| Antes de criar baseline | `cleanup_repository.py` + `sanitize_project.py` | `--dry-run` depois `--apply` |
| Espaço em disco crítico | `cleanup_emergency.py` | Padrão (dry-run -> aplicar) |
| Análise seletiva (só logs) | `cleanup_manual.py` | `--logs --days-logs 21` |
| Rotina semanal | `cleanup_repository.py` | `--apply` |
| Investigar lixo oculto | `sanitize_project.py` | `--dry-run` |

---
## 5. Política de Retenção
| Artefato | Regra | Script Principal | Notas |
|----------|------|------------------|-------|
| Backups DB | Manter últimos 5 (padrão) | `cleanup_repository.py` | Ajustável via flag |
| Logs | Remover > 14 dias | `cleanup_manual.py` | Parâmetro `--days-logs` |
| Relatórios / reports | Remover sempre que obsoletos | `cleanup_repository.py` | Regeráveis |
| Cache Python | Sempre remover | Todos | Regenera automaticamente |
| Build/Dist | Remover antes de rebuild | `cleanup_repository.py` | Evita resíduos antigos |
| Exportações | Manual (boa prática: limpar após uso) | - | Usuário decide |

---
## 6. Fluxo Recomendado Pré-Tag
```mermaid
digraph CLEAN_FLOW {
	A[Dry-run sanitize] --> B[Dry-run cleanup_repository]
	B --> C[Aplicar cleanup]
	C --> D[Verificar backups]
	D --> E[Rodar validações]
	E --> F[Baseline Tag]
}
```

---
## 7. Sequência Operacional Padronizada
1. `python sanitize_project.py --dry-run`
2. `python launchers/cleanup_repository.py --dry-run`
3. Se OK: `python launchers/cleanup_repository.py --apply`
4. (Opcional) Ajuste seletivo: `python launchers/cleanup_manual.py --logs --days-logs 21 --apply`
5. Validar backups restantes (`ls -1 data/historico_backups | wc -l`)
6. Executar gates de qualidade (docs/configs/smoke)
7. Prosseguir para baseline/tag

---
## 8. Métricas de Higiene
| Métrica | Meta | Coleta |
|---------|------|--------|
| Nº diretórios `__pycache__` | 0 pós-limpeza | `find . -name __pycache__` |
| Backups retidos | <= limite configurado | `ls data/historico_backups` |
| Tamanho total reports | Tendência decrescente | `du -sh reports/` |
| Tamanho build/ + dist/ | ~0 antes de rebuild | `du -sh build dist` |
| Tempo execução cleanup completo | < 10s (médio) | Cronometrar |

---
## 9. Riscos & Mitigações
| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Remoção acidental de artefato útil | Média | Sempre rodar dry-run antes |
| Backup insuficiente após limpeza | Alta | Verificar contagem > 0 depois |
| Execução em diretório errado | Alta | Validar caminho root (ex: sentinel .git) |
| Logs úteis apagados cedo demais | Baixa | Ajustar `--days-logs` conforme necessidade |

---
## 10. Padrões de Implementação (Scripts)
| Aspecto | Padrão |
|---------|--------|
| Dry-run | Default verdadeiro (sem `--apply`) |
| Saída JSON | Para integração CI: suportar `--json` |
| Códigos de Saída | 0 sucesso / 1 warnings→erro se promovidos / 2 falha interna |
| Logging | Verbose somente se `--verbose` (futuro) |
| Interatividade | Permitida apenas via flags explícitas |

---
## 11. Integração com Qualidade / Gates
Após limpeza e sanitização, executar:
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
| 1 | Padronização scripts (atual) | Base consistente |
| 2 | Script unificado `run_quality_gates.py` | Automação sequencial |
| 3 | Workflow CI (GitHub Actions) | Regressão preventiva |
| 4 | `retention_policy.py` (consolidação) | Centralização regras |
| 5 | Métricas automáticas (JSON artifact) | Observabilidade |
| 6 | Diff hygiene vs baseline anterior | Evolução mensurável |

---
## 13. Anexos (Comandos Úteis)
```bash
# Listar backups ordenados do mais recente
ls -1t data/historico_backups | head -n 10

# Ver total de espaço ocupado por backups
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
2. Limpar + validar + gate → só então baseline.
3. Conservar últimos 5 backups.
4. Não commitar artefatos regeneráveis.
5. Evoluir para automação CI ASAP.

> Higiene consistente reduz custo cognitivo e acelera releases seguras.

