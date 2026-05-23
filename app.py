
import streamlit as st
import pandas as pd
from feeder import read_feed
from engine import run_true_blender, run_recap_check, csv_bytes, load_locked_results, fetch_live_public_slate, merge_public_context, fetch_live_public_hitter_pool, rebuild_live_blender_feed, recalc_adaptive_weights_from_history
from ui import inject_css, hero, blender_machine, tickets_view, game_board_view, recap_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
hero()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state:
    st.session_state.results = load_locked_results()
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
    owner_names = []
    if st.session_state.results.get("owners") is not None and not st.session_state.results.get("owners").empty:
        owner_names = st.session_state.results["owners"]["player"].head(6).tolist()

    blender_machine(owner_names, st.session_state.machine_state)

    if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_v75", use_container_width=True):
        try:
            ctx, meta = fetch_live_public_slate()
            st.session_state.public_context = ctx
            if meta.get("error"):
                st.warning(f"Live public slate unavailable, upload feed still works: {meta.get('error')}")
            else:
                st.success(f"Live public slate loaded: {meta.get('games', 0)} games")
        except Exception as e:
            st.session_state.public_context = pd.DataFrame()
            st.warning(f"Live public slate unavailable, upload feed still works: {e}")

    if st.button("RUN LIVE PUBLIC BLENDER", key="run_live_public_blender_v78", use_container_width=True):
        try:
            pool, meta = fetch_live_public_hitter_pool()
            st.session_state.feed_df = pool
            st.session_state.machine_state = "BLENDING LIVE"
            st.info("Live pull loaded. Blender spinner engaged: AI Oil → 19 gates → owner isolation.")
            with st.spinner("BLENDER SPINNING LIVE PUBLIC POOL..."):
                results = run_true_blender(pool)
            st.session_state.results = results
            st.session_state.machine_state = "OWNERS LOCKED"
            st.warning(results.get("meta", {}).get("message", "No clean owners survived.")) if len(results.get("owners", [])) == 0 else st.success(f"Live public Blender finished: {len(results.get('owners', []))} locked owners · metrics matched: {meta.get('metric_rows', 0)}")
            st.rerun()
        except Exception as e:
            import traceback
            st.session_state.last_error = traceback.format_exc()
            st.warning(f"Live public Blender could not run safely: {e}")

    if st.button("RECALIBRATE MODEL WEIGHTS", key="recalibrate_model_weights_v80", use_container_width=True):
        try:
            weights = recalc_adaptive_weights_from_history()
            st.success(f"Adaptive model weights recalibrated: {weights}")
        except Exception as e:
            st.warning(f"Recalibration skipped safely: {e}")

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        label_visibility="visible",
        key="one_real_feed_uploader_v66"
    )

    if uploaded is not None:
        upload_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.last_uploaded_name != upload_key:
            st.session_state.last_uploaded_name = upload_key
            st.session_state.machine_state = "READING FEED"

            # UPLOAD_SAFE_V76
            try:
                df, audit = read_feed(uploaded.name, uploaded.read())
                df = merge_public_context(df, st.session_state.get("public_context", pd.DataFrame()))
                st.session_state.feed_df = df

                st.session_state.machine_state = "BLENDING UPLOAD"
                st.info("Blender spinner engaged: AI Oil → 19 gates → one owner per game.")
                with st.spinner("BLENDER SPINNING UPLOADED FEED..."):
                    results = run_true_blender(df)
                st.session_state.results = results
                st.session_state.machine_state = "OWNERS LOCKED"

                st.rerun()
            except Exception as e:
                import traceback
                st.session_state.machine_state = "READY"
                st.session_state.last_error = traceback.format_exc()
                st.error(f"Feed failed safely. No crash: {e}")
                with st.expander("Error details"):
                    st.code(st.session_state.last_error)

    if st.session_state.feed_df is not None and not st.session_state.feed_df.empty:
        df = st.session_state.feed_df
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game_key"].nunique() if "game_key" in df else (df["game"].nunique() if "game" in df else 0))
        c3.metric("Teams", df["team"].nunique() if "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)

        if st.button("RUN BLENDER NOW", key="manual_run_blender_restored_v99", use_container_width=True):
            try:
                st.session_state.machine_state = "BLENDING MANUAL"
                with st.spinner("BLENDER SPINNING CURRENT FEED..."):
                    results = run_true_blender(st.session_state.feed_df)
                st.session_state.results = results
                st.session_state.machine_state = "OWNERS LOCKED"
                st.success(results.get("meta", {}).get("message", "Blender complete."))
                st.rerun()
            except Exception as e:
                import traceback
                st.session_state.machine_state = "ERROR"
                st.session_state.last_error = traceback.format_exc()
                st.error(f"Manual run failed: {e}")
                with st.expander("Error details"):
                    st.code(st.session_state.last_error)

    if st.session_state.results and st.session_state.results.get("core") is not None and not st.session_state.results.get("core").empty:
        st.markdown("---")
        tickets_view(st.session_state.results, key_prefix='main_tickets_v65')

    recap_view(st.session_state.results)

with tabs[1]:
    if st.session_state.results and st.session_state.results.get("core") is not None and not st.session_state.results.get("core").empty:
        tickets_view(st.session_state.results, key_prefix='tickets_tab_restored_v99')
    else:
        st.info("Run the Blender first.")

with tabs[2]:
    game_board_view(st.session_state.results)


# RESULT_STATUS_V82
try:
    _res = st.session_state.get("results", {})
    if isinstance(_res, dict) and _res.get("meta"):
        _m = _res.get("meta", {})
        if _m.get("owners_locked", 0) == 0 and _m.get("input_rows", 0) > 0:
            st.warning(_m.get("message", "Blender ran but no clean owners survived."))
        elif _m.get("owners_locked", 0) > 0:
            st.success(_m.get("message", "Blender complete."))
except Exception:
    pass

try:
    if st.session_state.get("last_error"):
        with st.expander("Last app error details"):
            st.code(st.session_state.last_error)
except Exception:
    pass
