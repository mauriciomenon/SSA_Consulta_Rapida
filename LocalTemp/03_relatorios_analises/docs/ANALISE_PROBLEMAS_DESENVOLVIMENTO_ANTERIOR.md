# ANALISE DE PROBLEMAS DO DESENVOLVIMENTO ANTERIOR

Objetivo: registrar falhas recorrentes do ciclo de desenvolvimento anterior e acoes corretivas implementadas ou pendentes, evitando regressoes.

## 1. Sumario Executivo
As principais deficiencias identificadas concentraram-se em: acoplamento excessivo entre camadas, ausencia de padronizacao em nomes de arquivos, scripts de manutencao nao isolados e documentacao fragmentada. A atuacao atual focou em isolamento, padronizacao e consolidacao de documentacao.

## 2. Problemas Catalogados
| ID | Categoria | Descricao | Impacto | Status |
|----|-----------|-----------|---------|--------|
| P1 | Estrutura | Mistura de logica de GUI, banco e parsing no mesmo modulo | Dificulta manutencao | Mitigado parcialmente |
| P2 | Nomenclatura | Uso inconsistente de maiusculas/acento em nomes de arquivo | Quebra import / confunde | Corrigido (padronizacao ASCII snake_case) |
| P3 | Scripts | Execucao de scripts diretamente na raiz sem isolamento | Risco de estado sujo | Mitigado criando separacao manutencao vs dev |
| P4 | Banco | Falta de backup automatico antes de migracoes | Perda potencial de dados | Implementado mecanismo de backup em `data/historico_backups/` |
| P5 | Documentacao | Arquivos vazios / placeholders sem rotulo | Onboarding lento | Preenchidos e centralizacao em doc consolidada |
| P6 | Lint/Qualidade | Ruido excessivo de ferramenta sem foco | Desvia atencao | Politica “lint enxuto” definida |
| P7 | Cache | Estrategia de cache pouco clara | Performance irregular | Em revisao (ver `core/cache_manager.py`) |
| P8 | Config | Multiplos JSON sem descricao de campos | Erros de edicao manual | Necessario adicionar README por grupo (pendente) |
| P9 | Testes | Testes de GUI instaveis / poucos casos | Baixa confianca | Planejar harness minimo estavel (pendente) |

## 3. Raiz Causal (5 Whys Simplificado)
| Problema | 1o Por que? | 2o | 3o | Conclusao |
|----------|-------------|-----|-----|-----------|
| P1 | Pressa em entregar | Falta diretriz modular | Sem revisao arquitetural | Criar guia de limites de camada |
| P2 | Sem checklist nome | Nao existia convencao | Cultura “resolve depois” | Adotar verificacao pre-commit futura |
| P3 | Scripts rapidos viraram permanentes | Sem sandbox | Mistura responsabilidades | Padronizar pastas scripts_* |
| P5 | Criacao ad-hoc | Sem dono de documentacao | Sem auditoria | Definir “editor responsavel” |
| P9 | Foco em correcao manual | Sem harness | Nao priorizado | Criar pacote de smoke automatico |

## 4. Acoes Corretivas Implementadas
- Padronizacao de nomes (ASCII snake_case) reforcada nas novas criacoes.
- Backups automaticos de banco (multiplos snapshots com timestamp).
- Preenchimento de documentos criticos vazios (onboarding, larguras GUI, analise problemas).
- Politica de lint minimizada deixando apenas erros relevantes.
- Centralizacao de navegacao em `launchers/DOCUMENTACAO_CONSOLIDADA.md`.

## 5. Acoes Pendentes Prioritarias
| Acao | Beneficio | Prioridade |
|------|-----------|------------|
| README por subgrupo de JSON (config) | Evita edicao incorreta | Alta |
| Harness de smoke test (CLI + GUI basica) | Confianca em refactors | Alta |
| Verificacao automatica de nomes antes commit | Evita regressao P2 | Media |
| Script de auditoria de placeholders | Evita vazios futuros | Media |
| Documentar fluxo cache detalhado | Clareza performance | Media |

## 6. Metricas Recomendadas
- Tempo medio de execucao de import completo.
- Numero de arquivos .md vazios detectados no CI (alvo: 0).
- Numero de warnings criticos (alvo: reduzir a tendencia ou manter linear).
- Frequencia de backups criados vs execucoes de import.

## 7. Criterios de Encerramento (Definicao de “Problema Resolvido”)
| Problema | Criterio Objetivo |
|----------|-------------------|
| P1 | Nenhuma funcao mistura camadas (GUI chamando SQL direto). |
| P5 | Nenhum .md vazio em duas releases consecutivas. |
| P7 | Cache documentado com diagrama de fluxo. |
| P8 | Todos JSON criticos tem README ou bloco de comentarios explicativo. |
| P9 | Suite smoke com >= 5 cenarios basicos passando. |

## 8. Riscos se Nao Implementar Pendencias
- Reintroducao de nomes inconsistentes → confusao / regressao de imports.
- Crescimento de “docs” placeholder gera falsa sensacao de cobertura.
- Refactors arriscados por ausencia de testes base.
- Config editada incorretamente gerando erros silenciosos.

## 9. Proximos Passos Concretos (Sprint Sugerida)
1. Criar harness smoke (CLI lista + GUI abre + consulta simples).
2. Adicionar README em `config/` explicando cada JSON.
3. Script verificacao de placeholders vazios (falha se tamanho < N e nao marcado como placeholder intencional).
4. Documentar fluxo do cache e inserir link no consolidado.
5. Issue para padronizar commit hook (pre-commit) nomes.

## 10. Historico
Criado inicialmente para substituir arquivo vazio em 12/09/2025. Atualizar quando cada acao pendente for concluida.

