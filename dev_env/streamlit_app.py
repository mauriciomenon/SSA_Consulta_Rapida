"""Streamlit frontend otimizado para explorar SSAs utilizando o banco local."""
# Last modified: 2025-10-29T11:45:00 (improved arrow compatibility)
from __future__ import annotations

import hashlib
import importlib
import json
import logging
import math
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Optional, Tuple, cast

import pandas as pd
from core.app_logic import (
    filter_dataframe,
    get_filtered_data,
    import_files_to_database,
    parse_search_terms,
)
from core.config_manager import load_display_mappings_integrity
from gui.simple_width_manager import SimpleWidthManager
from utils.path_safety import PathSafetyError, ensure_path_is_allowed
from utils.remote_itaipu import RequestOptions, fetch_pending_ssas, map_to_dataframe

try:
    st = cast(Any, importlib.import_module("streamlit"))
except ModuleNotFoundError:
    class _StreamlitStub:
        session_state = None

        def __getattr__(self, _name: str):
            return None

    st = cast(Any, _StreamlitStub())

# pandas >= 3 keeps copy-on-write always enabled.

# Inicializar logging robusto
class _ASCIIOnlyFilter(logging.Filter):
    @staticmethod
    def _to_ascii(value):
        if isinstance(value, str):
            return value.encode('ascii', 'ignore').decode('ascii')
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._to_ascii(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: self._to_ascii(value) for key, value in record.args.items()}
            else:
                record.args = tuple(self._to_ascii(arg) for arg in record.args)
        if record.exc_text:
            record.exc_text = self._to_ascii(record.exc_text)
        return True


try:
    from utils.robust_logging import setup_logging
    setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
ascii_filter = _ASCIIOnlyFilter()
for handler in logging.getLogger().handlers:
    handler.addFilter(ascii_filter)
logger.debug("Logging configurado para Streamlit", extra={'component': 'streamlit'})

DB_PATH_DEFAULT = os.environ.get("SSA_DB_PATH", "data/ssas.db")
DOCS_DIR_DEFAULT = os.environ.get("SSA_DOCS_DIR", "docs_entrada")
DISPLAY_MAPPINGS = load_display_mappings_integrity()


