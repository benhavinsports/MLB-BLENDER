
import streamlit as st
import pandas as pd
import traceback
from feeder import read_feed
from engine import run_true_blender, load_locked_results, fetch_live_public_slate, merge_public_context, fetch_live_public_hitter_pool, recalc_adaptive_weights_from_history, actual_game_count
from ui import inject_css, hero, blender_visual, tickets_view, game_board_grid_view

APP_VERSION="v109_TODAY_TEST_READY"

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
hero()

def empty_results():
    return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":{}}

def safe_results(x):
    if not isinstance(x, dict): x = empty_results()
    for k in ["owners","core","alt","chaos","survivors"]:
        if k not in x or x[k] is None:
            x[k] = pd.DataFrame()
        elif not isinstance(x[k], pd.DataFrame):
            x[k] = pd.DataFrame(x[k])
    if "meta" not in x or x["meta"] is None:
        x["meta"] = {}
    return x

if st.session_state.get("_app_version") != APP_VERSION:
    st.session_state.clear()
    st.session_state["_app_version"] = APP_VERSION

defaults = {
    "feed_df": pd.DataFrame(),
    "results": safe_results(load_locked_results()),
    "machine_state": "READY",
    "public_context": pd.DataFrame(),
    "last_error": "",
    "last_audit": {},
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def commit(res):
    st.session_state.results = safe_results(res)
    owners = st.session_state.results.get("owners", pd.DataFrame())
    st.session_state.machine_state = "OWNERS LOCKED" if owners is not None and not owners.empty else "AUDIT"
    return st.session_state.results

def run(df, label):
    if df is None or df.empty:
        st.warning("No usable feed rows loaded yet.")
        return
    st.session_state.machine_state = "RUNNING 19 GATES"
    with st.spinner(f"Running true Blender on {label}..."):
        res = run_true_blender(df)
    res = commit(res)
    msg = res.get("meta", {}).get("message", "Run complete.")
    st.success(msg) if not res.get("owners", pd.DataFrame()).empty else st.warning(msg)

tabs = st.tabs(["🔥 Blender Visual", "🎟️ Tickets", "🧩 Game Board"])

with tabs[0]:
    blender_visual(st.session_state.results, st.session_state.feed_df, st.session_state.machine_state)

    if st.button("RESET APP STATE / CLEAR OLD CACHE", key="reset_v109", use_container_width=True):
        st.session_state.clear()
        st.session_state["_app_version"] = APP_VERSION
        st.success("State cleared. Refresh, then upload/run.")
        st.stop()

    st.markdown("## Feed Data")
    uploaded = st.file_uploader("FEED DATA HERE", type=["pdf","csv","xlsx","xls","txt","md"], key="uploader_v109")
    if uploaded is not None:
        try:
            with st.spinner("Reading feed..."):
                df, audit = read_feed(uploaded.name, uploaded.getvalue())
                df = merge_public_context(df, st.session_state.public_context)
            st.session_state.feed_df = df
            st.session_state.last_audit = audit
            if df is None or df.empty:
                st.error(f"Feed read 0 usable rows. Check Feeder Audit.")
            else:
                st.success(f"Feed loaded: {len(df)} rows. Click RUN BLENDER NOW.")
        except Exception as e:
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Feed failed safely: {e}")

    if st.button("RUN BLENDER NOW", key="run_v109", use_container_width=True):
        try:
            run(st.session_state.feed_df, "uploaded feed")
        except Exception as e:
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Run failed safely: {e}")
            st.code(st.session_state.last_error)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("LOAD LIVE PUBLIC SLATE", key="live_slate_v109", use_container_width=True):
            ctx, meta = fetch_live_public_slate()
            st.session_state.public_context = ctx
            st.session_state.feed_df = ctx
            st.info(str(meta))
    with c2:
        if st.button("RUN LIVE PUBLIC BLENDER", key="live_blender_v109", use_container_width=True):
            pool, meta = fetch_live_public_hitter_pool()
            st.session_state.feed_df = pool
            st.info(str(meta))
            run(pool, "live public proxy pool")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recal_v109", use_container_width=True):
        st.info(str(recalc_adaptive_weights_from_history()))

    st.markdown("## Current Feed")
    df = st.session_state.feed_df
    if df is not None and not df.empty:
        c = st.columns(4)
        c[0].metric("Players Read", len(df))
        c[1].metric("Games", actual_game_count(df))
        c[2].metric("Teams", df["team"].nunique() if "team" in df else 0)
        c[3].metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)
        with st.expander("Parsed Feed Preview", expanded=False):
            st.dataframe(df.head(100), use_container_width=True, hide_index=True)
    else:
        st.info("No feed loaded.")

    if st.session_state.last_audit:
        with st.expander("Feeder Audit", expanded=False):
            st.json(st.session_state.last_audit)
    if st.session_state.last_error:
        with st.expander("Last Error", expanded=False):
            st.code(st.session_state.last_error)

with tabs[1]:
    tickets_view(st.session_state.results, "tickets_v109")

with tabs[2]:
    game_board_grid_view(st.session_state.results, "gameboard_v109")
