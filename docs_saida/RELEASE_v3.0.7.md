# SSA Consulta Rápida v3.0.7

Tag: v3.0.7

Resumo:
- Correção do IndentationError no GUI PoC (`gui/gui_ssa_poc.py`).
- Refatoração do método `filter_data` (parsing e preview extraídos para helpers).
- Unificação de helpers de formatação e uso consistente em detalhes/cópia.
- Adicionado smoke test de GUI (`tests/gui_poc_smoke_test.py`).
- Configuração do Sourcery para reduzir alertas não críticos (`.sourcery.yaml`).
- Atualizações de mensagens/versões em scripts e README.

Notas:
- Banco `data/ssas.db` atualizado e verificado (integrity_check: ok).

Como atualizar:
1) `git pull` na branch `main`.
2) Opcional: checkout da tag `v3.0.7`.
3) Ativar ambiente e rodar `python main.py` (CLI) ou `python main.py --gui`.

