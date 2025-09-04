# Temas, Ícone e Empacotamento – Plano de Implementação

Este documento descreve as mudanças propostas (e sua justificativa) antes da criação de uma release maior.

## Objetivos
- Alternância de temas em tempo de execução: `Claro`, `Escuro` e `Gruvbox/Vim Dark` (inspiração VS Code: vim-theme e gruvbox).
- Ícone amigável para a aplicação (GUI) e futuros binários.
- Evitar que a janela de console apareça quando a GUI for aberta (wrapper dedicado, sem alterar a CLI atual).
- Preparar terreno para empacotamento enxuto (PyInstaller) – sem incluir pacotes desnecessários.

## Escopo (iterativo, seguro)
1. Adicionar suporte a temas na GUI:
   - Novo utilitário `utils/themes.py` com paletas (Claro, Escuro, Gruvbox).
   - Botão/menú “Tema” na barra superior (GUI), persistência em `config/gui_main_preferences.json`.
   - Aplicar paleta e pequenos ajustes de stylesheet (cabeçalho, foco, seleção).

2. Ícone da aplicação:
   - Arquivo `resources/app_icon.svg` simples (livre) para testes.
   - `setWindowIcon` na GUI.

3. Wrapper para abrir a GUI sem console no Windows:
   - Arquivo `launchers/gui_launcher.pyw` (usa `pythonw.exe`) → abre a GUI diretamente.
   - Não altera a CLI nem `main.py`; documentação indica “duplo clique” no `.pyw`/atalho.

4. Documentação e notas:
   - Este arquivo (plano de execução).
   - Atualização futura do README/RELEASE NOTES após testes.

## Fora de escopo (etapa seguinte)
- Empacotamento completo (PyInstaller + instalador). Será aberto em PR próprio após validação dos temas e do wrapper.
- Separação de documentação “limbo” em repositório privado (requer lista aprovada).

## Riscos e mitigação
- Drifts visuais por tema: preservar cabeçalho sem negrito; testar contraste em tabela e painéis.
- Persistência de tema: fallback robusto para `Escuro` se a chave não existir.

## Testes manuais sugeridos
- Alternar temas durante execução; persistir, fechar e reabrir.
- Conferir contraste de cabeçalhos, seleção, filtros por coluna.
- Abrir `launchers/gui_launcher.pyw` no Windows (sem console).

## Próximos passos
- Implementar utilitário de tema + menu de tema na GUI (commit 1).
- Adicionar ícone (commit 2).
- Adicionar `gui_launcher.pyw` e doc curta (commit 3).
- Depois: README/RELEASE NOTES + PR de empacotamento.

