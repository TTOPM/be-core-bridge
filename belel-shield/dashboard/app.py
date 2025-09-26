import os, json, time, pathlib
import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Belel Shield Dashboard", layout="wide")

HOME = pathlib.Path.home()
events_path = HOME/".belel"/"sovereign_events.jsonl"
dpi_path = HOME/".belel"/"dpi_events.jsonl"

st.title("🛡️ Belel Shield — Global Monitor")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Sovereign Shield Events")
    rows=[]
    if events_path.exists():
        with open(events_path) as f:
            for line in f:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    st.dataframe(df.tail(200), use_container_width=True)
with col2:
    st.subheader("DPI Events (last 200)")
    rows=[]
    if dpi_path.exists():
        with open(dpi_path) as f:
            for line in f: rows.append(json.loads(line))
    ddf = pd.DataFrame(rows[-200:]) if rows else pd.DataFrame()
    st.dataframe(ddf, use_container_width=True)

st.markdown("---")
st.subheader("Infra Map (OSINT)")
st.caption("Enter Shodan API and host to query. Privacy: calls Shodan API locally.")
key = st.text_input("Shodan API Key", type="password")
host = st.text_input("Lookup IP/Host (e.g., palantir.com)")
if st.button("Query") and key and host:
    os.environ["SHODAN_API"] = key
    from shodan_mapper import query_shodan
    try:
        data=query_shodan(host); st.json(data)
    except Exception as e:
        st.error(str(e))
