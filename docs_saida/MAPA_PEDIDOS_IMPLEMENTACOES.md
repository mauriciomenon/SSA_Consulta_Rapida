# Mapa de Pedidos → Implementações (completo e rastreável)

Rastreia de ponta a ponta: o que foi pedido, o que foi feito (arquivos), como validar (testes/rodadas manuais) e o que falta. Expandido com exemplos práticos, detalhes de configuração, algoritmos e plano do filtro “5 opções”.

Última atualização: 2025-08-15 — 67 testes passando.

---

## Guia de leitura
- O mapa é dividido por temas (A..H). Cada item aponta para: implementação, arquivos, testes e exemplos curtos.
- “Como validar” traz passos rápidos (CLI/GUI) para conferir a entrega.
- Não fixamos IDs de commits para não engessar a leitura; use git log para granularidade.

---

## Quadro de rastreabilidade (pedido → entrega → validação)
- Formatação unificada sem “.0”, sem NaN/NaT/None, datas dd/mm/yyyy e semanas inteiras
  - Implementação: utils/formatting.py (format_cell, format_dataframe_for_display)
  - Superfícies: CLI e GUI usam a mesma função
  - Testes: tests/test_formatting.py, tests/test_cli_formatting.py
  - Como validar: rodar CLI/GUI e conferir datas, números inteiros e nulos ocultos

- Cabeçalhos largos x curtos; short_labels
  - Implementação: interface/table_printer.py decide labels completos vs short_labels
  - Config: config/column_priority.json (short_labels), settings.display_settings.prefer_short_labels
  - Testes: tests/test_table_printer.py
  - Como validar: redimensionar terminal; ver headers mudarem sem perder clareza

- Seleção adaptativa de colunas (sempre visíveis + prioridade)
  - Implementação: table_printer._select_columns_for_width (ordem: always_visible → essential → priority_order; garante '#')
  - Testes: tests/test_cli_column_selection.py (inclui largura extrema)
  - Como validar: usar -cols e variar largura do terminal

- Larguras fixas de colunas (pedido)
  - Implementação: fixed_widths em column_priority.json; overrides por rótulo em settings.display_settings.column_widths
  - Mescla: table_printer correlaciona rótulo→coluna para compor fixed_widths efetivo
  - Testes: tests/test_docs_and_priority.py, tests/test_cli_column_selection.py
  - Como validar: definir largura para “Executor”/“Emissor” no settings e observar efeito na seleção

- Truncação inteligente de descrições
  - Implementação: table_printer limita e só adiciona “...” quando necessário
  - Como validar: reduzir terminal e observar descrições

- CLI: ordenação, colunas, filtros, listar/remover/limpar
  - Implementação: interface/cli.py (+ display.py, table_printer.py)
  - Testes: tests/test_cli_commands.py, tests/test_cli_formatting.py
  - Como validar: ver seção “Exemplos de CLI” abaixo

- Filtro “5 opções” (implementado)
  - 5 modos por termo (contém, começa, termina, igual, regex) e negativos
  - Parser compartilhado: core/app_logic.parse_search_terms
  - Aplicação: core/app_logic.filter_dataframe suporta os modos com fallback para literal quando regex inválida
  - Marcadores aceitos: `^` (prefixo), `$` (sufixo) também como atalho inicial, `=` (igual), `~` (regex), `!`/`-` para negativos
  - Ponto fino: quando o modo padrão é `regex`, `^`/`$` funcionam como âncoras em vez de trocar o modo
  - Testes: tests/test_filter_modes.py e tests/test_default_filter_mode.py
  - UX: GUI exibe tooltip com os 5 modos; CLI ajuda inclui sintaxe

- GUI: debounce, seletor de colunas, detalhes
  - Implementação: gui/gui_ssa.py (QTimer ~250ms; paginação; duplo clique para detalhes)
  - Como validar: digitar no campo de busca, observar debounce e paginação

- Extração com integridade de mapeamentos
  - Implementação: core/config_manager.load_display_mappings_integrity e load_column_mappings_integrity; extracao/extractor usa os mapeamentos íntegros
  - Proteção “arquivo mais recente”: utils/file_metadata.py exclui configs/docs protegidos
  - Testes: tests/test_extracao.py, tests/test_column_mappings_integrity.py, tests/test_protected_files.py

- Banco de dados (reset, upsert determinístico, índices idempotentes)
  - Implementação: armazenamento/database.py; config/schema.sql
  - Testes: tests/test_database.py, tests/test_db_reset_and_upsert.py, tests/test_ssa_normalization_db.py

- Exportação consistente (CSV/XLSX/JSON)
  - Implementação: exportacao/exporter.py (usa display_mappings)
  - Testes: tests/test_exporter.py

---

## A. Apresentação e Formatação (detalhado)
1) Regras de formatação
- Números: sem sufixo “.0” quando o valor é inteiro aparente
- Datas: dd/mm/yyyy; semanas como inteiros
- Nulos: NaN/NaT/None ocultos; quando aplicável, “-” para legibilidade
- SSA: normalização para 9 dígitos (prefixo do ano quando <=5; zfill para 7-8)
Arquivos: utils/formatting.py; interface/display.py (detalhes)
Validação: tests/test_formatting.py; abrir detalhes na CLI/GUI

2) Cabeçalhos e short_labels
- Critério: usar labels completos; cair para short_labels apenas quando necessário (largura < 80) ou por preferência do usuário
- Fonte de curto: config/column_priority.json → short_labels
- Preferência: settings.display_settings.prefer_short_labels (booleana)

3) Seleção adaptativa e sempre visíveis
- Algoritmo: calcular orçamento de largura a partir do terminal, somar cabeçalhos+espaçadores, incluir na ordem: always_visible → essential → priority_order → demais
- “#” (índice) sempre incluído; sempre_visíveis nunca são descartadas

