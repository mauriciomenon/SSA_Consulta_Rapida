# ARCH DB UPSERT (legacy pointer)

Documento legado mantido para compatibilidade de referencias antigas.
Fonte ativa no baseline atual `v4.36`:

1. `docs/SCHEMA_UNIFICADO_IMPORTACAO.md`
2. `docs/ARQUITETURA_IMPORTACAO.md`

Nota tecnica 2026-03-27:

1. Upsert nao-complementar agora aplica tie-breaker de `situacao` quando
   `data_cadastro` empata.
2. Regra de seguranca: bloquear downgrade de estado no empate de data.
3. Exemplo protegido: manter `STE` e rejeitar sobrescrita para `ADM`.
4. Implementacao: `armazenamento/database_upsert_logic.py::_should_update_existing`.
