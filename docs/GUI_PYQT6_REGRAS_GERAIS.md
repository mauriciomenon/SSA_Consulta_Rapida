# Regras Gerais Para GUI em PyQt6

## 1) Escopo e disciplina de mudanca
- Diagnosticar antes de editar, com evidencia objetiva.
- Aplicar patch minimo por slice.
- Evitar refatoracao ampla fora do objetivo.
- Listar impacto antes de alterar arquivos existentes.

## 2) Validacao obrigatoria
- Validar sempre no ambiente virtual do projeto.
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
