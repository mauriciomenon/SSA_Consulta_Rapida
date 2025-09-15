## Notas de Padronização e Governança (2025-09)

Foram aplicadas melhorias recentes de qualidade de código:

- Redução de números mágicos: constantes adicionadas em `armazenamento/database.py` (`NUMERO_SSA_LEN`, limites de ano, `MAX_TEXT_LEN`, etc.).
- Normalização de `numero_ssa`: funções consolidadas e uso consistente das regras (YYYY + 5 dígitos) com validação defensiva.
- Linhas longas (>100 colunas) quebradas para melhorar leitura e conformidade com lint.
- Remoção de `bare except` e adoção de verificações explícitas (`except Exception`).
- Marcação seletiva de `# noqa: S608` apenas onde interpolação de nome de tabela é segura (nome controlado internamente) para suprimir falso positivo de SQL injection.
- Suppressões de complexidade (`PLR0912`, `PLR0915`, etc.) usadas temporariamente em funções grandes; refatoração futura recomendada dividindo em helpers menores.
- Imports reorganizados e migração para tipos PEP 585 (`dict[str, Any]`).

Se novos avisos aparecerem:
1. Verifique se é possível resolver de forma estrutural antes de adicionar `noqa`.
2. Centralize novos limites em constantes.
3. Evite adicionar dependências não essenciais; priorize a lista mínima em `requirements.txt`.

Para auditoria de termos sensíveis existe um scanner interno (script em `scripts_manutencao/`) configurado para varrer apenas diretórios relevantes e ignorar arquivos grandes de dados.

Esta seção serve como referência rápida para manter a consistência daqui em diante.
# SSA_Consulta_Rapida

Versão atual: 3.10 (Sistema funcional)

##  Novidades v3.10 - Build System Multi-Plataforma

### ✅ Sistema de Build Completo
- **Executáveis funcionais**: CLI e GUI totalmente testados para macOS ARM64
- **Build rápido**: 30 segundos para desenvolvimento e testes
- **Build otimizado**: 1-5 minutos para produção com cache inteligente
- **Entry points corrigidos**: GUI principal (2232 linhas) em vez do POC

###  Otimizações Implementadas
- **Dependências reduzidas**: 236 → 6 pacotes essenciais
- **Cache de ambiente virtual**: Reutilização acelera builds subsequentes
- **Módulos resolvidos**: secrets, urllib, pandas, openpyxl totalmente funcionais
- **Documentação atualizada**: Vírgulas corrigidas, estrutura organizada

###  Como Usar os Executáveis
```bash
# CLI (teste rápido)
./launchers/dist/macos_arm64/SSA_CLI_v3.10_macos_arm64/SSA_CLI_v3.10_macos_arm64 --help

# GUI (App macOS)
open launchers/dist/macos_arm64/SSA_GUI_v3.10_macos_arm64.app

# Build próprio rápido
python launchers/build_simple.py gui && cd launchers/dist_simple && ./gui_entry
```

###  Funcionalidades v3.0 (Estáveis)_Rapida

Versão: 3.10 - SSA Consulta Rápida v3.10

Novidades v3.10:
- Remoção: GUI PoC (`gui/gui_ssa_poc.py`) retirada do repositório para reduzir ruído e simplificar manutenção.
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

Para build Windows com compressão UPX (redução de tamanho), instale também:
```pwsh
pip install -r launchers/platforms/windows_amd64/requirements_windows_build.txt
```
Esse arquivo separado evita alerta de dependência ausente em ambientes macOS/Linux onde `upx4py` não é necessário.

## Inicialização automática de diretórios
Na primeira execução o sistema garante a criação idempotente dos diretórios essenciais (ex.: `data/`, `data/historico_backups/`, `logs/`, `reports/`, `extracao/`, `exportacao/`).

Mecanismo:
- Implementado em `utils.setup_project_structure.setup_dirs()` e chamado cedo no `main.py`.
- Só registra log de nível INFO quando um diretório é criado pela primeira vez.
- Variável de ambiente opcional `SSA_EXTRA_DIRS="dir1,dir2"` permite acrescentar diretórios adicionais.
- Caso exista lógica legada mais rica pode ser reaproveitada definindo `SSA_LEGACY_SETUP_MODULE` apontando para um módulo Python que exponha `legacy_required_dirs() -> list[str]`; as pastas extras serão mescladas.

Validação:
- Teste de guarda `tests/test_setup_project_structure.py` impede remoção silenciosa.
- Método `setup_project_structure.validate()` pode ser usado em diagnósticos.

