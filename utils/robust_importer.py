# utils/robust_importer.py
"""Importador "à prova de bala" para planilhas SSA.

Objetivos:
  - Tolerar diferenças de cabeçalho (acentos, maiúsculas, quebras de linha, espaços extras)
  - Colapsar sinônimos conforme `config/column_mappings.json`
  - Evitar colunas semânticas duplicadas (coalescência linha-a-linha)
  - Normalizar ``numero_ssa`` usando lógica existente do módulo `armazenamento.database`
  - Fazer parsing resiliente de datas em múltiplos formatos e valores numéricos (serial Excel)
  - Não lançar exceções para linhas/colunas inválidas: registra estatísticas e segue
  - Deduplicar por ``numero_ssa`` mantendo o registro com data_cadastro mais recente (ou primeiro válido)

Retorna (DataFrame normalizado, stats_dict).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Tuple

import pandas as pd  # type: ignore
from core.numero_ssa import normalize_strict as normalize_numero_ssa_strict
from core.date_utils import parse_any_date

logger = logging.getLogger(__name__)

DATE_COLUMNS_CANDIDATES = [
    "data_cadastro",
    "prazo_limite",
    "data_limite",
    "desde",
    "desde_1",
]

SERIAL_DATE_MIN = 10_000  # serial excel abaixo disso costuma ser lixo para nosso contexto


def _clean_numero_ssa_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Centraliza limpeza usando core.numero_ssa.normalize_strict.

    Mantém API anterior retornando (serie_limpa, mascara_valida).
    """
    cleaned: List[str | None] = []
    for v in series.tolist():
        # Evita caso comum de leitura Excel -> float com .0 (ex.: 202500777.0)
        try:
            if isinstance(v, float) and v.is_integer():
                v = int(v)
        except Exception:  # pragma: no cover
            pass
        cleaned.append(normalize_numero_ssa_strict(v))
    cleaned_series = pd.Series(cleaned, dtype="string")
    return cleaned_series, cleaned_series.notna()


@dataclass
class ImportStats:
    total_rows_in: int = 0
    total_rows_out: int = 0
    original_columns_count: int = 0
    mapped_columns_count: int = 0
    dropped_columns: List[str] | None = None
    merged_columns: Dict[str, List[str]] | None = None
    date_parse_failures: Dict[str, int] | None = None
    duplicate_rows_dropped: int = 0
    invalid_numero_ssa_rows: int = 0
    file_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------- Utilidades -----------------

def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _canonicalize_header(h: str) -> str:
    h2 = h.replace("\n", " ")
    h2 = re.sub(r"\s+", " ", h2).strip()
    h2 = _strip_accents(h2)
    return h2.lower()


