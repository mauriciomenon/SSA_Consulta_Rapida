Especificacao do Numero SSA

Objetivo: padronizar validacao e formatacao do campo `numero_ssa` em todo o projeto.

Regra canonica
- Formato operacional atual: 9 digitos (`YYYY` + 5 digitos sequenciais) nas planilhas validadas do fluxo principal.
- Ano permitido: 1980–2050 (inclusive).
- Entradas com letras: invalidas para persistencia/valor canonico.
- Entradas com mais de 9 digitos nao devem ser tratadas como referencia de export atual sem evidencia de planilha real.
- Entradas com menos de 9 digitos: invalidas para persistencia/valor numerico.

APIs principais
- Persistencia e validacao do fluxo principal:
  - usar a referencia operacional de 9 digitos nas planilhas atuais
  - rejeitar letras e simbolos fora de `[0-9 -]`
  - manter ano no intervalo 1980-2050
  - tratar sobrecomprimento como caso legacy, nunca como evidencia de export atual

- Fachadas publicas retrocompativeis:
  - nomes antigos continuam existindo para evitar quebra de imports
  - essas fachadas agora seguem o mesmo contrato canonico de 9 digitos
  - entradas curtas nao devem virar SSA valida por prefixo de ano, zero-padding ou outras heuristicas de exibicao
  - decisao atual do projeto: valor curto invalido deve ser descartado e logado

Motivacao
- Evitar SSAs invalidos (comprimento incorreto ou ano fora do intervalo).
- Evitar que exibicao ou retrocompatibilidade redefinam o contrato de persistencia.
- Evitar aceitar silenciosamente entradas com letras ou sobrecomprimento.
- Separar claramente referencia operacional atual de compatibilidades legacy do helper.

Testes relacionados
- `tests/test_ssa_normalization_db.py`
- `tests/test_db_reset_and_upsert.py`

Observacoes
- A camada de persistencia deve sempre usar a forma textual canonica do `numero_ssa`.
- O helper numerico interno `_normalize_numero_ssa_value` existe apenas para compatibilidade de callsites legados e nao define o contrato do banco.
- Para DataFrame, o nome explicito do caminho canonico e `normalize_numero_ssa_dataframe_storage(...)`; `normalize_numero_ssa_dataframe(...)` permanece apenas como alias legado de nome para o mesmo comportamento textual.
- Qualquer regra antiga de prefixar ano para valor curto deve ser tratada como historica e superada pela decisao atual: curto invalido descarta e loga.
- A camada de exibicao deve mostrar o valor canonico somente quando ele for valido; entradas invalidas permanecem invalidas.


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