Exemplo rápido (adicionando diretórios extras temporários):
```bash
SSA_EXTRA_DIRS="tmp_cache,tmp_export" python main.py --help
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

### Script Unificado / Headless

Agora utilize o script para modos padronizados:

```
./scripts/run_tests.sh        # quiet
./scripts/run_tests.sh full   # verbose (-vv)
./scripts/run_tests.sh debug  # verbose + prints (-s)
./scripts/run_tests.sh cov    # cobertura
```

Filtrar por expressão:

```
PYTEST_ADDOPTS="-k upsert" ./scripts/run_tests.sh debug
```

Ambiente headless (Qt offscreen) já é configurado via `tests/conftest.py`. Se necessário reforçar manualmente:
```
QT_QPA_PLATFORM=offscreen ./scripts/run_tests.sh full
```

Documentação detalhada: `docs/TESTING_HEADLESS.md`.

### Quality Gates (Agregador)

O script `scripts/run_quality_gates.py` executa e consolida três (ou mais) gates de qualidade em uma única linha JSON:

Gates padrão:
- `validate_configs`: valida JSONs em `config/`.
- `smoke_cli`: execução mínima da CLI para garantir import e fluxo básico.
- `check_docs`: validação sintática/estrutural de arquivos Markdown selecionados.

Extensões:
- `--extra-config-dir <dir>` (pode repetir): cada diretório gera um gate adicional nomeado `validate_configs_extra_1`, `validate_configs_extra_2`, ... usando `validate_configs` apontado para aquele diretório via `--config-dir`.
- `--extra-doc <arquivo.md>` (pode repetir): adiciona arquivos ao escopo de `check_docs`.
- `--skip <gate>` / `--only <gate>`: filtram execução (`validate_configs`, `smoke_cli`, `check_docs`).
- `--no-fail-on-doc-issues`: torna problemas de documentação não-fatais (gate continua reportando issues porém status pode permanecer `ok`).

Formato JSON (resumido):
```json
{
	"overall_status": "ok|fail|error",
	"summary": { "overall_status": "ok", "executed_gates": ["validate_configs", "smoke_cli", ...] },
	"gates": {
		"validate_configs": {"status": "ok", "exit_code": 0, ...},
		"validate_configs_extra_1": {"status": "ok", ...}
	},
	"validate_configs": {"status": "ok", ...} // flatten redundante para compatibilidade de testes
}
```

Regras de severidade:
- `fail` tem precedência sobre `error` (um único gate `fail` define `overall_status=fail`).
- `error` usado para falhas internas (ex.: exceção inesperada, timeout, uso incorreto de argumento).

Exemplos:
```bash
# Caminho feliz completo
python scripts/run_quality_gates.py

# Apenas validar configs + dois diretórios extras
python scripts/run_quality_gates.py \
	--extra-config-dir caminho/dirA \
	--extra-config-dir caminho/dirB \
	--skip smoke_cli --skip check_docs

# Validar docs adicionais sem falhar por issues
python scripts/run_quality_gates.py --extra-doc README.md --no-fail-on-doc-issues
```

Teste dedicado: `tests/test_quality_gates_extra_config_dirs.py` assegura criação dos gates extras. Cenários de falha controlada: `tests/test_quality_gates_fail_paths.py`.

Boas práticas:
- Mantenha saída do script em **uma linha** (facilita parsing em pipelines).
- Para novos gates, seguir padrão de retorno (JSON parseável, exit codes 0/1/2) e adicionar documentação aqui.
- Evite acoplamento direto em CI: parse do `overall_status` é suficiente para bloquear.


### Estratégia de Testes (Governança)
Documento detalhado de pirâmide, fixtures, política de dtypes e limiares progressivos: consulte `docs/TESTING_STRATEGY.md`.

Executar smoke essencial (gates + núcleo integração rápido):
```
pytest -m "smoke" -q
```
Executar integração (exclui legacy/slow):
```
pytest -m "integration and not legacy and not slow" -q
```
Cobertura rápida dos módulos principais:
```
pytest --cov=armazenamento --cov=core --cov-report=term-missing -q
```

## Interface de Tabela (CLI) – Nova Implementação 2025-09

O módulo `interface/table_printer.py` foi reescrito para oferecer:

Principais características:
- Seleção dinâmica de colunas com prioridade (`essential`, `always_visible`, `priority_order`).
- Paginação estável com cabeçalho de página: `Página X de Y` e prompts interativos (`Enter`, `f`, `q`).
- Truncagem segura de descrições com largura mínima (`MIN_TRUNCATE_WIDTH = 8`) e expansão quando houver espaço.
- Heurística de largura baseada no percentil 95 do tamanho das células (evita efeito de outliers).
- Reatribuição adaptativa de espaço residual extra para `descricao_ssa` (até limite de 200 chars).
- Normalização de `numero_ssa` (_normalize_ssa) aplicada antes da renderização.
- Backwards compatibility: assinatura antiga de `_select_columns_for_width` ainda suportada por testes legados.
- Modo compacto automático quando:
	- largura do terminal < 100 colunas ou
	- número de colunas selecionadas >= 6
- Sanitização agressiva: remove controles ASCII, normaliza Unicode ⇒ ASCII, substitui vazio por `-`.
- Funções públicas exportadas: `pretty_print_df`, `format_dataframe_for_cli`, `paginate_dataframe`, `get_terminal_size`.

Constantes principais (ajude-se consultando o código):
```
HASH_COLUMN = '#'
HASH_WIDTH = 4
MAX_COL_WIDTH = 70
MAX_DESC_WIDTH = 200
PERCENTIL_WIDTH = 0.95
MIN_TRUNCATE_WIDTH = 8
SMALL_COLUMN_THRESHOLD = 4
SSA_FULL_LENGTH = 9
SSA_SHORT_THRESHOLD = 5
SSA_YEAR_PREFIX = '2025'
```

### Uso Básico
```python
from interface.table_printer import pretty_print_df, format_dataframe_for_cli
import pandas as pd

