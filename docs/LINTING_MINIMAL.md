# Politica de Lint Enxuta

Objetivo: mostrar apenas problemas que possam causar erro de execucao, comportamento incorreto claro ou risco de seguranca evidente.

## Niveis
- Ruff: `E, F, B, UP, I, S` (erros de sintaxe, imports, bugs provaveis, modernizacao segura, organizacao minima de imports, seguranca basica).
- Ignorados explicitamente: formatacao ja coberta pelo Black, warnings cosmeticos e casos de uso aceitavel em scripts (prints, asserts, random nao cripto, shell controlado).
- Pylance: type checking desativado (`off`); apenas alguns avisos de opcionalidade mantidos como *warning*.

## Justificativa
| Categoria | Mantido? | Motivo |
|-----------|----------|--------|
| Sintaxe (E) | Sim | Quebra execucao. |
| Imports / nomes (F) | Sim | Falhas em runtime / dead code. |
| Bugbear (B) | Sim | Padroes de bug real. |
| Modernizacao (UP) | Sim | Ajuda a manter compativel e limpo sem ruido excessivo. |
| Imports (I) | Parcial | Organizacao consistente facilita revisoes (remover se gerar ruido). |
| Seguranca (S) | Parcial | Mantem atencao em problemas concretos; relaxado para S101, S603/S607, S311. |
| Comprimento de linha | Nao | Black ja controla. |
| Complexidade | Nao | Refatorar depois sem bloquear fluxo. |
| Estilo/Whitespace | Nao | Ruido baixo valor. |

## Per-file Ignores
- `tests/*`: permite imports nao usados (fixtures implicitos), variaveis temporarias, prints.
- `scripts_manutencao/*` e `launchers/*`: permitem prints e imports organizativos.

## Como Expandir Futuro
1. Remover gradualmente ignores especificos (ex.: reativar `reportUnusedImport`).
2. Adicionar checagens de complexidade quando funcoes criticas estiverem estaveis.
3. Reativar modo `basic` de Pylance se houver capacidade de correcao incremental.

## Execucao Manual
```
ruff check .
black .
```
(Black nao falha em CI no modo atual — executar localmente antes de commits grandes.)

## Quando Escalar
Abra issue se encontrar:
- Uso de API obsoleta (UP) com impacto em compatibilidade.
- Codigo que engole excecoes silenciosamente.
- Manipulacao arriscada de caminhos / shell dinamico nao sanitizado.

---
Manter a friccao baixa acelera melhorias estruturais reais.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

