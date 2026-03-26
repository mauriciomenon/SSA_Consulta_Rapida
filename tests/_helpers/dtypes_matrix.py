#!/usr/bin/env python3
"""Matriz de dtypes e políticas de normalização esperadas para importações.

Esta matriz serve para centralizar expectativas usadas em asserts de testes.

Categorias de política:
  required   -> coluna deve existir e não ser completamente nula
  optional   -> pode faltar ou ser toda nula (quando presente, dtype avaliado fracamente)
  normalized -> deve passar por função de normalização (ex: numero_ssa)

Campos de cada entrada:
  name: nome canônico da coluna
  expected_dtype: dtype pandas desejado (string comparada com str(df[col].dtype))
  policy: ver acima
  notes: observações adicionais
"""

from __future__ import annotations

DTYPES_MATRIX = [
    {
        "name": "numero_ssa",
        "expected_dtype": "object",  # armazenado como texto padronizado
        "policy": "required|normalized",
        "notes": "identificador canonico numerico; planilhas atuais usam 9 digitos, com compatibilidade legacy isolada em helper",
    },
    {
        "name": "situacao",
        "expected_dtype": "object",
        "policy": "required",
        "notes": "Estado textual da solicitação",
    },
    {
        "name": "data_cadastro",
        "expected_dtype": "object",  # strings normalizadas YYYY-MM-DD HH:MM:SS
        "policy": "optional",
        "notes": "Pode ser vazia e posterior enriquecimento pode converter para datetime",
    },
    {
        "name": "descricao_ssa",
        "expected_dtype": "object",
        "policy": "optional",
        "notes": "Texto livre descritivo",
    },
    {
        "name": "setor_executor",
        "expected_dtype": "object",
        "policy": "optional",
        "notes": "Código/identificação do setor executor",
    },
]

# Mapeamento rápido para lookup por nome
DTYPES_BY_NAME = {e["name"]: e for e in DTYPES_MATRIX}

__all__ = ["DTYPES_MATRIX", "DTYPES_BY_NAME"]
