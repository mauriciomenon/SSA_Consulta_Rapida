# SSA Consulta Rápida v3.0.3

Tag: v3.0.3

Refino de UX da CLI, logs rotativos e robustez de configurações.

Principais mudanças:
- CLI
  - Sem listagem automática do DB ao iniciar; mostra apenas contagem + dica + comandos.
  - Ajuda com alias curto: `?` (além de `-h`).
  - “Nº SSA” sempre visível e fixado como 2ª coluna após `#`.
  - Ordem inicial “pinned” de colunas: `# | Nº SSA | Loc. | Exe. | St. | Desc. | …`.
  - Mesma largura da 1ª página e das demais; cabeçalho vazio nas páginas seguintes para manter alinhamento.
  - A “Descrição da SSA” ocupa exatamente o espaço restante após outras colunas (melhor uso do terminal).
  - Termos separados por espaço acumulam no filtro; negativos com `!termo` funcionam em conjunto.
  - Rótulos curtos padronizados: `Exe.`, `St.`, `Prog.`, `Emi.` (mantendo “Nº SSA”).

- Logging
  - Log em arquivo com rotação: `logs/ssa.log` (1 MB, 1 backup). Console exibe apenas warnings+.
  - Aviso de parsing ISO de datas silenciado (formato explícito aceito).

- Configurações
  - Geração automática de `default_settings.json` quando o `.example` estiver ausente.
  0  Auto-regeneração de `display_mappings.json` e `column_mappings.json` quando os `.example` não existirem (com log), respeitando `SSA_CONFIG_DIR`.

Testes
- Suíte: 67 passando.

Como atualizar
1) Atualize para a tag v3.0.3.
2) Ajustes finos de largura podem ser feitos por rótulo em `config/settings.json` (`display_settings.column_widths`).

Links
- Tag: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v3.0.3
- Notas v3.0.2: docs_saida/RELEASE_v3.0.2.md
- Notas v3.0.1: docs_saida/RELEASE_v3.0.1.md
- Notas v3.0.0: docs_saida/RELEASE_v3.0.0.md
