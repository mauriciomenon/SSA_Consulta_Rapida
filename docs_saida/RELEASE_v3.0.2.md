# SSA Consulta Rápida v3.0.2

Tag: v3.0.2

Hotfix de usabilidade da tabela (CLI) e robustez da GUI.

Correções/principais mudanças:
- CLI: restaura labels de exibição (longos/curtos conforme largura), aplica larguras fixas de `column_priority.json` (com mescla por rótulo em `settings.display_settings.column_widths`), respeita `always_visible`, `essential` e `priority_order`. Melhor aproveitamento do espaço via truncagem por largura fixa após formatação.
- GUI: corrige ordem do `sys.path` para permitir `from utils.formatting ...` quando executado diretamente (`python .\gui\gui_ssa.py`).
- Ajustes de largura: `localizacao_codigo=10`, `setor_executor=6`, `setor_emissor=6`, `data_cadastro=12`, `derivada_de=11` (em `config/column_priority.json`).

Notas:
- Sem alterações no banco ou nos modos de filtro (mantidos do 3.0.x).
- Testes: 67 passando.

Como atualizar:
1) Atualize para a tag v3.0.2.
2) Se desejar overrides por rótulo, ajuste `config/settings.json` em `display_settings.column_widths`.

Links:
- Tag: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v3.0.2
- Notas v3.0.1: docs_saida/RELEASE_v3.0.1.md
- Notas v3.0.0: docs_saida/RELEASE_v3.0.0.md
