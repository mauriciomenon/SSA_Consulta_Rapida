# Política de Lint Enxuta

Objetivo: mostrar apenas problemas que possam causar erro de execução, comportamento incorreto claro ou risco de segurança evidente.

## Níveis
- Ruff: `E, F, B, UP, I, S` (erros de sintaxe, imports, bugs prováveis, modernização segura, organização mínima de imports, segurança básica).
- Ignorados explicitamente: formatação já coberta pelo Black, warnings cosméticos e casos de uso aceitável em scripts (prints, asserts, random não cripto, shell controlado).
- Pylance: type checking desativado (`off`); apenas alguns avisos de opcionalidade mantidos como *warning*.

## Justificativa
| Categoria | Mantido? | Motivo |
|-----------|----------|--------|
| Sintaxe (E) | Sim | Quebra execução. |
| Imports / nomes (F) | Sim | Falhas em runtime / dead code. |
| Bugbear (B) | Sim | Padrões de bug real. |
| Modernização (UP) | Sim | Ajuda a manter compatível e limpo sem ruído excessivo. |
| Imports (I) | Parcial | Organização consistente facilita revisões (remover se gerar ruído). |
| Segurança (S) | Parcial | Mantém atenção em problemas concretos; relaxado para S101, S603/S607, S311. |
| Comprimento de linha | Não | Black já controla. |
| Complexidade | Não | Refatorar depois sem bloquear fluxo. |
| Estilo/Whitespace | Não | Ruído baixo valor. |

## Per-file Ignores
- `tests/*`: permite imports não usados (fixtures implícitos), variáveis temporárias, prints.
- `scripts_manutencao/*` e `launchers/*`: permitem prints e imports organizativos.

## Como Expandir Futuro
1. Remover gradualmente ignores específicos (ex.: reativar `reportUnusedImport`).
2. Adicionar checagens de complexidade quando funções críticas estiverem estáveis.
3. Reativar modo `basic` de Pylance se houver capacidade de correção incremental.

## Execução Manual
```
ruff check .
black .
```
(Black não falha em CI no modo atual — executar localmente antes de commits grandes.)

## Quando Escalar
Abra issue se encontrar:
- Uso de API obsoleta (UP) com impacto em compatibilidade.
- Código que engole exceções silenciosamente.
- Manipulação arriscada de caminhos / shell dinâmico não sanitizado.

---
Manter a fricção baixa acelera melhorias estruturais reais.