4) Larguras fixas de colunas e overrides
- fixed_widths (por nome interno da coluna) define base do cálculo
- column_widths (por rótulo de exibição/curto) permite ajuste amigável sem conhecer o nome interno
- Mescla: converte rótulos (display/short) para a coluna interna e compõe o mapa final
- Observação: o width influencia a seleção; a truncação de conteúdo é conservadora (apenas descrições)

Exemplo de override no settings.json (rótulos):
```json
{
  "display_settings": {
    "column_widths": {
      "Executor": 6,
      "Emissor": 6,
      "Semana prog.": 8,
      "Status": 5
    }
  }
}
```

---

## B. CLI e Filtros (com exemplos)
Comandos principais: -ord/-ordi/-ordn/-ordni, -cols, -f/-filtros, -x, -v, -clear, -clearall, -rescan, export.

Exemplos (opcionais para testar):
```
# ordenar por data de cadastro (desc)
-ord data_cadastro desc

# listar colunas com rótulos
-cols

# aplicar filtro contendo e negativo
MEL4,!cancelada

# remover último termo
-v

# remover termo específico
-x cancelada
```

Filtro atual (contém + negativos)
- Modo padrão: contém (case-insensitive) sobre colunas textuais
- Negativo: prefixar ! ou - em cada termo para excluir
- Empilhamento: cada busca adiciona ao stack; -v desfaz; -x remove termo específico

Filtro “5 opções” (planejamento detalhado)
- Sintaxe por termo:
  - contém (padrão): foo
  - começa com: ^foo
  - termina com: foo$
  - igual: =foo
  - regex: ~foo.*bar
  - negativos: prefixar ! (ex.: !^adm, !=fechado, !$2025, !~cancel.*)
- Parser: core/app_logic.parse_search_terms(texto: str) → List[Termo]
  - Termo: {raw, modo: {contains|prefix|suffix|exact|regex}, negativo: bool}
- Aplicação: core/app_logic.filter_dataframe(df, termos) com curto-circuito e segurança
- Segurança: regex com try/except e limite simples de tamanho; fallback para literal se inválida
- Testes a criar: combinações mistas (positivas/negativas), casos de borda (vazio, apenas negativo, regex inválida)

---

## C. GUI (comportamentos)
- Debounce: ~250ms para aplicar filtro após digitação
- Botão Buscar: alternativa previsível (aplica imediatamente)
- Seleção de colunas: baseada em display_mappings; persistência; detalhes em diálogo
- Paridade: usa utils/formatting e table_printer (onde aplicável) para consistência visual

---

## D. Importação, DB e Metadados (robustez)
- Extração resiliente: detecta cabeçalho, normaliza, remove vazios, renomeia via column_mappings.json
- Integridade de mapeamentos: se ausente/corrompido, recria defaults (SSA_CONFIG_DIR respeitado)
- Banco determinístico: upsert por numero_ssa com desempate por data_cadastro; índices idempotentes
- Proteção do “arquivo mais recente”: ignora README/CHANGELOG e JSONs de config

Como validar rapidamente:
1) Crie SSA_CONFIG_DIR temporário e remova display_mappings.json/column_mappings.json → ao rodar, serão recriados com log
2) Copie planilhas em docs_entrada e rode importação → ver DB e seleção estável
3) Testes unitários cobrem os fluxos principais

---

## E. Configuração e Integridade (formatos)
column_priority.json (estrutura canônica):
```json
{
  "essential": ["numero_ssa", "descricao_ssa"],
  "always_visible": ["numero_ssa"],
  "priority_order": ["data_cadastro", "status", "executor"],
  "short_labels": { "data_cadastro": "Dt Cad." },
  "fixed_widths": { "numero_ssa": 9, "data_cadastro": 10 },
  "hidden_by_default": []
}
```

display_mappings.json: mapa de coluna interna → rótulo de exibição

column_mappings.json: listas de possíveis cabeçalhos → coluna interna

Integridade e restauração automática:
- core/config_manager: load_display_mappings_integrity, load_column_mappings_integrity
- interface/table_printer._load_priority_config: restaura column_priority.json quando inválido

---

## F. Exportação
- CSV/XLSX/JSON com rótulos consistentes (via display_mappings)
- Verifique arquivos em docs_saida/ após exportar na CLI/GUI

---

## G. Validação rápida (checklist)
- Testes: pytest -q (esperado: 67 passed)
- Seleção/labels/larguras: rodar CLI, -cols, mudar largura do terminal
- Integridade: forçar ausência/erro dos JSONs em SSA_CONFIG_DIR e observar restauração + logs

---

## H. Próximos passos (curtos e objetivos)
P1) Implementar filtro “5 opções” com parser compartilhado e cobertura de testes
P2) Expor ajustes de largura por rótulo via CLI (-c) com persistência em settings
P3) Pequeno smoke-test de GUI (opcional) documentando atalhos; instância única já protegida em `main.py`

---

Apêndice – Exemplos adicionais de CLI (opcionais)
```
# ordenar por rótulo de exibição (desc)
-ordn "Data Cadastro" desc

# misto de termos (contém + começa com + negativo)
MEL ^ADM !cancelada

# (futuro) filtro com igualdade e sufixo
="APROVADO" PROJ$
```

Glossário
- “sempre visíveis”: colunas que nunca são descartadas, mesmo em terminais estreitos
- “short_labels”: rótulos curtos usados quando falta espaço
- “fixed_widths”: larguras base por coluna interna; “column_widths”: overrides por rótulo

Métricas rápidas
- Testes unitários: 56
- Ambientes: Windows + Python 3.13

Contato
- Abra uma issue descrevendo o pedido com exemplos de entrada/saída e prints quando aplicável.
