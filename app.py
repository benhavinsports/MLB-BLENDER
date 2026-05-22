
import streamlit as st
import pandas as pd
from feeder import read_feed
from engine import run_true_blender, run_recap_check, csv_bytes, load_locked_results
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

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    owner_names = []
    if st.session_state.results.get("owners") is not None and not st.session_state.results.get("owners").empty:
        owner_names = st.session_state.results["owners"]["player"].head(6).tolist()

    blender_machine(owner_names, st.session_state.machine_state)

    st.markdown("<div class='machine-stage'>TAP THE BOX BELOW TO FEED DATA INTO THE BLENDER</div>", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        label_visibility="visible",
        key="true_machine_feed"
    )

    if uploaded is not None:
        upload_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.last_uploaded_name != upload_key:
            st.session_state.last_uploaded_name = upload_key
            st.session_state.machine_state = "READING FEED"

            df, audit = read_feed(uploaded.name, uploaded.read())
            st.session_state.feed_df = df

            st.session_state.machine_state = "RUNNING GATES"
            results = run_true_blender(df)
            st.session_state.results = results
            st.session_state.machine_state = "OWNERS LOCKED"

            st.rerun()

    if st.session_state.feed_df is not None and not st.session_state.feed_df.empty:
        df = st.session_state.feed_df
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game"].nunique() if "game" in df else 0)
        c3.metric("Teams", df["team"].nunique() if "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if "pitcher" in df else 0)

    if st.session_state.results and st.session_state.results.get("core") is not None and not st.session_state.results.get("core").empty:
        st.markdown("---")
        tickets_view(st.session_state.results, key_prefix='main_tickets')

    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results, key_prefix='tab_tickets')

with tabs[2]:
    game_board_view(st.session_state.results)
