# SSA Consulta Rápida v4.0.1

Data: 2025-10-03

## Destaques
- GUI: OU por coluna via botão [+ OU], mantendo armazenamento interno com vírgulas e exibindo "OU" apenas na UI.
- Robustez: Limpeza explícita de QThreads (finished→deleteLater, quit()+wait(), desconexão de sinais) para evitar o warning "QThread: Destroyed while thread … is still running".
- Documentação: Relatório dos últimos 50 commits com histórico de branches, decisões e mapeamento de temas: `docs/HISTORICO_ULTIMOS_50_COMMITS.md` (com índice navegável e apêndice de comandos).
- Sem alterações cosméticas não solicitadas: nenhuma mudança em larguras de colunas ou temas/paletas.

## Compatibilidade
- Sem mudanças de esquema de banco.
- Sem alterações de sintaxe de filtros. A novidade é apenas UI (botão [+ OU]) para compor OU dentro da mesma coluna.

## Notas de Upgrade
- Nenhuma ação obrigatória. Se usar builds, gere novamente executáveis se necessário.

## Referências
- Histórico detalhado: `docs/HISTORICO_ULTIMOS_50_COMMITS.md`.
- Versão em `config/version.json` atualizada para 4.0.1.

## Agradecimentos
- Obrigado por manter a diretriz de estabilidade visual e por priorizar robustez nas threads e paridade de filtros entre interfaces.
