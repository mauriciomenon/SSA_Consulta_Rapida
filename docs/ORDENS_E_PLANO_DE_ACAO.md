# Ordens do Projeto e Plano de Ação (GUI)

Data: 2025-10-03
Responsável: Copilot (agora focado apenas no que foi solicitado)

## Ordens explícitas (do usuário)
- Não mexer em tamanhos de colunas. Não adicionar, alterar ou "proteger" larguras. Sem salvaguardas extras.
- Não mexer em temas ou paletas. Nada de ajustes cosméticos.
- Implementar OU apenas dentro do mesmo filtro por coluna, e apenas via um botão dedicado na UI do painel de filtros por coluna.
  - Não inventar nova sintaxe. O "OU" não deve ser digitado nem aceito como token textual.
  - O "OU" será gerado pela UI (botão) e tratado apenas para aquela coluna.
- Na busca geral, não introduzir novos conectivos nem sintaxes. Tratar termos literalmente (ex.: "svp" literal). Sem mudanças não solicitadas.
- Foco em resolver problemas reais. Parar de alterar áreas que estão funcionando.

## Escopo imediato (o que será feito)
1) Botão "OU" por linha de filtro de coluna (UI)
   - Adicionar um botão pequeno ao lado do campo de texto de cada filtro por coluna: [ + OU ].
   - Comportamento:
     - Ao clicar, a UI insere visualmente o separador " OU " entre termos na mesma linha daquela coluna.
     - Internamente, os termos continuam armazenados como lista separada por vírgulas (compatível com a lógica existente de split por ",").
     - Ao aplicar o filtro, a UI converte o visual " OU " para "," antes do processamento.
     - Ao exibir o resumo de filtros, mostrar "OU" para aquela coluna, mas sem alterar a semântica global.
   - Observação: Nenhum outro conector (AND/OR globais) será adicionado/interpretado. O botão só atua no filtro da coluna onde foi clicado.

2) Correção de encerramento seguro de threads (QThread warning)
   - Sintoma: "QThread: Destroyed while thread '' is still running" ao abrir/fechar a GUI.
   - Ação:
     - Auditar DataLoaderWorker/FilterWorker e pontos de start/finish.
     - Garantir `quit()` + `wait()` no `closeEvent` e na limpeza pós-filtro, com checagens defensivas.
     - Evitar iniciar threads em momentos em que a janela pode fechar logo em seguida.
     - Adicionar logs mínimos só para diagnóstico (sem ruído no console do usuário final).

## Fora de escopo (não será feito agora)
- Qualquer alteração em tamanhos de coluna (cálculo, aplicação, salvaguardas non-zero, timers etc.).
- Qualquer alteração de tema/paleta/QSS.
- Novas sintaxes de busca geral ou parsing diferente do atual.

## Critérios de aceitação
- UI do painel de filtros por coluna exibe, em cada linha, um botão [ + OU ].
  - Clique no botão insere um separador visual " OU " no campo daquela coluna.
  - Ao aplicar, o filtro funciona como alternativas (OR) dentro da mesma coluna, sem interferir em outras colunas.
  - O resumo de filtros mostra "OU" apenas para aquela coluna, mantendo a lógica existente.
- Nenhuma regressão em tamanhos de colunas ou temas.
- Ao abrir/fechar a GUI repetidas vezes, não exibir mais o warning: `QThread: Destroyed while thread '' is still running`.

## Plano de implementação (passos pequenos e seguros)
- [ ] Inserir o botão [ + OU ] na construção de cada linha de filtro por coluna (arquivo `gui/gui_ssa.py`, método do painel de filtros).
- [ ] No handler do botão, manipular apenas o texto da linha atual: inserir " OU " no ponto do cursor (sem parsing adicional).
- [ ] No momento de aplicar o filtro daquela linha: substituir " OU " por "," antes de atualizar `self._active_column_filters[col]`.
- [ ] No resumo, renderizar visualmente "OU" para a coluna (sem mudar armazenamento interno).
- [ ] Teste manual: criar 2-3 termos com [ + OU ] numa mesma coluna e confirmar o resultado filtrado esperado.
- [ ] Threads: revisar `closeEvent`, `on_filter_finished_cleanup`, e pontos de start dos workers para garantir `quit()`/`wait()` e desconexão de sinais ao fechar.
- [ ] Rodar `python main.py --gui` e abrir/fechar a janela 3x sem o warning do QThread.

## Riscos e mitigação
- Risco: O botão [ + OU ] interferir em campos protegidos (linhas fixas). Mitigação: aplicar o botão apenas às linhas editáveis.
- Risco: Alterar comportamento global sem querer. Mitigação: conversão " OU " ➜ "," só no momento do apply da coluna, e somente para a coluna clicada.
- Risco: QThread ainda emitir warning em cenários raros. Mitigação: adicionar guardas e `wait()` com timeout razoável; registrar logs de depuração off-by-default.

## Observações finais
- Nenhuma alteração de largura de coluna ou de temas será feita.
- As mudanças serão entregues em pequenos commits focados: (1) botão [ + OU ]; (2) encerramento de threads.
