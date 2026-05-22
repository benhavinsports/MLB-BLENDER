
import streamlit as st
import pandas as pd
from feeder import read_feed
from engine import run_true_blender, run_recap_check, csv_bytes
from ui import inject_css, hero, blender_machine, tickets_view, game_board_view, recap_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
hero()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state:
    st.session_state.results = {}

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board"])

with tabs[0]:
    owner_names = []
    if st.session_state.results.get("owners") is not None and not st.session_state.results.get("owners").empty:
        owner_names = st.session_state.results["owners"]["player"].head(6).tolist()
    blender_machine(owner_names)

    uploaded = st.file_uploader(
        "CLICK / FEED DATA HERE",
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "md"],
        label_visibility="collapsed"
    )

    if uploaded:
        df, audit = read_feed(uploaded.name, uploaded.read())
        st.session_state.feed_df = df

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Players Read", len(df))
        c2.metric("Games", df["game"].nunique() if not df.empty and "game" in df else 0)
        c3.metric("Teams", df["team"].nunique() if not df.empty and "team" in df else 0)
        c4.metric("Pitchers", df["pitcher"].nunique() if not df.empty and "pitcher" in df else 0)

        if audit:
            with st.expander("Feeder Audit"):
                st.write(audit)

        if st.button("BLEND NOW"):
            results = run_true_blender(df)
            st.session_state.results = results
            st.success("BLENDER COMPLETE — OWNERS LOCKED")
            if results.get("core") is not None and not results["core"].empty:
                st.download_button("Download Core CSV", csv_bytes(results["core"]), "core.csv", "text/csv")


    # Tickets also live directly under the Blender Machine after feed/blend.
    if st.session_state.results and st.session_state.results.get("core") is not None and not st.session_state.results.get("core").empty:
        st.markdown("---")
        tickets_view(st.session_state.results)

    recap_view(st.session_state.results)

with tabs[1]:
    tickets_view(st.session_state.results)

with tabs[2]:
    game_board_view(st.session_state.results)
