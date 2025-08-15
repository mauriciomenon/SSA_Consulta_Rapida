# SSA Consulta Rápida v3.0.0

Data: 2025-08-15
Tag: v3.0.0
Branch: main

## Destaques
- Filtro “5 opções” implementado (CLI/GUI): contém, ^prefixo, sufixo$ (ou $foo), =igual, ~regex; negativos com ! ou -.
- Modo padrão de filtro configurável via CLI (-c); aplicado a termos sem marcadores; GUI/CLI leem de settings.
- GUI com proteção de instância única (evita múltiplas janelas); tooltip no campo de busca com ajuda dos modos.
- Documentação revisada (README/MAPA/CHANGELOG);
- Suite de testes ampliada para 67 casos.

## Mudanças Técnicas
- core/app_logic.py: parse_search_terms e filter_dataframe com 5 modos, negativos, e fallback de regex para literal.
- interface/cli.py: ajuda atualizada; aplica default_filters com default_mode; integra parser compartilhado.
- gui/gui_ssa.py: tooltip nos modos; filtragem lendo default_mode; debounce preservado; correções de indentação.
- core/config_manager.py: menu interativo (-c) para ajustar user_preferences.filter_mode_default e default_filters.
- main.py: guarda de instância única para GUI via socket local; fallback para CLI se GUI falhar.
- docs: README/MAPA/CHANGELOG atualizados com sintaxe, UX e contagem de testes.
- tests: novos testes para modos e default_mode, incluindo regex e negativos.

## Como Atualizar
1) Atualize o repositório para incluir a tag v3.0.0.
2) (Opcional) Rode `pytest -q` — esperado: 67 passed.
3) Use `-c` na CLI para ajustar o modo padrão de filtro e filtros padrão.

## Quebras de Compatibilidade
- Nenhuma intencional. Sintaxe legada de filtros (contém + negativos) continua válida.

## Créditos
- Autor/maintainer: @mauriciomenon

---

Links úteis:
- Tag: https://github.com/mauriciomenon/SSA_Consulta_Rapida/releases/tag/v3.0.0
- Changelog detalhado: docs_saida/CHANGELOG_IMPLEMENTACOES.md
- Mapa de pedidos: docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md
