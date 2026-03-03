# Documentacao - Sistema de Importacao SSA

## Indice de Documentos

Esta pasta contem a documentacao do sistema de importacao do SSA_Consulta_Rapida, atualizada em 2026-03-01.

---

## Documentos Principais

### 1. ARQUITETURA_IMPORTACAO.md
Documento principal da arquitetura de importacao.

Conteudo:
- visao geral em camadas
- fluxo de dados
- componentes principais
- fluxo CLI e GUI
- erros conhecidos
- pontos fortes
- metricas de performance
- recomendacoes priorizadas

Leitura recomendada: comecar por este arquivo.

### 2. RESUMO_EXECUTIVO_IMPORTACAO.md
Resumo objetivo para decisao tecnica.

Conteudo:
- principais achados
- metricas de performance
- recomendacoes por impacto
- checklist de proximos passos
- riscos

### 3. TROUBLESHOOTING_IMPORTACAO.md
Guia de diagnostico e resolucao de problemas.

Conteudo:
- erros comuns
- problemas de performance
- problemas de dados
- diagnostico avancado
- checklist de resolucao

---

## Diagramas (PlantUML)

### 4. diagrams/arquitetura_importacao.puml
Diagrama de componentes por camada.

### 5. diagrams/fluxo_sequencia_importacao.puml
Diagrama de sequencia do fluxo de importacao.

### 6. diagrams/diagrama_classes.puml
Diagrama de classes das entidades principais.

---

## Como Usar Esta Documentacao

### Desenvolvedores
1. Ler ARQUITETURA_IMPORTACAO.md
2. Consultar diagrams/
3. Usar TROUBLESHOOTING_IMPORTACAO.md em incidentes

### Gestao tecnica
1. Ler RESUMO_EXECUTIVO_IMPORTACAO.md
2. Revisar recomendacoes priorizadas
3. Planejar backlog de melhoria

### QA
1. Revisar troubleshooting e erros conhecidos
2. Validar cenarios de regressao
3. Usar scripts de validacao em scripts_manutencao/

### Suporte
1. Consultar troubleshooting
2. Escalar com referencia de causa raiz

---

## Referencias

- docs/SCHEMA_UNIFICADO_IMPORTACAO.md
- docs/RECOVERY_BACKLOG.md
- AGENTS.md

---

Gerado por: Atlas (OhMyOpenCode)
Data: 2026-03-01
Versao: 1.0
Status: Completo
