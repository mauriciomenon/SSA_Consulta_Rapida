#  Comandos Rapidos - SSA Consulta Rapida v3.10

## INICIALIZACAO RAPIDA
```powershell
# Clonar projeto
git clone https://github.com/mauriciomenon/SSA_Consulta_Rapida.git
cd SSA_Consulta_Rapida

# Configurar ambiente
python -m venv venv
.\activate_env.ps1
pip install -r requirements.txt

# Verificar instalacao
.\verificar_instalacao.ps1

# Primeira execucao
python main.py --reset-db
python main.py
```

## COMANDOS PRINCIPAIS
```powershell
# Help completo
python main.py --help

# CLI Interativo
python main.py

# Interface Grafica
python main.py --gui

# Modo Otimizado
python main.py --optimized

# Reimportar tudo
python main.py --force-rescan

# Reset completo
python main.py --reset-db
```

## GUI – Filtros (TL;DR)
- Separe termos por virgula: `foo, bar`
- Modos: contem (`foo`), comeca (`^foo`), termina (`foo$`), igual (`=foo`), regex (`~padrao`), excluir (`!termo`)
- Por coluna: clique direito no cabecalho e use o painel a direita; botoes Aplicar/Limpar nao alteram as larguras da tabela

## Temas (GUI)
- Claro, Escuro e Gruvbox. No Claro, caixas "Semana" e "Status" tem contraste reforcado.

## RECUPERACAO RAPIDA (SAFE MODE)
```powershell
# 1) Criar checkpoint/restauracao (stash + pacote de recuperacao)
pwsh -File scripts_manutencao/quick_recovery.ps1 -Action checkpoint -Message "WIP rapida"

# 2) Apos reboot (ou em caso de duvida), listar/aplicar stash
pwsh -File scripts_manutencao/quick_recovery.ps1 -Action restore
git stash pop

# 3) Alternativa: aplicar patch salvo (se necessario)
pwsh -File scripts_manutencao/quick_recovery.ps1 -Action apply-patch -PatchPath docs_saida/SESSION_RECOVERY_YYYYMMDD_HHMMSS/uncommitted.patch

# 4) Banco minimo sem pandas (modo emergencia)
python utils/fallback/emergency_import.py       # cria data\ssas.db minimo (SQLite puro)
python main_simple.py            # CLI simplificada operando sobre ssa_table
```

## MANUTENCAO
```powershell
# Verificar status
git status
git pull

# Limpar dados antigos
python main.py --clean-data

# Verificar banco
ls data\ssas.db

# Ver logs (se habilitados)
type logs\ssa.log
```

## TESTES
```powershell
# Teste rapido
python -c "from core import app_logic; print(' OK')"

# Testes automatizados
python -m pytest tests\ -v

# Teste especifico
python tests\test_imports.py
```

## SOLUCAO DE PROBLEMAS
```powershell
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall

# Reset de ambiente
deactivate
Remove-Item venv -Recurse -Force
python -m venv venv
.\activate_env.ps1
pip install -r requirements.txt

# Permissoes PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
