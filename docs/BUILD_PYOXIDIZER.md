# Build com PyOxidizer

## Instalacao

```bash
pip install pyoxidizer
```

## Build

```bash
pyoxidizer build --release
```

Tempo de compilacao: 10-30 minutos (primeira vez)

## Resultado

Executavel gerado em: `build/x86_64-pc-windows-msvc/release/install/`

Estrutura:
```
install/
  SSA_Consulta_Rapida.exe    <- Executavel com Python e codigo compilado
  lib/                        <- Bibliotecas Python embutidas
  config/                     <- Configs JSON (editaveis)
  themes/                     <- Temas (editaveis)
  docs_entrada/               <- Pasta para Excel de entrada (vazia inicial)
  data/                       <- Pasta para banco de dados (vazia inicial)
```

## Distribuir

Copie toda a pasta `install/` para distribuir.

Usuario final:
1. Descompacta pasta
2. Executa `SSA_Consulta_Rapida.exe --gui`
3. Coloca arquivos Excel em `docs_entrada/`
4. Edita configs em `config/` se necessario

## Performance

- Startup: 2-3s (melhor que PyInstaller)
- Seguranca: Alta (codigo compilado para C nativo)
- Tamanho: ~150-200MB

## Pastas Editaveis

Usuario pode modificar:
- `config/gui_main_preferences.json` - Debounce, colunas, tema
- `config/column_mappings.json` - Mapeamento de colunas
- `themes/*.json` - Arquivos de tema
- `docs_entrada/` - Adicionar/remover Excels
- `data/` - Banco de dados gerado

## Pastas Protegidas (codigo compilado)

Nao editaveis, dentro do executavel:
- core/
- gui/
- armazenamento/
- extracao/
- utils/
- interface/
- exportacao/
- shared/
- Todas as libs Python (pandas, PyQt6, etc)

## Correcoes Implementadas

### Problema: "error: target install is not resolved"

Faltava `resolve_targets()` no final de `pyoxidizer.bzl`. Corrigido.

### Problema: Loop incorreto lendo arquivos fonte

O loop estava chamando `read_package_root()` com parametros identicos. Corrigido para:
```python
exe.add_python_resources(exe.read_package_root(
    path=".",
    packages=["core", "gui", "armazenamento", "extracao", "utils", "interface", "exportacao", "shared"],
))
```

## Troubleshooting

### Erro: "Module not found"

Adicione o modulo em `pyoxidizer.bzl`:
```python
exe.add_python_resources(exe.pip_install([
    "pandas",
    "openpyxl",
    "PyQt6",
    "novo_modulo_aqui",  # Adicione aqui
]))
```

### Erro: "Cannot find config/..."

Verifique se pasta `config/` esta na mesma pasta do executavel.

### Performance ruim

Compile com `--release`:
```bash
pyoxidizer build --release
```

### Build muito lento (primeira vez)

Normal. Primeira compilacao: 10-30 minutos.
- Baixa Python 3.10.9 (~100MB)
- Instala todas as dependencias
- Baixa Rust toolchain (~200MB)
- Compila tudo para nativo

Builds seguintes: 2-5 minutos (incremental).

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

