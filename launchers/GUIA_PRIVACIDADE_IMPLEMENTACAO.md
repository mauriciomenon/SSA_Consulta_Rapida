# Guia de Privacidade & Implementação de Controles

Este documento estabelece princípios, práticas e roadmap para tratamento responsável de dados no **SSA_Consulta_Rapida**. Foca em minimização, segurança, rastreabilidade e conformidade futura (LGPD / boas práticas). Não é um parecer jurídico; é um guia técnico-operacional.

---
## 1. Escopo Atual do Sistema
| Dimensão | Status Atual | Observações |
|----------|--------------|-------------|
| Origem Dados | Planilhas / base consolidada local | Sem ingestão remota dinâmica |
| Tipo de Dados | Operacionais de ordens/SSAs | Sem dados pessoais sensíveis explícitos (confirmar) |
| PII (Dados pessoais) | Potencial em campos livres (ex: solicitante) | Requer futura normalização/análise |
| Persistência | SQLite local (`data/ssas.db`) + backups | Sem replicação externa |
| Exportação | CSV/XLSX sob demanda | Sem envio automático para terceiros |
| Logs | Mínimos, não sensíveis | Expandir política de retenção |

---
## 2. Princípios Norteadores
1. Minimização: somente armazenar o necessário para funcionalidade do painel e análises básicas.
2. Clareza: campos e transformações documentados (mapeamentos de colunas versionados).
3. Isolamento Local: nenhuma transmissão externa automática enquanto não houver política revisada.
4. Reversibilidade: facilidade de purga/remoção de backups e reconstrução a partir da fonte.
5. Observabilidade Segura: logs não devem conter conteúdos de colunas sensíveis ou identificadores completos quando não indispensável.
6. Evolução Controlada: novos campos passam por classificação antes de persistirem.

---
## 3. Fluxo de Dados (Alto Nível)
```mermaid
digraph FLOW {
	rankdir=LR;
	A[Arquivos Origem XLSX/CSV] --> B[Import Logic (core.app_logic)]
	B --> C[Normalização & Mapeamentos]
	C --> D[(SQLite db)]
	D --> E[CLI Filtragem/Consulta]
	E --> F[Exportação CSV/XLSX]
	D --> G[Backups Rotativos]
}
```
Pontos de controle potenciais: ingestão (A→B), normalização (B→C), persistência (C→D), exportação (E→F), retenção (G).

---
## 4. Classificação de Dados (Inicial)
| Categoria | Exemplos | Nível | Ação Recomendada |
|-----------|----------|-------|------------------|
| Identificadores Operacionais | numero_ssa, derivada_de | Baixo | Manipulação normal |
| Metadados Temporais | data_cadastro, semana_programada | Baixo | Manter conforme |
| Texto Livre Potencialmente Sensível | descricao_ssa, descricao_execucao | Médio | Futuro scrub/limite de exportação |
| Possível PII (Nominal) | solicitante, responsavel_execucao | Médio | Avaliar hashing parcial/pseudonimização |
| Estado / Situação | situacao, execucao_parcial | Baixo | OK |
| Métricas Derivadas | tempo_total, tempo_excedido | Baixo | OK |

Legenda Nível: Baixo (aceito), Médio (monitorar / reduzir exposição), Alto (não identificado até o momento).

---
## 5. Riscos Identificados
| Risco | Impacto | Probabilidade | Mitigação Proposta |
|-------|---------|--------------|--------------------|
| Dados pessoais em campos livres | Exposição não intencional ao exportar | Médio | Criar lista de padrões (regex nomes / emails) para alerta |
| Backups excessivos retendo histórico longo | Aumento de superfície de exposição local | Baixo | Limite rígido já previsto (--max-backups) |
| Exportação irrestrita de colunas | Divulgação de campos desnecessários | Médio | Modo export whitelist futura |
| Logs futuros incluindo conteúdo de texto | Vazamento indireto | Baixo | Política de logs sanitizados |
| Mistura de ambientes (dev/prod) | Contaminação de dados | Médio | Diretórios isolados + prefixos |

---
## 6. Controles Implementados (Estado Atual)
| Controle | Implementação | Arquivo / Script |
|----------|---------------|------------------|
| Limpeza de artefatos | Scripts seletivos/dry-run | `cleanup_repository.py`, `cleanup_manual.py`, `cleanup_emergency.py` |
| Validação de configs | Estrutura e semântica básica | `scripts/validate_configs.py` |
| Auditoria de documentação | Proibição de placeholders | `scripts/check_docs.py` |
| Limite de backups | Parâmetros configuráveis | `cleanup_repository.py` / manual |
| Smoke test | Integridade entrypoint | `scripts/smoke_cli.py` |
| Normalização de colunas | Remapeamento controlado | `column_mappings.json` / `display_mappings.json` |

