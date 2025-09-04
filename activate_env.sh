#!/bin/zsh
# activate_env.sh - Script para ativar o ambiente Python no macOS
# Use: source activate_env.sh

echo "🔧 Ativando ambiente SSA Consulta Rápida..."

# Inicializar pyenv
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Ativar o ambiente virtual
pyenv activate ssa_consulta_rapida_py313

# Verificar se está funcionando
if python -c "import tabulate" 2>/dev/null; then
    echo "✅ Ambiente ativo! Python $(python --version) com tabulate"
    echo "📋 Para executar: python main.py"
    echo "🎨 Para GUI: python main.py --gui"
else
    echo "❌ Erro: tabulate não encontrado"
    echo "💡 Execute: pip install -r requirements.txt"
fi
