# README – MANUTENCAO DA DOCUMENTACAO

Guia pratico para criar, atualizar e auditar a documentacao do projeto de forma consistente e sustentavel.

## 1. Principios
- Documentacao deve acelerar decisao tecnica, nao duplicar codigo.
- Evitar redundancia: preferir linkar em vez de copiar blocos.
- Todo novo arquivo precisa responder: objetivo, escopo, publico-alvo.
- Arquivo nunca fica vazio: usar placeholder claro `TODO:` se incompleto.

## 2. Tipos de Documentos
| Tipo | Prefixo Sugerido | Exemplo | Caracteristica |
|------|------------------|---------|----------------|
| Guia (procedural) | `GUIA_` | `GUIA_MODO_OPTIMIZED.md` | Passo a passo | 
| Referencia (estrutura) | (sem) ou `REFERENCIA_` | `ESTRUTURA_PROJETO.md` | Define contratos / mapas |
| Relatorio (snapshot) | `RELATORIO_` | `RELATORIO_TESTES_FINAL.md` | Estado em ponto no tempo |
| Historico | `HISTORICO_` | `HISTORICO_RELEASES.md` | Linha do tempo |
| Checklist | `CHECKLIST_` | `CHECKLIST_PENDENCIAS_FUTURAS.md` | Controle de tarefas |
| Analise | `ANALISE_` | `ANALISE_PROBLEMAS_DESENVOLVIMENTO_ANTERIOR.md` | Profundidade tecnica |

## 3. Estrutura Minima Recomendada
```markdown
# TITULO
Objetivo curto (1–2 linhas)
## 1. Contexto / Objetivo
## 2. Escopo (O que cobre / nao cobre)
## 3. Conteudo principal
## 4. Referencias / Links
```

## 4. Regras de Criacao / Atualizacao
1. Verificar se assunto cabe como secao em documento existente.
2. Usar nomes ASCII snake_case (ou padrao prefixado conforme tipo).
3. Registrar mudancas significativas em changelog / historico relevante.
4. Manter tabelas alinhadas (legibilidade > compactacao exagerada).
5. Nunca duplicar tabela identica (linkar arquivo original).

## 5. Auditoria de Qualidade (Manual / Script Futuro)
Checklist rapido:
- [ ] Arquivo tem titulo H1.
- [ ] Possui objetivo claro.
- [ ] Nao esta vazio / so com titulo.
- [ ] Nao duplica outro doc (sem motivo declarado).
- [ ] Links relativos funcionam.
- [ ] Marcadores TODO nao superam limite (<= 5 por arquivo).

## 6. Ferramentas / Scripts Planejados
| Script | Objetivo | Status |
|--------|----------|--------|
| `scripts/check_docs.py` | Detectar docs vazios / apenas titulo / excesso de TODO | Pendente |
| `scripts/validate_configs.py` | Validar JSON em `config/` | Pendente |
| Agregador indice | Atualizar indice consolidado automaticamente | Adiado |

## 7. Padroes de Links
- Sempre relativos (ex.: `../docs/ARQUIVO.md`).
- Evitar URLs externas quebraveis; quando necessario, incluir titulo da referencia.

## 8. Politica de Placeholders
- Usar `TODO:` no inicio da linha.
- Secao pendente deve indicar o que falta (ex.: `TODO: adicionar metricas de performance`).
- Placeholders nao podem persistir alem de 2 ciclos de revisao.

## 9. Processo de Revisao
1. Autor abre PR com nova doc ou alteracao.
2. Revisor verifica checklist de auditoria.
3. Merge somente com objetivo claro + ausencia de secoes vazias.
4. Atualizar indice consolidado quando adicionar documento de navegacao ou referencia global.

## 10. Metricas Futuras (Sugestao)
| Metrica | Meta |
|---------|------|
| % docs sem TODO pendente critico | > 90% |
| Tempo medio para localizar doc (dev novo) | < 2 min |
| Docs vazios na branch principal | 0 |

## 11. Anti-Padroes a Evitar
- Criar `*_FINAL.md` em serie (usar historico versionado).
- Colar grandes blocos de codigo sem explicar proposito.
- Esconder decisoes em comentarios de commit sem refletir em docs.
- Manter docs que nao sao mais fonte de verdade (marcar como deprecado ou remover).

## 12. Deprecacao de Documentos
Criterios para deprecar:
- Conteudo substituido integralmente por outro arquivo.
- Informacao historica movida para `HISTORICO_*`.
- Documento nao consultado / atualizado em > 90 dias (avaliar relevancia).

## 13. Proximos Passos
1. Implementar `scripts/check_docs.py`.
2. Definir limites de TODO por arquivo no script.
3. Automatizar atualizacao parcial do indice.

---
Atualizado em: 2025-09-12


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

