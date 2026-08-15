# utils/robust_importer.py
# Last modified: 2025-10-29T11:30:00 (pandas import improvements)
# Referencia: documentacao de heuristicas e schema unificado em docs/SCHEMA_UNIFICADO_IMPORTACAO.md
"""Importador "à prova de bala" para planilhas SSA.

Objetivos:
    - Tolerar diferenças de cabeçalho (acentos, maiúsculas, quebras de linha, espaços extras)
    - Colapsar sinônimos conforme `config/column_mappings.json`
    - Evitar colunas semânticas duplicadas (coalescência linha-a-linha)
    - Normalizar ``numero_ssa`` usando lógica existente do módulo `armazenamento.database`
    - Parsing resiliente de datas (textual + serial Excel)
    - Não lançar exceções em linhas/colunas inválidas: registra estatísticas e segue
    - Deduplicar por ``numero_ssa`` mantendo registro com data_cadastro mais recente ou primeiro válido

Retorna: (DataFrame normalizado, stats_dict).
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

import pandas as pd

from shared.date_utils import parse_any_date
from shared.numero_ssa import normalize_strict as normalize_numero_ssa_strict

logger = logging.getLogger(__name__)

_DOTTED_DUPLICATE_RE = re.compile(r"^(?P<base>.+)\.(?P<suffix>\d+)$")
_SEMANTIC_DUPLICATE_COLUMNS: dict[str, list[str]] = {
    "desde": ["desde", "desde_1", "desde_2"],
    "ate": ["ate", "ate_1", "ate_2"],
    "sn": ["sn_retirado", "sn_instalado", "sn_extra"],
    "numero_ssa": [
        "numero_ssa",
        "numero_ssa_relacionada_1",
        "numero_ssa_relacionada_2",
        "numero_ssa_relacionada_3",
    ],
    "setor_emissor": [
        "setor_emissor",
        "setor_emissor_relacionado_1",
        "setor_emissor_relacionado_2",
    ],
    "setor_executor": [
        "setor_executor",
        "setor_executor_relacionado_1",
        "setor_executor_relacionado_2",
    ],
    "situacao": [
        "situacao",
        "situacao_relacionada_1",
        "situacao_relacionada_2",
    ],
}

DATE_COLUMNS_CANDIDATES = [
    "data_cadastro",
    "prazo_limite",
    "data_limite",
    "desde",
    "desde_1",
]

SSA_IDENTIFIER_COLUMNS = (
    "derivada_de",
    "numero_ssa_relacionada_1",
    "numero_ssa_relacionada_2",
    "numero_ssa_relacionada_3",
)

# Nota: threshold de serial Excel removido; lógica atual delega ao parse_any_date que
# já trata serials realistas e ignora ruídos sem depender de limite arbitrário.


def _clean_numero_ssa_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Centraliza limpeza usando core.numero_ssa.normalize_strict.

    Mantém API anterior retornando (serie_limpa, mascara_valida).
    """
    cleaned: List[str | None] = []
    for v in series.tolist():
        # Evita caso comum de leitura Excel -> float com .0 (ex.: 202500777.0)
        if isinstance(v, float) and v.is_integer():
            v = int(v)
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
    date_parse_failures: Dict[str, int] = field(default_factory=dict)
    duplicate_rows_dropped: int = 0
    invalid_numero_ssa_rows: int = 0
    file_path: str = ""
    # Novas métricas diagnósticas
    header_candidate_lines_considered: int = 0
    selected_header_line_index: int | None = None
    alias_hits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------- Utilidades -----------------


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def canonicalize_header(h: str) -> str:
    h2 = h.replace("\n", " ")
    h2 = re.sub(r"\s+", " ", h2).strip()
    h2 = _strip_accents(h2)
    return h2.lower()


