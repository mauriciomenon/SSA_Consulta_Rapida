"""Streamlit frontend otimizado para explorar SSAs utilizando o banco local."""
# Last modified: 2025-10-29T11:45:00 (improved arrow compatibility)
from __future__ import annotations

import hashlib
import importlib
import json
import logging
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
from utils.remote_itaipu import RequestOptions, fetch_pending_ssas, map_to_dataframe
st = cast(Any, importlib.import_module("streamlit"))

# Enable copy-on-write mode for performance (pandas 1.5+)
# With CoW, DataFrame.copy() returns lazy view that only copies on modification
# This makes cache operations much faster while maintaining safety
pd.options.mode.copy_on_write = True

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

        # Use Streamlit session_state if available, otherwise use local dict
        # This allows cache to work in tests and non-Streamlit contexts
        if hasattr(st, 'session_state') and st.session_state is not None:
            # Real Streamlit runtime - use session_state
            self._use_session_state = True
            if 'filter_cache' not in st.session_state:
                st.session_state.filter_cache = {}
            if 'cache_stats' not in st.session_state:
                st.session_state.cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        else:
            # Not in Streamlit runtime - use local dict
            self._use_session_state = False
            self._local_cache = {}
            self._local_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def _generate_key(self, df_shape: Tuple[int, int], search_terms: str, 
                     situacoes: list, executores: list, emissores: list) -> str:
        """Gera chave unica para o cache baseada nos parametros de filtro."""
        params = {
            'shape': df_shape,
            'search': search_terms,
            'situacoes': sorted(situacoes) if situacoes else [],
            'executores': sorted(executores) if executores else [],
            'emissores': sorted(emissores) if emissores else []
        }
        
        params_str = str(sorted(params.items()))
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()
    
    def get(self, df_shape: Tuple[int, int], search_terms: str,
           situacoes: list, executores: list, emissores: list) -> Optional[pd.DataFrame]:
        """Recupera resultado do cache se valido."""
        key = self._generate_key(df_shape, search_terms, situacoes, executores, emissores)

        # Get cache and stats from appropriate source
        if self._use_session_state:
            cache = st.session_state.filter_cache
            stats = st.session_state.cache_stats
        else:
            cache = self._local_cache
            stats = self._local_stats

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
    
    def put(self, df_shape: Tuple[int, int], search_terms: str,
           situacoes: list, executores: list, emissores: list, result: pd.DataFrame):
        """Armazena resultado no cache."""
        key = self._generate_key(df_shape, search_terms, situacoes, executores, emissores)

        # Get cache and stats from appropriate source
        if self._use_session_state:
            cache = st.session_state.filter_cache
            stats = st.session_state.cache_stats
        else:
            cache = self._local_cache
            stats = self._local_stats

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
        stats = st.session_state.cache_stats if self._use_session_state else self._local_stats
        total = stats['hits'] + stats['misses']
        hit_rate = (stats['hits'] / total * 100) if total > 0 else 0
        
        cache = st.session_state.filter_cache if self._use_session_state else self._local_cache

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
        cache = st.session_state.filter_cache
        entry = cache.get(key)
        if not entry:
            st.session_state.cache_stats['misses'] += 1
            return None
        if time.time() - entry['timestamp'] >= self.ttl_seconds:
            # expirada
            del cache[key]
            st.session_state.cache_stats['misses'] += 1
            return None
        st.session_state.cache_stats['hits'] += 1
        return entry['data'].copy()

    def cache_filter_result(self, key: str, result: pd.DataFrame, meta: Optional[dict] = None):
        cache = st.session_state.filter_cache
        # politica LRU simples
        if key in cache:
            del cache[key]
        while len(cache) >= self.max_size:
            oldest_key = next(iter(cache))
            del cache[oldest_key]
            st.session_state.cache_stats['evictions'] += 1
        cache[key] = {
            'data': result.copy(),
            'timestamp': time.time(),
            'meta': meta or {}
        }


# Instancia cache global
filter_cache = StreamlitFilterCache()


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
    # Verifica cache primeiro
    cached_result = filter_cache.get(df.shape, search_terms, situacoes, executores, emissores)
    if cached_result is not None:
        return cached_result
    
    # Cache miss - aplica filtros
    start_time = time.time()
    
    # Filtro de busca textual
    filtered_df = apply_cli_filters(df, search_terms)
    
    # Filtros de selecao multipla
    if situacoes:
        filtered_df = filtered_df[filtered_df['situacao'].isin(situacoes)]
    if executores:
        filtered_df = filtered_df[filtered_df['setor_executor'].isin(executores)]
    if emissores:
        filtered_df = filtered_df[filtered_df['setor_emissor'].isin(emissores)]
    
    # Reset index
    filtered_df = filtered_df.reset_index(drop=True)
    
    # Armazena no cache
    filter_cache.put(df.shape, search_terms, situacoes, executores, emissores, filtered_df)
    
    # Log performance se demorou mais que 100ms
    elapsed = time.time() - start_time
    if elapsed > 0.1:
        st.info(f" Filtro executado em {elapsed:.2f}s - resultado armazenado no cache")
    
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


