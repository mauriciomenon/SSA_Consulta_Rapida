# Build Windows em VM pelo ssh (sem clone permanente)

Procedimento para gerar os pacotes Windows de um commit numa VM/host Windows
acessado por `ssh`, sem deixar repositorio, venv ou cache na maquina. Vale para
`windows_amd64` e `windows_arm64` (um alvo por vez, nunca misturando venv,
dist ou ZIP entre eles).

## Regras

- So o canal ssh ja existente (alias no `~/.ssh/config` do Mac). Nada de tunel,
  porta nova, chave pessoal ou credencial na VM.
- Python so via uv. Se a VM nao tiver uv: `winget install --id astral-sh.uv -e`.
- Tudo o que o build cria fica dentro de uma pasta do usuario e sai inteiro na
  limpeza: o repositorio, o venv, o cache do uv e o Python gerenciado pelo uv.
- A guarda nativa (`scripts/env/native_host_guard.ps1`) so aceita o repositorio
  em `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`; essa e a pasta de
  trabalho. Se ela ja existir com outro conteudo, pare e confira antes.
- O pacote sai do commit exato informado (o `build_info.json` registra o SHA);
  o workspace precisa estar limpo, por isso o cache e o Python ficam fora do
  repositorio, numa pasta irma.

## Variaveis

No Mac (zsh/bash):

```bash
VM=w11                                  # alias ssh da VM
REF=rev                                 # branch/tag/commit a construir
SRC=$(git rev-parse "$REF")             # SHA conferido no fim
WORK=$(mktemp -d)                       # pasta temporaria local
```

Na VM (cmd), as pastas usadas:

- `%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6`: repositorio raso.
- `%USERPROFILE%\ssa_build_aux`: cache do uv, Python gerenciado e o `.tgz`.

## 1. Snapshot raso do commit (Mac)

Clone raso local: leva so a arvore do commit, com `.git` (o build usa
`git ls-files` e `git rev-parse`). Nao envia o historico.

```bash
git clone --quiet --depth 1 --branch "$REF" "file://$PWD" "$WORK/ssa_src"
test "$(git -C "$WORK/ssa_src" rev-parse HEAD)" = "$SRC"
tar -czf "$WORK/ssa_src.tgz" -C "$WORK" ssa_src
```

`--branch` aceita branch ou tag; para um SHA solto, crie antes uma tag local.

## 2. Transferir e extrair (Mac -> VM)

```bash
ssh "$VM" 'if exist "%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6" (echo EXISTE & exit 1) else (mkdir "%USERPROFILE%\ssa_build_aux" & mkdir "%USERPROFILE%\gitlab")'
scp "$WORK/ssa_src.tgz" "$VM:ssa_build_aux/ssa_src.tgz"
ssh "$VM" 'cd /d "%USERPROFILE%\gitlab" && tar -xzf "%USERPROFILE%\ssa_build_aux\ssa_src.tgz" && ren ssa_src ssa_consulta_rapida_pyqt6 && del "%USERPROFILE%\ssa_build_aux\ssa_src.tgz"'
```

## 3. Build (VM)

```bash
ssh "$VM" 'set "UV_CACHE_DIR=%USERPROFILE%\ssa_build_aux\uv-cache" && set "UV_PYTHON_INSTALL_DIR=%USERPROFILE%\ssa_build_aux\uv-python" && cd /d "%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6" && powershell -NoProfile -ExecutionPolicy Bypass -File .\release.ps1 -Target windows -Platform windows_amd64 -Backend pyinstaller -SkipInstaller -Yes'
```

- Sem Inno Setup na VM use `-SkipInstaller`.
- Sem `-IncludeRuntimeDb`: o pacote nao leva banco operacional.
- Para `windows_arm64`, rode so em Windows ARM64 nativo e informe o Python
  ARM64 do uv em `SSA_WINDOWS_ARM64_PYTHON`.
- Build longo: se a sessao ssh cair, o Windows encerra o processo. Rode em
  primeiro plano e confira o relatorio no fim.

## 4. Recuperar os pacotes (VM -> Mac)

```bash
DEST=builds/packages/windows_amd64
mkdir -p "$DEST"
scp "$VM:gitlab/ssa_consulta_rapida_pyqt6/builds/packages/windows_amd64/*.zip" "$DEST/"
scp "$VM:gitlab/ssa_consulta_rapida_pyqt6/builds/reports/release_report_windows_amd64.json" "$DEST/"
ssh "$VM" 'powershell -NoProfile -Command "Get-FileHash $env:USERPROFILE\gitlab\ssa_consulta_rapida_pyqt6\builds\packages\windows_amd64\*.zip -Algorithm SHA256 | Format-Table Hash,Path -AutoSize"'
shasum -a 256 "$DEST"/*.zip
```

Confira: o SHA-256 da copia igual ao da VM e o `commit` do relatorio igual a
`$SRC`.

## 5. Limpar (VM e Mac)

```bash
ssh "$VM" 'rmdir /s /q "%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6" & rmdir /s /q "%USERPROFILE%\ssa_build_aux"'
ssh "$VM" 'if exist "%USERPROFILE%\gitlab\ssa_consulta_rapida_pyqt6" (echo SOBROU) else (echo LIMPO) & if exist "%USERPROFILE%\ssa_build_aux" (echo SOBROU) else (echo LIMPO)'
rm -rf "$WORK"
```

`%USERPROFILE%\gitlab` so e removido se tiver sido criado neste procedimento e
estiver vazio (`rmdir "%USERPROFILE%\gitlab"` falha sozinho se houver outro
repositorio la).
