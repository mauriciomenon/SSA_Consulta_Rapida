# Estratégia de Supressão de Diagnósticos (VS Code / Pylance / Pyright)

A pedido do usuário, TODOS os avisos e erros de análise estática foram suprimidos na IDE para obter "zero problems" no painel de *Problems* do VS Code.

## O que foi feito

1. Criado `pyrightconfig.json` na raiz com severidades definidas como `none` para avisos considerados cosméticos (unused, unnecessary, optional, etc.).
2. Ajustado `.vscode/settings.json` adicionando `python.analysis.diagnosticSeverityOverrides` forçando `none` para praticamente todas as categorias relevantes.
3. Mantido `typeCheckingMode = off`.

## Arquivos Criados/Alterados

- `pyrightconfig.json`
- `.vscode/settings.json`
- Este documento explicativo.

## Como Reverter Gradualmente

1. Remover/editar blocos específicos em `.vscode/settings.json`:
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

- Problemas reais (ex.: acessos a atributos inexistentes, possíveis None) ficarão invisíveis.
- Diminui feedback precoce de regressões.
- Dificulta adoção futura de qualidade contínua se esquecido.

## Boas Práticas Futuras (quando desejar retomar)

1. Reintroduzir gradualmente regras: comece com unused + general type.
2. Usar CI separado que executa Pyright sem supressões para ter *gates* (não só local).
3. Criar um arquivo `pyproject.toml` com configuração para Ruff e ir removendo ignores.
4. Priorizar módulos críticos (ex.: `core/`, `utils/`) antes de todo o código GUI grande.

## Comandos Opcionais

Rodar pyright manual (usará config suprimida):
```
pyright
```
Para ver tudo ignorando o config atual (modo diagnóstico rápido):
```
pyright --verifytypes . --ignoreexternal
```
(Alguns avisos ainda podem não aparecer devido às supressões.)

---
Se quiser, posso montar um plano de reintrodução incremental. Basta pedir.
