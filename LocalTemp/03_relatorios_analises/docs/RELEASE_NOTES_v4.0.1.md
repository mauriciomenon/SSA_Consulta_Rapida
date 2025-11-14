# SSA Consulta Rapida v4.0.1

Data: 2025-10-03

## Destaques
- GUI: OU por coluna via botao [+ OU], mantendo armazenamento interno com virgulas e exibindo "OU" apenas na UI.
- Robustez: Limpeza explicita de QThreads (finished→deleteLater, quit()+wait(), desconexao de sinais) para evitar o warning "QThread: Destroyed while thread ... is still running".
- Documentacao: Relatorio dos ultimos 50 commits com historico de branches, decisoes e mapeamento de temas: `docs/HISTORICO_ULTIMOS_50_COMMITS.md` (com indice navegavel e apendice de comandos).
- Sem alteracoes cosmeticas nao solicitadas: nenhuma mudanca em larguras de colunas ou temas/paletas.

## Compatibilidade
- Sem mudancas de esquema de banco.
- Sem alteracoes de sintaxe de filtros. A novidade e apenas UI (botao [+ OU]) para compor OU dentro da mesma coluna.

## Notas de Upgrade
- Nenhuma acao obrigatoria. Se usar builds, gere novamente executaveis se necessario.

## Referencias
- Historico detalhado: `docs/HISTORICO_ULTIMOS_50_COMMITS.md`.
- Versao em `config/version.json` atualizada para 4.0.1.

## Agradecimentos
- Obrigado por manter a diretriz de estabilidade visual e por priorizar robustez nas threads e paridade de filtros entre interfaces.
