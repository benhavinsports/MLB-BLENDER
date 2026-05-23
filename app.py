
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
    with st.spinner(f"Running complete Blender engine on {source_label}..."):
        results = run_true_blender(df)
    st.session_state.results = safe_results(results)
    locked = len(st.session_state.results.get("owners", pd.DataFrame()))
    st.session_state.machine_state = "OWNERS LOCKED" if locked else "AUDIT ONLY"
    return st.session_state.results

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state:
    st.session_state.results = safe_results(load_locked_results())
if "machine_state" not in st.session_state:
    st.session_state.machine_state = "READY"
if "last_uploaded_name" not in st.session_state:
    st.session_state.last_uploaded_name = ""
if "public_context" not in st.session_state:
    st.session_state.public_context = pd.DataFrame()
if "last_error" not in st.session_state:
    st.session_state.last_error = ""

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    res = safe_results(st.session_state.results)
    owner_names = []
    if not res.get("owners", pd.DataFrame()).empty and "player" in res["owners"].columns:
        owner_names = res["owners"]["player"].head(6).astype(str).tolist()

    blender_machine(owner_names, st.session_state.machine_state)

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        label_visibility="visible",
        key="complete_real_feed_uploader"
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

    if st.session_state.feed_df is not None and not st.session_state.feed_df.empty:
        df = st.session_state.feed_df
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        game_count = df["game_key"].nunique() if "game_key" in df else (df["game"].nunique() if "game" in df else 0)
        c2.metric("Games", game_count)
        c3.metric("Teams", df["team"].nunique() if "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)

        if st.button("RUN BLENDER NOW", key="run_blender_now_complete_real", use_container_width=True):
            try:
                results = run_and_store(st.session_state.feed_df, "uploaded feed")
                msg = results.get("meta", {}).get("message", "Blender complete.")
                if len(results.get("owners", pd.DataFrame())):
                    st.success(msg)
                else:
                    st.warning(msg)
                st.rerun()
            except Exception as e:
                st.session_state.machine_state = "ERROR"
                st.session_state.last_error = traceback.format_exc()
                st.error(f"Run failed safely: {e}")
                st.code(st.session_state.last_error)

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_complete", use_container_width=True):
            try:
                ctx, meta = fetch_live_public_slate()
                st.session_state.public_context = ctx
                if meta.get("error"):
                    st.warning(f"Live public slate unavailable; upload feed still works: {meta.get('error')}")
                else:
                    st.success(f"Live public slate loaded: {meta.get('games', 0)} games")
            except Exception as e:
                st.warning(f"Live public slate unavailable; upload feed still works: {e}")

    with col_b:
        if st.button("RUN LIVE PUBLIC BLENDER", key="run_live_public_blender_complete", use_container_width=True):
            try:
                pool, meta = fetch_live_public_hitter_pool()
                st.session_state.feed_df = pool
                results = run_and_store(pool, "live public hitter pool")
                st.success(results.get("meta", {}).get("message", "Live Blender complete."))
                st.rerun()
            except Exception as e:
                st.session_state.last_error = traceback.format_exc()
                st.warning(f"Live public Blender could not run safely: {e}")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recalibrate_model_weights_complete", use_container_width=True):
        try:
            weights = recalc_adaptive_weights_from_history()
            st.success(f"Adaptive model weights recalibrated: {weights}")
        except Exception as e:
            st.warning(f"Recalibration skipped safely: {e}")

    res = safe_results(st.session_state.results)
    if res.get("meta"):
        meta = res.get("meta", {})
        if meta.get("owners_locked", 0) > 0:
            st.success(meta.get("message", "Blender complete."))
            tickets_view(res, key_prefix='main_tickets_complete')
        elif meta.get("input_rows", 0) > 0:
            st.warning(meta.get("message", "Blender ran but did not lock owners."))


    # SMART AI OIL STATUS PANEL
    res_ai = safe_results(st.session_state.results)
    meta_ai = res_ai.get("meta", {}) if isinstance(res_ai, dict) else {}
    if meta_ai.get("ai_oil_enabled"):
        st.markdown("### 🧠 SMART AI OIL LAYER")
        c_ai1, c_ai2, c_ai3 = st.columns(3)
        c_ai1.metric("AI Feed Status", meta_ai.get("ai_feed_status", "—"))
        c_ai2.metric("AI Feed Score", meta_ai.get("ai_feed_score", "—"))
        c_ai3.metric("AI Calibration", meta_ai.get("ai_calibration_status", "—"))
        with st.expander("AI Blender Explanation / Audit"):
            st.write(meta_ai.get("ai_validation_summary", ""))
            st.text(meta_ai.get("ai_explanation", ""))


    recap_view(res)

    if st.session_state.last_error:
        with st.expander("Last error details"):
            st.code(st.session_state.last_error)

with tabs[1]:
    res = safe_results(st.session_state.results)
    if res.get("core", pd.DataFrame()).empty and res.get("owners", pd.DataFrame()).empty:
        st.info("Run the Blender first.")
    else:
        tickets_view(res, key_prefix='tickets_tab_complete')

with tabs[2]:
    res = safe_results(st.session_state.results)
    game_board_view(res)
