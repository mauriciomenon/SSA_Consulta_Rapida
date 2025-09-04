# 🔄 TRANSIÇÃO DE CONVERSA – v3.10

Objetivo: finalizar e publicar a v3.10 (sem criar a tag ainda), garantindo contraste/UX e estabilidade dos filtros e larguras.

## Itens para validar rapidamente
- Tema padrão Gruvbox na abertura; troca para Claro mostra caixas “Semana/Status” com #eee/#aaa.
- Dica de busca (linha única) abaixo do campo, visível nos 3 temas.
- “Limpar” nas 3 caixas fixas de Filtros por Coluna apenas zera o termo e mantém a linha.
- “Limpar todos filtros de colunas” preserva as 3 entradas (vazias) e não altera a Pesquisa Geral.
- Larguras das colunas permanecem estáveis ao limpar/aplicar e ao paginar; só recalcula em mudança de colunas ou viewport > 12 px.
- CLI: banner inicial único e guia rápido sem bordas laterais.

## Depois do OK
- Atualizar `docs_saida/RELEASE_v3.10.md` de Draft → Final.
- Criar tag `v3.10` e GitHub Release.
- Seguir para backlog de 3.10.x (pequenos ajustes visuais e de UX, se surgirem).

## Referências
- docs_saida/CHANGELOG_v3.10_DRAFT.md
- docs_saida/RELEASE_v3.10.md (draft)
- README.md (seções GUI/Temas/Filtros)
