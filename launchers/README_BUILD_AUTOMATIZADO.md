# README – PIPELINE DE BUILD AUTOMATIZADO (RASCUNHO)

## CURRENT TRUTH 2026-08-09

- Branch fonte local: `dev`.
- Release estavel ativa: `v4.47`; tag anterior: `v4.46`.
- `origin` e GitLab, `bitbucket` e Bitbucket e `gh` e GitHub; `dev` esta publicado nos dois primeiros.
- O HTTP 403 por conta suspensa afeta somente `gh`; fetch, pull e push em `origin`/`bitbucket` permanecem operacionais.
- Artefatos antigos versionados sao ruido historico/local e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
- Fluxo atual: validar, gerar artefatos novos, publicar `v4.47` em GitLab e espelhar tag no Bitbucket.
- Windows usa `release.ps1` em clone nativo; Debian/macOS usam `release.sh` em clones nativos dos respectivos hosts.
- Nao compartilhar checkout ou venv entre Windows e WSL/Linux; WSL fica restrito ao CodeRabbit em clone Linux proprio.

## HISTORICAL SNAPSHOT 2026-05-04 01h14

- Branch alvo operacional: `dev` e `main` sincronizados.
- Base minima sincronizada: `4705c2e5722c4f3a5266ac02a5d15a1928d5a223 2026-05-04T02:07:12-03:00 Merge PR #59: sync docs and required CI`; usar este commit ou sucessor sincronizado em `main`/`dev`.
- PR #58 e PR #59: merged.
- PR #56 e PR #57: merged anteriormente; o estado ativo agora e pos-merge do PR #59.
- `main`, `dev`, `origin/main` e `origin/dev` apontam para o mesmo HEAD.
- Artefatos antigos anteriores a base minima `4705c2e5722c4f3a5266ac02a5d15a1928d5a223` seguem stale e nao devem ser usados para publicacao final.
- Fonte unica de backends/pacotes: `dev_env/build/release_targets.json`.
- Orquestradores ativos:
  - Windows AMD64: `dev_env/build/release_windows.ps1`.
  - Debian AMD64: `dev_env/build/release_debian.sh`.
  - Orquestrador local Windows+WSL: `dev_env/build/release_local.ps1`.
- Checks GitHub do merge PR #58:
  - Pass: `minimal-ci`, `Secret Scan`, `codeql-security-scan`, `opencode-pr-review`, `semgrep-cloud-platform/scan`, `security/snyk`, `GitGuardian`, `Socket`, `CodeFactor`, `DeepScan`, `CodeQL`.
  - Externos/advisory: `code/snyk (mauriciomenon)` falhou por limite `Code test limit reached`; `DeepSource: Python` falhou no dashboard externo.
- Protecao de codigo:
  - Nuitka continua backend preferencial para release protegido.
  - PyInstaller tem protecao parcial.
  - PyOxidizer so e aceitavel como protegido quando o pacote nao expuser `.py`/`.pyc` do app.
- Proximo passo operacional historico: rebuildar Windows AMD64 e Debian AMD64 a partir daquele HEAD, validar artefatos e atualizar a release somente com pacotes novos.

## 1. Objetivos
| Objetivo | Beneficio |
|----------|-----------|
| Reproduzir ambiente limpo | Evitar “funciona na minha maquina” |
| Validar configs antes de rodar app | Falha cedo em JSON invalido |
| Executar smoke CLI/DB | Garantir funcionalidade basica |
| Prevenir docs vazios | Qualidade documental consistente |
| Publicar artefatos (opcional) | Distribuicao controlada |

## 2. Fases da Pipeline (Proposta)
| Ordem | Fase | Ferramentas | Saida Esperada |
|-------|------|------------|----------------|
| 1 | Setup Python | pyenv / cache CI | Ambiente pronto |
| 2 | Instalacao deps | uv pip | Pacotes instalados |
| 3 | Validacao configs | script `scripts/validate_configs.py` | OK ou falha |
| 4 | Lint rapido (opcional) | flake8/ruff configurado minimo | Relatorio limpo |
| 5 | Testes smoke | pytest -k smoke | Passando 100% |
| 6 | Testes unit core | pytest (subset) | Passando |
| 7 | Verificacao docs | `scripts/check_docs.py` | Sem vazios |
| 8 | Build artefato | script em `build/` | Wheel / dist |
| 9 | Publicacao (manual) | upload (PyPI interno?) | Artefato versionado |

## 3. Scripts Necessarios
| Script | Status | Funcao |
|--------|--------|--------|
| `scripts/validate_configs.py` | Pendente | Validar estrutura basica JSON |
| `scripts/check_docs.py` | Pendente | Garantir ausencia de docs vazios |
| `tests/test_smoke_cli.py` | Pendente | Verificar CLI basica |
| `launchers/build_all.py` | Presente | Compatibilidade legada para fluxo completo de build |
| `launchers/cleanup_emergency.py` | Feito | Limpeza emergencial (manual) |

## 4. Criterios de Falha (Gate)
- JSON invalido → falha imediata.
- Doc vazio ou so titulo → falha.
- Smoke CLI falhou → bloqueia build.
- Teste unit core critico falhou → bloqueia build.
- Ausencia de `config/version.json` ou divergencia com modulo (se aplicavel) → alerta (upgrade para falha futuramente).

## 5. Estrutura de Pastas Recomendada (CI)
```
ci/
	install.sh            # instala dependencias
	run_validation.sh     # roda validate_configs + check_docs
	run_tests.sh          # pytest smoke + unit core
	build_artifact.sh     # empacota (opcional)
```

## 6. Exemplo de Sequencia Local
```bash
uv run --python 3.13 scripts/validate_configs.py
uv run --python 3.13 scripts/check_docs.py
pytest -k smoke
pytest -k core
uv run --python 3.13 launchers/build_all.py  # se aplicavel
```

## 7. Metricas a Registrar
| Metrica | Descricao |
|---------|-----------|
| Tempo instalacao deps | Cronometrar uv pip install |
| Duracao smoke | Tempo dos testes rapidos |
| Duracao core unit | Tempo casos core |
| No docs auditados | Quantidade verificada |
| Tamanho artefato | Peso final wheel/dist |

## 8. Proximos Passos Imediatos
1. Implementar scripts pendentes (validate + check_docs).
2. Criar testes smoke + 2 unit core.
3. Integrar pipeline minima (GitHub Actions / outro) – opcional inicial.
4. Documentar versao e alinhar VERSION file / `config/version.json`.

## 9. Evolucao Futuras (Roadmap)
- Adicionar analise estatica de seguranca leve.
- Cache de dependencias no CI.
- Geracao automatica de changelog baseado em commits (convencional).
- Publicacao condicionada a tag.

## 10. Notas
Documento rascunho: atualizar conforme scripts forem entrando. Evitar inflar com detalhes que pertencem a READMEs especificos.

---
Atualizado em: 2025-09-12


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
