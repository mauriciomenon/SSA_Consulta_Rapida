# Guia de Privacidade & Implementacao de Controles

Este documento estabelece principios, praticas e roadmap para tratamento responsavel de dados no **SSA_Consulta_Rapida**. Foca em minimizacao, seguranca, rastreabilidade e conformidade futura (LGPD / boas praticas). Nao e um parecer juridico; e um guia tecnico-operacional.

---
## 1. Escopo Atual do Sistema
| Dimensao | Status Atual | Observacoes |
|----------|--------------|-------------|
| Origem Dados | Planilhas / base consolidada local | Sem ingestao remota dinamica |
| Tipo de Dados | Operacionais de ordens/SSAs | Sem dados pessoais sensiveis explicitos (confirmar) |
| PII (Dados pessoais) | Potencial em campos livres (ex: solicitante) | Requer futura normalizacao/analise |
| Persistencia | SQLite local (`data/ssas.db`) + backups | Sem replicacao externa |
| Exportacao | CSV/XLSX sob demanda | Sem envio automatico para terceiros |
| Logs | Minimos, nao sensiveis | Expandir politica de retencao |

---
## 2. Principios Norteadores
1. Minimizacao: somente armazenar o necessario para funcionalidade do painel e analises basicas.
2. Clareza: campos e transformacoes documentados (mapeamentos de colunas versionados).
3. Isolamento Local: nenhuma transmissao externa automatica enquanto nao houver politica revisada.
4. Reversibilidade: facilidade de purga/remocao de backups e reconstrucao a partir da fonte.
5. Observabilidade Segura: logs nao devem conter conteudos de colunas sensiveis ou identificadores completos quando nao indispensavel.
6. Evolucao Controlada: novos campos passam por classificacao antes de persistirem.

---
## 3. Fluxo de Dados (Alto Nivel)
```mermaid
digraph FLOW {
	rankdir=LR;
	A[Arquivos Origem XLSX/CSV] --> B[Import Logic (core.app_logic)]
	B --> C[Normalizacao & Mapeamentos]
	C --> D[(SQLite db)]
	D --> E[CLI Filtragem/Consulta]
	E --> F[Exportacao CSV/XLSX]
	D --> G[Backups Rotativos]
}
```
Pontos de controle potenciais: ingestao (A→B), normalizacao (B→C), persistencia (C→D), exportacao (E→F), retencao (G).

---
## 4. Classificacao de Dados (Inicial)
| Categoria | Exemplos | Nivel | Acao Recomendada |
|-----------|----------|-------|------------------|
| Identificadores Operacionais | numero_ssa, derivada_de | Baixo | Manipulacao normal |
| Metadados Temporais | data_cadastro, semana_programada | Baixo | Manter conforme |
| Texto Livre Potencialmente Sensivel | descricao_ssa, descricao_execucao | Medio | Futuro scrub/limite de exportacao |
| Possivel PII (Nominal) | solicitante, responsavel_execucao | Medio | Avaliar hashing parcial/pseudonimizacao |
| Estado / Situacao | situacao, execucao_parcial | Baixo | OK |
| Metricas Derivadas | tempo_total, tempo_excedido | Baixo | OK |

Legenda Nivel: Baixo (aceito), Medio (monitorar / reduzir exposicao), Alto (nao identificado ate o momento).

---
## 5. Riscos Identificados
| Risco | Impacto | Probabilidade | Mitigacao Proposta |
|-------|---------|--------------|--------------------|
| Dados pessoais em campos livres | Exposicao nao intencional ao exportar | Medio | Criar lista de padroes (regex nomes / emails) para alerta |
| Backups excessivos retendo historico longo | Aumento de superficie de exposicao local | Baixo | Limite rigido ja previsto (--max-backups) |
| Exportacao irrestrita de colunas | Divulgacao de campos desnecessarios | Medio | Modo export whitelist futura |
| Logs futuros incluindo conteudo de texto | Vazamento indireto | Baixo | Politica de logs sanitizados |
| Mistura de ambientes (dev/prod) | Contaminacao de dados | Medio | Diretorios isolados + prefixos |

---
## 6. Controles Implementados (Estado Atual)
| Controle | Implementacao | Arquivo / Script |
|----------|---------------|------------------|
| Limpeza de artefatos | Scripts seletivos/dry-run | `cleanup_repository.py`, `cleanup_manual.py`, `cleanup_emergency.py` |
| Validacao de configs | Estrutura e semantica basica | `scripts/validate_configs.py` |
| Auditoria de documentacao | Proibicao de placeholders | `scripts/check_docs.py` |
| Limite de backups | Parametros configuraveis | `cleanup_repository.py` / manual |
| Smoke test | Integridade entrypoint | `scripts/smoke_cli.py` |
| Normalizacao de colunas | Remapeamento controlado | `column_mappings.json` / `display_mappings.json` |

