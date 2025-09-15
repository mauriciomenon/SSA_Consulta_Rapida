# ORGANIZACAO DA DOCUMENTACAO PROFISSIONAL

Este documento define padrões e a organização formal dos materiais de documentação do projeto.

## Objetivos
- Facilitar onboarding rápido.
- Reduzir duplicação e divergência entre arquivos.
- Definir responsabilidades por tipo de documento.

## Estrutura Macro
| Diretório / Arquivo | Papel | Observações |
|---------------------|-------|------------|
| `README.md` | Visão mínima de entrada | Execução básica / resumo. |
| `launchers/` | Guias operacionais rápidos | Build, quickstart, status. |
| `docs/` | Documentação técnica detalhada | Fonte principal consolidada. |
| `docs_saida/` | Resultados gerados / relatórios | Não editar manual. |
| `docs_entrada/` | Materiais brutos / insumos | Base para consolidação. |
| `scripts/` | Automação operacional | Referenciado em guias. |

## Classificação de Arquivos
- Guia: instruções procedurais (ex: instalação, build, modo optimized).
- Referência: definição de estruturas, mapeamentos, contratos.
- Relatório: estado consolidado em um ponto no tempo.
- Histórico: evolução (changelog, releases, versões).
- Checklist: controle de progresso e pendências.

## Convenções de Nome
- Letras maiúsculas separadas por underscore para títulos consolidados: `RELATORIO_FINAL_CONSOLIDADO.md`.
- Prefixos aceitos:
	- `RELATORIO_` (snapshot)
	- `CHECKLIST_` (controle)
	- `GUIA_` (procedural)
	- `HISTORICO_` (linha do tempo)
	- `ANALISE_` (profundidade técnica)
- Evitar sufixos redundantes como `_FINAL` em múltiplas gerações (usar versão sem repetir “FINAL”).

## Regras de Criação
1. Antes de criar novo arquivo, verificar se cabe como seção em existente.
2. Novo arquivo precisa ter ao menos: Título H1, Objetivo, Escopo.
3. Não duplicar bloco já presente em outro arquivo → referenciar com link relativo.
4. Se arquivo ficar obsoleto, adicionar cabeçalho: `STATUS: OBSOLETO` e apontar substituto.

## Processo de Atualização
1. Editar conteúdo em `docs/`.
2. Se impacto operacional (build, execução), refletir em `launchers/`.
3. Atualizar changelog se alterar comportamento visível.
4. Se reestruturação maior: registrar rationale em `ANALISES_TECNICAS.md`.

## Checklist de Qualidade de Documento
- [ ] H1 presente e claro.
- [ ] Objetivo explícito nas 10 primeiras linhas.
- [ ] Links relativos corretos.
- [ ] Sem parágrafos duplicados.
- [ ] Data ou versão onde aplicável.
- [ ] Indicar se substitui outro documento.

## Responsabilidades
| Tipo | Responsável Primário | Frequência Revisão |
|------|----------------------|--------------------|
| Guia Operacional | Manutenção / Operações | A cada mudança de processo |
| Referência Técnica | Dev Principal / Arquiteto | Quando schema ou APIs mudam |
| Histórico | Release Manager | Em cada release |
| Checklist | Dono do fluxo | Contínuo |

## Roadmap de Organização
- Unificar checklists dispersos em um índice único.
- Marcar explicitamente obsoletos (ex: relatórios antigos superseded).
- Criar README por subpasta crítica ausente.
- Automatizar verificação de cabeçalhos.

## Última Atualização
Preenchido inicialmente para substituir arquivo vazio. Ajustar conforme maturidade da doc.

