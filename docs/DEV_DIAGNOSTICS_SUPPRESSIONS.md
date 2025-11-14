# Estrategia de Supressao de Diagnosticos (VS Code / Pylance / Pyright)

A pedido do usuario, TODOS os avisos e erros de analise estatica foram suprimidos na IDE para obter "zero problems" no painel de *Problems* do VS Code.

## O que foi feito

1. Criado `pyrightconfig.json` na raiz com severidades definidas como `none` para avisos considerados cosmeticos (unused, unnecessary, optional, etc.).
2. Ajustado `.vscode/settings.json` adicionando `python.analysis.diagnosticSeverityOverrides` forcando `none` para praticamente todas as categorias relevantes.
3. Mantido `typeCheckingMode = off`.

## Arquivos Criados/Alterados

- `pyrightconfig.json`
- `.vscode/settings.json`
- Este documento explicativo.

## Como Reverter Gradualmente

1. Remover/editar blocos especificos em `.vscode/settings.json`:
   - Substituir uma categoria de `none` para `information` ou `warning` ou `error` conforme necessidade.
2. Ajustar `pyrightconfig.json` removendo linhas que definem severidades e deixar Pyright usar defaults.
3. (Opcional) Ativar checagem de tipos:
   - Alterar em `.vscode/settings.json`: `"python.analysis.typeCheckingMode": "basic"` ou `"strict"`.
4. Ativar apenas um pequeno conjunto inicial (exemplo sugerido):
   ```jsonc
   {
     "python.analysis.diagnosticSeverityOverrides": {
       "reportUnusedImport": "warning",
       "reportUnusedVariable": "warning",
       "reportGeneralTypeIssues": "warning"
     }
   }
   ```

## Riscos / Contras

- Problemas reais (ex.: acessos a atributos inexistentes, possiveis None) ficarao invisiveis.
- Diminui feedback precoce de regressoes.
- Dificulta adocao futura de qualidade continua se esquecido.

## Boas Praticas Futuras (quando desejar retomar)

1. Reintroduzir gradualmente regras: comece com unused + general type.
2. Usar CI separado que executa Pyright sem supressoes para ter *gates* (nao so local).
3. Criar um arquivo `pyproject.toml` com configuracao para Ruff e ir removendo ignores.
4. Priorizar modulos criticos (ex.: `core/`, `utils/`) antes de todo o codigo GUI grande.

## Comandos Opcionais

Rodar pyright manual (usara config suprimida):
```
pyright
```
Para ver tudo ignorando o config atual (modo diagnostico rapido):
```
pyright --verifytypes . --ignoreexternal
```
(Alguns avisos ainda podem nao aparecer devido as supressoes.)

---
Se quiser, posso montar um plano de reintroducao incremental. Basta pedir.