def _build_alias_mapping(mapping_json_path: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    try:
        with open(mapping_json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # pragma: no cover
        logger.error("Falha ao ler mapping %s: %s", mapping_json_path, e)
        return {}, {}
    alias_to_canonical: Dict[str, str] = {}
    canonical_to_aliases: Dict[str, List[str]] = {}
    for canonical, aliases in data.items():
        all_names = [canonical] + list(aliases)
        for name in all_names:
            alias_norm = _canonicalize_header(name)
            if alias_norm not in alias_to_canonical:  # first wins
                alias_to_canonical[alias_norm] = canonical
        canonical_to_aliases[canonical] = [ _canonicalize_header(a) for a in aliases ]
    return alias_to_canonical, canonical_to_aliases


def _parse_single_date(val) -> str | None:  # compat wrapper
    return parse_any_date(val)


def _coalesce_columns(df: pd.DataFrame, columns: List[str]) -> pd.Series:
    if not columns:
        return pd.Series(dtype=object)
    base = df[columns[0]]
    if len(columns) == 1:
        return base
    result = base.copy()
    for col in columns[1:]:
        mask = result.isna() | (result.astype(str).str.strip() == "")
        result.loc[mask] = df[col].loc[mask]
    return result


# ----------------- Núcleo -----------------

def import_excel_robust(
    file_path: str,
    *,
    mappings_path: str = "config/column_mappings.json",
    drop_empty_numero_ssa: bool = True,
    deduplicate: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Executa importação robusta retornando DataFrame normalizado + estatísticas.

    Nunca levanta exceção (salvo erros catastróficos de IO) – registra problemas no log e prossegue.
    """
    stats = ImportStats(file_path=file_path, dropped_columns=[], merged_columns={}, date_parse_failures={})

    if not os.path.exists(file_path):  # Falha primária
        logger.error("Arquivo não encontrado: %s", file_path)
        return pd.DataFrame(), stats.to_dict()

    debug_enabled = bool(os.environ.get("SSA_IMPORT_DEBUG"))
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
        logger.debug("[import_excel_robust] Lendo planilha %s", file_path)

    try:
        raw_df = pd.read_excel(file_path)  # confiar no pandas para engine
    except Exception as e:
        logger.error("Falha ao ler planilha %s: %s", file_path, e)
        return pd.DataFrame(), stats.to_dict()

    if debug_enabled:
        logger.debug("[import_excel_robust] Linhas lidas=%d colunas=%d", len(raw_df), len(raw_df.columns))

    stats.total_rows_in = len(raw_df)
    stats.original_columns_count = len(raw_df.columns)

    alias_map, _ = _build_alias_mapping(mappings_path)

    # Mapear cabeçalhos -> canônicos
    original_to_canonical: Dict[str, str] = {}
    canonical_groups: Dict[str, List[str]] = {}
    for col in raw_df.columns:
        norm = _canonicalize_header(str(col))
        canonical = alias_map.get(norm, norm)  # se não mapeado, usar normalização
        original_to_canonical[col] = canonical
        canonical_groups.setdefault(canonical, []).append(col)

        # Promoção explícita: garantir que tenhamos uma coluna 'numero_ssa' se algum alias conhecido apareceu
        if 'numero_ssa' not in canonical_groups:
            # Procurar qualquer coluna original cujo header normalizado corresponda a um alias de numero_ssa
            numero_alias_keys = [k for k, v in alias_map.items() if v == 'numero_ssa']
            candidate_cols = []
            for col in raw_df.columns:
                norm = _canonicalize_header(str(col))
                if norm in numero_alias_keys:
                    candidate_cols.append(col)
            if candidate_cols:
                # Escolhe a primeira aparição para promover; registra merge
                sel = candidate_cols[0]
                canonical_groups['numero_ssa'] = [sel]
                original_to_canonical[sel] = 'numero_ssa'
                if debug_enabled:
                    logger.debug("[import_excel_robust] Promovida coluna '%s' a numero_ssa (fallback explicito)", sel)

    if debug_enabled:
        logger.debug("[import_excel_robust] Mapeamento colunas => %s", original_to_canonical)

    # Construir DF novo com coalescência garantindo que cada canônico aparece só uma vez
    new_cols: Dict[str, pd.Series] = {}
    for canonical, originals in canonical_groups.items():
        if len(originals) > 1:
            if stats.merged_columns is None:
                stats.merged_columns = {}
            stats.merged_columns.setdefault(canonical, originals)
        series = _coalesce_columns(raw_df, originals)
        # Evitar sobrescrever caso já exista (não deve, mas por segurança)
        if canonical in new_cols:
            # Combinar preferindo valores não nulos já existentes
            existing = new_cols[canonical]
            mask = existing.isna() | (existing.astype(str).str.strip() == "")
            existing.loc[mask] = series.loc[mask]
            new_cols[canonical] = existing
        else:
            new_cols[canonical] = series
    work_df = pd.DataFrame(new_cols)
    # Garantia extra: remover colunas duplicadas exatas 'numero_ssa' mantendo somente a primeira
    if 'numero_ssa' in work_df.columns:
        seen = False
        keep = []
        for c in work_df.columns:
            if c == 'numero_ssa':
                if not seen:
                    keep.append(c)
                    seen = True
                else:
                    continue
            else:
                keep.append(c)
        work_df = work_df[keep]

    # Normalizar numero_ssa
    if "numero_ssa" in work_df.columns:
        # Limpeza padronizada
        original = work_df["numero_ssa"].copy()
        cleaned_series, valid_mask = _clean_numero_ssa_series(original)
        if debug_enabled:
            logger.debug("[import_excel_robust] original numero_ssa=%s", original.tolist())
            logger.debug("[import_excel_robust] cleaned numero_ssa=%s valid_mask=%s", cleaned_series.tolist(), valid_mask.tolist())
        # Política estrita: se todos None não há recuperação.
        work_df["_numero_ssa_clean"] = cleaned_series
        # Contar inválidos (inclui vazios / None)
        stats.invalid_numero_ssa_rows = int((~valid_mask).sum())
        # Preservar somente linhas onde numero_ssa limpo não é None se solicitado
        # (Mas primeiro promovemos coluna para manter consistência de schema mesmo que filtragem seja desativada)
        work_df.drop(columns=["numero_ssa"], inplace=True)
        work_df.rename(columns={"_numero_ssa_clean": "numero_ssa"}, inplace=True)
        if drop_empty_numero_ssa:
            before = len(work_df)
            work_df = work_df[work_df["numero_ssa"].notna()].reset_index(drop=True)
            if debug_enabled:
                logger.debug("[import_excel_robust] removidas %d linhas com numero_ssa vazio/invalido", before - len(work_df))
        work_df['numero_ssa'] = work_df['numero_ssa'].astype('string')
        if debug_enabled:
            logger.debug("[import_excel_robust] numero_ssa apos limpeza: %s", work_df['numero_ssa'].head().tolist())

    # Datas
    for dcol in DATE_COLUMNS_CANDIDATES:
        if dcol in work_df.columns:
            parsed: List[str | None] = []
            fails = 0
            for val in work_df[dcol].tolist():
                parsed_val = _parse_single_date(val)
                # Contabiliza falhas apenas para valores não vazios reais.
                # Usar pd.isna para evitar TypeError em comparações com pd.NA.
                is_effectively_empty = (
                    val is None
                    or (isinstance(val, str) and val.strip() == "")
                    or (isinstance(val, (float, int)) and pd.isna(val))
                )
                if parsed_val is None and not is_effectively_empty:
                    fails += 1
                parsed.append(parsed_val)
            work_df[dcol] = pd.Series(parsed, dtype="object")
            stats.date_parse_failures[dcol] = fails

    # Deduplicar por numero_ssa usando data_cadastro
    if deduplicate and "numero_ssa" in work_df.columns:
        if "data_cadastro" in work_df.columns:
            try:
                temp = work_df.copy()
                temp["_dt"] = pd.to_datetime(temp["data_cadastro"], errors="coerce")
                # Ordenar por numero_ssa e data desc
                temp.sort_values(["numero_ssa", "_dt"], ascending=[True, False], inplace=True)
                before = len(temp)
                temp = temp.drop_duplicates(subset=["numero_ssa"], keep="first")
                stats.duplicate_rows_dropped = before - len(temp)
                temp.drop(columns=["_dt"], inplace=True)
                work_df = temp.reset_index(drop=True)
                if debug_enabled:
                    logger.debug("[import_excel_robust] Deduplicacao: removidos=%d linhas_finais=%d", stats.duplicate_rows_dropped, len(work_df))
            except Exception as e:  # pragma: no cover
                logger.warning("Falha deduplicacao numero_ssa: %s", e)

    # Filtragem adicional de numero_ssa inválido que escapou por formatação com traços ou caracteres
    # (ex.: '2025-22222' pode gerar '202522222' com tamanho incorreto / ano inválido após strip).
    if 'numero_ssa' in work_df.columns:
        # Como já filtramos inválidos, apenas garantir tipo string consistente
        work_df['numero_ssa'] = work_df['numero_ssa'].astype('string')

    # Remover colunas "Unnamed:" (pandas cria ao exportar índices) para evitar falha no insert SQL.
    unnamed_cols = [c for c in work_df.columns if c.startswith('unnamed:') or c.startswith('Unnamed:')]
    if unnamed_cols:
        work_df.drop(columns=unnamed_cols, inplace=True)
        if stats.dropped_columns is not None:
            stats.dropped_columns.extend(unnamed_cols)
        else:
            stats.dropped_columns = unnamed_cols

    stats.total_rows_out = len(work_df)
    stats.mapped_columns_count = len(work_df.columns)

    # Colunas descartadas são aquelas originais que não foram usadas? (nenhuma por ora)
    used_originals = set()
    for group in canonical_groups.values():
        used_originals.update(group)
    dropped = [c for c in raw_df.columns if c not in used_originals]
    stats.dropped_columns = dropped

    if debug_enabled:
        logger.debug("[import_excel_robust] Final rows=%d cols=%d", len(work_df), len(work_df.columns))
    stats_dict = stats.to_dict()
    # Persist consolidated stats JSON (dashboard consumption) if reports/ exists or can be created.
    try:
        os.makedirs("reports", exist_ok=True)
        # Enriquecimento leve: adicionar timestamp e versão de schema se disponível.
        from datetime import datetime
        schema_version = None
        try:
            with open("config/version.json", encoding="utf-8") as vf:  # reutiliza caso exista
                data_v = json.load(vf)
                schema_version = data_v.get("version") or data_v.get("app_version")
        except Exception:  # pragma: no cover
            pass
        enriched = dict(stats_dict)
        enriched["generated_at_utc"] = datetime.utcnow().isoformat() + "Z"
        if schema_version:
            enriched["schema_version"] = schema_version
        with open(os.path.join("reports", "last_import_stats.json"), "w", encoding="utf-8") as fh:
            json.dump(enriched, fh, ensure_ascii=False, indent=2)
    except Exception:  # pragma: no cover
        pass
    return work_df, stats_dict


__all__ = ["import_excel_robust", "ImportStats", "_clean_numero_ssa_series"]
