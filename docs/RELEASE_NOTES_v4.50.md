# Release v4.50

Data: 2026-09-08. Fonte: branch `dev`.

## Correcoes

- Importacao otimizada preserva o contrato canonical, transacoes e ordem de duplicados.
- Resultados de importacao ficam isolados por thread; gravacao parcial provoca recarga mesmo com falha ou cancelamento posterior.
- Relatorio de integridade descreve o banco restaurado.
- Busca vazia cancela trabalho anterior, preserva desfazer e rejeita resultados atrasados.
- Caches possuem limites em bytes; detalhes guardam posicoes sem reter DataFrames filtrados.
- O CLI simplificado le o banner de `VERSION` pelo caminho do script, sem depender do diretorio de execucao. Main e GUI nao exibem mais `3.11+` quando o carregamento da versao falha; registram a causa e indicam indisponibilidade.

## Validacao e limites

Compilacao, Ruff e ty aprovados no codigo alterado. Rodadas integradas e focadas, revisoes independentes, scanners e oito fluxos de desempenho constam no [controle da rodada](CONTROLE_CORRECOES_REVISAO_2026_09_08.md).
GUI real exercitada no macOS. A repeticao final da suite ampla e do smoke visual foi interrompida por pedido do usuario; nao conta como aprovada.
Clawpatch teve bloqueio HTTP 429. A auditoria de dependencias possui pendencias anteriores descritas no controle.
Sem novos binarios, instaladores ou validacao de artefatos Windows/Linux nesta publicacao.
