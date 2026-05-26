import traceback
import pandas as pd
import streamlit as st
from feeder import read_feed, actual_game_count, attack_pool_count
from engine import run_true_blender, load_locked_results, fetch_live_public_slate, attach_slate_matchup_context
from ui import inject_css, hero, blender_visual, tickets_view, game_board_grid_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css(); hero()

if "feed_df" not in st.session_state: st.session_state.feed_df = pd.DataFrame()
if "official_slate" not in st.session_state: st.session_state.official_slate = pd.DataFrame()
if "official_meta" not in st.session_state: st.session_state.official_meta = {}
if "results" not in st.session_state: st.session_state.results = load_locked_results()
if "last_audit" not in st.session_state: st.session_state.last_audit = {}
if "last_error" not in st.session_state: st.session_state.last_error = ""

@st.cache_data(show_spinner=False, ttl=3600)
def cached_read_feed(filename: str, raw: bytes):
    return read_feed(filename, raw)

def attach_official(df):
    # SPEED RULE: never auto-fetch live slate during upload/run.
    # Only attach official context if user explicitly pressed LOAD OFFICIAL MLB SLATE.
    if df is None or df.empty:
        return df
    slate = st.session_state.get("official_slate", pd.DataFrame())
    if slate is None or slate.empty:
        return df
    return attach_slate_matchup_context(df, slate)

def read_uploaded(uploaded):
    if uploaded is None: return False
    try:
        raw = uploaded.getvalue()
        cache_key = (uploaded.name, len(raw))
        if st.session_state.get("last_upload_key") == cache_key and not st.session_state.feed_df.empty:
            return True
        with st.spinner("Reading uploaded feed..."):
            df, audit = cached_read_feed(uploaded.name, raw)
            st.session_state.last_audit = audit
            df = attach_official(df)
            st.session_state.feed_df = df if isinstance(df,pd.DataFrame) else pd.DataFrame()
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
            st.warning("No usable feed rows loaded yet."); return
        # Do not refetch or reparse anything here. Run only on the already-loaded feed.
        df = attach_official(df)
        st.session_state.feed_df = df
        with st.spinner("Blender is spinning..."):
            st.session_state.results = run_true_blender(df)
        st.success(st.session_state.results.get("meta",{}).get("message","Blender complete."))
    except Exception:
        st.session_state.last_error = traceback.format_exc()
        st.error("Blender runtime error. Open Last error details.")

tabs = st.tabs(["🔥 Blender Visual", "🎟️ Tickets", "🧩 Game Board"])
with tabs[0]:
    blender_visual()
    uploaded = st.file_uploader("FEED DATA HERE", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed")
    if uploaded is not None:
        ok = read_uploaded(uploaded)
        if ok: st.success(f"Feed loaded: {len(st.session_state.feed_df)} rows. Click RUN BLENDER NOW.")
        else: st.error("Feed read 0 usable rows. Check Feeder Audit.")

    if st.button("RUN BLENDER NOW", use_container_width=True): run_blender()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("LOAD OFFICIAL MLB SLATE", use_container_width=True):
            try:
                slate, meta = fetch_live_public_slate()
                st.session_state.official_slate = slate; st.session_state.official_meta = meta
                st.success(f"Official MLB slate loaded: {meta.get('games',0)} games.")
            except Exception:
                st.session_state.last_error = traceback.format_exc(); st.error("Official MLB slate pull failed.")
    with col2:
        if st.button("RUN OFFICIAL MLB SLATE BLENDER", use_container_width=True): run_blender()

    st.markdown("## Current Feed")
    df = st.session_state.feed_df
    if df is None or df.empty:
        st.info("No feed loaded.")
    else:
        c=st.columns(5)
        c[0].metric("Players Read", len(df)); c[1].metric("Official Games", int(df["game_pk"].dropna().astype(str).replace("",pd.NA).dropna().nunique()) if "game_pk" in df.columns else actual_game_count(df)); c[2].metric("Attack Pools", attack_pool_count(df)); c[3].metric("Teams", df["team"].nunique() if "team" in df else 0); c[4].metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)
        metric_rows = int((df.get("metric_count", pd.Series(dtype=float)).fillna(0) > 0).sum()) if "metric_count" in df else 0
        official_matches = int(df.get("official_slate_attached", pd.Series(dtype=bool)).fillna(False).sum()) if "official_slate_attached" in df else 0
        st.success(f"Parser Health: {metric_rows}/{len(df)} usable metric rows · Official matched {official_matches}/{len(df)} rows.")
        with st.expander("Parsed Feed Preview", expanded=False):
            cols=[c for c in ["player","team","opponent","pitcher","game_key","game_time_et","slate_window","pull_pct","hard_hit_pct","barrel_pct","dmg","hpi","hr_lane","pitch_edge","metric_count"] if c in df.columns]
            st.dataframe(df[cols].head(100), use_container_width=True, hide_index=True)
    with st.expander("Feeder Audit", expanded=False): st.json(st.session_state.last_audit)
    if st.session_state.last_error:
        with st.expander("Last error details", expanded=False): st.code(st.session_state.last_error)

with tabs[1]: tickets_view(st.session_state.results)
with tabs[2]: game_board_grid_view(st.session_state.results)
