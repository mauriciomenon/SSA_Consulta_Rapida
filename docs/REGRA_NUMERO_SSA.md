Especificação do Número SSA

Objetivo: padronizar validação e formatação do campo `numero_ssa` em todo o projeto.

Regra canônica
- Formato: 9 dígitos, sendo `YYYY` + 5 dígitos sequenciais.
- Ano permitido: 1980–2050 (inclusive).
- Entradas com mais de 9 dígitos: considerar apenas os 9 primeiros.
- Entradas com menos de 9 dígitos: inválidas para persistência/valor numérico.

APIs principais
- Valor numérico (para persistência e comparações):
  - Função: `armazenamento.database._normalize_numero_ssa_value(value) -> int | None`
  - Comportamento:
    - Extrai apenas dígitos do `value`.
    - Se vazio → `None`.
    - Se `len(dígitos) > 9` → usa os 9 primeiros.
    - Se `len(dígitos) != 9` → `None`.
    - Se ano (4 primeiros dígitos) não estiver entre 1980–2050 → `None`.
    - Caso válido → retorna `int(YYYYNNNNN)`.

- Formatação para exibição (string de 9 dígitos):
  - Função: `armazenamento.database.normalize_numero_ssa(value) -> str | None`
  - Casos aceitos:
    - `None`/vazio → `None`.
    - Remove não‑dígitos e zeros à esquerda para decidir casos curtos.
    - 1..5 dígitos (após remover zeros à esquerda) → prefixa "2025" e completa para 5: "2025" + zfill(5).
    - 7 dígitos iniciando com 21–25 → prefixa "20" (ex.: "2501234" → "202501234").
    - Ainda <9 → zfill(9).
    - >9 → usa os 9 primeiros.
    - 9 → retorna como está.

Motivação
- Evitar SSAs inválidos (comprimento incorreto ou ano fora do intervalo).
- Manter comportamento previsível para exibição de casos curtos (ex.: rascunhos, entradas parciais) sem comprometer a persistência.

Testes relacionados
- `tests/test_ssa_normalization_db.py`
- `tests/test_db_reset_and_upsert.py`

Observações
- A camada de persistência deve sempre usar a função numérica `_normalize_numero_ssa_value` (retorna `None` quando inválido).
- A camada de exibição pode usar `normalize_numero_ssa` para representar entradas parciais de maneira consistente, sem comprometer a validação.

