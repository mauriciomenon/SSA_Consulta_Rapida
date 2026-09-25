# Regras Gerais Para GUI em PyQt6

## Atualizacao 2026-03-01 (popup/button stability follow-up)
- Em seletores com popup de multiselect, limitar largura por:
  1. largura do botao disparador
  2. limite maximo proporcional a largura de tela
  3. nunca expandir sem necessidade de conteudo real
- Em callbacks de checkbox com exclusao mutua, validar widget ativo antes de:
  1. `isChecked()`
  2. `blockSignals(...)`
  3. `setChecked(...)`
- Em botoes de acao lado a lado (`Aplicar`/`Limpar`), preferir:
  1. largura alvo compacta por orcamento de celula
  2. sem separador visual extra entre botoes
  3. sem alterar posicionamento global da janela
- Em listas de colunas para filtros, evitar placeholders de perfil e ruido tecnico.

## Atualizacao 2026-03-27 (filtros e thread principal)
- O marcador `[f]` no cabecalho deve refletir tanto filtro de coluna quanto filtro avancado equivalente.
- O resumo `Filtros ativos` nao deve duplicar o mesmo conceito vindo de mais de uma fonte de estado.
- A caixa `Filtros ativos` pode usar borda destacada e negrito como estado visual de filtro ativo, sem trocar o contrato do `[f]`.
- O prompt `Filtrar "nome da coluna"` deve expor hint curto de sintaxe no proprio dialogo.
- Operacao manual pesada de derivadas nao deve bloquear a GUI; runtime normal deve usar background e entrega por sinais/timer.
- Validacao de banco selecionado em `load_other_database()` tambem nao deve bloquear a GUI no runtime normal.
- Contagem `filtrado/total` deve ficar separada da caixa operacional de status.
- Links operacionais externos simples, como `Abrir SAM` e o clique no `#`, podem usar navegador padrao sem navegador embutido.
- O detalhe da SSA deve expandir a sigla de `situacao` e permitir copia direta do numero sem alterar o texto exibido.
- Quando o fluxo exigir exploracao de derivadas, preferir aba dedicada no dialogo de detalhes com:
  1. arvore de relacoes na metade superior
  2. detalhes da SSA na metade inferior
  3. navegacao por links entre SSAs
  4. quando houver grafo, manter renderer local (SVG) sem dependencia de engine externa

## 1) Escopo e disciplina de mudanca
- Diagnosticar antes de editar, com evidencia objetiva.
- Aplicar patch minimo por slice.
- Evitar refatoracao ampla fora do objetivo.
- Listar impacto antes de alterar arquivos existentes.

## 2) Validacao obrigatoria
- Validar sempre no ambiente virtual do projeto.
- Preferir comando padrao: `uv run --python 3.13 ...`.
- Quando 3.13 nao estiver disponivel, usar fallback em ordem: 3.12, 3.11, 3.10.
- Rodar validacoes tecnicas (compile, lint, type-check) antes de commit.
- Rodar smoke de GUI com timeout para evitar sessao travada.
- Nao declarar resolvido sem execucao real do fluxo alterado.
- Antes de declarar pronto, validar visualmente em 3 tamanhos reais:
  - minimo util;
  - tamanho padrao de abertura;
  - tela ampla.

## 3) Layout responsivo
- Usar layout managers; evitar geometria fixa manual.
- Priorizar regras continuas de layout; evitar faixas fixas rigidas.
- Quando o produto exigir, permitir politica de colunas fixas com ajuste dinamico interno por celula.
- Definir min/max width e min/max height coerentes para controles.
- Definir limites por celula para impedir crescimento exagerado de um controle especifico.
- Garantir que areas criticas de conteudo nao sejam invadidas.
- Evitar sobreposicao de titulo, label e campo.
- Evitar nesting excessivo de containers sem ganho funcional.

## 4) Visibilidade e usabilidade
- Garantir que acoes primarias fiquem acessiveis em tamanhos pequenos, medios e grandes.
- Manter barra de acoes ancorada fora do scroll de campos quando a ultima linha for critica.
- Usar scroll apenas quando necessario e com limites coerentes.
- Ajustar altura do scroll pela altura real do conteudo para evitar corte da ultima linha e espaco morto.
- Evitar espaco vazio excessivo quando ha pouco conteudo.
- Manter navegacao consistente em resize, troca de aba e troca de estado.
- Em politica de 4 colunas fixas, usar limites por celula para prevenir controles dominantes.

## 5) Tema, contraste e estilo
- Evitar hardcode de cor sem necessidade forte.
- Respeitar palette/tema ativo.
- Preservar contraste legivel para texto, foco e estados.
- Evitar estilos locais agressivos que quebrem consistencia visual.
- Politica de fonte deve ser dinamica por largura: reduzir apenas quando necessario e com piso minimo de leitura.
- Fonte de acoes primarias pode ser tratada separadamente da fonte dos campos.

## 6) Performance de UI
- Evitar recalculo caro repetido em resize, paint e montagem.
- Cachear metricas de layout quando seguro.
- Evitar processamento pesado no thread principal.
- Mover trabalho pesado para worker e atualizar via signal/slot.

## 7) Sinais, slots e estado
- Evitar conexoes duplicadas de signals.
- Bloquear sinais apenas no trecho minimo necessario.
- Sincronizar estado de widgets sem loop de eventos.
- Manter atualizacoes de UI deterministicas apos cada acao.

## 8) Tratamento de erro
- Nao usar try/except vazio.
- Nao suprimir erro real de forma silenciosa.
- Tratar excecoes em blocos relevantes, com log objetivo.
- Evitar excesso de condicionais e tratamento fragmentado sem necessidade.

## 9) Compatibilidade interna
- Se mudar assinatura de helper/facade de UI, atualizar todos os chamadores no mesmo commit.
- Evitar quebrar runtime por mudanca parcial de API interna.

## 10) Entrega
- Commits atomicos e rollback facil.
- Registrar pendencias nao bloqueantes em backlog.
- Reportar bloqueios de ambiente de forma explicita.

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

