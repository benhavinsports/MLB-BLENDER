
import streamlit as st
import pandas as pd

from feeder import read_feed
from engine import (
    run_true_blender, run_recap_check, csv_bytes, load_locked_results,
    fetch_live_public_slate, merge_public_context, fetch_live_public_hitter_pool,
    recalc_adaptive_weights_from_history
)
from ui import inject_css, hero, blender_machine, tickets_view, game_board_view, recap_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
hero()

def init_state():
    defaults = {
        "feed_df": pd.DataFrame(),
        "results": load_locked_results(),
        "machine_state": "READY",
        "public_context": pd.DataFrame(),
        "last_uploaded_name": "",
        "last_audit": {},
        "last_action": "Ready"
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def run_and_store(df, label="Blender"):
    if df is None or getattr(df, "empty", True):
        st.warning("No feed data loaded yet.")
        return
    st.session_state.machine_state = "RUNNING GATES"
    st.session_state.last_action = f"{label} running"
    with st.spinner(f"{label} running full 18-gate engine..."):
        results = run_true_blender(df)
    st.session_state.results = results
    st.session_state.machine_state = "OWNERS LOCKED"
    st.session_state.last_action = f"{label} complete"
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    if meta.get("owners_locked", 0) > 0:
        st.success(meta.get("message", "Run complete."))
    else:
        st.warning(meta.get("message", "Run complete: no clean owners survived."))

def render_loaded_metrics():
    df = st.session_state.get("feed_df", pd.DataFrame())
    if df is not None and not df.empty:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game_key"].nunique() if "game_key" in df.columns else (df["game"].nunique() if "game" in df.columns else 0))
        c3.metric("Teams", df["team"].nunique() if "team" in df.columns else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df.columns else 0)

owner_names = []
res = st.session_state.get("results", {})
if isinstance(res, dict) and res.get("owners") is not None and not res.get("owners").empty:
    owner_names = res["owners"]["player"].head(6).tolist()

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    blender_machine(owner_names, st.session_state.machine_state)

    if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_v87", use_container_width=True):
        with st.spinner("Loading live MLB slate..."):
            ctx, meta = fetch_live_public_slate()
        st.session_state.public_context = ctx
        st.session_state.feed_df = ctx
        if meta.get("error"):
            st.warning(f"Live public slate unavailable: {meta.get('error')}")
        else:
            st.success(f"Live public slate loaded: {meta.get('games', 0)} games")
        render_loaded_metrics()

    if st.button("RUN LIVE PUBLIC BLENDER", key="run_live_public_blender_v87", use_container_width=True):
        with st.spinner("Building live public hitter pool..."):
            pool, meta = fetch_live_public_hitter_pool()
        st.session_state.feed_df = pool
        st.info(f"Live pool rows: {0 if pool is None else len(pool)} · metrics matched: {meta.get('metric_rows', 0)}")
        run_and_store(pool, "Live public Blender")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recalibrate_model_weights_v87", use_container_width=True):
        try:
            weights = recalc_adaptive_weights_from_history()
            st.success(f"Adaptive model weights recalibrated: {weights}")
        except Exception as e:
            st.warning(f"Recalibration skipped safely: {e}")

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        key="one_real_feed_uploader_v87"
    )

    if uploaded is not None:
        upload_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.last_uploaded_name != upload_key:
            st.session_state.last_uploaded_name = upload_key
            st.session_state.machine_state = "READING FEED"
            try:
                with st.spinner("Reading feed..."):
                    df, audit = read_feed(uploaded.name, uploaded.read())
                    df = merge_public_context(df, st.session_state.get("public_context", pd.DataFrame()))
                st.session_state.feed_df = df
                st.session_state.last_audit = audit
                st.success(f"Feed loaded: {len(df)} rows")
                run_and_store(df, "Uploaded feed Blender")
            except Exception as e:
                st.session_state.machine_state = "READY"
                st.error(f"Feed failed safely. No crash: {e}")

    if st.button("RUN BLENDER NOW", key="run_loaded_feed_v87", use_container_width=True):
        run_and_store(st.session_state.feed_df, "Loaded feed Blender")

    st.markdown("### Current Feed")
    render_loaded_metrics()

    if st.session_state.get("last_audit"):
        with st.expander("Feeder Audit", expanded=False):
            st.json(st.session_state.last_audit)

    st.markdown("---")
    tickets_view(st.session_state.results, key_prefix="main_tickets_v87")
    st.markdown("---")
    game_board_view(st.session_state.results)
    st.markdown("---")
    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results, key_prefix="tickets_tab_v87")

with tabs[2]:
    game_board_view(st.session_state.results)
