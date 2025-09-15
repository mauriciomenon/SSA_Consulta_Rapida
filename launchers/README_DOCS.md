# README – MANUTENÇÃO DA DOCUMENTAÇÃO

Guia prático para criar, atualizar e auditar a documentação do projeto de forma consistente e sustentável.

## 1. Princípios
- Documentação deve acelerar decisão técnica, não duplicar código.
- Evitar redundância: preferir linkar em vez de copiar blocos.
- Todo novo arquivo precisa responder: objetivo, escopo, público-alvo.
- Arquivo nunca fica vazio: usar placeholder claro `TODO:` se incompleto.

## 2. Tipos de Documentos
| Tipo | Prefixo Sugerido | Exemplo | Característica |
|------|------------------|---------|----------------|
| Guia (procedural) | `GUIA_` | `GUIA_MODO_OPTIMIZED.md` | Passo a passo | 
| Referência (estrutura) | (sem) ou `REFERENCIA_` | `ESTRUTURA_PROJETO.md` | Define contratos / mapas |
| Relatório (snapshot) | `RELATORIO_` | `RELATORIO_TESTES_FINAL.md` | Estado em ponto no tempo |
| Histórico | `HISTORICO_` | `HISTORICO_RELEASES.md` | Linha do tempo |
| Checklist | `CHECKLIST_` | `CHECKLIST_PENDENCIAS_FUTURAS.md` | Controle de tarefas |
| Análise | `ANALISE_` | `ANALISE_PROBLEMAS_DESENVOLVIMENTO_ANTERIOR.md` | Profundidade técnica |

## 3. Estrutura Mínima Recomendada
```markdown
# TÍTULO
Objetivo curto (1–2 linhas)
## 1. Contexto / Objetivo
## 2. Escopo (O que cobre / não cobre)
## 3. Conteúdo principal
## 4. Referências / Links
```

## 4. Regras de Criação / Atualização
1. Verificar se assunto cabe como seção em documento existente.
2. Usar nomes ASCII snake_case (ou padrão prefixado conforme tipo).
3. Registrar mudanças significativas em changelog / histórico relevante.
4. Manter tabelas alinhadas (legibilidade > compactação exagerada).
5. Nunca duplicar tabela idêntica (linkar arquivo original).

## 5. Auditoria de Qualidade (Manual / Script Futuro)
Checklist rápido:
- [ ] Arquivo tem título H1.
- [ ] Possui objetivo claro.
- [ ] Não está vazio / só com título.
- [ ] Não duplica outro doc (sem motivo declarado).
- [ ] Links relativos funcionam.
- [ ] Marcadores TODO não superam limite (<= 5 por arquivo).

## 6. Ferramentas / Scripts Planejados
| Script | Objetivo | Status |
|--------|----------|--------|
| `scripts/check_docs.py` | Detectar docs vazios / apenas título / excesso de TODO | Pendente |
| `scripts/validate_configs.py` | Validar JSON em `config/` | Pendente |
| Agregador índice | Atualizar índice consolidado automaticamente | Adiado |

## 7. Padrões de Links
- Sempre relativos (ex.: `../docs/ARQUIVO.md`).
- Evitar URLs externas quebráveis; quando necessário, incluir título da referência.

## 8. Política de Placeholders
- Usar `TODO:` no início da linha.
- Seção pendente deve indicar o que falta (ex.: `TODO: adicionar métricas de performance`).
- Placeholders não podem persistir além de 2 ciclos de revisão.

## 9. Processo de Revisão
1. Autor abre PR com nova doc ou alteração.
2. Revisor verifica checklist de auditoria.
3. Merge somente com objetivo claro + ausência de seções vazias.
4. Atualizar índice consolidado quando adicionar documento de navegação ou referência global.

## 10. Métricas Futuras (Sugestão)
| Métrica | Meta |
|---------|------|
| % docs sem TODO pendente crítico | > 90% |
| Tempo médio para localizar doc (dev novo) | < 2 min |
| Docs vazios na branch principal | 0 |

## 11. Anti-Padrões a Evitar
- Criar `*_FINAL.md` em série (usar histórico versionado).
- Colar grandes blocos de código sem explicar propósito.
- Esconder decisões em comentários de commit sem refletir em docs.
- Manter docs que não são mais fonte de verdade (marcar como deprecado ou remover).

## 12. Deprecação de Documentos
Critérios para deprecar:
- Conteúdo substituído integralmente por outro arquivo.
- Informação histórica movida para `HISTORICO_*`.
- Documento não consultado / atualizado em > 90 dias (avaliar relevância).

## 13. Próximos Passos
1. Implementar `scripts/check_docs.py`.
2. Definir limites de TODO por arquivo no script.
3. Automatizar atualização parcial do índice.

---
Atualizado em: 2025-09-12

