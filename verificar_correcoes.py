#!/usr/bin/env python3
"""
Verificação Rápida das Correções - SSA Consulta Rápida
Script para validar se as melhorias implementadas estão funcionando
"""

import json
import os

def verificar_labels_curtos():
    """Verifica se os labels curtos estão configurados corretamente."""
    print("🔍 Verificando labels curtos...")
    
    config_file = "config/gui_main_preferences.json"
    if not os.path.exists(config_file):
        print("❌ Arquivo de configuração não encontrado")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    mappings = config.get("display_mappings", config.get("column_display_names", {}))
    
    esperados = {
        "semana_programada": "Prog.",
        "setor_executor": "Exec.", 
        "situacao": "Sit.",
        "setor_emissor": "Emis.",
        "localizacao_codigo": "Loc."
    }
    
    for key, expected in esperados.items():
        actual = mappings.get(key)
        if actual == expected:
            print(f"  ✅ {key}: '{actual}'")
        else:
            print(f"  ❌ {key}: '{actual}' (esperado: '{expected}')")
            return False
    
    return True

def verificar_arquivos_principais():
    """Verifica se os arquivos principais existem."""
    print("\n📁 Verificando arquivos principais...")
    
    arquivos = [
        "gui/gui_ssa.py",
        "config/gui_main_preferences.json", 
        "main.py"
    ]
    
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            print(f"  ✅ {arquivo}")
        else:
            print(f"  ❌ {arquivo}")
            return False
    
    return True

def main():
    """Executa verificação rápida."""
    print("🧪 VERIFICAÇÃO RÁPIDA DAS CORREÇÕES")
    print("=" * 50)
    
    testes = [
        ("Labels Curtos", verificar_labels_curtos),
        ("Arquivos Principais", verificar_arquivos_principais)
    ]
    
    todos_ok = True
    for nome, teste in testes:
        if not teste():
            todos_ok = False
    
    print("\n" + "=" * 50)
    if todos_ok:
        print("✅ TODAS AS VERIFICAÇÕES PASSARAM!")
        print("As correções estão funcionando corretamente.")
    else:
        print("❌ ALGUMAS VERIFICAÇÕES FALHARAM")
        print("Revise as configurações.")

if __name__ == "__main__":
    main()