# === Compatibilidade e Cache para Streamlit ===
# Variaveis padrao para evitar referencias nao definidas quando nao estiver em runtime real
db_path: str = DB_PATH_DEFAULT
docs_dir: str = DOCS_DIR_DEFAULT
search_terms: str = ""
limit_rows: int = 500
consult_api: bool = False
situacoes: list[str] = []
situacao_sel: list[str] = []
executores: list[str] = []
executor_sel: list[str] = []
emissores: list[str] = []
emissor_sel: list[str] = []
selected_columns: list[str] = []
# Placeholders para dados de exibicao quando fora de runtime real
view_df: pd.DataFrame = pd.DataFrame()
rename_map: dict[str, str] = {}
display_df: pd.DataFrame = pd.DataFrame()
column_config: dict[str, object] = {}
class StreamlitFilterCache:
    """Cache inteligente para filtros do Streamlit com TTL e estatisticas."""
    
    def __init__(self, max_size: int = 30, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._use_session_state = False
        self._local_cache: dict[str, dict[str, Any]] = {}
        self._local_stats: dict[str, int] = {'hits': 0, 'misses': 0, 'evictions': 0}
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        if not hasattr(st, 'session_state'):
            return
        try:
            session_state = st.session_state
            if session_state is None:
                return
            if 'filter_cache' not in session_state:
                session_state.filter_cache = {}
            if 'cache_stats' not in session_state:
                session_state.cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
            self._use_session_state = True
        except Exception as exc:
            logger.debug("Streamlit session_state unavailable in current runtime: %s", exc)

    def _resolve_backend(self) -> tuple[dict[str, Any], dict[str, int]]:
        if self._use_session_state:
            return st.session_state.filter_cache, st.session_state.cache_stats
        return self._local_cache, self._local_stats
    
    def _generate_key(
        self,
        df_shape: Tuple[int, int],
        search_terms: str,
        situacoes: list,
        executores: list,
        emissores: list,
        df_token: Any = None,
    ) -> str:
        """Gera chave unica para o cache baseada nos parametros de filtro."""
        params = {
            'shape': df_shape,
            'search': search_terms,
            'situacoes': sorted(situacoes) if situacoes else [],
            'executores': sorted(executores) if executores else [],
            'emissores': sorted(emissores) if emissores else [],
            'df_token': df_token,
        }
        
        params_str = str(sorted(params.items()))
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()
    
    def get(
        self,
        df_shape: Tuple[int, int],
        search_terms: str,
        situacoes: list,
        executores: list,
        emissores: list,
        df_token: Any = None,
    ) -> Optional[pd.DataFrame]:
        """Recupera resultado do cache se valido."""
        key = self._generate_key(df_shape, search_terms, situacoes, executores, emissores, df_token=df_token)
        cache, stats = self._resolve_backend()

        if key in cache:
            entry = cache[key]
            # Verifica TTL
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                # Move para o final (LRU)
                cache[key] = cache.pop(key)
                stats['hits'] += 1
                return entry['data'].copy()
            else:
                # Cache expirado
                del cache[key]

        stats['misses'] += 1
        return None
    
    def put(
        self,
        df_shape: Tuple[int, int],
        search_terms: str,
        situacoes: list,
        executores: list,
        emissores: list,
        result: pd.DataFrame,
        df_token: Any = None,
    ):
        """Armazena resultado no cache."""
        key = self._generate_key(df_shape, search_terms, situacoes, executores, emissores, df_token=df_token)
        cache, stats = self._resolve_backend()

        # Remove entrada existente se houver
        if key in cache:
            del cache[key]

        # Implementa politica LRU
        while len(cache) >= self.max_size:
            # Remove item mais antigo
            oldest_key = next(iter(cache))
            del cache[oldest_key]
            stats['evictions'] += 1

        # Adiciona nova entrada
        cache[key] = {
            'data': result.copy(),
            'timestamp': time.time()
        }
    
    def get_stats(self) -> dict:
        """Retorna estatisticas do cache."""
        cache, stats = self._resolve_backend()
        total = stats['hits'] + stats['misses']
        hit_rate = (stats['hits'] / total * 100) if total > 0 else 0

        return {
            'size': len(cache),
            'entries': len(cache),
            'max_size': self.max_size,
            'hits': stats['hits'],
            'misses': stats['misses'],
            'evictions': stats['evictions'],
            'hit_rate': hit_rate,
            'ttl_seconds': self.ttl_seconds
        }

    def clear(self):
        """Limpa todo o cache."""
        if self._use_session_state:
            st.session_state.filter_cache = {}
            st.session_state.cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        else:
            self._local_cache = {}
            self._local_stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    # --- Metodos de compatibilidade com scripts de teste ---
    def get_cached_filter(self, key: str) -> Optional[pd.DataFrame]:
        cache, stats = self._resolve_backend()
        entry = cache.get(key)
        if not entry:
            stats['misses'] += 1
            return None
        if time.time() - entry['timestamp'] >= self.ttl_seconds:
            # expirada
            del cache[key]
            stats['misses'] += 1
            return None
        stats['hits'] += 1
        return entry['data'].copy()

    def cache_filter_result(self, key: str, result: pd.DataFrame, meta: Optional[dict] = None):
        cache, stats = self._resolve_backend()
        # politica LRU simples
        if key in cache:
            del cache[key]
        while len(cache) >= self.max_size:
            oldest_key = next(iter(cache))
            del cache[oldest_key]
            stats['evictions'] += 1
        cache[key] = {
            'data': result.copy(),
            'timestamp': time.time(),
            'meta': meta or {}
        }


# Instancia cache global
filter_cache = StreamlitFilterCache()
width_manager = SimpleWidthManager()


def load_dataframe(db_path: str) -> pd.DataFrame:
    """
    Carrega dados do banco de dados com tratamento de erros.

    Returns:
        DataFrame com dados ou DataFrame vazio em caso de erro
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return pd.DataFrame()

    try:
        df = get_filtered_data(db_path)
        if df.empty:
            logger.info(f"Database query returned empty result: {db_path}")
        else:
            logger.debug(f"Loaded {len(df)} records from {db_path}")
        return df
    except sqlite3.Error as e:
        logger.error(f"SQLite error loading data from {db_path}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error loading data from {db_path}: {e}")
        return pd.DataFrame()

# Aplica cache do Streamlit se disponivel; adiciona clear() no fallback
if hasattr(st, "cache_data") and callable(getattr(st, "cache_data")):
    load_dataframe = st.cache_data(show_spinner=False)(load_dataframe)
else:
    setattr(load_dataframe, "clear", lambda: None)

# Alias para compatibilidade: funcao utilitaria esperada pelos testes
def apply_filters_with_cache(df: pd.DataFrame, search_terms: str,
                            situacoes: list, executores: list, emissores: list) -> pd.DataFrame:
    return apply_all_filters_cached(df, search_terms, situacoes, executores, emissores)


def _compute_df_cache_token(df: pd.DataFrame) -> tuple[Any, ...]:
    """Compute lightweight token to reduce stale cache hits on equal shapes."""
    cached_token = df.attrs.get("_streamlit_cache_token")
    if cached_token is not None:
        return cached_token

    columns = tuple(str(col) for col in df.columns)
    if len(df.columns) == 0:
        token = (len(df), columns, None, None)
        df.attrs["_streamlit_cache_token"] = token
        return token
    if df.empty:
        token = (0, columns, None, None)
        df.attrs["_streamlit_cache_token"] = token
        return token
    sample_column = 'numero_ssa' if 'numero_ssa' in df.columns else df.columns[0]
    sample_series = df[sample_column]
    head_values = tuple(str(value) for value in sample_series.head(10).tolist())
    tail_values = tuple(str(value) for value in sample_series.tail(10).tolist())
    token = (len(df), columns, str(sample_column), head_values, tail_values)
    df.attrs["_streamlit_cache_token"] = token
    return token


def _build_streamlit_column_config(
    page_df: pd.DataFrame,
    rename_map: dict[str, str],
    available_width: int = 1600,
) -> dict[str, Any]:
    column_config_api = getattr(st, "column_config", None)
    if column_config_api is None:
        return {}
    computed_buckets = width_manager.compute_streamlit_width_buckets(
        page_df,
        available_width=available_width,
        column_order=list(page_df.columns),
    )
    config: dict[str, Any] = {}
    for col in page_df.columns:
        display_name = rename_map.get(col, col)
        bucket = str(computed_buckets.get(col, "medium"))
        if "data" in col.lower():
            config[display_name] = column_config_api.DatetimeColumn(width=bucket)
        elif col == "numero_ssa":
            config[display_name] = column_config_api.TextColumn(
                width=bucket,
                help="Numero da SSA",
            )
        else:
            config[display_name] = column_config_api.TextColumn(width=bucket)
    return config


def apply_cli_filters(df: pd.DataFrame, search_text: str) -> pd.DataFrame:
    """Aplica filtros CLI com fallback para caso sem cache."""
    if not search_text.strip():
        return df
    raw_terms = [term.strip() for term in search_text.split(',') if term.strip()]
    parsed = parse_search_terms(raw_terms)
    return filter_dataframe(df, parsed)


def apply_all_filters_cached(df: pd.DataFrame, search_terms: str, 
                           situacoes: list, executores: list, emissores: list) -> pd.DataFrame:
    """Aplica todos os filtros com cache inteligente."""
    df_token = _compute_df_cache_token(df)
    # Verifica cache primeiro
    cached_result = filter_cache.get(
        df.shape,
        search_terms,
        situacoes,
        executores,
        emissores,
        df_token=df_token,
    )
    if cached_result is not None:
        return cached_result
    
    # Cache miss - aplica filtros
    start_time = time.time()
    
    # Filtro de busca textual
    filtered_df = apply_cli_filters(df, search_terms)
    
    # Filtros de selecao multipla
    if situacoes and 'situacao' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['situacao'].isin(situacoes)]
    if executores and 'setor_executor' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['setor_executor'].isin(executores)]
    if emissores and 'setor_emissor' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['setor_emissor'].isin(emissores)]
    
    # Reset index
    filtered_df = filtered_df.reset_index(drop=True)
    
    # Armazena no cache
    filter_cache.put(
        df.shape,
        search_terms,
        situacoes,
        executores,
        emissores,
        filtered_df,
        df_token=df_token,
    )
    
    # Log performance se demorou mais que 100ms
    elapsed = time.time() - start_time
    if elapsed > 0.1:
        logger.info("Filtro streamlit executado em %.2fs (cache miss)", elapsed)
    
    return filtered_df


def ensure_arrow_compatible(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza colunas para evitar falhas do Streamlit/Arrow.

    Tenta preservar tipos numericos quando possivel, convertendo apenas
    colunas verdadeiramente mistas para string.
    """
    safe = df.copy()  # Cheap with copy-on-write
    conversions_made = []

    for col in safe.columns:
        series = safe[col]
        dtype_str = str(series.dtype)

        # Skip modern nullable dtypes (already Arrow-compatible)
        if dtype_str.startswith('string') or dtype_str in ['Int64', 'Int32', 'Float64', 'Float32']:
            continue

        if series.dtype == "object":
            non_null = series.dropna()
            if not non_null.empty:
                sample_types = {type(x) for x in non_null.head(20)}

                # Check if truly mixed types
                if len(sample_types) > 1:
                    # Sample more values to determine majority type
                    sample_size = min(100, len(non_null))
                    type_counts: dict[type[Any], int] = {}
                    for val in non_null.head(sample_size):
                        t = type(val)
                        type_counts[t] = type_counts.get(t, 0) + 1

                    majority_type = max(type_counts, key=type_counts.__getitem__)

                    # If mostly numeric, try to preserve as numeric
                    if majority_type in (int, float):
                        try:
                            safe[col] = pd.to_numeric(series, errors='coerce')
                            conversions_made.append(f"{col}: mixed->numeric")
                            continue
                        except Exception:
                            pass  # Fall through to string conversion

                    # Otherwise convert to string
                    safe[col] = series.astype(str)
                    conversions_made.append(f"{col}: mixed->string")
                    continue

                # Handle list/dict types
                sample = non_null.iloc[0]
                if isinstance(sample, (list, dict)):
                    safe[col] = series.apply(
                        lambda x: json.dumps(x, ensure_ascii=False)
                        if isinstance(x, (list, dict))
                        else x
                    )
                    conversions_made.append(f"{col}: list/dict->json")

        elif pd.api.types.is_integer_dtype(series.dtype):
            safe[col] = series.astype("Int64")

    if conversions_made:
        logger.debug(f"Arrow compatibility conversions: {', '.join(conversions_made)}")

    return safe


def _build_filter_options(df: pd.DataFrame) -> tuple[list[Any], list[Any], list[Any]]:
    situacoes = sorted(
        df.get('situacao', pd.Series(dtype=str)).dropna().unique().tolist(),
        key=lambda value: str(value),
    )
    executores = sorted(
        df.get('setor_executor', pd.Series(dtype=str)).dropna().unique().tolist(),
        key=lambda value: str(value),
    )
    emissores = sorted(
        df.get('setor_emissor', pd.Series(dtype=str)).dropna().unique().tolist(),
        key=lambda value: str(value),
    )
    return situacoes, executores, emissores


def _paginate_dataframe(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int]:
    if page_size <= 0:
        raise ValueError("page_size must be greater than zero")
    total_pages = max(1, math.ceil(len(df) / page_size))
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end].reset_index(drop=True), total_pages


