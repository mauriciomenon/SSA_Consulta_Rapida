# Changelog v3.10

Data: 2025-09-04
Estado: Final

Principais mudanças
- GUI: Painel “Filtros por Coluna” compacto, com labels próximos e botões fixos (Aplicar/Limpar) sem alterar a altura da linha.
- Estabilidade de colunas: larguras não mudam ao limpar/aplicar filtros ou paginar; recalcula somente quando muda o conjunto/ordem de colunas ou quando a largura útil do viewport varia > 12 px.
- Tema: abre sempre em Gruvbox; Tema Claro mais cinza (menos branco). Caixas informativas (Semana/Status) com fundo #eee e borda #aaa.
- UX de busca: dica TL;DR visível (“Separe por vírgulas… ! exclui… busca vale para qualquer coluna”). Placeholders dos filtros por coluna alinhados com os modos.
- CLI: banner inicial único (sem duplicação), painel de ajuda inicial sem bordas laterais para evitar quebra.

Correções
- “Limpar” nas três caixas fixas de Filtros por Coluna mantém as linhas e apenas zera os termos.
- Dica de busca visível e com contraste em todos os temas.

Notas de migração
- Nenhuma ação requerida. Preferência de tema é persistida, porém a aplicação inicializa em Gruvbox por padrão.

Checklist para Release
- [ ] Validar contraste do tema Claro nas caixas Semana/Status
- [ ] Validar “Limpar” individual e “Limpar todos” no painel de filtros por coluna
- [ ] Validar que larguras de coluna permanecem estáveis em limpar/aplicar/paginar
- [ ] Verificar que o help inicial da CLI não quebra na lateral direita
- [ ] Atualizar tag e GitHub Release após o OK
