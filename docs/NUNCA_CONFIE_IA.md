# NUNCA CONFIE IA

Este documento existe porque ja houve erro grave demais em fluxo critico de dados.
Ele nao e teoria. Ele registra falhas reais ocorridas neste repo para impedir repeticao.

## Objetivo

1. impedir que hipotese vire contrato operacional sem evidencia
2. impedir que teste synthetic contamine runtime
3. impedir sidequest, worktree sujo esquecido e doc stale
4. reduzir regressao e reintroducao de erro em ciclos longos

## Incidentes reais que motivaram este documento

### 1. numero_ssa de 10 digitos virou contrato sem prova

O que aconteceu:
1. numero bruto achado em XML/regex de `.xlsx` foi confundido com `numero_ssa` realmente extraido pelo pipeline
2. um teste synthetic com `2026000654` contaminou runtime e docs
3. o helper central passou a aceitar `10 digitos` sem planilha real provando isso

Evidencia:
1. commit `ea50416a` introduziu a narrativa `10-digit exports`
2. commit `f9c71b77` removeu esse caminho synthetic
3. planilhas reais medidas nesta rodada produziram `9 digitos`, nao `10`

Regra obrigatoria:
1. nunca promover formato de identificador sem planilha real + pipeline real + teste cross-layer

### 2. bug real de ordenacao foi misturado com causa errada

O que aconteceu:
1. havia bug real na ordem dos snapshots
2. a correcao valida era a ordenacao por data embutida no nome
3. junto disso entrou uma tese errada sobre `10 digitos`

Regra obrigatoria:
1. quando houver bug real, isolar a causa antes de ampliar o escopo do patch
2. nao colar "talvez relacionado" no mesmo commit de hotfix critico

### 3. storage e exibicao quase voltaram a se misturar

O que aconteceu:
1. `shared/numero_ssa.py` dizia ser strict, mas ainda carregava regra de exibicao
2. o caminho de storage quase ficou dependente de heuristica de ano dinamico

Regra obrigatoria:
1. strict/canonico
2. storage/persistencia
3. exibicao/compatibilidade
4. essas tres coisas devem ficar separadas

### 4. docs vivos ficaram stale e atrapalharam o proximo ciclo

O que aconteceu:
1. backlog e handoff ficaram descrevendo slice antigo
2. `docs/README.md` mandava reabrir configuracao de Kluster quando isso ja nao era o trabalho atual

Regra obrigatoria:
1. se o topo do backlog/handoff ficar stale, corrigir no mesmo ciclo

## Regras de contencao antes de tocar em fluxo critico

### Evidencia minima

Antes de editar:
1. identificar arquivo e funcao alvo
2. provar o comportamento com repro real ou teste real
3. dizer explicitamente o que nao sera alterado
4. listar se a evidencia veio de:
   - planilha real
   - pipeline real
   - banco real
   - teste synthetic
   - regex/XML bruto

Nunca aceitar como prova suficiente:
1. regex em XML de `.xlsx`
2. teste synthetic isolado
3. comentario de bot
4. "parece que"
5. "deve ser"

### Testes obrigatorios em caminho critico

Se o patch tocar em `numero_ssa`, importacao, upsert, cache ou CLI:
1. teste positivo com dado realista
2. teste negativo do mesmo contrato
3. teste cross-layer
4. teste de integracao do fluxo tocado
5. pelo menos um teste que prove resultado, nao apenas ausencia de crash

### Anti-padroes proibidos

1. teste synthetic definindo contrato operacional
2. helper do helper sem necessidade real
3. regra paralela de normalizacao fora da fonte central
4. fallback silencioso no caminho de storage
5. usar exibicao para decidir persistencia
6. sidequest antes de aterrar slice local aberto
7. doc viva stale dizendo para continuar um trabalho ja encerrado

## Checklist curto antes de commit em fluxo critico

1. o contrato foi provado em dado real?
2. o teste novo falha sem o patch?
3. strict, storage e exibicao continuam separados?
4. nao entrou regra nova por inferencia?
5. docs vivos do topo continuam verdadeiros?
6. o slice aberto anterior foi aterrado ou explicitamente mantido?

## Checklist curto antes de acreditar em review de IA

1. a IA leu o arquivo inteiro ou so o diff?
2. a IA esta confundindo dado bruto com campo extraido?
3. a IA esta usando teste synthetic como se fosse producao?
4. a IA esta propondo helper novo sem cortar o antigo?
5. a IA esta abrindo sidequest?
6. a IA esta atualizando handoff/backlog no mesmo ciclo?

## Areas do repo que exigem paranoia extra

1. `shared/numero_ssa.py`
2. `armazenamento/numero_ssa_utils.py`
3. `armazenamento/database_upsert_logic.py`
4. `armazenamento/database_optimized.py`
5. `core/app_logic.py`
6. `utils/caching.py`
7. `utils/formatting.py`

## Regra final

Se a IA nao consegue provar com:
1. planilha real
2. pipeline real
3. teste de contrato
4. diff minimo

entao a resposta correta e:
1. parar
2. medir
3. provar
4. so depois editar

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

