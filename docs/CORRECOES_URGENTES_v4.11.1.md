# Correcoes Urgentes - v4.11.1

**Data**: 2025-11-19
**Versao**: 4.11.1
**Prioridade**: CRITICA

## Problemas Corrigidos

### PROBLEMA 1: Executavel PyInstaller nao funciona em pastas OneDrive/rede

**Sintoma**:
```
Arquivo main.py nao encontrado em C:\Users\lcica\OneDrive - ITAIPU Binacional\...\ssa_consulta_rapida_411\_internal\main.py
Erro ao abrir pasta: Command '[explore]' returned non-zero exit status 1.
```

**Causa Raiz**:
O codigo em [main.py:191](main.py:191) estava usando `sys._MEIPASS` como diretorio raiz do projeto. `sys._MEIPASS` eh o diretorio TEMPORARIO onde o PyInstaller extrai os arquivos internos, NAO o diretorio onde o usuario colocou o executavel.

Quando o usuario executa de uma pasta OneDrive ou rede, o codigo tentava acessar arquivos relativos ao `_MEIPASS` em vez da pasta real do executavel.

**Correcao Aplicada**:
```python
# ANTES (ERRADO):
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    return sys._MEIPASS  # <-- ERRADO!

# DEPOIS (CORRETO):
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    return os.path.dirname(os.path.abspath(sys.executable))  # <-- CORRETO!
```

**Arquivo Modificado**: [main.py:189-193](main.py:189-193)

**Impacto**: CRITICO - Afeta TODOS os usuarios do executavel PyInstaller, especialmente em ambientes corporativos com OneDrive/SharePoint.

---

### PROBLEMA 2: Erro "too many SQL variables" ao importar arquivos grandes

**Sintoma**:
```
2025-11-18 08:40:01 - ERROR - armazenamento.database - Erro de banco de dados: too many SQL variables
2025-11-18 08:40:01 - ERROR - armazenamento.database_optimized - [ERRO] Erro na insercao otimizada: too many SQL variables
```

**Causa Raiz**:
O parametro `method='multi'` no pandas `to_sql()` tenta criar um INSERT com multiplos VALUES em uma unica query. Quando ha muitas colunas (82+), o numero total de variaveis SQL excede o limite do SQLite (999).

Embora o codigo JA calculasse `chunksize` dinamicamente, o `method='multi'` IGNORAVA esse valor e tentava inserir tudo de uma vez.

**Correcao Aplicada**:
Removido `method='multi'` de todas as chamadas `to_sql()`:

```python
# ANTES (ERRADO):
insert_df.to_sql(table_name, conn, if_exists='append',
                 index=False, method='multi', chunksize=safe_chunksize)

# DEPOIS (CORRETO):
insert_df.to_sql(table_name, conn, if_exists='append',
                 index=False, chunksize=safe_chunksize)
```

**Arquivos Modificados**:
- [armazenamento/database_optimized.py:194](armazenamento/database_optimized.py:194)
- [armazenamento/database_optimized.py:219](armazenamento/database_optimized.py:219)

**Impacto**: ALTO - Afeta importacao de planilhas com muitas colunas ou muitos dados.

---

## Testes Necessarios

Antes de distribuir a versao corrigida:

### Teste 1: PyInstaller em OneDrive
1. Copiar executavel PyInstaller para pasta OneDrive
2. Executar: `SSA_Consulta_Rapida.exe --version`
3. Executar: `SSA_Consulta_Rapida.exe --help`
4. Verificar se nao ha erros de "main.py not found"

### Teste 2: Importacao de arquivo grande
1. Preparar planilha Excel com 2000+ linhas e 80+ colunas
2. Colocar em docs_entrada/
3. Executar importacao
4. Verificar se nao ha erro "too many SQL variables"
5. Verificar se dados foram importados corretamente

### Teste 3: GUI em diferentes locais
1. Executar GUI de pasta local (C:\)
2. Executar GUI de pasta rede (\\\servidor\)
3. Executar GUI de pasta OneDrive
4. Verificar funcionamento normal em todos os casos

---

## Comandos para Rebuild

### Rebuild PyInstaller (mais afetado):
```batch
cmd.exe //C build_pyinstaller.bat
```

### Rebuild todos:
```batch
cmd.exe //C build_pyinstaller.bat
cmd.exe //C build_pyoxidizer.bat
cmd.exe //C build_nuitka_clean.bat
```

### Criar novos pacotes de distribuicao:
```bash
python scripts/create_distribution.py --all --skip-installer
```

---

## Changelog v4.11.1

### CRITICAL FIXES
- **[PyInstaller]** Corrigido uso incorreto de `sys._MEIPASS` causando falha em pastas OneDrive/rede
- **[Database]** Removido `method='multi'` que ignorava `chunksize` e causava "too many SQL variables"

### Arquivos Modificados
- main.py (linhas 189-193)
- armazenamento/database_optimized.py (linhas 194, 219)
- VERSION (4.11.0 → 4.11.1)

### Impacto
- **PyInstaller**: TODOS os usuarios afetados, especialmente ambientes corporativos
- **Database**: Usuarios que importam planilhas grandes (2000+ linhas, 80+ colunas)

### Proximos Passos
1. Rebuild de todos os executaveis
2. Testes em ambiente OneDrive
3. Testes de importacao com arquivos grandes
4. Redistribuir pacotes corrigidos

---

## Notas para Desenvolvedores

### Sobre sys._MEIPASS

`sys._MEIPASS` eh um diretorio TEMPORARIO criado pelo PyInstaller em:
- Windows: `C:\Users\<user>\AppData\Local\Temp\_MEI<random>\`
- Contem arquivos extraidos do executavel
- **NUNCA** deve ser usado como diretorio raiz do projeto
- **SEMPRE** use `os.path.dirname(sys.executable)` para PyInstaller

### Sobre method='multi' no pandas

O parametro `method='multi'` no pandas `to_sql()`:
- Tenta criar INSERT com multiplos VALUES: `INSERT INTO t VALUES (...), (...), (...)`
- **IGNORA** o parametro `chunksize`
- Pode causar "too many SQL variables" com muitas colunas
- **Alternativa**: Usar apenas `chunksize` sem `method='multi'`

---

**Responsavel**: Sistema de correcao automatica
**Data**: 2025-11-19
**Status**: CORRECOES APLICADAS - AGUARDANDO REBUILD E TESTES
