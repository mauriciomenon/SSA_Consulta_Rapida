"""Normalization helpers for SSA details relations."""

from __future__ import annotations

import pandas as pd

from gui.ssa import details_derivadas_model
from utils.robust_logging import get_robust_logger

logger = get_robust_logger().get_logger(__name__, "gui")


def is_missing_scalar(value) -> bool:
    if value is None:
        return True
    try:
        if not pd.api.types.is_scalar(value):
            return False
        return bool(pd.isna(value))
    except Exception as exc:
        logger.debug("Falha ao avaliar valor escalar ausente: %s", exc)
        return False


def normalize_ssa_relation_value(value) -> str:
    if is_missing_scalar(value):
        return ""
    return details_derivadas_model.normalize_relation_value(value)


def normalize_ssa_relation_series(series: pd.Series) -> pd.Series:
    try:
        series_obj = series.astype("object")
        codes, uniques = pd.factorize(series_obj, sort=False)
        normalized_uniques = [normalize_ssa_relation_value(value) for value in uniques]
        resolved = [""] * len(series_obj)
        for index, code in enumerate(codes):
            if code >= 0:
                resolved[index] = normalized_uniques[code]
        return pd.Series(resolved, index=series_obj.index, dtype="object", name=series.name)
    except (TypeError, ValueError, AttributeError) as exc:
        logger.debug("Falha ao normalizar serie de relacoes SSA via factorize: %s", exc)
        mapped = series.map(normalize_ssa_relation_value)
        return pd.Series(mapped, index=series.index, dtype="object", name=series.name)
