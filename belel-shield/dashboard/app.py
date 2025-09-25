import os, json, time
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px
from pathlib import Path

from utils import (
    load_alerts, normalize_alerts, load_blocklist_status,
    firewall_present, process_running, geoip_lookup, GEOLITE_DB
)

st.set_page_config(page_title="Belel Shield Dashboard", page_icon="🛡️", layout="wide")
with open(Path(__file__).with_name("styles.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🛡️ Belel Shield — Live Defense Dashboard")

# Sidebar controls
st.sidebar.header("Controls")
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_sec = st.sidebar.slider("Refresh interval (sec)", 2, 30, 5)
use_geoip = st.sidebar.checkbox("Use local GeoIP (GeoLite2-City.mmdb in ~/.belel)", value=True)
external_ip_lookup = st.sidebar.checkbox("Allow external IP lookups (NOT recommended)", value=False, help="Disabled by default for privacy.")
min_conf = st.sidebar.slider("Min points for heatmap", 1, 100, 5)

# System status
colA, colB, colC, colD = st.columns(4)
with colA:
    running = process_running()
    st.metric("Scanner Running", "Yes" if running else "No")
with colB:
    fw = firewall_present()
    st.metric("Firewall Detected", "Yes" if fw else "No")
with colC:
    bl = load_blocklist_status()
    ok = bl["checksum_ok"]
    if bl["present"] is False:
        st.metric("Blocklist Cache", "Missing")
    elif ok is None:
        st.metric("Blocklist Cache", "Unverified")
    else:
        st.metric("Blocklist Checksum", "OK" if ok else "MISMATCH")
with colD:
    st.metric("Auto-refresh", f"{refresh_sec}s" if auto_refresh else "Off")

st.markdown("---")

# Load alerts
rows = normalize_alerts(load_alerts())
df = pd.DataFrame(rows)
if not df.empty:
    df = df.sort_values("dt")
st.subheader("Recent Alerts")
st.caption("Local events only; never transmitted.")

if df.empty:
    st.info("No alerts yet. Keep the scanner running to populate events.")
else:
    # Basic stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Alerts", len(df))
    with c2:
        st.metric("Unique IPs", df["ip"].nunique())
    with c3:
        st.metric("Unique Hosts", df["host"].fillna("unknown").nunique())

    # Timeline
    timeline = df.groupby(pd.Grouper(key="dt", freq="5min"))["ip"].count().reset_index()
    timeline.columns = ["time","alerts"]
    fig = px.area(timeline, x="time", y="alerts", title="Alert Volume (5-min bins)")
    st.plotly_chart(fig, use_container_width=True)

    # Optional GeoIP
    geos = []
    reader = None
    if use_geoip and GEOLITE_DB.exists():
        try:
            import geoip2.database
            reader = geoip2.database.Reader(str(GEOLITE_DB))
        except Exception as e:
            st.warning(f"GeoIP reader unavailable: {e}")

    for _, r in df.iterrows():
        g = geoip_lookup(r["ip"], reader) if reader else None
        if g and g.get("lat") and g.get("lon"):
            geos.append({
                "lat": g["lat"], "lon": g["lon"], "ip": r["ip"],
                "host": r["host"] or "unknown",
                "city": g.get("city") or "",
                "country": g.get("country") or "",
                "reason": r["reason"] or ""
            })

    # Map
    st.subheader("Global Threat Map")
    if geos:
        gdf = pd.DataFrame(geos)

        heat = pdk.Layer(
            "HeatmapLayer",
            data=gdf,
            get_position=["lon", "lat"],
            aggregation="MEAN",
            get_weight=1,
            radiusPixels=60,
        )
        scatter = pdk.Layer(
            "ScatterplotLayer",
            data=gdf,
            get_position=["lon", "lat"],
            get_radius=40000,
            pickable=True,
            auto_highlight=True,
        )
        tooltip = {"html": "<b>{ip}</b><br/>{host}<br/>{city}, {country}<br/>{reason}", "style": {"color": "white"}}
        view = pdk.ViewState(latitude=20, longitude=0, zoom=1.2)

        st.pydeck_chart(pdk.Deck(map_style="mapbox://styles/mapbox/dark-v10",
                                 initial_view_state=view,
                                 tooltip=tooltip,
                                 layers=[heat, scatter] if len(gdf)>=min_conf else [scatter]))
    else:
        st.info("No geo points (provide ~/.belel/GeoLite2-City.mmdb to enable local GeoIP).")

    st.markdown("---")
    st.subheader("Table & Export")
    st.dataframe(df[["timestamp","ip","port","host","reason"]], use_container_width=True)
    cexp1, cexp2 = st.columns(2)
    csv = df.to_csv(index=False).encode()
    json_bytes = df.to_json(orient="records").encode()
    with cexp1:
        st.download_button("⬇️ Download CSV", csv, file_name="belel_alerts.csv", mime="text/csv")
    with cexp2:
        st.download_button("⬇️ Download JSON", json_bytes, file_name="belel_alerts.json", mime="application/json")

# Footer
st.markdown("---")
st.caption("Belel Shield • local-first • no telemetry")

# Auto refresh
if auto_refresh:
    st.experimental_rerun() if st.session_state.get("_tick") else st.session_state.update({"_tick": True})
    time.sleep(refresh_sec)
