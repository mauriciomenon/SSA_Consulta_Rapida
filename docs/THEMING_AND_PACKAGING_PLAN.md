# Temas, Icone e Empacotamento – Plano de Implementacao

Este documento descreve as mudancas propostas (e sua justificativa) antes da criacao de uma release maior.

## Objetivos
- Alternancia de temas em tempo de execucao: `Claro`, `Escuro` e `Gruvbox/Vim Dark` (inspiracao VS Code: vim-theme e gruvbox).
- Icone amigavel para a aplicacao (GUI) e futuros binarios.
- Evitar que a janela de console apareca quando a GUI for aberta (wrapper dedicado, sem alterar a CLI atual).
- Preparar terreno para empacotamento enxuto (PyInstaller) – sem incluir pacotes desnecessarios.

## Escopo (iterativo, seguro)
1. Adicionar suporte a temas na GUI:
   - Novo utilitario `utils/themes.py` com paletas (Claro, Escuro, Gruvbox).
   - Botao/menu “Tema” na barra superior (GUI), persistencia em `config/gui_main_preferences.json`.
   - Aplicar paleta e pequenos ajustes de stylesheet (cabecalho, foco, selecao).

2. Icone da aplicacao:
   - Arquivo `resources/app_icon.svg` simples (livre) para testes.
   - `setWindowIcon` na GUI.

3. Wrapper para abrir a GUI sem console no Windows:
   - Arquivo `launchers/gui_launcher.pyw` (usa `pythonw.exe`) → abre a GUI diretamente.
   - Nao altera a CLI nem `main.py`; documentacao indica “duplo clique” no `.pyw`/atalho.

4. Documentacao e notas:
   - Este arquivo (plano de execucao).
   - Atualizacao futura do README/RELEASE NOTES apos testes.

## Fora de escopo (etapa seguinte)
- Empacotamento completo (PyInstaller + instalador). Sera aberto em PR proprio apos validacao dos temas e do wrapper.
- Separacao de documentacao “limbo” em repositorio privado (requer lista aprovada).

## Riscos e mitigacao
- Drifts visuais por tema: preservar cabecalho sem negrito; testar contraste em tabela e paineis.
- Persistencia de tema: fallback robusto para `Escuro` se a chave nao existir.

## Testes manuais sugeridos
- Alternar temas durante execucao; persistir, fechar e reabrir.
- Conferir contraste de cabecalhos, selecao, filtros por coluna.
- Verificar no tema Claro: caixa "Semana Atual" e "Status" com fundo cinza (#f3f3f3) e borda (#bdbdbd) visiveis.
- Abrir `launchers/gui_launcher.pyw` no Windows (sem console).

## Proximos passos
- Implementar utilitario de tema + menu de tema na GUI (commit 1).
- Adicionar icone (commit 2).
- Adicionar `gui_launcher.pyw` e doc curta (commit 3).
- Depois: README/RELEASE NOTES + PR de empacotamento.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

