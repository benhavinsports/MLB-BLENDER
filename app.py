
import streamlit as st, pandas as pd
from feeder import load_any
from engine import run_true_blender, ENGINE_VERSION
from ui import inject_css, render_results
st.set_page_config(page_title="BenHavin TRUE Blender", layout="wide")
inject_css()
st.title("BENHAVIN TRUE BLENDER MACHINE")
st.caption(f"Engine: {ENGINE_VERSION}")
st.write("Fix: **pitcher weakness archetype first → hitter match gate → survivor pressure**. No backwards classify-after-only logic.")
up=st.file_uploader("Upload Star Tool PDF / CSV / Excel", type=["pdf","csv","xlsx","xls"])
if up:
    with st.spinner("Reading slate, locking pitcher archetypes, then running gate survival..."):
        df=load_any(up)
        result=run_true_blender(df)
    with st.expander("Feeder rows"):
        st.dataframe(df,use_container_width=True,height=280)
    render_results(result)
    owners=[o["owner"] for o in result.get("owners",[])]
    if owners:
        st.download_button("Download ALL GAME OWNERS CSV", pd.DataFrame(owners).to_csv(index=False), "true_blender_game_owners.csv", "text/csv")
        st.download_button("Download CORE 3 CSV", pd.DataFrame(result.get("core",[])).to_csv(index=False), "true_blender_core3.csv", "text/csv")
else:
    st.info("Upload today’s PDF. The engine locks pitcher weakness archetypes first, then only lets matching hitters survive.")
