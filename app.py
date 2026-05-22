import streamlit as st
import pandas as pd
from feeder import read_feed
from engine import (
    run_true_blender, run_recap_check, csv_bytes, load_locked_results,
    fetch_live_public_slate, merge_public_context
)
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
if "last_upload_key" not in st.session_state:
    st.session_state.last_upload_key = ""
if "public_context" not in st.session_state:
    st.session_state.public_context = pd.DataFrame()
if "feed_audit" not in st.session_state:
    st.session_state.feed_audit = []
if "public_meta" not in st.session_state:
    st.session_state.public_meta = {}

with st.container():
    owner_names = []
    owners = st.session_state.results.get("owners") if isinstance(st.session_state.results, dict) else None
    if owners is not None and not owners.empty and "player" in owners:
        owner_names = owners["player"].dropna().astype(str).head(6).tolist()
    elif st.session_state.feed_df is not None and not st.session_state.feed_df.empty and "player" in st.session_state.feed_df:
        owner_names = st.session_state.feed_df["player"].dropna().astype(str).head(6).tolist()

    blender_machine(owner_names, st.session_state.machine_state)

    col_live, col_status = st.columns([1, 2])
    with col_live:
        if st.button("LOAD LIVE PUBLIC SLATE", key="load_live_public_slate_safe", use_container_width=True):
            with st.spinner("Loading public slate context..."):
                ctx, meta = fetch_live_public_slate()
            st.session_state.public_context = ctx
            st.session_state.public_meta = meta
            if meta.get("error"):
                st.warning(f"Public slate unavailable: {meta.get('error')}")
            else:
                st.success(f"Public slate loaded: {meta}")
    with col_status:
        if st.session_state.public_meta:
            st.caption(f"Public context: {st.session_state.public_meta}")

    uploaded_files = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "xls", "png", "jpg", "jpeg", "webp", "txt", "md"],
        accept_multiple_files=True,
        key="true_multi_feed_uploader_v72",
    )

    if uploaded_files:
        upload_key = "|".join([f"{f.name}:{getattr(f, 'size', 0)}" for f in uploaded_files])
        if st.session_state.last_upload_key != upload_key:
            st.session_state.last_upload_key = upload_key
            st.session_state.machine_state = "READING FEED"
            frames = []
            audits = []
            with st.spinner("Reading feed files..."):
                for uploaded in uploaded_files:
                    data = uploaded.read()
                    df_one, audit = read_feed(uploaded.name, data)
                    audits.append({"file": uploaded.name, "audit": audit, "rows": 0 if df_one is None else len(df_one)})
                    if df_one is not None and not df_one.empty:
                        frames.append(df_one)
                df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                df = merge_public_context(df, st.session_state.get("public_context", pd.DataFrame()))
            st.session_state.feed_df = df
            st.session_state.feed_audit = audits
            st.session_state.machine_state = "RUNNING 18 GATES"
            with st.spinner("Running Blender gates..."):
                st.session_state.results = run_true_blender(df)
            st.session_state.machine_state = "OWNERS LOCKED"
            st.rerun()

    df = st.session_state.feed_df
    if df is not None and not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game_key"].nunique() if "game_key" in df else (df["game"].nunique() if "game" in df else 0))
        c3.metric("Teams", df["team"].nunique() if "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)
        with st.expander("Parsed feed preview", expanded=False):
            keep = [c for c in ["game","game_key","team","opponent","pitcher","player","lineup_slot","pull_pct","sweet_spot_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"] if c in df.columns]
            st.dataframe(df[keep].head(200), use_container_width=True, hide_index=True)

    if isinstance(st.session_state.results, dict):
        tickets_view(st.session_state.results, key_prefix='main_tickets_v72')
        recap_view(st.session_state.results)
        game_board_view(st.session_state.results)

    with st.expander("Feed audit / debug", expanded=False):
        st.write(st.session_state.feed_audit)