def _is_real_streamlit_runtime() -> bool:
    # Evita executar UI completa durante import por testes com mocks
    try:
        return callable(getattr(st, 'set_page_config', None)) and callable(getattr(st, 'columns', None))
    except Exception:
        return False

if _is_real_streamlit_runtime():
    st.set_page_config(
        page_title="SSA Consulta Rapida",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 0.5rem; }
        h1 { font-size: 1.45rem !important; margin-bottom: 0.25rem; }
        .section-label { font-size: 0.85rem; color: #1f3b6d; margin-bottom: 0.4rem; }
        .filter-summary { margin-top: 0.4rem; font-weight: 600; font-size: 0.92rem; color: #1f3b6d; }
        .stButton button { width: 100%; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Cabecalho limpo
if _is_real_streamlit_runtime():
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.markdown("<h1>SSA Consulta Rapida</h1>", unsafe_allow_html=True)
        st.markdown("<p class='section-label'>Dashboard para analise e exportacao de SSAs</p>", unsafe_allow_html=True)
    with header_right:
        st.caption(f"Atualizado as {datetime.now().strftime('%H:%M:%S')}")

if _is_real_streamlit_runtime():
    with st.sidebar:
        st.subheader("Fonte de dados")
        db_path = st.text_input("Arquivo do banco", value=DB_PATH_DEFAULT)
        docs_dir = st.text_input("Pasta com planilhas", value=DOCS_DIR_DEFAULT)
        consult_api = st.checkbox("Sincronizar com API Itaipu", value=False)

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
                except Exception as e:
                    logger.warning(f"Failed to clear load_dataframe cache: {e}")
                filter_cache.clear()

                progress_holder.progress(100)
                if ok:
                    status_holder.info("Importacao concluida com sucesso.")
                else:
                    status_holder.warning("Nenhum arquivo novo processado.")
            except Exception as exc:  # noqa: BLE001
                progress_holder.progress(0)
                status_holder.error(f"Importacao falhou: {exc}")
            finally:
                time.sleep(0.5)
                progress_holder.empty()

        if btn_col_load.button("Carregar dados"):
            _execute_import(force=False)

        if btn_col_reimport.button("Reimportar planilhas"):
            _execute_import(force=True)

        st.caption("Use 'Carregar dados' para atualizar o banco existente. 'Reimportar planilhas' reprocessa todas as planilhas do diretorio.")
        st.divider()
        st.subheader("Cache")
        cache_stats = filter_cache.get_stats()
        st.write(f"Entradas: {cache_stats['size']} / {cache_stats['max_size']}")
        st.write(f"Hits: {cache_stats['hits']}  |  Falhas: {cache_stats['misses']}")
        st.write(f"Taxa de acerto: {cache_stats['hit_rate']:.1f}%  |  TTL: {cache_stats['ttl_seconds']}s")
        if st.button("Limpar cache"):
            filter_cache.clear()
            st.info("Cache limpo.")

# Carregar dados
raw_df = load_dataframe(db_path) if _is_real_streamlit_runtime() else pd.DataFrame()
if _is_real_streamlit_runtime() and raw_df.empty:
    st.info(
        "Banco nao encontrado ou sem dados. Utilize o botao 'Atualizar banco' na barra lateral "
        "para importar as planilhas."
    )
    st.stop()

search_terms = ""
situacao_sel = []
executor_sel = []
emissor_sel = []
selected_columns = list(raw_df.columns)

if _is_real_streamlit_runtime() and not raw_df.empty:
    st.subheader("Filtros rapidos")
    filter_cols = st.columns([3, 2, 2, 2, 1])

    search_terms = filter_cols[0].text_input(
        "Busca (mesma sintaxe da CLI)",
        value="",
        placeholder="ex.: svp, !ste, mel4",
    )

    situacoes = sorted(raw_df.get('situacao', pd.Series(dtype=str)).dropna().unique().tolist())
    default_situacao = situacoes
    situacao_sel = filter_cols[1].multiselect("Situacao", situacoes, default=default_situacao)

    executores = sorted(raw_df.get('setor_executor', pd.Series(dtype=str)).dropna().unique().tolist())
    default_executor = ['IEE3'] if 'IEE3' in executores else executores[:1]
    executor_sel = filter_cols[2].multiselect("Setor executor", executores, default=default_executor)

    emissores = sorted(raw_df.get('setor_emissor', pd.Series(dtype=str)).dropna().unique().tolist())
    default_emissor = ['IEE3'] if 'IEE3' in emissores else emissores[:1]
    emissor_sel = filter_cols[3].multiselect("Setor emissor", emissores, default=default_emissor)

    limit_rows = int(
        filter_cols[4].number_input(
            "Limite",
            min_value=50,
            max_value=5000,
            value=limit_rows,
            step=50,
            label_visibility="collapsed",
        )
    )
    filter_cols[4].caption(f"Limite: {limit_rows}")

    column_display_names = {col: DISPLAY_MAPPINGS.get(col, col) for col in raw_df.columns}
    default_columns = [col for col in raw_df.columns if col in (
        'numero_ssa', 'situacao', 'descricao_ssa', 'setor_executor', 'setor_emissor',
        'data_cadastro', 'prazo_limite'
    )]
    if not default_columns:
        default_columns = list(raw_df.columns[:10])

    column_container = st.container()
    selected_display = column_container.multiselect(
        "Colunas",
        options=[column_display_names[col] for col in raw_df.columns],
        default=[column_display_names[col] for col in default_columns],
        label_visibility="collapsed",
    )
    column_container.caption("Colunas exibidas")
    display_to_internal = {v: k for k, v in column_display_names.items()}
    selected_columns = [display_to_internal.get(name, name) for name in selected_display]

    with st.expander("Ajuda rapida", expanded=False):
        st.markdown(
            "* Sintaxe basica: `svp, !ste, mel4`\n"
            "* Use `OU` ou `OR` para alternativas (`svp OU mel4`)\n"
            "* Prefixos uteis: `^` inicio, `$` final, `=` igual, `~` regex\n"
            "* `!` inverte um termo (`!^adm`, `!mel4`)\n"
            "* Virgulas equivalem a E/AND; espacos tambem separam termos"
        )


# Aplica todos os filtros com cache inteligente (somente em runtime real)
if _is_real_streamlit_runtime():
    filtered_df = apply_all_filters_cached(
        raw_df, 
        search_terms,
        situacao_sel, 
        executor_sel, 
        emissor_sel
    )
    if limit_rows and len(filtered_df) > limit_rows:
        filtered_df = filtered_df.head(limit_rows)
else:
    filtered_df = pd.DataFrame()

active_summary: list[str] = []
if _is_real_streamlit_runtime() and search_terms.strip():
    active_summary.append(f"Busca: {search_terms.strip()}")
if _is_real_streamlit_runtime() and situacao_sel and situacoes and len(situacao_sel) != len(situacoes):
    active_summary.append("Situacao: " + ", ".join(situacao_sel))
if _is_real_streamlit_runtime() and executor_sel and executores and len(executor_sel) != len(executores):
    active_summary.append("Executor: " + ", ".join(executor_sel))
if _is_real_streamlit_runtime() and emissor_sel and emissores and len(emissor_sel) != len(emissores):
    active_summary.append("Emissor: " + ", ".join(emissor_sel))
if _is_real_streamlit_runtime() and consult_api:
    active_summary.append("API: ativada")

if _is_real_streamlit_runtime() and active_summary:
    st.markdown("**Filtros ativos:** " + " | ".join(active_summary))

# Indicadores rapidos em formato compacto
if _is_real_streamlit_runtime():
    total_ssas = len(filtered_df)
    original_count = len(raw_df)
    reduction_pct = ((original_count - total_ssas) / original_count * 100) if original_count else 0

    status_cols = st.columns(4)
    status_cols[0].markdown(f"**Total filtrado**<br>{total_ssas}", unsafe_allow_html=True)
    status_cols[1].markdown(f"**Total original**<br>{original_count}", unsafe_allow_html=True)
    status_cols[2].markdown(f"**Reducao**<br>{reduction_pct:.1f}%", unsafe_allow_html=True)

    if 'situacao' in filtered_df.columns and total_ssas:
        status_counts = filtered_df['situacao'].value_counts()
        executadas = int(status_counts.get('EXECUTADA', 0))
        exec_rate = (executadas / total_ssas * 100) if total_ssas else 0
        status_cols[3].markdown(f"**Execucao concluida**<br>{exec_rate:.1f}%", unsafe_allow_html=True)
    else:
        status_cols[3].markdown("**Execucao concluida**<br>-", unsafe_allow_html=True)

# Consulta opcional da API para dados mais recentes (nao bloqueia fluxo offline)
recent_df: pd.DataFrame | None = None
if _is_real_streamlit_runtime() and consult_api:
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
            st.success(
                f"API Itaipu retornou {len(recent_df)} registros recentes (campos limitados)."
            )
        else:
            st.info("API Itaipu respondeu sem novos registros. Exibindo apenas dados do banco local.")
    except Exception as e:
            logger.error(f"Failed to fetch data from Itaipu API: {e}")
            st.warning(
                "Nao foi possivel acessar dados mais recentes via API. O dashboard continua com o banco local."
            )

# Secao de dados com controles avancados
if _is_real_streamlit_runtime():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"Dados filtrados ({len(filtered_df)} registros)")
    with col2:
        table_height = st.selectbox("Altura da tabela (px)", [400, 600, 800, 1000], index=1)
    with col3:
        auto_width = st.checkbox("Ajuste automatico de largura", value=True)
else:
    table_height = 600
    auto_width = True

if _is_real_streamlit_runtime():
    # Preparacao dos dados para exibicao
    view_df = filtered_df[selected_columns] if selected_columns else filtered_df
    rename_map = {col: DISPLAY_MAPPINGS.get(col, col) for col in view_df.columns}
    display_df = ensure_arrow_compatible(view_df.rename(columns=rename_map))

    # Configuracao avancada de colunas
    column_config = {}
    for col in view_df.columns:
        display_name = rename_map.get(col, col)
        
        if col in {"situacao", "setor_executor", "setor_emissor"}:
            column_config[display_name] = st.column_config.TextColumn(width="small")
        elif col == "numero_ssa":
            column_config[display_name] = st.column_config.TextColumn(width="medium", help="Numero da SSA")
        elif "data" in col.lower():
            column_config[display_name] = st.column_config.DatetimeColumn(width="small")
        elif col == "descricao_ssa":
            column_config[display_name] = st.column_config.TextColumn(width="large")

# Exibe a tabela com configuracoes otimizadas
if _is_real_streamlit_runtime():
    if auto_width:
        st.dataframe(
            display_df,
            width="stretch",
            height=table_height,
            column_config=column_config,
            hide_index=True
        )
    else:
        st.dataframe(
            display_df,
            width="content",
            height=table_height,
            column_config=column_config,
            hide_index=True
        )

# Secao de exportacao
if _is_real_streamlit_runtime():
    st.markdown("### Exportacao")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # CSV basico
        csv_data = view_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV",
            csv_data,
            file_name=f"ssas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help=f"Exporta {len(view_df)} registros em CSV"
        )

    with col2:
        # Excel com formatacao
        if st.button("Gerar Excel", help="Prepara arquivo Excel com formatacao"):
            try:
                import io
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill
                
                buffer = io.BytesIO()
                wb = Workbook()
                ws = wb.active
                ws.title = "SSAs Filtradas"
                
                # Cabecalhos com formatacao
                for col_num, col_name in enumerate(view_df.columns, 1):
                    cell = ws.cell(row=1, column=col_num, value=rename_map.get(col_name, col_name))
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                
                # Dados
                for row_num, row_data in enumerate(view_df.itertuples(index=False), 2):
                    for col_num, value in enumerate(row_data, 1):
                        ws.cell(row=row_num, column=col_num, value=value)

                wb.save(buffer)
                buffer.seek(0)
                
                st.download_button(
                    "Excel formatado",
                    buffer.getvalue(),
                    file_name=f"ssas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.error("openpyxl nao instalado - usando CSV simples")

    with col3:
        # JSON para APIs
        json_text = view_df.to_json(orient='records', date_format='iso', indent=2)
        if json_text is None:
            raise RuntimeError("to_json retornou None")
        json_data = json_text.encode('utf-8')
        st.download_button(
            "Baixar JSON",
            json_data,
            file_name=f"ssas_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            help="Formato JSON para integracao com APIs"
        )

    with col4:
        # Estatisticas do filtro
        if st.button("Resumo estatistico", help="Mostra resumo estatistico"):
            stats_info = {
                "total_registros": len(view_df),
                "colunas_selecionadas": len(selected_columns),
                "filtros_ativos": len([x for x in [search_terms, situacao_sel, executor_sel, emissor_sel] if x]),
                "cache_hit_rate": f"{filter_cache.get_stats()['hit_rate']:.1f}%"
            }
            st.json(stats_info)

# Grafico simples de situacoes
if _is_real_streamlit_runtime() and 'situacao' in filtered_df.columns and not filtered_df.empty:
    chart_df = (
        filtered_df['situacao']
        .value_counts()
        .rename_axis('Situacao')
        .reset_index(name='Quantidade')
    )
    st.subheader("Distribuicao por Situacao")
    st.bar_chart(chart_df.set_index('Situacao'))

if _is_real_streamlit_runtime() and recent_df is not None and not recent_df.empty:
    st.markdown("### Dados recentes via API (campos limitados)")
    st.dataframe(ensure_arrow_compatible(recent_df), width='stretch', height=220)