---
## 7. Controles Recomendados (Backlog)
| Prioridade | Controle | Descricao | Etapa |
|------------|----------|-----------|-------|
| Alta | Detecao PII basica | Scanner regex nomes/emails em campos livres | Import / Export |
| Alta | Export Whitelist | Lista de colunas exportaveis | Exportacao |
| Media | Pseudonimizacao | Hash estavel para campos nominativos | Persistencia |
| Media | Politica de Logs | Formato estruturado e sem conteudo sensivel | Logging |
| Media | Checksum DB | Geracao de hash para integridade | Backup |
| Baixa | Criptografia local opcional | Encrypt at rest (wrapper SQLite) | Persistencia |
| Baixa | Relatorio de diffs de dados | Mudancas agregadas entre imports | Observabilidade |

---
## 8. Estrategia de Minimizacao
1. Nao armazenar colunas nao utilizadas ativamente (revisar schema vs uso real da CLI).
2. Reduzir texto livre em exportacoes (ex: truncar descricoes > N caracteres opcionalmente).
3. Oferecer flag `--safe-export` ocultando possiveis PII (futuro).
4. Evitar replicar o mesmo dado em multiplos caches.

---
## 9. Politica Inicial de Retencao
| Artefato | Retencao Proposta | Mecanismo |
|----------|------------------|-----------|
| Backups DB | Ultimos 5 (configuravel) | Scripts de cleanup |
| Logs antigos | > 14 dias removidos | `cleanup_manual.py --logs` |
| Arquivos exportados | Usuario decide (nao auto-purge) | Documentar recomendacao |
| Relatorios temporarios | Limpeza manual | Incluir em futuro agregador |

Futuro: adicionar script de retencao unificado (`retention_policy.py`).

---
## 10. Acesso & Controle
Atualmente monousuario/local: controle de acesso delegado ao SO. Futuras camadas possiveis:
| Fase | Medida |
|------|--------|
| 1 | Marcacao de diretorios sensiveis (chmod restritivo) |
| 2 | Abstracao de leitura via camada de servico | 
| 3 | Modo read-only para auditoria (flag de execucao) |

---
## 11. Seguranca Tecnica (Baseline)
| Vetor | Situacao | Proximos Passos |
|-------|----------|-----------------|
| Execucao de codigo | Codigo local controlado | Adicionar bandit (lint seguranca) |
| Injecao SQL | Queries estaticas | Manter parametrizacao se ampliar | 
| Exfiltracao | Sem rede externa | Monitorar se adicionar integracoes |
| Integridade DB | Sem checksum | Adicionar SHA256 pos-import |
| Logs sensiveis | Baixo volume | Formalizar formato minimo |

---
## 12. Plano de Implementacao (Roadmap Evolutivo)
| Iteracao | Entrega | Metrica de Sucesso |
|----------|--------|--------------------|
| 1 | Este guia + baseline de scripts | Documento versionado |
| 2 | Scanner PII simples (regex) | No ocorrencias detectadas por import |
| 3 | Export whitelist + `--safe-export` | Exports conformes por padrao |
| 4 | Hash/Checksum DB + relatorio integridade | Hash registrado por baseline |
| 5 | Pseudonimizacao opcional | Flag ativa sem quebra de fluxo |
| 6 | Politica de logs estruturados | 0 logs contendo campos marcados |
| 7 | Criptografia local (opcional) | Overhead < 10% I/O |

---
## 13. Metricas Iniciais Sugeridas
| Metrica | Objetivo |
|---------|----------|
| % colunas efetivamente usadas | > 70% das armazenadas |
| Tamanho medio do backup | Monitorar variacao |
| Ocorrencias PII detectadas (regex) | Reduzir a 0 pos sanitizacao |
| No exportacoes "safe" vs "raw" | Aumentar proporcao safe |
| Tempo para reconstruir DB | < 5 min a partir das fontes |

---
## 14. Procedimento de Avaliacao Periodica
1. Executar scanner PII (quando implementado) em lote historico.
2. Verificar se novos campos foram introduzidos sem classificacao.
3. Revisar se backups excedem politica (ajustar limite se necessario).
4. Registrar metrica de compressao/opcional se incorporar compressao de backups.

Periodicidade recomendada: trimestral ou antes de releases maiores.

---
## 15. Glossario Resumido
| Termo | Definicao |
|-------|----------|
| PII | Informacao Pessoal (potencial identificacao de pessoa) |
| Minimizacao | Reducao do escopo de dados ao estritamente necessario |
| Pseudonimizacao | Transformacao que substitui identificadores por tokens | 
| Whitelist de Exportacao | Lista explicita de colunas liberadas |

---
## 16. Referencias Internas
- `column_mappings.json` / `display_mappings.json` – alinhamento de nomenclaturas.
- `scripts/validate_configs.py` – integridade estrutural.
- `launchers/BASELINE_TAG.md` – procedimento de baseline.
- `cleanup_*` scripts – reducao de superficie e retencao.

---
## 17. Revisoes Futuras
Adicionar secao de "Modelo de Ameacas" caso o sistema passe a operar em ambiente multiusuario ou com sincronizacao externa.

---
## 18. TL;DR Operacional
1. Nao expandir schema sem classificar o campo.
2. Evitar exportar campos livres sensiveis ate whitelist existir.
3. Limitar backups e logs conforme scripts.
4. Planejar scanner PII antes de novas integracoes.
5. Medir integridade (checksum DB) antes de criptografar.

> Este guia evoluira junto com a maturidade de seguranca e privacidade do projeto.

