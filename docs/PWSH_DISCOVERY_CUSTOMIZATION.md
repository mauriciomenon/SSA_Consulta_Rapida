# pwsh_discovery — Customização e exemplos

Este documento descreve todos os campos e formas de customização que o helper
`pwsh_discovery` tenta reconhecer ao procurar por `pwsh`/`powershell` no
ambiente e no `settings.json` do VS Code. O objetivo é tornar reproduzível como
configurar ou inspecionar perfis de terminal em Windows, Linux, WSL e macOS.

Resumo da estratégia

- Procura por `pwsh`/`powershell` no PATH usando `shutil.which`.
- Analisa `.vscode/settings.json` do workspace, aceitando formatos novos e legados:
  - `terminal.integrated.profiles.windows`: pode ser um mapeamento name -> dict ou name -> string.
  - `terminal.integrated.shell.windows` (legado).
  - `terminal.external.windowsExec`.
  - Varredura por qualquer string no `settings.json` que contenha `pwsh`/`powershell`.
- Verifica caminhos comuns do sistema (Windows Program Files, macOS Homebrew, Unix).
- Em WSL, também inspeciona os caminhos Windows montados (ex.: `/mnt/c/Program Files/...`).
- Normaliza entradas: expande `~`, expande variáveis de ambiente (`$VAR` / `%VAR%`), remove aspas e extrai o executável quando a string contém argumentos.

Campos/configurações que o detector reconhece (exemplos)

1) `terminal.integrated.profiles.windows` (novo formato)

- Exemplo 1 — perfil com dicionário com `path`:

```json
"terminal.integrated.profiles.windows": {
  "PowerShell 7": {
    "path": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
    "args": ["-NoProfile"]
  }
}
```

- Exemplo 2 — perfil com caminho como string (menos comum mas possível):

```json
"terminal.integrated.profiles.windows": {
  "MyShell": "C:\\custom\\pwsh-custom.exe --some-arg"
}
```

O detector aceita ambos: ele normaliza a string, expande variáveis e extrai `C:\custom\pwsh-custom.exe`.

2) `terminal.integrated.shell.windows` (legado)

```json
"terminal.integrated.shell.windows": "C:\\Program Files\\PowerShell\\7\\pwsh.exe"
```

3) `terminal.external.windowsExec`

```json
"terminal.external.windowsExec": "C:\\Windows\\System32\\cmd.exe"
```

Mesmo que esta chave aponte para `cmd.exe`, o detector a verifica e inclui se corresponder a pwsh/powershell.

4) Entradas com variáveis e `~`

```json
"terminal.integrated.profiles.windows": {
  "UserPwsh": {
    "path": "%USERPROFILE%\\AppData\\Local\\Programs\\PowerShell\\7\\pwsh.exe"
  }
}
```

O detector expande `%USERPROFILE%` (Windows) e `$HOME`/`~` (Unix) antes de checar a existência.

5) Strings contendo comando + args

```json
"terminal.integrated.profiles.windows": {
  "PSArgs": "C:\\Program Files\\PowerShell\\7\\pwsh.exe -NoLogo -NoProfile"
}
```

O detector usa `shlex` para extrair o primeiro token (`pwsh.exe`) mesmo quando há argumentos.

Como reproduzir e inspecionar

- Para listar candidatos detectados para um workspace atual:

```powershell
python scripts/pwsh_discovery.py --workspace . --list
```

- Para obter o primeiro candidato:

```powershell
python scripts/pwsh_discovery.py --workspace . --first
```

- Para saída JSON (útil para CI):

```powershell
python scripts/pwsh_discovery.py --workspace . --json
```

Boas práticas e recomendações

- Mantenha caminhos absolutos em `settings.json` sempre que possível para evitar ambiguidades.
- Se você tem uma instalação personalizada do PowerShell (por exemplo, em `%USERPROFILE%`), use `path` em `terminal.integrated.profiles.windows` com a expansão completa ou `%USERPROFILE%` — o detector irá expandir.
- Teste com `--list` antes de usar em scripts automatizados.

Próximos aprimoramentos sugeridos

- Extração heurística de `command` / `args` em perfis mais complexos.
- Normalização mais robusta (ex.: suporte a `cmd /c "..."` wrappers).
- Integração com `psutil` para melhor gerenciamento de processos (cuidado: adiciona dependência).

Contato

- Arquivo do helper: `scripts/pwsh_discovery.py`
- Testes: `tests/test_pwsh_discovery.py`
- Wrappers: `scripts/run_pytest_with_timeout_v2.py`, `scripts/run_pytest_stream_and_log_v2.py`

Coloque estas instruções no repositório e adapte conforme seu ambiente local.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

