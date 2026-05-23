
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

APP_VERSION = "v96_TODAY_READY"

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
hero()

def empty_results():
    return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame(), "meta":{}}

def safe_results(obj):
    if not isinstance(obj, dict):
        obj = empty_results()
    for k in ["owners","core","alt","chaos","survivors"]:
        if k not in obj or obj[k] is None:
            obj[k] = pd.DataFrame()
        elif not isinstance(obj[k], pd.DataFrame):
            obj[k] = pd.DataFrame(obj[k])
    if "meta" not in obj or obj["meta"] is None:
        obj["meta"] = {}
    return obj

if st.session_state.get("_app_version") != APP_VERSION:
    st.session_state.clear()
    st.session_state["_app_version"] = APP_VERSION

if "feed_df" not in st.session_state: st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state: st.session_state.results = safe_results(load_locked_results())
if "machine_state" not in st.session_state: st.session_state.machine_state = "READY"
if "public_context" not in st.session_state: st.session_state.public_context = pd.DataFrame()
if "last_error" not in st.session_state: st.session_state.last_error = ""
if "last_run_message" not in st.session_state: st.session_state.last_run_message = ""

def commit_results(results):
    results = safe_results(results)
    st.session_state.results = results
    owners = results.get("owners", pd.DataFrame())
    st.session_state.machine_state = "OWNERS LOCKED" if owners is not None and not owners.empty else "AUDIT"
    st.session_state.last_run_message = results.get("meta", {}).get("message", "")
    return results

def run_and_store(df, source_label="feed"):
    if df is None or getattr(df, "empty", True):
        st.warning("No feed data loaded yet.")
        return safe_results(st.session_state.results)
    st.session_state.machine_state = "RUNNING 19 GATES"
    with st.spinner(f"Running true Blender on {source_label}..."):
        results = run_true_blender(df)
    results = commit_results(results)
    msg = results.get("meta", {}).get("message", "Run complete.")
    if not results.get("owners", pd.DataFrame()).empty:
        st.success(msg)
    else:
        st.warning(msg)
    return results

def render_feed_metrics():
    df = st.session_state.feed_df
    if df is not None and not df.empty:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game_key"].nunique() if "game_key" in df.columns else (df["game"].nunique() if "game" in df.columns else 0))
        c3.metric("Teams", df["team"].nunique() if "team" in df.columns else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df.columns else 0)
    else:
        st.info("No feed loaded yet.")

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    res = safe_results(st.session_state.results)
    owners = res.get("owners", pd.DataFrame())
    owner_names = owners["player"].head(6).astype(str).tolist() if owners is not None and not owners.empty and "player" in owners else []
    blender_machine(owner_names, st.session_state.machine_state)

    if st.button("RESET APP STATE / CLEAR OLD CACHE", key="reset_state_v96", use_container_width=True):
        st.session_state.clear()
        st.session_state["_app_version"] = APP_VERSION
        st.success("State cleared. Reload page, then upload feed.")
        st.stop()

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        key="real_feed_uploader_v96"
    )

    if uploaded is not None:
        try:
            with st.spinner("Reading feed..."):
                df, audit = read_feed(uploaded.name, uploaded.getvalue())
                df = merge_public_context(df, st.session_state.get("public_context", pd.DataFrame()))
            st.session_state.feed_df = df
            st.success(f"Feed loaded: {len(df)} rows. Click RUN BLENDER NOW.")
        except Exception as e:
            st.session_state.machine_state = "READY"
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Feed failed safely: {e}")

    if st.button("RUN BLENDER NOW", key="run_blender_now_v96", use_container_width=True):
        try:
            run_and_store(st.session_state.feed_df, "uploaded feed")
        except Exception as e:
            st.session_state.machine_state = "ERROR"
            st.session_state.last_error = traceback.format_exc()
            st.error(f"Run failed safely: {e}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_v96", use_container_width=True):
            try:
                ctx, meta = fetch_live_public_slate()
                st.session_state.public_context = ctx
                st.session_state.feed_df = ctx
                if meta.get("error"):
                    st.warning(f"Live public slate unavailable: {meta.get('error')}")
                else:
                    st.success(f"Live public slate loaded: {meta.get('games', 0)} games")
            except Exception as e:
                st.session_state.last_error = traceback.format_exc()
                st.warning(f"Live slate failed safely: {e}")

    with col_b:
        if st.button("RUN LIVE PUBLIC BLENDER", key="run_live_public_blender_v96", use_container_width=True):
            try:
                pool, meta = fetch_live_public_hitter_pool()
                st.session_state.feed_df = pool
                st.info(f"Live pool rows: {0 if pool is None else len(pool)} · metrics matched: {meta.get('metric_rows', 0)}")
                run_and_store(pool, "live public pool")
            except Exception as e:
                st.session_state.last_error = traceback.format_exc()
                st.warning(f"Live public Blender failed safely: {e}")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recalibrate_v96", use_container_width=True):
        try:
            weights = recalc_adaptive_weights_from_history()
            st.success(f"Adaptive weights recalibrated: {weights}")
        except Exception as e:
            st.warning(f"Recalibration skipped safely: {e}")

    st.markdown("### Current Feed")
    render_feed_metrics()

    if st.session_state.last_run_message:
        st.info(st.session_state.last_run_message)

    if st.session_state.last_error:
        with st.expander("Last Error", expanded=False):
            st.code(st.session_state.last_error)

    st.markdown("---")
    tickets_view(st.session_state.results, key_prefix="main_tickets_v96")
    st.markdown("---")
    game_board_view(st.session_state.results)
    st.markdown("---")
    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results, key_prefix="tickets_tab_v96")

with tabs[2]:
    game_board_view(st.session_state.results)
