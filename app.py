
import streamlit as st
import pandas as pd
import traceback

from feeder import read_feed
from engine import (
    run_true_blender, load_locked_results, fetch_live_public_slate,
    merge_public_context, fetch_live_public_hitter_pool, recalc_adaptive_weights_from_history
)
from ui import inject_css, hero, blender_machine, tickets_view, game_board_view, recap_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide")
inject_css()
hero()

def empty_results():
    return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":{}}

def ensure_results(x):
    if not isinstance(x, dict):
        return empty_results()
    for k in ["owners","core","alt","chaos","survivors"]:
        if k not in x or x[k] is None:
            x[k] = pd.DataFrame()
    if "meta" not in x or x["meta"] is None:
        x["meta"] = {}
    return x

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state:
    st.session_state.results = ensure_results(load_locked_results())
if "public_context" not in st.session_state:
    st.session_state.public_context = pd.DataFrame()
if "machine_state" not in st.session_state:
    st.session_state.machine_state = "READY"
if "last_error" not in st.session_state:
    st.session_state.last_error = ""

def run_blender_now(df, label):
    if df is None or df.empty:
        st.warning("No feed rows loaded. Upload data or load live pool first.")
        return
    st.session_state.machine_state = "RUNNING"
    with st.spinner(f"Running true Blender on {label}..."):
        res = run_true_blender(df)
    st.session_state.results = ensure_results(res)
    st.session_state.machine_state = "DONE"
    msg = st.session_state.results.get("meta",{}).get("message","Run complete.")
    owners = st.session_state.results.get("owners", pd.DataFrame())
    if owners is not None and not owners.empty:
        st.success(msg)
    else:
        st.warning(msg)

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    owners = st.session_state.results.get("owners", pd.DataFrame())
    names = owners["player"].head(6).tolist() if owners is not None and not owners.empty and "player" in owners.columns else []
    blender_machine(names, st.session_state.machine_state)

    st.markdown("## Feed Data")
    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf","csv","xlsx","png","jpg","jpeg","webp","txt","md"],
        key="v94_feed_uploader"
    )

    if uploaded is not None:
        try:
            with st.spinner("Reading feed..."):
                df, audit = read_feed(uploaded.name, uploaded.getvalue())
                df = merge_public_context(df, st.session_state.public_context)
            st.session_state.feed_df = df
            st.success(f"Feed loaded: {len(df)} rows")
        except Exception as e:
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Feed failed: {e}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("RUN BLENDER NOW", key="v94_run_button", use_container_width=True):
            try:
                run_blender_now(st.session_state.feed_df, "uploaded feed")
            except Exception as e:
                st.session_state.last_error = traceback.format_exc()
                st.error(f"Run failed: {e}")
                st.code(st.session_state.last_error)
    with col2:
        if st.button("LOAD LIVE PUBLIC SLATE", key="v94_live_slate", use_container_width=True):
            ctx, meta = fetch_live_public_slate()
            st.session_state.public_context = ctx
            st.session_state.feed_df = ctx
            st.info(str(meta))
    with col3:
        if st.button("RUN LIVE PUBLIC BLENDER", key="v94_live_blender", use_container_width=True):
            pool, meta = fetch_live_public_hitter_pool()
            st.session_state.feed_df = pool
            st.info(str(meta))
            run_blender_now(pool, "live public pool")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="v94_recalibrate", use_container_width=True):
        st.info(str(recalc_adaptive_weights_from_history()))

    st.markdown("## Current Feed")
    df = st.session_state.feed_df
    if df is not None and not df.empty:
        m = st.columns(4)
        m[0].metric("Rows", len(df))
        m[1].metric("Games", df["game_key"].nunique() if "game_key" in df.columns else (df["game"].nunique() if "game" in df.columns else 0))
        m[2].metric("Teams", df["team"].nunique() if "team" in df.columns else 0)
        m[3].metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df.columns else 0)
        with st.expander("Preview feed rows", expanded=False):
            st.dataframe(df.head(50), use_container_width=True)
    else:
        st.info("No feed loaded.")

    if st.session_state.last_error:
        with st.expander("Last error", expanded=False):
            st.code(st.session_state.last_error)

    st.markdown("---")
    st.markdown("# Output")
    tickets_view(st.session_state.results, "main_v94")
    game_board_view(st.session_state.results)
    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results, "tickets_v94")

with tabs[2]:
    game_board_view(st.session_state.results)
