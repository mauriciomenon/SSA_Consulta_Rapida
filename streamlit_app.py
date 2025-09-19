"""
Simple Streamlit frontend for Itaipu SSA queries using utils.remote_itaipu.

Run locally:
  streamlit run streamlit_app.py
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from utils.remote_itaipu import (
    RequestOptions,
    fetch_pending_ssas,
    map_to_dataframe,
)


st.set_page_config(page_title="SSA Consulta Rápida - Streamlit", layout="wide")
st.title("SSA Consulta Rápida - Streamlit")

with st.sidebar:
    st.header("Consulta")
    start = st.text_input("Start Localization", value="A000A000")
    end = st.text_input("End Localization", value="Z999Z999")
    years = st.number_input("Years", min_value=1, max_value=100000, value=100000, step=1)
    timeout = st.number_input("Timeout (s)", min_value=1.0, max_value=120.0, value=30.0, step=1.0)
    verify_ssl = st.checkbox("Verify SSL", value=True)
    run = st.button("Fetch")

if "last_df" not in st.session_state:
    st.session_state["last_df"] = None

col1, col2 = st.columns([3, 2])

if run:
    opts = RequestOptions(timeout=float(timeout), verify_ssl=bool(verify_ssl))
    with st.spinner("Fetching from API..."):
        try:
            items: List[Dict[str, Any]] = fetch_pending_ssas(start=start, end=end, years=int(years), opts=opts)
            df = map_to_dataframe(items)
            st.session_state["last_df"] = df
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
            st.session_state["last_df"] = None

df = st.session_state.get("last_df")
if df is not None and not df.empty:  # type: ignore[truthy-bool]
    with col1:
        st.subheader("Resultados")
        st.dataframe(df, use_container_width=True)
    with col2:
        st.subheader("Download")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar CSV", csv, file_name="ssas.csv", mime="text/csv")
else:
    st.info("Sem dados carregados ainda. Configure os filtros e clique em Fetch.")
