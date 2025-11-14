Especificacao do Numero SSA

Objetivo: padronizar validacao e formatacao do campo `numero_ssa` em todo o projeto.

Regra canonica
- Formato: 9 digitos, sendo `YYYY` + 5 digitos sequenciais.
- Ano permitido: 1980–2050 (inclusive).
- Entradas com mais de 9 digitos: considerar apenas os 9 primeiros.
- Entradas com menos de 9 digitos: invalidas para persistencia/valor numerico.

APIs principais
- Valor numerico (para persistencia e comparacoes):
  - Funcao: `armazenamento.database._normalize_numero_ssa_value(value) -> int | None`
  - Comportamento:
    - Extrai apenas digitos do `value`.
    - Se vazio → `None`.
    - Se `len(digitos) > 9` → usa os 9 primeiros.
    - Se `len(digitos) != 9` → `None`.
    - Se ano (4 primeiros digitos) nao estiver entre 1980–2050 → `None`.
    - Caso valido → retorna `int(YYYYNNNNN)`.

- Formatacao para exibicao (string de 9 digitos):
  - Funcao: `armazenamento.database.normalize_numero_ssa(value) -> str | None`
  - Casos aceitos:
    - `None`/vazio → `None`.
    - Remove nao‐digitos e zeros a esquerda para decidir casos curtos.
    - 1..5 digitos (apos remover zeros a esquerda) → prefixa "2025" e completa para 5: "2025" + zfill(5).
    - 7 digitos iniciando com 21–25 → prefixa "20" (ex.: "2501234" → "202501234").
    - Ainda <9 → zfill(9).
    - >9 → usa os 9 primeiros.
    - 9 → retorna como esta.

Motivacao
- Evitar SSAs invalidos (comprimento incorreto ou ano fora do intervalo).
- Manter comportamento previsivel para exibicao de casos curtos (ex.: rascunhos, entradas parciais) sem comprometer a persistencia.

Testes relacionados
- `tests/test_ssa_normalization_db.py`
- `tests/test_db_reset_and_upsert.py`

Observacoes
- A camada de persistencia deve sempre usar a funcao numerica `_normalize_numero_ssa_value` (retorna `None` quando invalido).
- A camada de exibicao pode usar `normalize_numero_ssa` para representar entradas parciais de maneira consistente, sem comprometer a validacao.

