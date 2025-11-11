# ANÁLISE DE PROBLEMAS DO DESENVOLVIMENTO ANTERIOR

Objetivo: registrar falhas recorrentes do ciclo de desenvolvimento anterior e ações corretivas implementadas ou pendentes, evitando regressões.

## 1. Sumário Executivo
As principais deficiências identificadas concentraram-se em: acoplamento excessivo entre camadas, ausência de padronização em nomes de arquivos, scripts de manutenção não isolados e documentação fragmentada. A atuação atual focou em isolamento, padronização e consolidação de documentação.

## 2. Problemas Catalogados
| ID | Categoria | Descrição | Impacto | Status |
|----|-----------|-----------|---------|--------|
| P1 | Estrutura | Mistura de lógica de GUI, banco e parsing no mesmo módulo | Dificulta manutenção | Mitigado parcialmente |
| P2 | Nomenclatura | Uso inconsistente de maiúsculas/acento em nomes de arquivo | Quebra import / confunde | Corrigido (padronização ASCII snake_case) |
| P3 | Scripts | Execução de scripts diretamente na raiz sem isolamento | Risco de estado sujo | Mitigado criando separação manutenção vs dev |
| P4 | Banco | Falta de backup automático antes de migrações | Perda potencial de dados | Implementado mecanismo de backup em `data/historico_backups/` |
| P5 | Documentação | Arquivos vazios / placeholders sem rótulo | Onboarding lento | Preenchidos e centralização em doc consolidada |
| P6 | Lint/Qualidade | Ruído excessivo de ferramenta sem foco | Desvia atenção | Política “lint enxuto” definida |
| P7 | Cache | Estratégia de cache pouco clara | Performance irregular | Em revisão (ver `core/cache_manager.py`) |
| P8 | Config | Múltiplos JSON sem descrição de campos | Erros de edição manual | Necessário adicionar README por grupo (pendente) |
| P9 | Testes | Testes de GUI instáveis / poucos casos | Baixa confiança | Planejar harness mínimo estável (pendente) |

## 3. Raiz Causal (5 Whys Simplificado)
| Problema | 1º Por quê? | 2º | 3º | Conclusão |
|----------|-------------|-----|-----|-----------|
| P1 | Pressa em entregar | Falta diretriz modular | Sem revisão arquitetural | Criar guia de limites de camada |
| P2 | Sem checklist nome | Não existia convenção | Cultura “resolve depois” | Adotar verificação pré-commit futura |
| P3 | Scripts rápidos viraram permanentes | Sem sandbox | Mistura responsabilidades | Padronizar pastas scripts_* |
| P5 | Criação ad-hoc | Sem dono de documentação | Sem auditoria | Definir “editor responsável” |
| P9 | Foco em correção manual | Sem harness | Não priorizado | Criar pacote de smoke automático |

## 4. Ações Corretivas Implementadas
- Padronização de nomes (ASCII snake_case) reforçada nas novas criações.
- Backups automáticos de banco (múltiplos snapshots com timestamp).
- Preenchimento de documentos críticos vazios (onboarding, larguras GUI, análise problemas).
- Política de lint minimizada deixando apenas erros relevantes.
- Centralização de navegação em `launchers/DOCUMENTACAO_CONSOLIDADA.md`.

## 5. Ações Pendentes Prioritárias
| Ação | Benefício | Prioridade |
|------|-----------|------------|
| README por subgrupo de JSON (config) | Evita edição incorreta | Alta |
| Harness de smoke test (CLI + GUI básica) | Confiança em refactors | Alta |
| Verificação automática de nomes antes commit | Evita regressão P2 | Média |
| Script de auditoria de placeholders | Evita vazios futuros | Média |
| Documentar fluxo cache detalhado | Clareza performance | Média |

## 6. Métricas Recomendadas
- Tempo médio de execução de import completo.
- Número de arquivos .md vazios detectados no CI (alvo: 0).
- Número de warnings críticos (alvo: reduzir a tendência ou manter linear).
- Frequência de backups criados vs execuções de import.

## 7. Critérios de Encerramento (Definição de “Problema Resolvido”)
| Problema | Critério Objetivo |
|----------|-------------------|
| P1 | Nenhuma função mistura camadas (GUI chamando SQL direto). |
| P5 | Nenhum .md vazio em duas releases consecutivas. |
| P7 | Cache documentado com diagrama de fluxo. |
| P8 | Todos JSON críticos têm README ou bloco de comentários explicativo. |
| P9 | Suite smoke com >= 5 cenários básicos passando. |

## 8. Riscos se Não Implementar Pendências
- Reintrodução de nomes inconsistentes → confusão / regressão de imports.
- Crescimento de “docs” placeholder gera falsa sensação de cobertura.
- Refactors arriscados por ausência de testes base.
- Config editada incorretamente gerando erros silenciosos.

## 9. Próximos Passos Concretos (Sprint Sugerida)
1. Criar harness smoke (CLI lista + GUI abre + consulta simples).
2. Adicionar README em `config/` explicando cada JSON.
3. Script verificação de placeholders vazios (falha se tamanho < N e não marcado como placeholder intencional).
4. Documentar fluxo do cache e inserir link no consolidado.
5. Issue para padronizar commit hook (pre-commit) nomes.

## 10. Histórico
Criado inicialmente para substituir arquivo vazio em 12/09/2025. Atualizar quando cada ação pendente for concluída.

