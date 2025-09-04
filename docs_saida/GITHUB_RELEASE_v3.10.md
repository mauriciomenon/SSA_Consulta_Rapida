# SSA Consulta Rápida v3.10 – Release Notes

Este release consolida as melhorias visuais e de previsibilidade na GUI, além de ajustes de UX no CLI.

Resumo (GUI)
- Painel “Filtros por Coluna” compacto: labels próximos, botões fixos (Aplicar/Limpar) e altura estável.
- Estabilidade das colunas: larguras não mudam ao limpar/aplicar filtros ou paginar; recalcula apenas quando muda o conjunto/ordem de colunas ou quando a largura útil do viewport varia > 12 px.
- Tema: inicia em Gruvbox; Tema Claro mais cinza (fundo #eee, borda #aaa nas caixas de Semana/Status).
- Dica de busca visível nos três temas: “Separe por vírgulas. Use ! para excluir. A busca vale para qualquer coluna.”

Resumo (CLI)
- Banner inicial único (sem duplicação de versão).
- Guia rápido inicial sem bordas laterais para evitar quebra à direita.

Arquivos relacionados
- docs_saida/RELEASE_v3.10.md
- docs_saida/CHANGELOG_v3.10.md

Agradecimentos
- Testes rápidos, feedback de UX e direção de release: @mauriciomenon
