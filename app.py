import time
import pandas as pd
import streamlit as st
from feeder_brain import read_file
from auto_star_feed import pull_star_tool
from blender_engine import run_machine, audit_feed
from ui import inject_css, top_shell, live_blender, player_card

def safe_display_df(df, height=360):
    """Streamlit-safe table display: converts nested/list/dict/object values to strings so pyarrow cannot crash."""
    if df is None:
        st.info("No data.")
        return
    try:
        show = df.copy()
        for col in show.columns:
            show[col] = show[col].apply(lambda x: str(x) if isinstance(x, (list, tuple, dict, set)) else x)
            if show[col].dtype == "object":
                show[col] = show[col].astype(str)
        st.dataframe(show, use_container_width=True, height=height)
    except Exception as e:
        st.warning(f"Table preview could not render safely: {e}")
        st.write(df.astype(str).head(200))


def to_csv_bytes(df):
    if df is None or df.empty: return b""
    return df.to_csv(index=False).encode("utf-8")

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
inject_css()
top_shell()

tabs=st.tabs(["Launch","Feeder Lab","Machine","Game Board","Tickets","Kill Feed","Exports"])

with tabs[0]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]
        live_blender(owners.head(6).player.tolist(), owners.iloc[0].player if not owners.empty else "OWNER", f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS")
    else:
        live_blender()

    if st.button("AUTO PULL STAR TOOL DATA"):
        with st.spinner("Connecting to MLB Star Tool feed..."):
            df,status,debug = pull_star_tool()
        st.session_state.update({"df":df,"raw_text":status,"debug":[debug]})
        if df is None or df.empty:
            st.error(status)
            st.info("If this fails, add STAR_EXPORT_URL in Secrets from the Star Tool export/download link. PDF upload still works as backup.")
        else:
            st.success(status)
            st.rerun()

    st.markdown("<div class='chip'>PDF / CSV / XLSX BACKUP FEED</div>", unsafe_allow_html=True)
    uploaded=st.file_uploader("Upload slate",type=["pdf","csv","xlsx"])
    if uploaded:
        try:
            df,raw_text,debug=read_file(uploaded.name, uploaded.read())
        except Exception as e:
            st.error(f"Feeder error: {e}")
            df=pd.DataFrame(); raw_text=""; debug=[]
        st.session_state.update({"df":df,"raw_text":raw_text,"debug":debug})

        if df.empty:
            st.error("No valid player rows parsed.")
        else:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Players",len(df))
            c2.metric("Games",df.game.nunique())
            c3.metric("Teams",df.team.replace('',pd.NA).dropna().nunique())
            c4.metric("Pitchers",df.pitcher.replace('',pd.NA).dropna().nunique())

            ok,issues=audit_feed(df)
            with st.expander("Feeder Accuracy Audit"):
                if ok:
                    st.markdown("<div class='audit-good'>FEEDER LOCKED</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='audit-bad'>FEEDER NOT LOCKED</div>", unsafe_allow_html=True)
                    st.write(issues)

            if st.button("ENGAGE BLENDER"):
                if not ok:
                    st.error("Feeder quality failed. Go to Feeder Lab — no fake locks.")
                else:
                    progress=st.progress(0); msg=st.empty()
                    for i,txt in enumerate(["Reading feeder map","Running hard gates","Checking 10.5 transfer","Locking game owners","Building slips"]):
                        msg.info(f"MACHINE SPEAKS: {txt.upper()}...")
                        progress.progress((i+1)/5)
                        time.sleep(.12)
                    owners,core,alt,logs,survivors=run_machine(df)
                    st.session_state.update({"owners":owners,"core":core,"alt":alt,"logs":logs,"survivors":survivors})
                    msg.success("MACHINE COMPLETE — FINAL BOARD READY")

            with st.expander("Parsed Slate Preview"):
                safe_display_df(df, height=360)

with tabs[1]:
    st.subheader("Feeder Lab")
    if "df" in st.session_state:
        df=st.session_state["df"]
        raw_text=st.session_state.get("raw_text","")
        debug=st.session_state.get("debug",[])
        st.write("This tab shows the feeder truth before any picks.")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Rows",len(df))
        c2.metric("Games",df.game.nunique() if not df.empty else 0)
        c3.metric("Blank Teams",int((df.team.fillna('').astype(str).str.strip()=="").sum()) if not df.empty else 0)
        c4.metric("Blank Pitchers",int((df.pitcher.fillna('').astype(str).str.strip()=="").sum()) if not df.empty else 0)
        safe_display_df(df, height=420)
        st.download_button("Download feeder rows CSV",data=to_csv_bytes(df),file_name="feeder_rows.csv",mime="text/csv")
        if debug:
            st.write("Page debug")
            safe_display_df(pd.DataFrame(debug), height=260)
        with st.expander("Raw PDF text sample"):
            st.text("\n".join(str(raw_text).splitlines()[:250]) if raw_text else "No raw text.")
        if raw_text:
            st.download_button("Download raw PDF text",data=raw_text.encode("utf-8"),file_name="raw_pdf_text.txt",mime="text/plain")
    else:
        st.info("Upload a slate first.")

with tabs[2]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]
        live_blender(owners.head(6).player.tolist(), owners.iloc[0].player if not owners.empty else "OWNER", f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS")
    else:
        live_blender()

with tabs[3]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows():
            player_card(r)
    else:
        st.info("Run a slate first.")

with tabs[4]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        core=st.session_state["core"]; alt=st.session_state["alt"]
        st.markdown("<div class='ticket'><h3>CORE SLIP</h3>", unsafe_allow_html=True)
        for _,r in core.iterrows():
            st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='lock'>LOCK CORE</div></div>", unsafe_allow_html=True)
        if not alt.empty:
            st.markdown("<div class='ticket'><h3>ALT SLIP</h3>", unsafe_allow_html=True)
            for _,r in alt.head(3).iterrows():
                st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='lock'>LOCK ALT</div></div>", unsafe_allow_html=True)
    else:
        st.info("Run a slate first.")

with tabs[5]:
    if "logs" in st.session_state:
        logs=st.session_state["logs"]
        st.markdown("<div class='feed-box'>", unsafe_allow_html=True)
        for _,r in logs.head(140).iterrows():
            st.markdown(f"<div class='leg'><span>Gate {r['Gate']} · {r['Game']}</span><span class='odds'>ALIVE {r['After']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Full Audit Table"):
            safe_display_df(logs, height=540)
    else:
        st.info("Run a slate first.")

with tabs[6]:
    if "core" in st.session_state:
        st.download_button("Download Core CSV",data=to_csv_bytes(st.session_state["core"]),file_name="blender_core.csv",mime="text/csv")
        st.download_button("Download Alt CSV",data=to_csv_bytes(st.session_state["alt"]),file_name="blender_alt.csv",mime="text/csv")
        st.download_button("Download Owners CSV",data=to_csv_bytes(st.session_state["owners"]),file_name="blender_game_owners.csv",mime="text/csv")
        st.download_button("Download Full Feeder CSV",data=to_csv_bytes(st.session_state["df"]),file_name="full_feeder_rows.csv",mime="text/csv")
    else:
        st.info("Run a slate first.")
