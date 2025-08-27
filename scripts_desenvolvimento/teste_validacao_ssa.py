#!/usr/bin/env python3
"""
Teste da correção da função _normalize_numero_ssa_value
"""

import re
import pandas as pd
import logging

# Setup básico de logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def _normalize_numero_ssa_value(v) -> int | None:
    """Função corrigida (copiada do database.py)"""
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = re.sub(r"\D", "", str(v))
        if not s:
            return None
        
        # NÃO remover zeros à esquerda - SSAs podem começar com zeros válidos!
        
        # Validar formato: deve ter exatamente 9 dígitos
        if len(s) != 9:
            logger.warning(f"SSA inválido - deve ter 9 dígitos: '{s}' (original: '{v}')")
            return None
            
        # Validar ano (primeiros 4 dígitos): deve estar entre 2019-2050
        ano_str = s[:4]
        try:
            ano = int(ano_str)
            if not (2019 <= ano <= 2050):
                logger.warning(f"SSA inválido - ano fora do range 2019-2050: '{s}' (ano: {ano})")
                return None
        except ValueError:
            logger.warning(f"SSA inválido - ano não numérico: '{s}'")
            return None
            
        # Converter para int
        return int(s)
        
    except Exception as e:
        logger.warning(f"Erro ao normalizar numero_ssa '{v}': {e}")
        return None

print("=== TESTE DA CORREÇÃO ===")

# Casos de teste
test_cases = [
    "202513402",    # Valor correto esperado
    "202513586",    # Outro valor correto
    "202100033",    # Valor correto com 2021
]

print("Testando casos:")
for i, case in enumerate(test_cases):
    result = _normalize_numero_ssa_value(case)
    status = "✅" if result is not None else "❌"
    print(f"  [{i+1}] {status} '{case}' -> {result}")

print(f"\n🎯 RESULTADO ESPERADO:")
print(f"  - '202513402' deve retornar 202513402 (não None)")
print(f"  - Deve preservar zeros à esquerda corretamente")
