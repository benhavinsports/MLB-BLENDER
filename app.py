
import streamlit as st
import pandas as pd
import traceback
from feeder import read_feed
from engine import run_true_blender, load_locked_results, fetch_live_public_slate, merge_public_context, fetch_live_public_hitter_pool, recalc_adaptive_weights_from_history
from ui import inject_css, hero, blender_machine, tickets_view, game_board_view, recap_view

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide")
inject_css(); hero()

def empty_results():
    return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":{}}
for k,v in {"feed_df":pd.DataFrame(),"results":load_locked_results(),"machine_state":"READY","public_context":pd.DataFrame(),"last_error":""}.items():
    if k not in st.session_state: st.session_state[k]=v
if not isinstance(st.session_state.results, dict): st.session_state.results=empty_results()

def run(df,label):
    if df is None or df.empty:
        st.warning("No feed data loaded.")
        return
    st.session_state.machine_state="RUNNING"
    with st.spinner(f"Running true 4/27 Blender on {label}..."):
        st.session_state.results=run_true_blender(df)
    st.session_state.machine_state="OWNERS LOCKED" if len(st.session_state.results.get("owners",pd.DataFrame())) else "AUDIT"
    st.success(st.session_state.results.get("meta",{}).get("message","Run complete."))

tabs=st.tabs(["Blender Machine","Tickets","Game Board"])
with tabs[0]:
    owners=st.session_state.results.get("owners",pd.DataFrame())
    names=owners["player"].head(5).tolist() if owners is not None and not owners.empty and "player" in owners else []
    blender_machine(names, st.session_state.machine_state)

    uploaded=st.file_uploader("FEED DATA HERE", type=["pdf","csv","xlsx","png","jpg","jpeg","webp","txt","md"], key="v93_uploader")
    if uploaded is not None:
        try:
            df,audit=read_feed(uploaded.name, uploaded.getvalue())
            df=merge_public_context(df, st.session_state.public_context)
            st.session_state.feed_df=df
            st.success(f"Feed loaded: {len(df)} rows")
        except Exception as e:
            st.session_state.last_error=traceback.format_exc()
            st.error(f"Feed failed: {e}")

    if st.button("RUN BLENDER NOW", use_container_width=True):
        run(st.session_state.feed_df, "uploaded feed")

    c1,c2=st.columns(2)
    with c1:
        if st.button("LOAD LIVE PUBLIC SLATE", use_container_width=True):
            ctx,meta=fetch_live_public_slate(); st.session_state.public_context=ctx; st.session_state.feed_df=ctx
            st.info(str(meta))
    with c2:
        if st.button("RUN LIVE PUBLIC BLENDER", use_container_width=True):
            pool,meta=fetch_live_public_hitter_pool(); st.session_state.feed_df=pool; st.info(str(meta)); run(pool,"live public pool")

    if st.button("RECALIBRATE MODEL WEIGHTS", use_container_width=True):
        st.info(str(recalc_adaptive_weights_from_history()))

    df=st.session_state.feed_df
    if df is not None and not df.empty:
        m=st.columns(4); m[0].metric("Rows",len(df)); m[1].metric("Games",df["game_key"].nunique() if "game_key" in df else 0); m[2].metric("Teams",df["team"].nunique() if "team" in df else 0); m[3].metric("Pitchers",df["pitcher"].nunique() if "pitcher" in df else 0)
    if st.session_state.last_error:
        with st.expander("Last Error"): st.code(st.session_state.last_error)
    tickets_view(st.session_state.results,"main")
    game_board_view(st.session_state.results)
    recap_view(st.session_state.results)
with tabs[1]:
    tickets_view(st.session_state.results,"tab")
with tabs[2]:
    game_board_view(st.session_state.results)
