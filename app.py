import time
import pandas as pd
import streamlit as st
from feeder import read_file
from audit import audit_feed
from engine import run_machine
from ui import css, hero, wheel, card, safe_table

def csv_bytes(df):
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
css()
hero()

tabs = st.tabs(["Launch","Feeder Lab","Machine","Game Board","Tickets","Kill Feed","Exports"])

with tabs[0]:
    wheel("READY")
    uploaded = st.file_uploader("Manual feed", type=["pdf","csv","xlsx"])
    if uploaded:
        try:
            df, raw_text, debug = read_file(uploaded.name, uploaded.read())
        except Exception as e:
            st.error(f"Feeder crash: {e}")
            df, raw_text, debug = pd.DataFrame(), "", []

        st.session_state.update({"df":df, "raw_text":raw_text, "debug":debug})

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Rows", len(df))
        c2.metric("Games", df.game.nunique() if not df.empty else 0)
        c3.metric("Teams", df.team.replace("", pd.NA).dropna().nunique() if not df.empty else 0)
        c4.metric("Pitchers", df.pitcher.replace("", pd.NA).dropna().nunique() if not df.empty else 0)

        ok, issues = audit_feed(df)
        if ok:
            st.markdown("<div class='good'>FEEDER LOCKED</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='bad'>FEEDER NOT LOCKED — RESULTS BLOCKED</div>", unsafe_allow_html=True)
            st.write(issues)

        if st.button("ENGAGE BLENDER"):
            if not ok:
                st.error("No fake locks. Fix feed first in Feeder Lab.")
            else:
                msg = st.empty()
                progress = st.progress(0)
                for i, step in enumerate(["FEED VERIFIED","GATES LOADED","10.5 CHECKED","OWNERS LOCKED","TICKETS BUILT"]):
                    msg.info(step)
                    progress.progress((i+1)/5)
                    time.sleep(.12)
                owners, core, alt, logs, survivors = run_machine(df)
                st.session_state.update({"owners":owners, "core":core, "alt":alt, "logs":logs, "survivors":survivors})
                st.success("MACHINE COMPLETE")

with tabs[1]:
    st.subheader("Feeder Lab")
    if "df" in st.session_state:
        df = st.session_state["df"]
        debug = st.session_state.get("debug", [])
        raw_text = st.session_state.get("raw_text", "")
        safe_table(df, 420)
        st.download_button("Download feeder rows CSV", csv_bytes(df), "feeder_rows.csv", "text/csv")
        if debug:
            with st.expander("Page Section Debug"):
                safe_table(pd.DataFrame(debug), 320)
        with st.expander("Raw text sample"):
            st.text("\\n".join(str(raw_text).splitlines()[:250]) if raw_text else "No raw text.")
    else:
        st.info("Upload a feed first.")

with tabs[2]:
    status = "LOCKED" if "owners" in st.session_state else "READY"
    wheel(status)

with tabs[3]:
    if "owners" in st.session_state and not st.session_state["owners"].empty:
        for _, r in st.session_state["owners"].iterrows():
            card(r)
    else:
        st.info("Run a locked feed first.")

with tabs[4]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        st.markdown("<div class='ticket'><h2>CORE 3</h2>", unsafe_allow_html=True)
        for _, r in st.session_state["core"].iterrows():
            st.markdown(f"<p><b>{r['player']}</b> — {r.get('team','')} vs {r.get('pitcher','')} — {int(r.get('score',0))}%</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            st.markdown("<div class='ticket'><h2>ALT 3</h2>", unsafe_allow_html=True)
            for _, r in st.session_state["alt"].iterrows():
                st.markdown(f"<p><b>{r['player']}</b> — {r.get('team','')} vs {r.get('pitcher','')} — {int(r.get('score',0))}%</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Run a locked feed first.")

with tabs[5]:
    if "logs" in st.session_state:
        safe_table(st.session_state["logs"], 520)
    else:
        st.info("Run a locked feed first.")

with tabs[6]:
    if "df" in st.session_state:
        st.download_button("Download Full Feed CSV", csv_bytes(st.session_state["df"]), "full_feed.csv", "text/csv")
    if "owners" in st.session_state:
        st.download_button("Download Owners CSV", csv_bytes(st.session_state["owners"]), "owners.csv", "text/csv")
        st.download_button("Download Core CSV", csv_bytes(st.session_state["core"]), "core.csv", "text/csv")
        st.download_button("Download Alt CSV", csv_bytes(st.session_state["alt"]), "alt.csv", "text/csv")