def _build_alias_mapping(
    mapping_json_path: str,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
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
            alias_norm = canonicalize_header(name)
            if alias_norm not in alias_to_canonical:  # first wins
                alias_to_canonical[alias_norm] = canonical
        canonical_to_aliases[canonical] = [canonicalize_header(a) for a in aliases]
    return alias_to_canonical, canonical_to_aliases


def _parse_single_date(val) -> str | None:  # compat wrapper
    return parse_any_date(val)


def _read_excel_source(
    excel_source: str | pd.ExcelFile,
    *,
    sheet_name: str | int,
    header: int | None,
) -> pd.DataFrame:
    if isinstance(excel_source, pd.ExcelFile):
        return pd.read_excel(
            excel_source,
            sheet_name=sheet_name,
            header=header,
            dtype_backend="numpy_nullable",
        )
    from extracao.extractor import open_validated_excel_source

    with open_validated_excel_source(excel_source) as source_stream:
        return pd.read_excel(
            source_stream,
            sheet_name=sheet_name,
            header=header,
            engine="openpyxl",
            dtype_backend="numpy_nullable",
        )


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


def _resolve_semantic_duplicate_columns(
    columns: list[str],
    *,
    alias_map: dict[str, str],
) -> list[str]:
    resolved: list[str] = []
    used: set[str] = set()

    for original_name in columns:
        normalized_name = canonicalize_header(str(original_name))
        match = _DOTTED_DUPLICATE_RE.fullmatch(normalized_name)
        base_name = match.group("base") if match else normalized_name
        suffix_index = int(match.group("suffix")) if match else 0
        canonical_base = alias_map.get(base_name, base_name)
        options = _SEMANTIC_DUPLICATE_COLUMNS.get(canonical_base)

        if options is None:
            if match:
                candidate = f"{canonical_base}_{suffix_index}"
            elif canonical_base != base_name:
                candidate = canonical_base
            else:
                candidate = str(original_name)
        elif 0 <= suffix_index < len(options):
            candidate = options[suffix_index]
        else:
            candidate = f"{options[0]}_{suffix_index}"

        if candidate not in used:
            used.add(candidate)
            resolved.append(candidate)
            continue

        dedup_index = 1
        dedup_candidate = f"{candidate}_{dedup_index}"
        while dedup_candidate in used:
            dedup_index += 1
            dedup_candidate = f"{candidate}_{dedup_index}"
        used.add(dedup_candidate)
        resolved.append(dedup_candidate)

    return resolved


# ----------------- Nucleo -----------------


def import_excel_robust(
    file_path: str | pd.ExcelFile,
    *,
    mappings_path: str = "config/column_mappings.json",
    drop_empty_numero_ssa: bool = True,
    deduplicate: bool = True,
    sheet_name: str | int = 0,
    header: int | None = 0,
    raw_mode: bool = False,
    raise_on_error: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Executa importação robusta retornando DataFrame normalizado + estatísticas.

    Modo padrao aplica normalizacao canonica de SSA e deduplicacao.
    `raw_mode=True` e um caminho controlado para callers internos que precisam
    ler a aba crua preservando colunas originais.
    Por padrao registra problemas no log e prossegue; com raise_on_error=True
    propaga falhas de leitura e arquivo ausente.
    """
    source_label = str(getattr(file_path, "io", file_path))
    excel_source = file_path

    stats = ImportStats(
        file_path=source_label,
        dropped_columns=[],
        merged_columns={},
        date_parse_failures={},
    )

    if not isinstance(excel_source, pd.ExcelFile) and not os.path.exists(
        excel_source
    ):  # Falha primária
        logger.error("Arquivo não encontrado: %s", excel_source)
        if raise_on_error:
            raise FileNotFoundError(f"Arquivo nao encontrado: {excel_source}")
        return pd.DataFrame(), stats.to_dict()

    debug_enabled = bool(os.environ.get("SSA_IMPORT_DEBUG"))
    if debug_enabled:
        logger.setLevel(logging.DEBUG)
        logger.debug("[import_excel_robust] Lendo planilha %s", source_label)

    try:
        raw_df = _read_excel_source(
            excel_source,
            sheet_name=sheet_name,
            header=header,
        )
    except Exception as e:
        logger.error("Falha ao ler planilha %s: %s", source_label, e)
        if raise_on_error:
            raise
        return pd.DataFrame(), stats.to_dict()

    if isinstance(raw_df, dict):
        error = ValueError("import_excel_robust requires a concrete sheet_name")
        logger.error("Falha ao ler planilha %s: %s", source_label, error)
        if raise_on_error:
            raise error
        return pd.DataFrame(), stats.to_dict()

    if raw_mode:
        stats.total_rows_in = len(raw_df)
        stats.total_rows_out = len(raw_df)
        stats.original_columns_count = len(raw_df.columns)
        stats.mapped_columns_count = len(raw_df.columns)
        return raw_df, stats.to_dict()

    if debug_enabled:
        logger.debug(
            "[import_excel_robust] Linhas lidas=%d colunas=%d",
            len(raw_df),
            len(raw_df.columns),
        )

    # Heurística 1: cabeçalho mesclado único replicado por todas as colunas (ex.: um título abrangendo a linha)
    # Sinal: muitos (>5) nomes de colunas idênticos e não vazios -> provavelmente a linha 0 é só título e a linha real de cabeçalhos é a próxima
    distinct_non_empty = {
        str(c).strip()
        for c in raw_df.columns
        if str(c).strip() != "" and not str(c).lower().startswith("unnamed")
    }
    if len(distinct_non_empty) == 1 and raw_df.shape[1] > 5:
        if debug_enabled:
            logger.debug(
                "[import_excel_robust] Detectado header mesclado único (%s). Tentando reinterpretar próxima linha como cabeçalho real.",
                list(distinct_non_empty)[0],
            )
        try:
            # Releitura bruta sem header para inspecionar.
            raw_no_header = _read_excel_source(
                excel_source,
                sheet_name=sheet_name,
                header=None,
            )
            # Procurar primeira linha (após a 0) que contenha >=5 strings não vazias curtas.
            candidate_idx = None
            max_scan = min(15, raw_no_header.shape[0])
            for ridx in range(1, max_scan):  # começa em 1 (linha 0 é título)
                row = raw_no_header.iloc[ridx]
                non_null = row.dropna()
                str_like = [
                    v
                    for v in non_null
                    if isinstance(v, str) and 0 < len(v.strip()) < 80
                ]
                if len(str_like) >= 5:
                    candidate_idx = ridx
                    break
            if candidate_idx is not None:
                if debug_enabled:
                    logger.debug(
                        "[import_excel_robust] Linha %d escolhida como header real.",
                        candidate_idx,
                    )
                raw_df = _read_excel_source(
                    excel_source,
                    sheet_name=sheet_name,
                    header=candidate_idx,
                )
            else:
                if debug_enabled:
                    logger.debug(
                        "[import_excel_robust] Nenhuma linha candidata encontrada; mantendo header original."
                    )
        except Exception as e:  # pragma: no cover
            if debug_enabled:
                logger.debug(
                    "[import_excel_robust] Falha ao reprocessar header mesclado: %s", e
                )

    stats.total_rows_in = len(raw_df)
    stats.original_columns_count = len(raw_df.columns)

    alias_map, _ = _build_alias_mapping(mappings_path)
    alias_hit_counter = 0
    # Cache simples para canonicalização de headers repetidos
    _header_cache: dict[str, str] = {}

    # Função auxiliar interna para tentar reconstruir DataFrame com um header específico e remapear.
    def _attempt_reheader(
        candidate_header_row: int,
    ) -> tuple[pd.DataFrame, dict[str, list[str]], dict[str, str]]:
        try:
            tmp_df = _read_excel_source(
                excel_source,
                sheet_name=sheet_name,
                header=candidate_header_row,
            )
        except Exception:
            return raw_df, {}, {}
        orig_to_can: Dict[str, str] = {}
        can_groups: Dict[str, List[str]] = {}
        for c in tmp_df.columns:
            n = canonicalize_header(str(c))
            can = alias_map.get(n, n)
            orig_to_can[c] = can
            can_groups.setdefault(can, []).append(c)
        return tmp_df, can_groups, orig_to_can

    # Mapear cabeçalhos -> canônicos
    original_to_canonical: Dict[str, str] = {}
    canonical_groups: Dict[str, List[str]] = {}
    for col in raw_df.columns:
        raw_col_str = str(col)
        norm = _header_cache.get(raw_col_str)
        if norm is None:
            norm = canonicalize_header(raw_col_str)
            _header_cache[raw_col_str] = norm
        canonical = alias_map.get(norm, norm)  # se não mapeado, usar normalização
        if canonical != norm:
            alias_hit_counter += 1
        original_to_canonical[col] = canonical
        canonical_groups.setdefault(canonical, []).append(col)

    # Se após mapeamento inicial houver somente 1 grupo canônico e número de colunas originais > 5,
    # tentar detectar linha de cabeçalho real entre as primeiras 10 linhas.
    if len(canonical_groups) <= 1 and raw_df.shape[1] > 5:
        if debug_enabled:
            logger.debug(
                "[import_excel_robust] Apenas %d colunas canônicas detectadas; tentando reheader multi-linha.",
                len(canonical_groups),
            )
        best_df = raw_df
        best_groups = canonical_groups
        best_map = original_to_canonical
        improved = False
        # Examina linhas 0..9 como potenciais cabeçalhos
        max_scan_env = os.environ.get("SSA_MAX_HEADER_SCAN")
        try:
            max_scan_conf = int(max_scan_env) if max_scan_env else 10
        except ValueError:  # pragma: no cover
            max_scan_conf = 10
        scan_limit = min(max_scan_conf, max(1, raw_df.shape[0]))
        selected_header_line_index: int | None = None
        for candidate in range(scan_limit):
            tmp_df, tmp_groups, tmp_map = _attempt_reheader(candidate)
            if len(tmp_groups) > len(best_groups):
                best_df, best_groups, best_map = tmp_df, tmp_groups, tmp_map
                improved = True
                selected_header_line_index = candidate
                if debug_enabled:
                    logger.debug(
                        "[import_excel_robust] Reheader candidate %d => %d grupos.",
                        candidate,
                        len(tmp_groups),
                    )
                if len(best_groups) >= 5:  # heurística de suficiência
                    break
        stats.header_candidate_lines_considered = scan_limit
        if improved:
            raw_df = best_df
            canonical_groups = best_groups
            original_to_canonical = best_map
            if debug_enabled:
                logger.debug(
                    "[import_excel_robust] Reheader aplicado com sucesso. Total grupos=%d",
                    len(canonical_groups),
                )
            stats.selected_header_line_index = selected_header_line_index

    # Promoção explícita: garantir que exista coluna 'numero_ssa' se algum alias conhecido apareceu
    if "numero_ssa" not in canonical_groups:
        numero_alias_keys = [k for k, v in alias_map.items() if v == "numero_ssa"]
        candidate_cols = []
        for col in raw_df.columns:
            norm = canonicalize_header(str(col))
            if norm in numero_alias_keys:
                candidate_cols.append(col)
        if candidate_cols:
            sel = candidate_cols[0]
            canonical_groups["numero_ssa"] = [sel]
            original_to_canonical[sel] = "numero_ssa"
            if debug_enabled:
                logger.debug(
                    "[import_excel_robust] Promovida coluna '%s' a numero_ssa (fallback explicito)",
                    sel,
                )

    # Fallback adicional: detectar planilhas onde a primeira coluna é título geral da folha
    # Ex: 'SSAs com Desvio na Programação' aparecendo como único cabeçalho => gera apenas 1 coluna mapeada.
    # Heurística: se mapped_columns_count ficar muito baixo depois (tratado mais adiante) ou
    # se só existir 1 coluna e ela contém > 70% de valores NaN vs linhas totais, tentar usar primeira linha como header real.
    if (
        len(raw_df.columns) == 1
        and raw_df.columns[0]
        and raw_df.columns[0].strip() != ""
        and raw_df.iloc[0].notna().sum() > 3
    ):
        # Verifica se a primeira linha parece mais um cabeçalho (strings curtas diversificadas)
        possible_header = raw_df.iloc[0].tolist()
        string_cells = [
            c for c in possible_header if isinstance(c, str) and 0 < len(c) < 60
        ]
        if len(string_cells) >= 3:
            new_headers = []
            for idx, val in enumerate(possible_header):
                base = str(val).strip() if val is not None else f"col_{idx}"
                if base == "" or base.lower().startswith("unnamed"):
                    base = f"col_{idx}"
                new_headers.append(base)
            if debug_enabled:
                logger.debug(
                    "[import_excel_robust] Reinterpretando primeira linha como cabeçalho: %s",
                    new_headers,
                )
            raw_df = raw_df.iloc[1:].reset_index(drop=True)
            raw_df.columns = new_headers
            # Reprocessar mapeamentos com novos headers
            original_to_canonical.clear()
            canonical_groups.clear()
            for col in raw_df.columns:
                raw_col_str = str(col)
                norm = _header_cache.get(raw_col_str)
                if norm is None:
                    norm = canonicalize_header(raw_col_str)
                    _header_cache[raw_col_str] = norm
                canonical = alias_map.get(norm, norm)
                if canonical != norm:
                    alias_hit_counter += 1
                original_to_canonical[col] = canonical
                canonical_groups.setdefault(canonical, []).append(col)
            if "numero_ssa" not in canonical_groups:
                # tenta novamente promover numero_ssa
                numero_alias_keys = [
                    k for k, v in alias_map.items() if v == "numero_ssa"
                ]
                for col in raw_df.columns:
                    norm = canonicalize_header(str(col))
                    if norm in numero_alias_keys:
                        canonical_groups["numero_ssa"] = [col]
                        original_to_canonical[col] = "numero_ssa"
                        break

    if debug_enabled:
        logger.debug(
            "[import_excel_robust] Mapeamento colunas => %s", original_to_canonical
        )

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
    work_df.columns = _resolve_semantic_duplicate_columns(
        list(work_df.columns),
        alias_map=alias_map,
    )
    # Garantia extra: remover colunas duplicadas exatas 'numero_ssa' mantendo somente a primeira
    if "numero_ssa" in work_df.columns:
        seen = False
        keep = []
        for c in work_df.columns:
            if c == "numero_ssa":
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
            logger.debug(
                "[import_excel_robust] original numero_ssa=%s", original.tolist()
            )
            logger.debug(
                "[import_excel_robust] cleaned numero_ssa=%s valid_mask=%s",
                cleaned_series.tolist(),
                valid_mask.tolist(),
            )
        # Política estrita: se todos None não há recuperação.
        work_df["_numero_ssa_clean"] = cleaned_series
        # Contar inválidos (inclui vazios / None)
        stats.invalid_numero_ssa_rows = int((~valid_mask).sum())
        # Preservar somente linhas onde numero_ssa limpo não é None se solicitado
        # (Primeiro promovemos coluna para manter consistência de schema mesmo sem filtragem)
        work_df.drop(columns=["numero_ssa"], inplace=True)
        work_df.rename(columns={"_numero_ssa_clean": "numero_ssa"}, inplace=True)
        if drop_empty_numero_ssa:
            before = len(work_df)
            work_df = work_df[work_df["numero_ssa"].notna()].reset_index(drop=True)
            if debug_enabled:
                logger.debug(
                    "[import_excel_robust] removidas %d linhas com numero_ssa vazio/invalido",
                    before - len(work_df),
                )
        work_df["numero_ssa"] = work_df["numero_ssa"].astype("string")
        if debug_enabled:
            logger.debug(
                "[import_excel_robust] numero_ssa apos limpeza: %s",
                work_df["numero_ssa"].head().tolist(),
            )

    for column_name in SSA_IDENTIFIER_COLUMNS:
        if column_name not in work_df.columns:
            continue
        cleaned_series, _ = _clean_numero_ssa_series(work_df[column_name])
        work_df[column_name] = cleaned_series.astype("string")
        if debug_enabled:
            logger.debug(
                "[import_excel_robust] %s apos limpeza canonica: %s",
                column_name,
                work_df[column_name].head().tolist(),
            )

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
                temp.sort_values(
                    ["numero_ssa", "_dt"], ascending=[True, False], inplace=True
                )
                before = len(temp)
                temp = temp.drop_duplicates(subset=["numero_ssa"], keep="first")
                stats.duplicate_rows_dropped = before - len(temp)
                temp.drop(columns=["_dt"], inplace=True)
                work_df = temp.reset_index(drop=True)
                if debug_enabled:
                    logger.debug(
                        "[import_excel_robust] Deduplicacao: removidos=%d linhas_finais=%d",
                        stats.duplicate_rows_dropped,
                        len(work_df),
                    )
            except Exception as e:  # pragma: no cover
                logger.warning("Falha deduplicacao numero_ssa: %s", e)

    # Filtragem adicional de numero_ssa inválido que escapou por formatação com traços ou caracteres
    # (ex.: '2025-22222' pode gerar '202522222' com tamanho incorreto / ano inválido após strip).
    if "numero_ssa" in work_df.columns:
        # Como já filtramos inválidos, apenas garantir tipo string consistente
        work_df["numero_ssa"] = work_df["numero_ssa"].astype("string")

    # Remover colunas "Unnamed:" (pandas cria ao exportar índices) para evitar falha no insert SQL.
    unnamed_cols = [
        c
        for c in work_df.columns
        if c.startswith("unnamed:") or c.startswith("Unnamed:")
    ]
    if unnamed_cols:
        work_df.drop(columns=unnamed_cols, inplace=True)
        if stats.dropped_columns is not None:
            stats.dropped_columns.extend(unnamed_cols)
        else:
            stats.dropped_columns = unnamed_cols

    stats.total_rows_out = len(work_df)
    stats.mapped_columns_count = len(work_df.columns)
    stats.alias_hits = alias_hit_counter

    # Colunas descartadas são aquelas originais que não foram usadas? (nenhuma por ora)
    used_originals = set()
    for group in canonical_groups.values():
        used_originals.update(group)
    dropped = [c for c in raw_df.columns if c not in used_originals]
    stats.dropped_columns = dropped

    if debug_enabled:
        logger.debug(
            "[import_excel_robust] Final rows=%d cols=%d",
            len(work_df),
            len(work_df.columns),
        )
    stats_dict = stats.to_dict()
    # Persist consolidated stats JSON (dashboard consumption) if reports/ exists or can be created.
    try:
        os.makedirs("reports", exist_ok=True)
        # Enriquecimento leve: adicionar timestamp e versão de schema se disponível.
        from datetime import datetime, timezone

        schema_version = None
        try:
            with open(
                "config/version.json", encoding="utf-8"
            ) as vf:  # reutiliza caso exista
                data_v = json.load(vf)
                schema_version = data_v.get("version") or data_v.get("app_version")
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            logger.debug("Nao foi possivel ler config/version.json: %s", exc)
        enriched = dict(stats_dict)
        enriched["generated_at_utc"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        if schema_version:
            enriched["schema_version"] = schema_version
        with open(
            os.path.join("reports", "last_import_stats.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump(enriched, fh, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError) as exc:  # pragma: no cover
        logger.warning("Falha ao gravar reports/last_import_stats.json: %s", exc)
    return work_df, stats_dict


__all__ = ["import_excel_robust", "ImportStats", "_clean_numero_ssa_series"]