---
## 7. Controles Recomendados (Backlog)
| Prioridade | Controle | Descrição | Etapa |
|------------|----------|-----------|-------|
| Alta | Deteção PII básica | Scanner regex nomes/emails em campos livres | Import / Export |
| Alta | Export Whitelist | Lista de colunas exportáveis | Exportação |
| Média | Pseudonimização | Hash estável para campos nominativos | Persistência |
| Média | Política de Logs | Formato estruturado e sem conteúdo sensível | Logging |
| Média | Checksum DB | Geração de hash para integridade | Backup |
| Baixa | Criptografia local opcional | Encrypt at rest (wrapper SQLite) | Persistência |
| Baixa | Relatório de diffs de dados | Mudanças agregadas entre imports | Observabilidade |

---
## 8. Estratégia de Minimização
1. Não armazenar colunas não utilizadas ativamente (revisar schema vs uso real da CLI).
2. Reduzir texto livre em exportações (ex: truncar descrições > N caracteres opcionalmente).
3. Oferecer flag `--safe-export` ocultando possíveis PII (futuro).
4. Evitar replicar o mesmo dado em múltiplos caches.

---
## 9. Política Inicial de Retenção
| Artefato | Retenção Proposta | Mecanismo |
|----------|------------------|-----------|
| Backups DB | Últimos 5 (configurável) | Scripts de cleanup |
| Logs antigos | > 14 dias removidos | `cleanup_manual.py --logs` |
| Arquivos exportados | Usuário decide (não auto-purge) | Documentar recomendação |
| Relatórios temporários | Limpeza manual | Incluir em futuro agregador |

Futuro: adicionar script de retenção unificado (`retention_policy.py`).

---
## 10. Acesso & Controle
Atualmente monousuário/local: controle de acesso delegado ao SO. Futuras camadas possíveis:
| Fase | Medida |
|------|--------|
| 1 | Marcação de diretórios sensíveis (chmod restritivo) |
| 2 | Abstração de leitura via camada de serviço | 
| 3 | Modo read-only para auditoria (flag de execução) |

---
## 11. Segurança Técnica (Baseline)
| Vetor | Situação | Próximos Passos |
|-------|----------|-----------------|
| Execução de código | Código local controlado | Adicionar bandit (lint segurança) |
| Injeção SQL | Queries estáticas | Manter parametrização se ampliar | 
| Exfiltração | Sem rede externa | Monitorar se adicionar integrações |
| Integridade DB | Sem checksum | Adicionar SHA256 pós-import |
| Logs sensíveis | Baixo volume | Formalizar formato mínimo |

---
## 12. Plano de Implementação (Roadmap Evolutivo)
| Iteração | Entrega | Métrica de Sucesso |
|----------|--------|--------------------|
| 1 | Este guia + baseline de scripts | Documento versionado |
| 2 | Scanner PII simples (regex) | Nº ocorrências detectadas por import |
| 3 | Export whitelist + `--safe-export` | Exports conformes por padrão |
| 4 | Hash/Checksum DB + relatório integridade | Hash registrado por baseline |
| 5 | Pseudonimização opcional | Flag ativa sem quebra de fluxo |
| 6 | Política de logs estruturados | 0 logs contendo campos marcados |
| 7 | Criptografia local (opcional) | Overhead < 10% I/O |

---
## 13. Métricas Iniciais Sugeridas
| Métrica | Objetivo |
|---------|----------|
| % colunas efetivamente usadas | > 70% das armazenadas |
| Tamanho médio do backup | Monitorar variação |
| Ocorrências PII detectadas (regex) | Reduzir a 0 pós sanitização |
| Nº exportações "safe" vs "raw" | Aumentar proporção safe |
| Tempo para reconstruir DB | < 5 min a partir das fontes |

---
## 14. Procedimento de Avaliação Periódica
1. Executar scanner PII (quando implementado) em lote histórico.
2. Verificar se novos campos foram introduzidos sem classificação.
3. Revisar se backups excedem política (ajustar limite se necessário).
4. Registrar métrica de compressão/opcional se incorporar compressão de backups.

Periodicidade recomendada: trimestral ou antes de releases maiores.

---
## 15. Glossário Resumido
| Termo | Definição |
|-------|----------|
| PII | Informação Pessoal (potencial identificação de pessoa) |
| Minimização | Redução do escopo de dados ao estritamente necessário |
| Pseudonimização | Transformação que substitui identificadores por tokens | 
| Whitelist de Exportação | Lista explícita de colunas liberadas |

---
## 16. Referências Internas
- `column_mappings.json` / `display_mappings.json` – alinhamento de nomenclaturas.
- `scripts/validate_configs.py` – integridade estrutural.
- `launchers/BASELINE_TAG.md` – procedimento de baseline.
- `cleanup_*` scripts – redução de superfície e retenção.

---
## 17. Revisões Futuras
Adicionar seção de "Modelo de Ameaças" caso o sistema passe a operar em ambiente multiusuário ou com sincronização externa.

---
## 18. TL;DR Operacional
1. Não expandir schema sem classificar o campo.
2. Evitar exportar campos livres sensíveis até whitelist existir.
3. Limitar backups e logs conforme scripts.
4. Planejar scanner PII antes de novas integrações.
5. Medir integridade (checksum DB) antes de criptografar.

> Este guia evoluirá junto com a maturidade de segurança e privacidade do projeto.

