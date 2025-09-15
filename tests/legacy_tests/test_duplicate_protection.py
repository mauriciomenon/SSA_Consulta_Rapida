"""LEGACY REFERENCE TEST (duplicate protection)

Mantido somente para histórico de fluxo real com arquivo Excel e banco real.
Coberto por `tests/test_no_duplicate_on_reimport.py` na suíte moderna.
Pode ser removido após consolidação.
"""
# (imports removidos; legacy placeholder sem dependências)
# from core.app_logic import import_single_file  # legacy import (mantido comentado)

def test_duplicate_protection():  # legacy placeholder
    """Legacy placeholder desativado.

    Fluxo original dependia de IO real e foi substituído por
    `tests/test_no_duplicate_on_reimport.py`. Mantido apenas como referência
    textual para eventual auditoria. Não executa nenhuma ação.
    """
    return

if __name__ == "__main__":  # pragma: no cover
    print("Legacy test - não executa lógica ativa.")