def _normalize_filter_selection(selected: list[Any], options: list[Any]) -> list[Any]:
    if not options:
        return []
    normalized = [value for value in selected if value in options]
    if len(normalized) == len(options):
        return []
    return normalized


def _default_visible_columns(columns: list[str]) -> list[str]:
    core = [
        'numero_ssa',
        'situacao',
        'descricao_ssa',
        'setor_executor',
        'setor_emissor',
        'data_cadastro',
        'prazo_limite',
    ]
    picked = [col for col in columns if col in core]
    return picked if picked else list(columns[:10])


def _build_column_presets(columns: list[str]) -> dict[str, list[str]]:
    defaults = _default_visible_columns(columns)
    return {
        "core": defaults,
        "all": list(columns),
    }


def _is_real_streamlit_runtime() -> bool:
    # Evita executar UI completa fora do runtime do streamlit.
    try:
        runtime_module = getattr(st, "runtime", None)
        exists_fn = getattr(runtime_module, "exists", None)
        if callable(exists_fn):
            return bool(exists_fn())
        has_ui_api = callable(getattr(st, 'set_page_config', None)) and callable(getattr(st, 'columns', None))
        has_state = hasattr(st, 'session_state') and st.session_state is not None
        return bool(has_ui_api and has_state)
    except Exception:
        return False
