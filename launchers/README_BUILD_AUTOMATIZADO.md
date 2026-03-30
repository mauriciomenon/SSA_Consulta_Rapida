# README – PIPELINE DE BUILD AUTOMATIZADO (RASCUNHO)

Este documento descreve como estruturar uma pipeline de build/test/validacao minima para o projeto visando reprodutibilidade e deteccao precoce de problemas.

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
| `build/build_all.py` | Presente | Auxiliar build (ajustar logs) |
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
uv run --python 3.13 build/build_all.py  # se aplicavel
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

