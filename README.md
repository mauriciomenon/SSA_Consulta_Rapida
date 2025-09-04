# SSA_Consulta_Rapida

Versão: 3.10 - SSA Consulta Rápida v3.10

Novidades v3.10:
- Correção: `IndentationError` no GUI PoC (`gui/gui_ssa_poc.py`) resolvido.
- Refatoração: `filter_data` simplificado com `_parse_search_terms` e `_show_unfiltered_preview`.
- Padronização: unificação de helpers de formatação e uso consistente na GUI.
- Teste: adicionado smoke test da GUI (`tests/gui_poc_smoke_test.py`).
- Tooling: `.sourcery.yaml` configurado para reduzir alertas não críticos (foco em problemas relevantes).
 - GUI: painel “Filtros por Coluna” compacto (labels próximos, botões fixos) e estabilidade de larguras (recalcula apenas em mudança de colunas ou viewport > 12 px).
 - Tema Claro: contraste reforçado (caixas “Semana” e “Status” com fundo #eee e borda #aaa). Ajuda da busca em TL;DR e placeholder/labels mais claros.

Resumo do 3.0:
- Filtro “5 opções” implementado (CLI/GUI) com negativos e fallback de regex
- Modo padrão de filtro configurável (-c) e default_filters aplicados no start
- GUI com proteção de instância única e tooltip de ajuda nos modos
- Documentação revisada (README/MAPA/CHANGELOG); 67 testes passando

Ferramenta para consulta rápida de SSAs com CLI e GUI (Python). Foco em previsibilidade, desempenho e paridade de exibição.

Links úteis:
- Mapa de Pedidos → Implementações: docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md
- Changelog técnico: docs_saida/CHANGELOG_IMPLEMENTACOES.md

## Requisitos
- Python 3.13+
- Windows (testado) ou ambiente compatível com PyQt6

## Instalação
```pwsh
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso rápido
- CLI (padrão):
```pwsh
python main.py
```
- GUI:
```pwsh
python main.py --gui
```

Notas de importação e versão dos dados:
- O arquivo “mais novo” é escolhido pela data no nome (quando existir), senão por mtime/ctime
- Em empates/sem data, a evolução de situação desempata (ASE → ADI → APL → APG → SPG → SEE → SAD → STE)

## Regras de exibição (CLI/GUI)
- Numero SSA com 9 dígitos (prefixo ano para <=5 dígitos; zfill p/ 7–8)
- Datas: dd/mm/yyyy (sem horário)
- Semanas: inteiras (sem “.0”)
- Valores nulos: não exibir "nan/NaT/None" (usa “-” quando aplicável)

Extras do CLI
- Destaque de termos da última busca (negrito ANSI quando suportado). Defina NO_COLOR=1 ou SSA_NO_COLOR=1 para desativar
- Larguras fixas por rótulo (overrides): ver “Configuração” abaixo
- Filtros avançados “5 opções” por termo (implementado):
	- contém (padrão): foo
	- começa com: ^foo
	- termina com: foo$
	- igual: =foo
	- regex: ~foo.*bar
	- negativos: prefixe ! ou - (ex.: !^adm, !$2025, !=fechado, !~cancel.*)
	- modo padrão configurável: `-c` abre menu para ajustar `user_preferences.filter_mode_default`

## CLI – guia rápido
Comandos principais: `-ord/-ordi/-ordn/-ordni`, `-cols`, `-f/-filtros`, `-x`, `-v`, `-clear`, `-clearall`, `-rescan`, export.

Exemplos:
```text
# ordenar por data de cadastro (desc)
-ord data_cadastro desc

# listar colunas com rótulos
-cols

# aplicar filtro contendo e negativo
MEL4,!cancelada

# remover último termo da pilha
-v

# remover termo específico
-x cancelada
```

Filtro “5 opções” (implementado)
- contém (padrão): `foo`
- começa com: `^foo`
- termina com: `foo$` ou `$foo`
- igual: `=foo`
- regex: `~foo.*bar` (quando o modo padrão é regex, `^`/`$` funcionam como âncoras)
- negativos: prefixar `!` ou `-` (ex.: `!^adm`, `!$2025`, `!=fechado`, `!~cancel.*`)

## GUI – desempenho e previsibilidade
- Modelo leve (QAbstractTableModel)
- Filtro com debounce (~250–350 ms) e botão “Aplicar”; ajuda TL;DR sob o campo de busca
- Filtros por Coluna compactos: labels próximos, botões fixos (Aplicar/Limpar) e largura estável
- Estabilidade de colunas: larguras só recalculam quando muda o conjunto/ordem de colunas ou o viewport varia > 12 px
- Indicador [f] no cabeçalho quando uma coluna tem filtro ativo
- Suporte a `=NULL`/`NULL` e `!` (negativos) também na GUI, igual ao CLI
- Resguardo de instância única: se já houver uma janela aberta, um novo `--gui` não abre outra
- Seletor de colunas com nomes de exibição e ordem preservada

## Temas (GUI)
- Alternância: Claro, Escuro e Gruvbox
- Tema Claro com contraste melhorado: caixas informativas (Semana, Status) usam fundo cinza-claro e borda visível
- Dica de busca (TL;DR) legível em claro/escuro
- Persistência do tema em `config/gui_main_preferences.json`

## GUI – filtros (TL;DR)
- Separe termos por vírgulas: `foo, bar`
- Modos por termo: contém (`foo`), começa (`^foo`), termina (`foo$`), igual (`=foo`), regex (`~padrao`), excluir (`!termo`)
- Por coluna: clique direito no cabeçalho para abrir o painel; campos exibem a mesma dica TL;DR

## Importação – robustez
- Ignora arquivos sem colunas obrigatórias (ex.: `numero_ssa`) com log
- `KeyboardInterrupt` (Ctrl+C) cancela com rollback seguro

## Configuração e integridade
- Prioridades/labels: `config/column_priority.json` (estrutura: essential, always_visible, priority_order, short_labels, fixed_widths, hidden_by_default)
- Larguras fixas e overrides:
	- `fixed_widths` (por nome interno) em `column_priority.json`
	- `display_settings.column_widths` (por rótulo de exibição/curto) em `config/settings.json`
	- O `table_printer` mescla rótulo→coluna para compor a largura efetiva
- Mapeamentos: `display_mappings.json` e `column_mappings.json` têm auto-restauração (integrity) via `core/config_manager.py`; respeitam `SSA_CONFIG_DIR`
- Proteção do “arquivo mais recente”: README/CHANGELOG e JSONs de config são ignorados

## Exportação
- CSV/XLSX/JSON em `docs_saida/` com rótulos consistentes (usa `display_mappings`)

## Hooks de Git (bloqueio de arquivos grandes)
- Pre-commit (>99MB): `scripts/pre-commit-size-check.ps1`
- Pre-push (objetos >=99MB no histórico): `scripts/pre-push-large-object-check.ps1`

Ativação:
```pwsh
pwsh -NoProfile -File scripts/setup-git-hooks.ps1
```

## Testes
```pwsh
pytest -q
```

## Solução de problemas
- “Headers sumindo” em terminal estreito: use `-cols` e aumente a largura; colunas `always_visible` nunca são descartadas
- “Rótulo curto” inesperado: desative `prefer_short_labels` no `settings.json`
- “Filtro lento” na GUI: debounce já ativo; desmarque “Aplicar automaticamente” para aplicar só ao clicar
- “Mapeamento ausente/corrompido”: defina `SSA_CONFIG_DIR` e deixe o loader recriar os JSONs

## Notas
- Consulte `docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md` para pedidos/entregas/validação
- Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para decisões e linha do tempo técnica
