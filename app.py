import traceback
import hashlib
import pandas as pd
import streamlit as st

from feeder import read_feed, actual_game_count, attack_pool_count
from engine import (
    run_true_blender,
    load_locked_results,
    fetch_live_public_slate,
    attach_slate_matchup_context,
)
import ui

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

ui.inject_css()
ui.hero()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "official_slate" not in st.session_state:
    st.session_state.official_slate = pd.DataFrame()
if "official_meta" not in st.session_state:
    st.session_state.official_meta = {}
if "results" not in st.session_state:
    st.session_state.results = load_locked_results()
if "last_audit" not in st.session_state:
    st.session_state.last_audit = {}
if "last_error" not in st.session_state:
    st.session_state.last_error = ""

@st.cache_data(show_spinner=False, ttl=3600)
def cached_read_feed(filename: str, raw: bytes):
    return read_feed(filename, raw)

def attach_official(df):
    if df is None or df.empty:
        return df
    slate = st.session_state.get("official_slate", pd.DataFrame())
    if slate is None or slate.empty:
        return df
    return attach_slate_matchup_context(df, slate)

def read_uploaded(uploaded):
    if uploaded is None:
        return False
    try:
        raw = uploaded.getvalue()
        cache_key = (uploaded.name, hashlib.md5(raw).hexdigest())
        if st.session_state.get("last_upload_key") == cache_key and not st.session_state.feed_df.empty:
            return True
        with st.spinner("Reading uploaded feed..."):
            df, audit = cached_read_feed(uploaded.name, raw)
            st.session_state.last_audit = audit
            df = attach_official(df)
            st.session_state.feed_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
            st.session_state.last_upload_key = cache_key
        return not st.session_state.feed_df.empty
    except Exception:
        st.session_state.last_error = traceback.format_exc()
        st.session_state.feed_df = pd.DataFrame()
        return False

def run_blender():
    try:
        df = st.session_state.feed_df.copy()
        if df.empty:
            st.warning("No usable feed rows loaded yet.")
            return
        df = attach_official(df)
        st.session_state.feed_df = df
        with st.spinner("Blender is spinning..."):
            st.session_state.results = run_true_blender(df)
        st.success(st.session_state.results.get("meta", {}).get("message", "Blender complete."))
    except Exception:
        st.session_state.last_error = traceback.format_exc()
        st.error("Blender runtime error. Open Last error details.")

# SINGLE PAGE ONLY
uploaded = ui.start_upload_area()
if uploaded is not None:
    ok = read_uploaded(uploaded)
    if ok:
        st.success(f"Feed loaded: {len(st.session_state.feed_df)} rows. Click RUN BLENDER NOW.")
    else:
        st.error("Feed read 0 usable rows. Check Feeder Audit.")

ui.render_public_gameboard(st.session_state.results)

run_col, slate_col = st.columns(2)
with run_col:
    if st.button("RUN BLENDER NOW", use_container_width=True, type="primary", key="run_blender_now_main"):
        run_blender()
with slate_col:
    if st.button("LOAD LIVE PUBLIC MLB SLATE", use_container_width=True, key="load_live_slate_main"):
        try:
            slate, meta = fetch_live_public_slate()
            st.session_state.official_slate = slate
            st.session_state.official_meta = meta
            st.success(f"Official MLB slate loaded: {meta.get('games', 0)} games.")
        except Exception:
            st.session_state.last_error = traceback.format_exc()
            st.error("Official MLB slate pull failed.")

ui.render_selected_game_details(st.session_state.results)

with st.expander("Current Feed / Parser Audit", expanded=False):
    df = st.session_state.feed_df
    if df is None or df.empty:
        st.info("No feed loaded.")
    else:
        c = st.columns(5)
        c[0].metric("Players Read", len(df))
        c[1].metric("Games", int(df["game_pk"].dropna().astype(str).replace("", pd.NA).dropna().nunique()) if "game_pk" in df.columns else actual_game_count(df))
        c[2].metric("Attack Pools", attack_pool_count(df))
        c[3].metric("Teams", df["team"].nunique() if "team" in df else 0)
        c[4].metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)
        cols = [c for c in ["player","team","opponent","pitcher","game_key","binding_status","original_game_key","original_team","game_time_et","slate_window","pull_pct","hard_hit_pct","barrel_pct","dmg","hpi","hr_lane","pitch_edge","metric_count"] if c in df.columns]
        st.dataframe(df[cols].head(100), use_container_width=True, hide_index=True)
    st.json(st.session_state.last_audit)
    if st.session_state.last_error:
        st.code(st.session_state.last_error)
