"""Streamlit frontend simplificado para explorar SSAs utilizando o banco local."""
from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

from core.app_logic import (
    filter_dataframe,
    get_filtered_data,
    import_files_to_database,
    parse_search_terms,
)
from core.config_manager import load_display_mappings_integrity
from utils.remote_itaipu import RequestOptions, fetch_pending_ssas, map_to_dataframe

DB_PATH_DEFAULT = os.environ.get("SSA_DB_PATH", "data/ssas.db")
DOCS_DIR_DEFAULT = os.environ.get("SSA_DOCS_DIR", "docs_entrada")
DISPLAY_MAPPINGS = load_display_mappings_integrity()


@st.cache_data(show_spinner=False)
def load_dataframe(db_path: str) -> pd.DataFrame:
    if not os.path.exists(db_path):
        return pd.DataFrame()
    return get_filtered_data(db_path)


def apply_cli_filters(df: pd.DataFrame, search_text: str) -> pd.DataFrame:
    if not search_text.strip():
        return df
    raw_terms = [term.strip() for term in search_text.split(',') if term.strip()]
    parsed = parse_search_terms(raw_terms)
    return filter_dataframe(df, parsed)


def ensure_arrow_compatible(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza colunas para evitar falhas do Streamlit/Arrow."""
    safe = df.copy()
    for col in safe.columns:
        series = safe[col]
        if series.dtype == "object":
            non_null = series.dropna()
            if not non_null.empty:
                sample_types = {type(x) for x in non_null.head(20)}
                if len(sample_types) > 1:
                    safe[col] = series.astype(str)
                    continue
                sample = non_null.iloc[0]
                if isinstance(sample, (list, dict)):
                    safe[col] = series.apply(
                        lambda x: json.dumps(x, ensure_ascii=False)
                        if isinstance(x, (list, dict))
                        else x
                    )
        elif pd.api.types.is_integer_dtype(series.dtype):
            safe[col] = series.astype("Int64")
    return safe


st.set_page_config(page_title="SSA Consulta Rápida", layout="wide")
st.title("SSA Consulta Rápida – Dashboard Streamlit")

with st.sidebar:
    with st.expander("Fonte de dados", expanded=True):
        db_path = st.text_input("Caminho do banco SQLite", value=DB_PATH_DEFAULT)
        docs_dir = st.text_input("Diretório de planilhas", value=DOCS_DIR_DEFAULT)
        col_sync_1, col_sync_2 = st.columns(2)
        with col_sync_1:
            force_import = st.checkbox("Forçar reimportação", value=False)
        with col_sync_2:
            if st.button("Atualizar banco", use_container_width=True):
                with st.spinner("Importando planilhas..."):
                    ok = import_files_to_database(
                        docs_dir=docs_dir,
                        db_path=db_path,
                        force_import=force_import,
                    )
                    if ok:
                        st.success("Importação concluída.")
                    else:
                        st.error("Falha ao importar dados. Clique nos logs para detalhes.")
                load_dataframe.clear()

    with st.expander("Filtros", expanded=True):
        search_terms = st.text_input(
            "Busca rapida (virgulas, mesma sintaxe da CLI)",
            value="",
            help="Separe por virgulas. Use OU/OR para alternativas e ! para exclusoes.",
        )
        limit_rows = st.slider("Limitar linhas exibidas", min_value=50, max_value=2000, value=500, step=50)
        consult_api = st.checkbox(
            "Consultar API Itaipu por dados recentes",
            value=False,
            help=(
                "A API oficial fornece apenas campos básicos (número, situação, setores, emissor). "
                "Se estiver indisponível, os dados locais continuam sendo exibidos normalmente."
            ),
        )

# Carregar dados
raw_df = load_dataframe(db_path)
if raw_df.empty:
    st.info(
        "Banco não encontrado ou sem dados. Utilize o botão 'Atualizar banco' na barra lateral "
        "para importar as planilhas."
    )
    st.stop()

# Filtros adicionais (exibidos com base no dataset carregado)
with st.sidebar:
    st.subheader("Filtros rápidos")
    situacoes = sorted([s for s in raw_df.get('situacao', pd.Series(dtype=str)).dropna().unique()])
    situacao_sel = st.multiselect("Situações", situacoes, default=situacoes[:1])
    executores = sorted([s for s in raw_df.get('setor_executor', pd.Series(dtype=str)).dropna().unique()])
    default_executor = ['IEE3'] if 'IEE3' in executores else executores[:1]
    executor_sel = st.multiselect("Setores executores", executores, default=default_executor)
    emissores = sorted([s for s in raw_df.get('setor_emissor', pd.Series(dtype=str)).dropna().unique()])
    default_emissor = ['IEE3'] if 'IEE3' in emissores else emissores[:1]
    emissor_sel = st.multiselect("Setores emissores", emissores, default=default_emissor)
    column_display_names = {
        col: DISPLAY_MAPPINGS.get(col, col)
        for col in raw_df.columns
    }
default_columns = [col for col in raw_df.columns if col in (
        'numero_ssa', 'situacao', 'descricao_ssa', 'setor_executor', 'setor_emissor',
        'data_cadastro', 'prazo_limite'
    )]
    if not default_columns:
        default_columns = list(raw_df.columns[:10])
    selected_display = st.multiselect(
        "Colunas para exibir",
        options=[column_display_names[col] for col in raw_df.columns],
        default=[column_display_names[col] for col in default_columns],
    )
    display_to_internal = {v: k for k, v in column_display_names.items()}
    selected_columns = [display_to_internal.get(name, name) for name in selected_display]

    with st.expander("Ajuda de filtros", expanded=False):
        st.markdown(
            """
* Sintaxe basica: `svp, !ste, mel4`
* Use `OU` ou `OR` para alternativas (`svp OU mel4`)
* Prefixos uteis: `^` inicio, `$` final, `=` igual, `~` regex
* `!` inverte um termo (`!^adm`, `!mel4`)
* Virgulas equivalem a E/AND; espacos tambem separam termos
            """
        )


filtered_df = apply_cli_filters(raw_df, search_terms)
if situacao_sel:
    filtered_df = filtered_df[filtered_df['situacao'].isin(situacao_sel)]
if executor_sel:
    filtered_df = filtered_df[filtered_df['setor_executor'].isin(executor_sel)]
if emissor_sel:
    filtered_df = filtered_df[filtered_df['setor_emissor'].isin(emissor_sel)]

filtered_df = filtered_df.reset_index(drop=True)
if limit_rows and len(filtered_df) > limit_rows:
    filtered_df = filtered_df.head(limit_rows)

active_summary: list[str] = []
if search_terms.strip():
    active_summary.append(f"Busca: {search_terms.strip()}")
if situacao_sel and situacoes and len(situacao_sel) != len(situacoes):
    active_summary.append("Situacao: " + ", ".join(situacao_sel))
if executor_sel and executores and len(executor_sel) != len(executores):
    active_summary.append("Executor: " + ", ".join(executor_sel))
if emissor_sel and emissores and len(emissor_sel) != len(emissores):
    active_summary.append("Emissor: " + ", ".join(emissor_sel))
if consult_api:
    active_summary.append("API: ativada")

if active_summary:
    st.markdown("**Filtros ativos:** " + " | ".join(active_summary))

# Indicadores rápidos
metric_cols = st.columns(3)
metric_cols[0].metric("Total de SSAs", len(filtered_df))
if 'situacao' in filtered_df.columns:
    status_counts = filtered_df['situacao'].value_counts()
    metric_cols[1].metric("Executadas", int(status_counts.get('EXECUTADA', 0)))
    metric_cols[2].metric("Pendentes", int(status_counts.get('ABERTA', 0)))
else:
    metric_cols[1].metric("Executadas", "-")
    metric_cols[2].metric("Pendentes", "-")

# Consulta opcional da API para dados mais recentes (não bloqueia fluxo offline)
recent_df: pd.DataFrame | None = None
if consult_api:
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
    except Exception:
            st.warning(
                "Não foi possível acessar dados mais recentes via API. O dashboard continua com o banco local."
            )

st.subheader(f"Total de registros exibidos: {len(filtered_df)}")
view_df = filtered_df[selected_columns] if selected_columns else filtered_df
rename_map = {col: DISPLAY_MAPPINGS.get(col, col) for col in view_df.columns}
display_df = ensure_arrow_compatible(view_df.rename(columns=rename_map))
column_config = {
    rename_map.get(col, col): st.column_config.TextColumn(width="small")
    for col in view_df.columns
    if col in {"situacao", "setor_executor", "setor_emissor"}
}
st.dataframe(
    display_df,
    width='stretch',
    height=600,
    column_config=column_config,
)

st.download_button(
    "Baixar CSV",
    view_df.to_csv(index=False).encode("utf-8"),
    file_name="ssas_filtradas.csv",
    mime="text/csv",
)

# Gráfico simples de situações
if 'situacao' in filtered_df.columns and not filtered_df.empty:
    chart_df = (
        filtered_df['situacao']
        .value_counts()
        .rename_axis('Situação')
        .reset_index(name='Quantidade')
    )
    st.subheader("Distribuição por Situação")
    st.bar_chart(chart_df.set_index('Situação'))

if recent_df is not None and not recent_df.empty:
    st.markdown("### Dados recentes via API (campos limitados)")
    st.dataframe(ensure_arrow_compatible(recent_df), width='stretch', height=220)
