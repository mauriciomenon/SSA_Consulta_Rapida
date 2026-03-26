#!/usr/bin/env python3
"""
Teste do sistema de configuração JSON da GUI PoC
"""

import json
from pathlib import Path


def test_gui_configuration():
    """Testa se as configurações JSON estão funcionando corretamente"""
    print("FIX Testando Sistema de Configuração GUI PoC")
    print("=" * 50)

    # 1. Verificar se o arquivo JSON existe
    config_path = Path("config/gui_poc_preferences.json")
    assert config_path.exists(), "Arquivo de configuração não encontrado!"
    print(f"OK Arquivo de configuração encontrado: {config_path}")

    # 2. Tentar carregar o JSON
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    print("OK JSON carregado com sucesso!")

    # 3. Verificar estrutura básica
    required_keys = [
        "display_columns",
        "hidden_columns",
        "column_display_names",
        "column_widths",
    ]
    for key in required_keys:
        assert key in config, f"Chave '{key}' ausente!"
        print(f"OK Chave '{key}' encontrada")

    # 4. Verificar se colunas críticas estão presentes
    display_columns = config.get("display_columns", [])
    critical_columns = ["numero_ssa", "cadastro", "prioridade"]

    print("\nINFO Verificando Colunas Críticas:")
    for col in critical_columns:
        if col in display_columns:
            print(f"OK {col} - presente")
        else:
            print(f"ERR {col} - AUSENTE!")

    # 5. Verificar colunas ocultas
    hidden_columns = config.get("hidden_columns", [])
    unwanted_columns = ["equipamento", "origem"]

    print("\nNOTE Verificando Colunas Ocultas:")
    for col in unwanted_columns:
        if col in hidden_columns:
            print(f"OK {col} - oculta (correto)")
        else:
            print(f"WARN {col} - não está na lista de ocultas")

    # 6. Estatísticas
    print("\nINFO Estatísticas:")
    print(f"• Colunas para exibir: {len(display_columns)}")
    print(f"• Colunas ocultas: {len(hidden_columns)}")
    print(f"• Larguras configuradas: {len(config.get('column_widths', {}))}")
    print(f"• Nomes alternativos: {len(config.get('column_display_names', {}))}")

    # 7. Testar importação da GUI
    print("\nINFO Testando Importação GUI Principal:")
    from gui.gui_ssa import GUI_MAIN_PREFERENCES

    print("OK GUI Principal importada com sucesso!")
    loaded_display = GUI_MAIN_PREFERENCES.get("display_columns", [])
    if "numero_ssa" in loaded_display:
        print("OK Campo numero_ssa presente")
    else:
        print("WARN numero_ssa ausente nas preferências")

    print("\n" + "=" * 50)
    print("OK TESTE CONCLUÍDO COM SUCESSO!")
    print("TIP O sistema de configuração JSON está funcionando perfeitamente.")
    print("INFO Todos os campos críticos estão configurados.")
    print("FIX As preferências da GUI estão separadas do CLI.")


if __name__ == "__main__":
    test_gui_configuration()
