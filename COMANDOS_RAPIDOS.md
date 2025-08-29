# 🚀 Comandos Rápidos - SSA Consulta Rápida v3.0.7

## INICIALIZAÇÃO RÁPIDA
```powershell
# Clonar projeto
git clone https://github.com/mauriciomenon/SSA_Consulta_Rapida.git
cd SSA_Consulta_Rapida

# Configurar ambiente
python -m venv venv
.\activate_env.ps1
pip install -r requirements.txt

# Verificar instalação
.\verificar_instalacao.ps1

# Primeira execução
python main.py --reset-db
python main.py
```

## COMANDOS PRINCIPAIS
```powershell
# Help completo
python main.py --help

# CLI Interativo
python main.py

# Interface Gráfica
python main.py --gui

# Modo Otimizado
python main.py --optimized

# Reimportar tudo
python main.py --force-rescan

# Reset completo
python main.py --reset-db
```

## MANUTENÇÃO
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
# Teste rápido
python -c "from core import app_logic; print('✅ OK')"

# Testes automatizados
python -m pytest tests\ -v

# Teste específico
python tests\test_imports.py
```

## SOLUÇÃO DE PROBLEMAS
```powershell
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall

# Reset de ambiente
deactivate
Remove-Item venv -Recurse -Force
python -m venv venv
.\activate_env.ps1
pip install -r requirements.txt

# Permissões PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
