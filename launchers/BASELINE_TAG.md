# Baseline Tag – Procedimento e Checklist

Este documento define o processo padronizado para gerar uma "Baseline Tag" de referencia estavel do projeto **SSA_Consulta_Rapida**. A baseline funciona como ancora de comparacao (diff funcional, performance, estrutura) para evolucoes futuras e rollback rapido.

---
## 1. Objetivo da Baseline
- Congelar um estado considerado minimamente confiavel (scripts de higiene / validacao / documentacao completos).
- Registrar artefatos obrigatorios (versao curta/longa, snapshot de configs, integridade de banco local, conjunto de scripts utilitarios).
- Servir como origem para medicao de melhorias posteriores (tempo de load, tamanho do DB, no de colunas, saude de docs, etc.).

---
## 2. Criterios de Prontidao (Gate MUST PASS)
| Gate | Ferramenta / Arquivo | Comando (referencia) | Criterio | Acao em Falha |
|------|----------------------|----------------------|---------|---------------|
| Sanitizacao Estrutural | `sanitize_project.py` | `python sanitize_project.py --dry-run` | 0 erros criticos | Corrigir nomes/arquivos antes de prosseguir |
| Limpeza Repositorio | `launchers/cleanup_repository.py` | `python launchers/cleanup_repository.py --dry-run` | Sem lixo acumulado relevante | Limpar artefatos e rerodar |
| Documentacao | `scripts/check_docs.py` | `python scripts/check_docs.py --fail-on-issues` | Exit 0 | Preencher/ajustar docs |
| Configs JSON | `scripts/validate_configs.py` | `python scripts/validate_configs.py --fail-on-warn` | Exit 0 | Corrigir estrutura/config |
| Smoke CLI | `scripts/smoke_cli.py` | `python scripts/smoke_cli.py` | Exit 0 | Ajustar entrypoint/paths |
| Versao | `config/version.json` | (verificacao manual) | version_short e long coerentes | Atualizar version.json |
| Banco / Backup | `data/ssas.db` + backups | (ls + tamanho) | DB existe e >= tamanho minimo esperado | Regerar/importar dados |

---
## 3. Checklist Pre-Tag
Marcar todos como concluidos antes de criar a tag.

- [ ] ( ) Sanitizacao sem pendencias criticas.
- [ ] ( ) Repositorio limpo (sem `__pycache__`, `dist/`, `build/` residuais, logs antigos massivos).
- [ ] ( ) `scripts/check_docs.py` => Exit 0.
- [ ] ( ) `scripts/validate_configs.py --fail-on-warn` => Exit 0.
- [ ] ( ) `scripts/smoke_cli.py` => Exit 0.
- [ ] ( ) `version.json` revisado (sem texto obsoleto na descricao longa).
- [ ] ( ) `launchers/STATUS_FINAL.md` atualizado (se necessario).
- [ ] ( ) `launchers/RELATORIO_TESTES_FINAL.md` coerente com estado atual.
- [ ] ( ) Backups em `data/historico_backups/` tem retencao adequada (nao exceder politica definida).
- [ ] ( ) Tamanho do DB (anotar abaixo).
- [ ] ( ) Git working tree limpo (`git status` sem modificacoes nao intencionais).

### Snapshot de Referencia (preencher)
- Data/Hora: `____`
- Versao curta: `____`
- Tamanho DB (`du -h data/ssas.db`): `____`
- No colunas principais (apos normalizacao): `____`
- No arquivos .md (total / nao vazios): `____ / ____`
- No scripts utilitarios (launchers + scripts root): `____`

---
## 4. Procedimento de Criacao
1. Garantir branch principal atualizada:
   - `git checkout main`
   - `git pull --ff-only`
2. Executar gates localmente (exemplos abaixo em bloco de comandos).
3. Atualizar/confirmar metricas em `STATUS_FINAL.md` se algo mudou.
4. Commit final dos ajustes (se houver):
   - Mensagem sugerida: `chore: baseline preparation (docs+configs+sanity)`
5. Criar tag anotada:
   - Formato sugerido: `baseline-v3.10.0` (usar semantica ou sub-revisao ex: `.0`).
6. Assinar (opcional):
   - `git tag -s baseline-v3.10.0 -m "Baseline v3.10.0"`
7. Push tag:
   - `git push origin baseline-v3.10.0`
8. (Opcional) Criar release no GitHub apontando para a tag, anexar changelog e metricas snapshot.

---
## 5. Bloco de Comandos (Referencia)
```bash
# 1. Higiene e sanity
python sanitize_project.py --dry-run
python launchers/cleanup_repository.py --dry-run

# 2. Validacoes
python scripts/check_docs.py --fail-on-issues
python scripts/validate_configs.py --fail-on-warn
python scripts/smoke_cli.py

# 3. Snapshot rapido
du -h data/ssas.db || ls -lh data/ssas.db
python - <<'PY'
import json, os, glob
with open('config/version.json','r',encoding='utf-8') as f:
    v=json.load(f)
print('Versao:', v.get('version_short'), '| Desc len:', len(v.get('version_long',''))) 
print('MD files:', len(glob.glob('**/*.md', recursive=True)))
PY

# 4. Tag (apos commit final)
git tag -a baseline-v3.10.0 -m "Baseline v3.10.0"
git push origin baseline-v3.10.0
```

---
## 6. Pos-Tag (Opcional mas Recomendado)
| Acao | Objetivo |
|------|----------|
| Criar release GitHub | Facilitar download + notas versao |
| Exportar relatorio consolidado PDF | Artefato imutavel para auditoria |
| Registrar metricas de performance inicial | Base para otimizacoes futuras |
| Abrir issues de evolucao a partir dos gaps mapeados | Planejamento incremental |

---
## 7. Estrategia de Evolucao de Baselines
- Criar novas baselines apenas quando: mudanca estrutural relevante, salto de performance, refatoracao ampla ou inclusao de grande bloco funcional.
- Manter historico limpo: no maximo 1 baseline por versao menor (ex: v3.10.x) salvo se houver pivo arquitetural.
- Vincular sempre a um changelog sintetizado.

---
## 8. Criterios de Rejeicao (Nao Baselinear se...)
- Existem docs vazias ou placeholders detectados.
- `validate_configs.py` reporta aviso critico promovido a erro.
- Smoke CLI falha ou mais de um fallback necessario.
- Banco ausente ou corrompido.
- Versionamento inconsistente (ex: codigo menciona v3.11 e config v3.10).

---
## 9. Futuras Automacao / Roadmap
| Fase | Automacao | Descricao |
|------|-----------|-----------|
| 1 | (Atual) Scripts manuais | Execucao local dos gates |
| 2 | CI Pipeline | Workflow GitHub Actions roda sanitize + validate + smoke |
| 3 | Artifact Snapshot | Upload automatico de metricas e artefatos (DB checksum, contagens) |
| 4 | Diff Analyzer | Script compara baseline anterior e gera delta estruturado |

---
## 10. Resumo Rapido (TL;DR)
1. Rodar hygiene + validacoes.
2. Confirmar versao / docs / configs / DB.
3. Atualizar STATUS_FINAL se necessario.
4. Commit final e criar tag `baseline-vX.Y.Z`.
5. Publicar release (opcional) e registrar metricas.

> Esta baseline e um compromisso: so crie quando o estado estiver verdadeiramente estavel.
