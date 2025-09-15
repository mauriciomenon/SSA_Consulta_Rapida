# Baseline Tag – Procedimento e Checklist

Este documento define o processo padronizado para gerar uma "Baseline Tag" de referência estável do projeto **SSA_Consulta_Rapida**. A baseline funciona como âncora de comparação (diff funcional, performance, estrutura) para evoluções futuras e rollback rápido.

---
## 1. Objetivo da Baseline
- Congelar um estado considerado minimamente confiável (scripts de higiene / validação / documentação completos).
- Registrar artefatos obrigatórios (versão curta/longa, snapshot de configs, integridade de banco local, conjunto de scripts utilitários).
- Servir como origem para medição de melhorias posteriores (tempo de load, tamanho do DB, nº de colunas, saúde de docs, etc.).

---
## 2. Critérios de Prontidão (Gate MUST PASS)
| Gate | Ferramenta / Arquivo | Comando (referência) | Critério | Ação em Falha |
|------|----------------------|----------------------|---------|---------------|
| Sanitização Estrutural | `sanitize_project.py` | `python sanitize_project.py --dry-run` | 0 erros críticos | Corrigir nomes/arquivos antes de prosseguir |
| Limpeza Repositório | `launchers/cleanup_repository.py` | `python launchers/cleanup_repository.py --dry-run` | Sem lixo acumulado relevante | Limpar artefatos e rerodar |
| Documentação | `scripts/check_docs.py` | `python scripts/check_docs.py --fail-on-issues` | Exit 0 | Preencher/ajustar docs |
| Configs JSON | `scripts/validate_configs.py` | `python scripts/validate_configs.py --fail-on-warn` | Exit 0 | Corrigir estrutura/config |
| Smoke CLI | `scripts/smoke_cli.py` | `python scripts/smoke_cli.py` | Exit 0 | Ajustar entrypoint/paths |
| Versão | `config/version.json` | (verificação manual) | version_short e long coerentes | Atualizar version.json |
| Banco / Backup | `data/ssas.db` + backups | (ls + tamanho) | DB existe e >= tamanho mínimo esperado | Regerar/importar dados |

---
## 3. Checklist Pré-Tag
Marcar todos como concluídos antes de criar a tag.

- [ ] ( ) Sanitização sem pendências críticas.
- [ ] ( ) Repositório limpo (sem `__pycache__`, `dist/`, `build/` residuais, logs antigos massivos).
- [ ] ( ) `scripts/check_docs.py` => Exit 0.
- [ ] ( ) `scripts/validate_configs.py --fail-on-warn` => Exit 0.
- [ ] ( ) `scripts/smoke_cli.py` => Exit 0.
- [ ] ( ) `version.json` revisado (sem texto obsoleto na descrição longa).
- [ ] ( ) `launchers/STATUS_FINAL.md` atualizado (se necessário).
- [ ] ( ) `launchers/RELATORIO_TESTES_FINAL.md` coerente com estado atual.
- [ ] ( ) Backups em `data/historico_backups/` têm retenção adequada (não exceder política definida).
- [ ] ( ) Tamanho do DB (anotar abaixo).
- [ ] ( ) Git working tree limpo (`git status` sem modificações não intencionais).

### Snapshot de Referência (preencher)
- Data/Hora: `____`
- Versão curta: `____`
- Tamanho DB (`du -h data/ssas.db`): `____`
- Nº colunas principais (após normalização): `____`
- Nº arquivos .md (total / não vazios): `____ / ____`
- Nº scripts utilitários (launchers + scripts root): `____`

---
## 4. Procedimento de Criação
1. Garantir branch principal atualizada:
   - `git checkout main`
   - `git pull --ff-only`
2. Executar gates localmente (exemplos abaixo em bloco de comandos).
3. Atualizar/confirmar métricas em `STATUS_FINAL.md` se algo mudou.
4. Commit final dos ajustes (se houver):
   - Mensagem sugerida: `chore: baseline preparation (docs+configs+sanity)`
5. Criar tag anotada:
   - Formato sugerido: `baseline-v3.10.0` (usar semântica ou sub-revisão ex: `.0`).
6. Assinar (opcional):
   - `git tag -s baseline-v3.10.0 -m "Baseline v3.10.0"`
7. Push tag:
   - `git push origin baseline-v3.10.0`
8. (Opcional) Criar release no GitHub apontando para a tag, anexar changelog e métricas snapshot.

---
## 5. Bloco de Comandos (Referência)
```bash
# 1. Higiene e sanity
python sanitize_project.py --dry-run
python launchers/cleanup_repository.py --dry-run

# 2. Validações
python scripts/check_docs.py --fail-on-issues
python scripts/validate_configs.py --fail-on-warn
python scripts/smoke_cli.py

# 3. Snapshot rápido
du -h data/ssas.db || ls -lh data/ssas.db
python - <<'PY'
import json, os, glob
with open('config/version.json','r',encoding='utf-8') as f:
    v=json.load(f)
print('Versão:', v.get('version_short'), '| Desc len:', len(v.get('version_long',''))) 
print('MD files:', len(glob.glob('**/*.md', recursive=True)))
PY

# 4. Tag (após commit final)
git tag -a baseline-v3.10.0 -m "Baseline v3.10.0"
git push origin baseline-v3.10.0
```

---
## 6. Pós-Tag (Opcional mas Recomendado)
| Ação | Objetivo |
|------|----------|
| Criar release GitHub | Facilitar download + notas versão |
| Exportar relatório consolidado PDF | Artefato imutável para auditoria |
| Registrar métricas de performance inicial | Base para otimizações futuras |
| Abrir issues de evolução a partir dos gaps mapeados | Planejamento incremental |

---
## 7. Estratégia de Evolução de Baselines
- Criar novas baselines apenas quando: mudança estrutural relevante, salto de performance, refatoração ampla ou inclusão de grande bloco funcional.
- Manter histórico limpo: no máximo 1 baseline por versão menor (ex: v3.10.x) salvo se houver pivô arquitetural.
- Vincular sempre a um changelog sintetizado.

---
## 8. Critérios de Rejeição (Não Baselinear se...)
- Existem docs vazias ou placeholders detectados.
- `validate_configs.py` reporta aviso crítico promovido a erro.
- Smoke CLI falha ou mais de um fallback necessário.
- Banco ausente ou corrompido.
- Versionamento inconsistente (ex: código menciona v3.11 e config v3.10).

---
## 9. Futuras Automação / Roadmap
| Fase | Automação | Descrição |
|------|-----------|-----------|
| 1 | (Atual) Scripts manuais | Execução local dos gates |
| 2 | CI Pipeline | Workflow GitHub Actions roda sanitize + validate + smoke |
| 3 | Artifact Snapshot | Upload automático de métricas e artefatos (DB checksum, contagens) |
| 4 | Diff Analyzer | Script compara baseline anterior e gera delta estruturado |

---
## 10. Resumo Rápido (TL;DR)
1. Rodar hygiene + validações.
2. Confirmar versão / docs / configs / DB.
3. Atualizar STATUS_FINAL se necessário.
4. Commit final e criar tag `baseline-vX.Y.Z`.
5. Publicar release (opcional) e registrar métricas.

> Esta baseline é um compromisso: só crie quando o estado estiver verdadeiramente estável.
