#!/usr/bin/env python3
"""
Script de teste para verificar as melhorias implementadas na GUI principal.
"""

import json
import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_config_files():
    """Testa se os arquivos de configuração estão corretos."""
    print("FIX TESTANDO ARQUIVOS DE CONFIGURAÇÃO")
    print("=" * 50)

    # Testa gui_main_preferences.json
    config_path = os.path.join(project_root, "config", "gui_main_preferences.json")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        print("OK gui_main_preferences.json encontrado")

        # Verifica labels curtos
        labels = config.get("column_display_names", {})
        tests = [
            ("setor_executor", "Exec."),
            ("situacao", "Sit."),
            ("setor_emissor", "Emis."),
            ("localizacao_codigo", "Loc."),
            ("semana_cadastro", "Sem. Cad."),
            ("semana_programada", "Sem. Prog."),
        ]

        print("\nINFO VERIFICAÇÃO DE LABELS CURTOS:")
        for key, expected in tests:
            actual = labels.get(key, "NÃO ENCONTRADO")
            status = "OK" if actual == expected else "ERR"
            print(f"  {status} {key}: '{actual}' (esperado: '{expected}')")

        # Verifica largura do solicitante
        widths = config.get("column_widths", {})
        solicitante_width = widths.get("solicitante", 0)
        status = "OK" if solicitante_width >= 121 else "ERR"
        print("\nNOTE LARGURA SOLICITANTE:")
        print(f"  {status} solicitante: {solicitante_width}px (mínimo: 121px)")

    else:
        print("ERR gui_main_preferences.json NÃO ENCONTRADO")


def test_gui_imports():
    """Testa se a GUI pode ser importada."""
    print("\nINFO TESTANDO IMPORTAÇÃO DA GUI")
    print("=" * 50)

    try:
        from gui.gui_ssa import load_gui_main_preferences

        print("OK GUI importada com sucesso")

        # Testa carregamento de preferências
        prefs = load_gui_main_preferences()
        labels = prefs.get("column_display_names", {})

        print("OK Preferências carregadas com sucesso")
        print(f"   Labels encontrados: {len(labels)}")

        # Verifica alguns labels específicos
        key_labels = [
            "setor_executor",
            "situacao",
            "setor_emissor",
            "localizacao_codigo",
        ]
        for key in key_labels:
            label = labels.get(key, "NÃO ENCONTRADO")
            print(f"   {key}: '{label}'")

    except Exception as e:
        print(f"ERR Erro ao importar GUI: {e}")


def main():
    """Executa todos os testes."""
    print("TEST TESTE DAS MELHORIAS IMPLEMENTADAS")
    print("DONE Verificando labels curtos, larguras e configurações")
    print("=" * 60)

    test_config_files()
    test_gui_imports()

    print("\n CONCLUSÃO")
    print("=" * 50)
    print(
        "Se todos os testes mostraram OK, as melhorias foram implementadas corretamente."
    )
    print("Para testar a GUI completa, execute: python main.py --gui")
    print("\nVerifique se:")
    print("1. Os headers das colunas mostram labels curtos (Exec., Sit., Emis., Loc.)")
    print("2. A coluna Solicitante mostra nomes completos sem truncamento excessivo")
    print("3. Redimensionar a janela recalcula as larguras automaticamente")
    print("4. O texto nas descrições se adapta à largura da coluna")


if __name__ == "__main__":
    main()
