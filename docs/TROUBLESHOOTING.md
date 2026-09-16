# Troubleshooting (Baseline v4.44)

Guia ativo de diagnostico rapido para operacao diaria.

## Regra de leitura

1. Comecar por este documento.
2. Para importacao detalhada, usar `docs/TROUBLESHOOTING_IMPORTACAO.md`.

## Checklist rapido

1. Confirmar branch e status local.
2. Confirmar runtime (`uv run --python 3.13 ...`).
3. Rodar validacao minima.
4. Revisar logs de erro da rodada.

## Comandos de diagnostico

```bash
# estado do repo
 git status --short
 git branch --show-current

# sanity de tooling
 uv run --python 3.13 python -m py_compile main.py
 uv run --python 3.13 ruff check main.py
 uv run --python 3.13 ty check main.py

# testes docs/gui smoke
 uv run --python 3.13 pytest -q tests/test_docs_and_priority.py tests/test_gui_menu_import_external.py
```

## Problemas comuns

### GUI nao abre

1. Verificar dependencias: `uv sync`.
2. Executar: `uv run --python 3.13 main.py --gui`.

### Full rescan sem atualizacao

1. Confirmar existencia de arquivos de entrada.
2. Verificar mensagens no dialog/log de importacao.
3. Validar DB com comando de integridade (sqlite pragma) antes de novo rescan.

### Banco ausente, zerado ou corrompido

1. Na proxima importacao, o app tenta restaurar automaticamente o snapshot
   valido mais recente de `data/historico_backups/` — nenhuma acao manual
   e necessaria. Snapshots com dados tem prioridade sobre vazios.
2. Se o banco estava corrompido, o original fica preservado em
   `data/historico_backups/<nome>.corrupt_<timestamp>.db` para analise.
3. Se nao houver snapshot utilizavel, o schema e recriado vazio e os dados
   voltam com a proxima reimportacao das planilhas-fonte.
4. Uma falha critica no processo de restauracao aborta a importacao e
   preserva o estado em disco — nao force recriacao manual antes de
   copiar os artefatos para analise.

### Divergencia de docs

1. Validar baseline em `VERSION` e `config/version.json`.
2. Conferir topo de `docs/HISTORICO_RELEASES.md`, `README.md` e `docs/README.md`.

## Escalonamento


<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->