df = pd.DataFrame([
		{"numero_ssa": "202512345", "situacao": "APL", "descricao_ssa": "Trocar válvula"},
		{"numero_ssa": "123", "situacao": "ADI", "descricao_ssa": "Inspeção"},
])

# Impressão paginada interativa
pretty_print_df(df, display_map={"numero_ssa": "Número SSA", "situacao": "Sit.", "descricao_ssa": "Descrição"}, settings={})

# Obter string formatada (sem paginação) – útil para logs ou export improvisado
table_str = format_dataframe_for_cli(df, display_map={"numero_ssa": "Número SSA"})
print(table_str)
```

### Configuração de Larguras e Visibilidade
- `config/column_priority.json` define: `essential`, `always_visible`, `priority_order`, `short_labels`, `fixed_widths`.
- `config/settings.json` (chave `display_settings`):
	- `column_widths`: mapeamento por rótulo (full/short) → largura fixa.
	- `column_visibility`: `{ "coluna_interna": true/false }` (false oculta, exceto se estiver em `always_visible`).

Mesclagem de larguras:
1. `fixed_widths` (por nome interno)
2. Override por rótulo em `display_settings.column_widths` (se rótulo curto/full corresponder)
3. Caso nada definido, estima via `_estimate_column_width` (percentil 95).

### Normalização do Número SSA
Regra (_resumida_):
- Remove não-dígitos.
- Menos que 5 dígitos ⇒ retorna como está (sem prefixo artificial nesta versão).
- 9 dígitos começando com `2025` ⇒ mantido.
- >=9 dígitos sem atender condição anterior ⇒ últimos 9.

### Comportamento de Paginação
- Tamanho de página = `linhas_terminal - LOW_HEIGHT_MARGIN` (margem = 8).
- `f` após qualquer página ativa “auto-scroll” até o fim.
- Se `auto_scroll_to_end=true` nas preferências e total de páginas > `max_auto_scroll_pages`, o auto-scroll é desativado silenciosamente para evitar flood.

### Boas Práticas / Extensão
- Para adicionar nova coluna “sempre visível” sem quebrar testes: inclua em `always_visible` no JSON e garanta que mapeamentos (`display_mappings.json`) tenham rótulo correspondente.
- Evite aumentar `MAX_DESC_WIDTH` acima de 200 sem avaliar quebra de layout em terminais pequenos.
- Se precisar suportar terminal extremamente estreito (<40 colunas), considere fallback adicional reduzindo ainda mais cabeçalhos (ex.: siglas).

### Testes Cobertos
- `_normalize_ssa`: casos curtos, 9 dígitos, excesso, caracteres mistos, `None`.
- `paginate_dataframe`: vazio, divisão exata, resto, page_size=1.
- Backward compatibility: testes antigos que chamam assinatura anterior de `_select_columns_for_width` continuam funcionando (wrapper aceita kwargs legados).

### Roadmap Futuro (Sugestões)
- Cache leve de larguras por hash de amostra para grandes DataFrames.
- Modo “raw export” ignorando truncagem (para piping em scripts): flag em settings.
- Otimização de re-render parcial quando apenas filtros alteram subconjunto de linhas (mantendo colunas fixas).

---


## Solução de problemas
- “Headers sumindo” em terminal estreito: use `-cols` e aumente a largura; colunas `always_visible` nunca são descartadas
- “Rótulo curto” inesperado: desative `prefer_short_labels` no `settings.json`
- “Filtro lento” na GUI: debounce já ativo; desmarque “Aplicar automaticamente” para aplicar só ao clicar
- “Mapeamento ausente/corrompido”: defina `SSA_CONFIG_DIR` e deixe o loader recriar os JSONs

## Notas
- Consulte `docs_saida/MAPA_PEDIDOS_IMPLEMENTACOES.md` para pedidos/entregas/validação
- Consulte `docs_saida/CHANGELOG_IMPLEMENTACOES.md` para decisões e linha do tempo técnica