REAL_RUNTIME = _is_real_streamlit_runtime()

if REAL_RUNTIME:
    st.set_page_config(
        page_title="SSA Consulta Rapida",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 0.8rem; padding-bottom: 0.5rem; }
        h1 { font-size: 1.35rem !important; margin-bottom: 0.15rem; }
        .section-label { font-size: 0.84rem; color: #1f3b6d; margin-bottom: 0.35rem; }
        .stButton button { width: 100%; }
        </style>
        """,
        unsafe_allow_html=True,
    )

db_path = DB_PATH_DEFAULT
docs_dir = DOCS_DIR_DEFAULT
consult_api = False

if REAL_RUNTIME:
    header_left, header_right = st.columns([5, 1])
    with header_left:
        st.markdown("<h1>SSA Consulta Rapida</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p class='section-label'>Painel streamlit com filtros, tabela paginada e exportacao</p>",
            unsafe_allow_html=True,
        )
    with header_right:
        st.caption(f"Atualizado as {datetime.now().strftime('%H:%M:%S')}")

    with st.sidebar:
        st.subheader("Fonte de dados")
        db_path = st.text_input("Arquivo do banco", value=DB_PATH_DEFAULT)
        docs_dir = st.text_input("Pasta com planilhas", value=DOCS_DIR_DEFAULT)
        try:
            db_path = str(
                ensure_path_is_allowed(
                    db_path,
                    purpose="Arquivo do banco",
                    expect_directory=False,
                )
            )
            docs_dir = str(
                ensure_path_is_allowed(
                    docs_dir,
                    purpose="Pasta com planilhas",
                    expect_directory=True,
                )
            )
        except PathSafetyError as exc:
            st.error(str(exc))
            st.stop()

        btn_col_load, btn_col_reimport = st.columns(2)
        status_holder = st.empty()
        progress_holder = st.empty()

        def _execute_import(force: bool) -> None:
            try:
                progress_holder.progress(15)
                status_holder.info("Verificando arquivos ...")
                ok = import_files_to_database(
                    docs_dir=docs_dir,
                    db_path=db_path,
                    force_import=force,
                    raise_on_error=True,
                )
                progress_holder.progress(60)
                status_holder.info("Atualizando cache ...")
                try:
                    if hasattr(load_dataframe, "clear"):
                        load_dataframe.clear()
                except Exception as exc:
                    logger.warning("Falha ao limpar cache de load_dataframe: %s", exc)
                filter_cache.clear()
                if hasattr(st, "session_state") and st.session_state is not None:
                    st.session_state["recent_api_df"] = None
                progress_holder.progress(100)
                if ok:
                    status_holder.info("Importacao concluida com sucesso.")
                else:
                    status_holder.warning("Nenhum arquivo novo processado.")
            except Exception as exc:  # noqa: BLE001
                progress_holder.progress(0)
                status_holder.error(f"Importacao falhou: {exc}")
            finally:
                progress_holder.empty()

        if btn_col_load.button("Carregar dados"):
            _execute_import(force=False)
        if btn_col_reimport.button("Reimportar planilhas"):
            _execute_import(force=True)

        st.caption(
            "Use 'Carregar dados' para atualizar o banco existente. "
            "'Reimportar planilhas' refaz o processamento completo."
        )

raw_df = load_dataframe(db_path) if REAL_RUNTIME else pd.DataFrame()
if REAL_RUNTIME and raw_df.empty:
    st.info(
        "Banco nao encontrado ou sem dados. Use os botoes da barra lateral para importar planilhas."
    )
    st.stop()

search_terms = ""
situacao_sel: list[Any] = []
executor_sel: list[Any] = []
emissor_sel: list[Any] = []
selected_columns = list(raw_df.columns)
limit_rows = 500
page_size = 250
page_number = 1
table_height = 600
auto_width = True
recent_df: pd.DataFrame | None = None
situacoes: list[Any] = []
executores: list[Any] = []
emissores: list[Any] = []

if REAL_RUNTIME and not raw_df.empty:
    tab_filters, tab_table, tab_export, tab_ops = st.tabs(
        ["Filtros", "Tabela", "Exportacao", "Cache e API"]
    )

    with tab_filters:
        st.subheader("Filtros")
        situacoes, executores, emissores = _build_filter_options(raw_df)
        default_executor = ['IEE3'] if 'IEE3' in executores else executores[:1]
        default_emissor = ['IEE3'] if 'IEE3' in emissores else emissores[:1]
        column_display_names = {col: DISPLAY_MAPPINGS.get(col, col) for col in raw_df.columns}
        default_columns = _default_visible_columns(list(raw_df.columns))
        column_presets = _build_column_presets(list(raw_df.columns))

        state_key = "streamlit_filters_state"
        if state_key not in st.session_state:
            st.session_state[state_key] = {
                "search_terms": "",
                "consult_api": False,
                "situacao_sel": situacoes,
                "executor_sel": default_executor,
                "emissor_sel": default_emissor,
                "limit_rows": limit_rows,
                "selected_display": [column_display_names[col] for col in default_columns],
            }
        filter_state = st.session_state[state_key]
        filter_state["situacao_sel"] = [value for value in filter_state.get("situacao_sel", []) if value in situacoes] or situacoes
        filter_state["executor_sel"] = [value for value in filter_state.get("executor_sel", []) if value in executores] or default_executor
        filter_state["emissor_sel"] = [value for value in filter_state.get("emissor_sel", []) if value in emissores] or default_emissor
        valid_display_values = set(column_display_names.values())
        selected_display_state = [value for value in filter_state.get("selected_display", []) if value in valid_display_values]
        filter_state["selected_display"] = selected_display_state or [column_display_names[col] for col in default_columns]

        table_state_key = "streamlit_table_state"
        if table_state_key not in st.session_state:
            st.session_state[table_state_key] = {
                "sort_column": "(Sem ordenacao)",
                "sort_desc": False,
                "page_size": 250,
                "table_height": 600,
                "auto_width": True,
                "page_number": 1,
                "width_profile": "Padrao (1600)",
            }
        table_state = st.session_state[table_state_key]
        table_state["page_size"] = int(table_state.get("page_size", 250))
        table_state["table_height"] = int(table_state.get("table_height", 600))
        table_state["auto_width"] = bool(table_state.get("auto_width", True))
        table_state["sort_desc"] = bool(table_state.get("sort_desc", False))
        table_state["page_number"] = int(table_state.get("page_number", 1))
        table_state["width_profile"] = str(table_state.get("width_profile", "Padrao (1600)"))

        with st.form("filters_form", clear_on_submit=False):
            search_input = st.text_input(
                "Busca (mesma sintaxe da CLI)",
                value=filter_state.get("search_terms", ""),
                placeholder="ex.: svp, !ste, mel4",
            )
            consult_api_input = st.checkbox(
                "Ativar consulta manual da API Itaipu",
                value=bool(filter_state.get("consult_api", False)),
            )
            row_filters = st.columns([2, 2, 2, 1])
            situacao_input = row_filters[0].multiselect(
                "Situacao",
                situacoes,
                default=filter_state.get("situacao_sel", situacoes),
            )
            executor_input = row_filters[1].multiselect(
                "Setor executor",
                executores,
                default=filter_state.get("executor_sel", default_executor),
            )
            emissor_input = row_filters[2].multiselect(
                "Setor emissor",
                emissores,
                default=filter_state.get("emissor_sel", default_emissor),
            )
            limit_input = int(
                row_filters[3].number_input(
                    "Limite de linhas",
                    min_value=50,
                    max_value=20000,
                    value=int(filter_state.get("limit_rows", limit_rows)),
                    step=50,
                )
            )
            selected_display_input = st.multiselect(
                "Colunas exibidas",
                options=[column_display_names[col] for col in raw_df.columns],
                default=filter_state.get("selected_display", [column_display_names[col] for col in default_columns]),
            )
            preset_cols = st.columns(3)
            preset_core = preset_cols[0].form_submit_button("Preset core")
            preset_all = preset_cols[1].form_submit_button("Preset all")
            preset_keep = preset_cols[2].form_submit_button("Manter custom")
            with st.expander("Ajuda rapida", expanded=False):
                st.markdown(
                    "* Sintaxe basica: `svp, !ste, mel4`\n"
                    "* Use `OU` ou `OR` para alternativas (`svp OU mel4`)\n"
                    "* Prefixos uteis: `^` inicio, `$` final, `=` igual, `~` regex\n"
                    "* `!` inverte termo (`!^adm`, `!mel4`)\n"
                    "* Virgulas equivalem a E/AND; espacos tambem separam termos"
                )
            form_cols = st.columns(2)
            apply_filters = form_cols[0].form_submit_button("Aplicar filtros")
            reset_filters = form_cols[1].form_submit_button("Resetar filtros")

        if reset_filters:
            st.session_state[state_key] = {
                "search_terms": "",
                "consult_api": False,
                "situacao_sel": situacoes,
                "executor_sel": default_executor,
                "emissor_sel": default_emissor,
                "limit_rows": 500,
                "selected_display": [column_display_names[col] for col in default_columns],
            }
            st.session_state[table_state_key] = {
                "sort_column": "(Sem ordenacao)",
                "sort_desc": False,
                "page_size": 250,
                "table_height": 600,
                "auto_width": True,
                "page_number": 1,
                "width_profile": "Padrao (1600)",
            }
            rerun_fn = getattr(st, "rerun", None)
            if callable(rerun_fn):
                rerun_fn()
            else:
                legacy_rerun_fn = getattr(st, "experimental_rerun", None)
                if callable(legacy_rerun_fn):
                    legacy_rerun_fn()

        if preset_core:
            filter_state["selected_display"] = [column_display_names[col] for col in column_presets["core"]]
        elif preset_all:
            filter_state["selected_display"] = [column_display_names[col] for col in column_presets["all"]]
        elif preset_keep:
            filter_state["selected_display"] = selected_display_input

        if apply_filters:
            st.session_state[state_key] = {
                "search_terms": search_input,
                "consult_api": consult_api_input,
                "situacao_sel": situacao_input,
                "executor_sel": executor_input,
                "emissor_sel": emissor_input,
                "limit_rows": limit_input,
                "selected_display": selected_display_input,
            }

        filter_state = st.session_state[state_key]
        search_terms = str(filter_state.get("search_terms", ""))
        consult_api = bool(filter_state.get("consult_api", False))
        situacao_sel = list(filter_state.get("situacao_sel", situacoes))
        executor_sel = list(filter_state.get("executor_sel", default_executor))
        emissor_sel = list(filter_state.get("emissor_sel", default_emissor))
        limit_rows = int(filter_state.get("limit_rows", 500))
        selected_display = list(filter_state.get("selected_display", [column_display_names[col] for col in default_columns]))
        display_to_internal = {v: k for k, v in column_display_names.items()}
        selected_columns = [display_to_internal.get(name, name) for name in selected_display]

    situacao_filter = _normalize_filter_selection(situacao_sel, situacoes)
    executor_filter = _normalize_filter_selection(executor_sel, executores)
    emissor_filter = _normalize_filter_selection(emissor_sel, emissores)

    filtered_df = apply_all_filters_cached(
        raw_df,
        search_terms,
        situacao_filter,
        executor_filter,
        emissor_filter,
    )
    if limit_rows and len(filtered_df) > limit_rows:
        filtered_df = filtered_df.head(limit_rows).reset_index(drop=True)

    view_df = filtered_df[selected_columns] if selected_columns else filtered_df
    rename_map = {col: DISPLAY_MAPPINGS.get(col, col) for col in view_df.columns}

    active_summary: list[str] = []
    if search_terms.strip():
        active_summary.append(f"Busca: {search_terms.strip()}")
    if situacao_filter:
        active_summary.append("Situacao: " + ", ".join(str(value) for value in situacao_filter))
    if executor_filter:
        active_summary.append("Executor: " + ", ".join(str(value) for value in executor_filter))
    if emissor_filter:
        active_summary.append("Emissor: " + ", ".join(str(value) for value in emissor_filter))
    if consult_api:
        active_summary.append("API: manual")

    with tab_table:
        total_ssas = len(filtered_df)
        original_count = len(raw_df)
        reduction_pct = ((original_count - total_ssas) / original_count * 100) if original_count else 0
        table_left, table_right = st.columns([4, 1.2])
        with table_left:
            status_cols = st.columns(4)
            status_cols[0].metric("Total filtrado", total_ssas)
            status_cols[1].metric("Total original", original_count)
            status_cols[2].metric("Reducao", f"{reduction_pct:.1f}%")
            if 'situacao' in filtered_df.columns and total_ssas:
                status_counts = filtered_df['situacao'].value_counts()
                executadas = int(status_counts.get('EXECUTADA', 0))
                exec_rate = (executadas / total_ssas * 100) if total_ssas else 0
                status_cols[3].metric("Execucao concluida", f"{exec_rate:.1f}%")
            else:
                status_cols[3].metric("Execucao concluida", "-")

        with table_right:
            st.caption("Resumo")
            st.write(f"Registros visiveis: {len(view_df)}")
            st.write(f"Colunas visiveis: {len(view_df.columns)}")
            st.write(f"Cache hit rate: {filter_cache.get_stats()['hit_rate']:.1f}%")

        control_cols = st.columns([2, 1, 1, 1, 1, 1.5])
        sort_options = ["(Sem ordenacao)"] + list(view_df.columns)
        sort_column = str(
            control_cols[0].selectbox(
                "Ordenar por",
                sort_options,
                index=sort_options.index(table_state.get("sort_column", "(Sem ordenacao)"))
                if table_state.get("sort_column", "(Sem ordenacao)") in sort_options
                else 0,
            )
        )
        sort_desc = bool(control_cols[1].checkbox("Desc", value=table_state.get("sort_desc", False)))
        page_size = int(
            control_cols[2].selectbox(
                "Linhas por pagina",
                [100, 250, 500, 1000, 2000],
                index=[100, 250, 500, 1000, 2000].index(table_state.get("page_size", 250))
                if table_state.get("page_size", 250) in [100, 250, 500, 1000, 2000]
                else 1,
            )
        )
        table_height = int(
            control_cols[3].selectbox(
                "Altura tabela (px)",
                [400, 600, 800, 1000],
                index=[400, 600, 800, 1000].index(table_state.get("table_height", 600))
                if table_state.get("table_height", 600) in [400, 600, 800, 1000]
                else 1,
            )
        )
        auto_width = bool(control_cols[4].checkbox("Auto largura", value=table_state.get("auto_width", True)))
        width_profile_options = [
            "Compacto (1200)",
            "Padrao (1600)",
            "Largo (2000)",
            "XL (2400)",
        ]
        width_profile = str(
            control_cols[5].selectbox(
                "Perfil largura",
                width_profile_options,
                index=width_profile_options.index(table_state.get("width_profile", "Padrao (1600)"))
                if table_state.get("width_profile", "Padrao (1600)") in width_profile_options
                else 1,
            )
        )
        width_profile_pixels = {
            "Compacto (1200)": 1200,
            "Padrao (1600)": 1600,
            "Largo (2000)": 2000,
            "XL (2400)": 2400,
        }

        table_view_df = view_df
        if sort_column != "(Sem ordenacao)" and sort_column in table_view_df.columns:
            try:
                table_view_df = table_view_df.sort_values(
                    by=sort_column,
                    ascending=not sort_desc,
                    kind="stable",
                )
            except Exception as exc:
                logger.warning("Falha ao ordenar por %s: %s", sort_column, exc)

        _, total_pages = _paginate_dataframe(table_view_df, page=1, page_size=page_size)
        default_page = min(max(int(table_state.get("page_number", 1)), 1), total_pages)
        page_col_left, page_col_right = st.columns([1, 4])
        page_number = int(
            page_col_left.number_input(
                f"Pagina (1..{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=default_page,
                step=1,
            )
        )
        page_col_right.caption(
            "Dica: use perfil de largura maior para reduzir truncamento de descricao."
        )
        page_df, total_pages = _paginate_dataframe(table_view_df, page=page_number, page_size=page_size)
        table_state.update(
            {
                "sort_column": sort_column,
                "sort_desc": sort_desc,
                "page_size": page_size,
                "table_height": table_height,
                "auto_width": auto_width,
                "page_number": page_number,
                "width_profile": width_profile,
            }
        )

        display_df = ensure_arrow_compatible(page_df.rename(columns=rename_map))
        column_config = _build_streamlit_column_config(
            page_df,
            rename_map,
            available_width=width_profile_pixels.get(width_profile, 1600),
        )

        st.dataframe(
            display_df,
            width="stretch" if auto_width else "content",
            height=table_height,
            column_config=column_config,
            hide_index=True,
        )
        st.caption(
            f"Exibindo pagina {page_number}/{total_pages} | "
            f"linhas nesta pagina: {len(page_df)} | linhas filtradas: {len(table_view_df)}"
        )
        if active_summary:
            st.markdown("**Filtros ativos:** " + " | ".join(active_summary))

        if 'situacao' in filtered_df.columns and not filtered_df.empty:
            chart_df = (
                filtered_df['situacao']
                .value_counts()
                .rename_axis('Situacao')
                .reset_index(name='Quantidade')
            )
            st.subheader("Distribuicao por Situacao")
            st.bar_chart(chart_df.set_index('Situacao'))

    with tab_export:
        st.subheader("Exportacao")
        export_cols = st.columns(4)
        csv_data = view_df.to_csv(index=False).encode("utf-8")
        export_cols[0].download_button(
            "Baixar CSV",
            csv_data,
            file_name=f"ssas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help=f"Exporta {len(view_df)} registros em CSV",
        )

        with export_cols[1]:
            if st.button("Gerar Excel", help="Prepara arquivo Excel com formatacao"):
                try:
                    import io
                    from openpyxl import Workbook
                    from openpyxl.styles import Font, PatternFill

                    buffer = io.BytesIO()
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "SSAs Filtradas"
                    for col_num, col_name in enumerate(view_df.columns, 1):
                        cell = ws.cell(row=1, column=col_num, value=rename_map.get(col_name, col_name))
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    for row_num, row_data in enumerate(view_df.itertuples(index=False), 2):
                        for col_num, value in enumerate(row_data, 1):
                            ws.cell(row=row_num, column=col_num, value=value)
                    wb.save(buffer)
                    buffer.seek(0)
                    st.download_button(
                        "Excel formatado",
                        buffer.getvalue(),
                        file_name=f"ssas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except ImportError:
                    st.error("openpyxl nao instalado - usando CSV simples")

        json_text = view_df.to_json(orient='records', date_format='iso', indent=2)
        if json_text is None:
            raise RuntimeError("to_json retornou None")
        export_cols[2].download_button(
            "Baixar JSON",
            json_text.encode('utf-8'),
            file_name=f"ssas_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            help="Formato JSON para integracao com APIs",
        )

        if export_cols[3].button("Resumo estatistico", help="Mostra resumo estatistico"):
            stats_info = {
                "total_registros": len(view_df),
                "colunas_selecionadas": len(selected_columns),
                "filtros_ativos": len([x for x in [search_terms, situacao_sel, executor_sel, emissor_sel] if x]),
                "cache_hit_rate": f"{filter_cache.get_stats()['hit_rate']:.1f}%",
            }
            st.json(stats_info)

    with tab_ops:
        st.subheader("Cache")
        cache_stats = filter_cache.get_stats()
        ops_col1, ops_col2, ops_col3 = st.columns(3)
        ops_col1.metric("Entradas cache", f"{cache_stats['size']} / {cache_stats['max_size']}")
        ops_col2.metric("Hit rate", f"{cache_stats['hit_rate']:.1f}%")
        ops_col3.metric("Evictions", cache_stats['evictions'])
        if st.button("Limpar cache", key="clear_cache_ops"):
            filter_cache.clear()
            st.info("Cache limpo.")

        st.subheader("API Itaipu")
        if consult_api:
            if hasattr(st, "session_state") and st.session_state is not None:
                if "recent_api_df" not in st.session_state:
                    st.session_state["recent_api_df"] = None
            api_actions = st.columns(2)
            if api_actions[0].button("Atualizar dados API", key="refresh_api_data"):
                try:
                    api_items = fetch_pending_ssas(years=1, opts=RequestOptions(timeout=5.0))
                    mapped = map_to_dataframe(api_items)
                    if mapped is not None and not mapped.empty:
                        cols = [
                            col
                            for col in (
                                "numero_ssa",
                                "situacao",
                                "setor_emissor",
                                "setor_executor",
                                "descricao_ssa",
                                "data_cadastro",
                            )
                            if col in mapped.columns
                        ]
                        recent_df = mapped[cols].copy()
                        if hasattr(st, "session_state") and st.session_state is not None:
                            st.session_state["recent_api_df"] = recent_df
                        st.success(f"API retornou {len(recent_df)} registros.")
                    else:
                        st.info("API sem novos registros.")
                except Exception as exc:  # noqa: BLE001
                    logger.error("Falha ao consultar API Itaipu: %s", exc)
                    st.warning("Nao foi possivel consultar API. Dashboard segue com base local.")
            if api_actions[1].button("Limpar snapshot API", key="clear_api_data"):
                if hasattr(st, "session_state") and st.session_state is not None:
                    st.session_state["recent_api_df"] = None
                st.info("Snapshot de API removido.")
            if hasattr(st, "session_state") and st.session_state is not None:
                recent_df = st.session_state.get("recent_api_df")
            if recent_df is not None and not recent_df.empty:
                st.dataframe(ensure_arrow_compatible(recent_df), width='stretch', height=240)
        else:
            st.info("Ative a opcao de API na aba Filtros para consultar dados recentes.")
