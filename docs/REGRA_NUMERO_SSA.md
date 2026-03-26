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

- Compatibilidades legacy:
  - helpers antigos de exibicao e normalizacao continuam existindo por retrocompatibilidade
  - esses detalhes ficam cobertos por testes e pelo codigo
  - nao devem ser usados para redefinir o contrato operacional atual sem evidencia de planilha real

Motivacao
- Evitar SSAs invalidos (comprimento incorreto ou ano fora do intervalo).
- Manter comportamento previsivel para exibicao de casos curtos (ex.: rascunhos, entradas parciais) sem comprometer a persistencia.
- Evitar aceitar silenciosamente entradas com letras ou sobrecomprimento.
- Separar claramente referencia operacional atual de compatibilidades legacy do helper.

Testes relacionados
- `tests/test_ssa_normalization_db.py`
- `tests/test_db_reset_and_upsert.py`

Observacoes
- A camada de persistencia deve sempre usar a funcao numerica `_normalize_numero_ssa_value` (retorna `None` quando invalido).
- A camada de exibicao pode usar `normalize_numero_ssa` para representar entradas parciais de maneira consistente, sem comprometer a validacao.

