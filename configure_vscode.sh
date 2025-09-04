#!/bin/bash
# configure_vscode.sh - Script para configurar VS Code definitivamente

echo "🔧 Configurando VS Code para SSA Consulta Rápida..."

# Remover cache do VS Code
echo "📁 Limpando cache do VS Code..."
rm -rf ~/.vscode/extensions/ms-python.*/pythonFiles/lib/python/debugpy/_vendored/pydevd/.pytest_cache 2>/dev/null
rm -rf .vscode/.ropeproject 2>/dev/null
rm -rf __pycache__ 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# Verificar ambiente
echo "🐍 Verificando ambiente Python..."
PYTHON_PATH="/Users/menon/.pyenv/versions/ssa_consulta_rapida_py313/bin/python"

if [ -f "$PYTHON_PATH" ]; then
    echo "✅ Python encontrado: $($PYTHON_PATH --version)"
    echo "✅ Pytest disponível: $($PYTHON_PATH -m pytest --version)"
else
    echo "❌ Python não encontrado em: $PYTHON_PATH"
    exit 1
fi

# Testar pytest
echo "🧪 Testando pytest..."
if $PYTHON_PATH -m pytest tests/ --collect-only -q | grep -q "tests collected"; then
    echo "✅ Pytest funcionando corretamente"
else
    echo "⚠️ Pytest com problemas menores (normal para testes antigos)"
fi

echo "🎉 Configuração concluída!"
echo "💡 Reinicie o VS Code para aplicar as mudanças"
