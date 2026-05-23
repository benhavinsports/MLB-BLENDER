
import streamlit as st
import pandas as pd
import traceback

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

def empty_results():
    return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame(), "meta":{}}

def safe_results(obj):
    if isinstance(obj, dict):
        for k in ["owners","core","alt","chaos","survivors"]:
            if k not in obj or obj[k] is None:
                obj[k] = pd.DataFrame()
        if "meta" not in obj or obj["meta"] is None:
            obj["meta"] = {}
        return obj
    return empty_results()

def run_and_store(df, source_label="uploaded feed"):
    st.session_state.machine_state = "RUNNING 19 GATES"
    with st.spinner(f"Running v90 AI Oil Blender on {source_label}..."):
        results = run_true_blender(df)
    st.session_state.results = safe_results(results)
    locked = len(st.session_state.results.get("owners", pd.DataFrame()))
    st.session_state.machine_state = "OWNERS LOCKED" if locked else "AUDIT ONLY"
    return st.session_state.results

for k,v in {
    "feed_df": pd.DataFrame(),
    "results": safe_results(load_locked_results()),
    "machine_state": "READY",
    "last_uploaded_name": "",
    "public_context": pd.DataFrame(),
    "last_error": "",
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    res = safe_results(st.session_state.results)
    owner_names = res["owners"]["player"].head(6).astype(str).tolist() if not res["owners"].empty and "player" in res["owners"] else []
    blender_machine(owner_names, st.session_state.machine_state)

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        key="v90_real_feed_uploader"
    )

    if uploaded is not None:
        try:
            upload_key = f"{uploaded.name}:{uploaded.size}"
            raw = uploaded.getvalue()
            df, audit = read_feed(uploaded.name, raw)
            df = merge_public_context(df, st.session_state.get("public_context", pd.DataFrame()))
            st.session_state.feed_df = df
            st.session_state.last_uploaded_name = upload_key
            st.session_state.machine_state = "FEED LOADED"
            st.success(f"Feed loaded: {len(df)} rows. Click RUN BLENDER NOW.")
        except Exception as e:
            st.session_state.machine_state = "READY"
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Feed failed safely: {e}")

    if st.button("RUN BLENDER NOW", key="run_blender_now_v90", use_container_width=True):
        try:
            results = run_and_store(st.session_state.feed_df, "uploaded feed")
            msg = results.get("meta", {}).get("message", "Blender complete.")
            if len(results.get("owners", pd.DataFrame())):
                st.success(msg)
            else:
                st.warning(msg)
        except Exception as e:
            st.session_state.machine_state = "ERROR"
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Run failed safely: {e}")
            st.code(st.session_state.last_error)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_v90", use_container_width=True):
            try:
                ctx, meta = fetch_live_public_slate()
                st.session_state.public_context = ctx
                if meta.get("error"):
                    st.warning(f"Live public slate unavailable: {meta.get('error')}")
                else:
                    st.success(f"Live public slate loaded: {meta.get('games', 0)} games")
            except Exception as e:
                st.warning(f"Live slate failed safely: {e}")

    with col_b:
        if st.button("RUN LIVE PUBLIC BLENDER", key="run_live_public_blender_v90", use_container_width=True):
            try:
                pool, meta = fetch_live_public_hitter_pool()
                st.session_state.feed_df = pool
                st.info(f"Live pool rows: {len(pool)} · metrics matched: {meta.get('metric_rows',0)}")
                results = run_and_store(pool, "live public pool")
                st.success(results.get("meta", {}).get("message", "Live Blender complete."))
            except Exception as e:
                st.warning(f"Live public Blender failed safely: {e}")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recalibrate_v90", use_container_width=True):
        try:
            weights = recalc_adaptive_weights_from_history()
            st.success(f"Adaptive weights recalibrated: {weights}")
        except Exception as e:
            st.warning(f"Recalibration skipped safely: {e}")

    st.markdown("### Current Feed")
    df = st.session_state.feed_df
    if df is not None and not df.empty:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game_key"].nunique() if "game_key" in df else (df["game"].nunique() if "game" in df else 0))
        c3.metric("Teams", df["team"].nunique() if "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)
    else:
        st.info("No feed loaded yet.")

    meta = safe_results(st.session_state.results).get("meta", {})
    if meta:
        st.info(meta.get("message","Ready"))

    st.markdown("---")
    tickets_view(st.session_state.results, key_prefix="main_v90")
    st.markdown("---")
    game_board_view(st.session_state.results)
    st.markdown("---")
    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results, key_prefix="tickets_v90")

with tabs[2]:
    game_board_view(st.session_state.results)
