# ORGANIZACAO DA DOCUMENTACAO PROFISSIONAL

Este documento define padroes e a organizacao formal dos materiais de documentacao do projeto.

## Objetivos
- Facilitar onboarding rapido.
- Reduzir duplicacao e divergencia entre arquivos.
- Definir responsabilidades por tipo de documento.

## Estrutura Macro
| Diretorio / Arquivo | Papel | Observacoes |
|---------------------|-------|------------|
| `README.md` | Visao minima de entrada | Execucao basica / resumo. |
| `launchers/` | Guias operacionais rapidos | Build, quickstart, status. |
| `docs/` | Documentacao tecnica detalhada | Fonte principal consolidada. |
| `docs_saida/` | Resultados gerados / relatorios | Nao editar manual. |
| `docs_entrada/` | Materiais brutos / insumos | Base para consolidacao. |
| `scripts/` | Automacao operacional | Referenciado em guias. |

## Classificacao de Arquivos
- Guia: instrucoes procedurais (ex: instalacao, build, modo optimized).
- Referencia: definicao de estruturas, mapeamentos, contratos.
- Relatorio: estado consolidado em um ponto no tempo.
- Historico: evolucao (changelog, releases, versoes).
- Checklist: controle de progresso e pendencias.

## Convencoes de Nome
- Letras maiusculas separadas por underscore para titulos consolidados: `RELATORIO_FINAL_CONSOLIDADO.md`.
- Prefixos aceitos:
	- `RELATORIO_` (snapshot)
	- `CHECKLIST_` (controle)
	- `GUIA_` (procedural)
	- `HISTORICO_` (linha do tempo)
	- `ANALISE_` (profundidade tecnica)
- Evitar sufixos redundantes como `_FINAL` em multiplas geracoes (usar versao sem repetir “FINAL”).

## Regras de Criacao
1. Antes de criar novo arquivo, verificar se cabe como secao em existente.
2. Novo arquivo precisa ter ao menos: Titulo H1, Objetivo, Escopo.
3. Nao duplicar bloco ja presente em outro arquivo → referenciar com link relativo.
4. Se arquivo ficar obsoleto, adicionar cabecalho: `STATUS: OBSOLETO` e apontar substituto.

## Processo de Atualizacao
1. Editar conteudo em `docs/`.
2. Se impacto operacional (build, execucao), refletir em `launchers/`.
3. Atualizar changelog se alterar comportamento visivel.
4. Se reestruturacao maior: registrar rationale em `ANALISES_TECNICAS.md`.

## Checklist de Qualidade de Documento
- [ ] H1 presente e claro.
- [ ] Objetivo explicito nas 10 primeiras linhas.
- [ ] Links relativos corretos.
- [ ] Sem paragrafos duplicados.
- [ ] Data ou versao onde aplicavel.
- [ ] Indicar se substitui outro documento.

## Responsabilidades
| Tipo | Responsavel Primario | Frequencia Revisao |
|------|----------------------|--------------------|
| Guia Operacional | Manutencao / Operacoes | A cada mudanca de processo |
| Referencia Tecnica | Dev Principal / Arquiteto | Quando schema ou APIs mudam |
| Historico | Release Manager | Em cada release |
| Checklist | Dono do fluxo | Continuo |

## Roadmap de Organizacao
- Unificar checklists dispersos em um indice unico.
- Marcar explicitamente obsoletos (ex: relatorios antigos superseded).
- Criar README por subpasta critica ausente.
- Automatizar verificacao de cabecalhos.

## Ultima Atualizacao
Preenchido inicialmente para substituir arquivo vazio. Ajustar conforme maturidade da doc.

