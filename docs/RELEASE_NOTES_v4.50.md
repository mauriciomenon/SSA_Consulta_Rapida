# Release v4.50

Data: 2026-09-08. Fonte: branch `dev`.

## Correcoes

- Importacao otimizada preserva o contrato canonical, transacoes e ordem de duplicados.
- Resultados de importacao ficam isolados por thread; gravacao parcial provoca recarga mesmo com falha ou cancelamento posterior.
- Relatorio de integridade descreve o banco restaurado.
- Busca vazia cancela trabalho anterior, preserva desfazer e rejeita resultados atrasados.
- Caches possuem limites em bytes; detalhes guardam posicoes sem reter DataFrames filtrados.
- O CLI simplificado le o banner de `VERSION` pelo caminho do script, sem depender do diretorio de execucao. Main e GUI nao exibem mais `3.11+` quando o carregamento da versao falha; registram a causa e indicam indisponibilidade.

## Distribuicao e validacao

Publicacao de fontes, sem novos binarios ou instaladores.
Compilacao, lint, tipos e testes focados foram executados no macOS. A validacao de artefatos Windows/Linux nao esta incluida nesta publicacao.
