# SSA Consulta Rápida v3.10

Status: Final
Data: 2025-09-04

Resumo das mudanças desde v3.0.7:
- GUI: Painel “Filtros por Coluna” compacto (labels próximos, botões Aplicar/Limpar com largura fixa), evitando que a linha cresça e sem empurrar componentes.
- Estabilidade de colunas: larguras só recalculam quando muda o conjunto/ordem de colunas ou quando a largura útil do viewport varia > 12 px. Limpar/aplicar filtros e paginar não alteram as colunas.
- Tema Claro: contraste reforçado nas caixas informativas (Semana/Status) – fundo `#eee`, borda `#aaa`; dica TL;DR visível.
- Busca geral: texto de ajuda mais claro e direto (separe por vírgulas; `!` para excluir; vale para qualquer coluna).
- Placeholders de filtros por coluna mais descritivos (mesmos modos do filtro geral).

Instruções de atualização:
1) `git pull` na branch principal.
2) Rodar `python main.py --gui` e alternar o tema em “Tema → Claro” para conferir contraste.
3) Validar que “Limpar todos filtros de colunas” preserva Situação/Executor/Descrição com entradas vazias e não altera as larguras da tabela.

Observações:
- Para empacotar GUI, veja docs/THEMING_AND_PACKAGING_PLAN.md.
