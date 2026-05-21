import time, pandas as pd, streamlit as st
from feeder.file_reader import read_file
from checks.feeder_lock import audit_feed
from machine.blender import run_machine
from interface.styles import inject_css
from interface.components import top_shell, live_blender, player_card
from exports.csv_export import to_csv_bytes
st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css(); top_shell()
tabs=st.tabs(["Launch","Machine","Game Board","Tickets","Kill Feed","Exports"])
with tabs[0]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]; live_blender(owners.head(6).player.tolist(), owners.iloc[0].player if not owners.empty else "OWNER", f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS → CORE LOCKED")
    else: live_blender()
    uploaded=st.file_uploader("Upload slate",type=["pdf","csv","xlsx"])
    if uploaded:
        try: df,raw_text=read_file(uploaded.name, uploaded.read())
        except Exception as e:
            st.error(f"Parser error: {e}"); df=pd.DataFrame(); raw_text=""
        if df.empty: st.error("No valid player rows parsed.")
        else:
            c1,c2,c3,c4=st.columns(4); c1.metric("Players",len(df)); c2.metric("Games",df.game.nunique()); c3.metric("Teams",df.team.nunique()); c4.metric("Pitchers",df.pitcher.nunique())
            ok,issues=audit_feed(df)
            with st.expander("Feeder Accuracy Audit"):
                if ok: st.markdown("<div class='audit-good'>FEEDER LOCKED</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='audit-bad'>FEEDER NOT LOCKED</div>", unsafe_allow_html=True); st.write(issues)
            if st.button("ENGAGE BLENDER"):
                if not ok: st.error("Feeder quality failed. Fix feed before producing picks — no fake locks.")
                else:
                    progress=st.progress(0); msg=st.empty()
                    for i,txt in enumerate(["Feeding slate","Mapping columns","Running hard gates","Checking 10.5 transfer","Locking game owners","Building slips"]):
                        msg.info(f"MACHINE SPEAKS: {txt.upper()}..."); progress.progress((i+1)/6); time.sleep(.12)
                    owners,core,alt,logs,survivors=run_machine(df); st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs,"survivors":survivors}); msg.success("MACHINE COMPLETE — FINAL BOARD READY")
            with st.expander("Parsed Slate Preview"): st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='section'><h2>CORE 3</h2><span class='tag'>ONE OWNER PER GAME</span></div>", unsafe_allow_html=True)
        cols=st.columns(3)
        for i,(_,r) in enumerate(st.session_state["core"].iterrows()):
            with cols[i]: player_card(r)
        st.markdown("<div class='section'><h2>ALT 3</h2><span class='tag'>LEGAL BACKUPS</span></div>", unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(st.session_state["alt"].head(3).iterrows()):
                with cols[i]: player_card(r)
with tabs[1]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]; live_blender(owners.head(6).player.tolist(), owners.iloc[0].player if not owners.empty else "OWNER", f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS → CORE LOCKED")
    else: live_blender()
with tabs[2]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): player_card(r)
    else: st.info("Run a slate first.")
with tabs[3]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        core=st.session_state["core"]; alt=st.session_state["alt"]
        st.markdown("<div class='ticket'><h3>CORE SLIP</h3>", unsafe_allow_html=True)
        for _,r in core.iterrows(): st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='lock'>LOCK CORE</div></div>", unsafe_allow_html=True)
        if not alt.empty:
            st.markdown("<div class='ticket'><h3>ALT SLIP</h3>", unsafe_allow_html=True)
            for _,r in alt.head(3).iterrows(): st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='lock'>LOCK ALT</div></div>", unsafe_allow_html=True)
    else: st.info("Run a slate first.")
with tabs[4]:
    if "logs" in st.session_state:
        logs=st.session_state["logs"]; st.markdown("<div class='feed-box'>", unsafe_allow_html=True)
        for _,r in logs.head(140).iterrows(): st.markdown(f"<div class='feed-row'><span class='gate'>{r['Gate']}</span> · <span class='cut'>CUT {r['Cut']}</span> · <span class='alive'>ALIVE {r['After']}</span><br/><span style='color:#aaa093'>{r['Game']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Full Audit Table"): st.dataframe(logs,use_container_width=True,height=540)
    else: st.info("Run a slate first.")
with tabs[5]:
    if "core" in st.session_state:
        st.download_button("Download Core CSV",data=to_csv_bytes(st.session_state["core"]),file_name="blender_core.csv",mime="text/csv")
        st.download_button("Download Alt CSV",data=to_csv_bytes(st.session_state["alt"]),file_name="blender_alt.csv",mime="text/csv")
        st.download_button("Download Owners CSV",data=to_csv_bytes(st.session_state["owners"]),file_name="blender_game_owners.csv",mime="text/csv")
    else: st.info("Run a slate first.")
