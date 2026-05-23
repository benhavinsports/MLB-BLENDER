
import streamlit as st
import pandas as pd
from engine import csv_bytes

TEAM_COLORS = {
    "Arizona Diamondbacks": ("#A71930", "#E3D4AD"), "Atlanta Braves": ("#CE1141", "#13274F"),
    "Baltimore Orioles": ("#DF4601", "#000000"), "Boston Red Sox": ("#BD3039", "#0C2340"),
    "Chicago White Sox": ("#C4CED4", "#27251F"), "Chicago Cubs": ("#0E3386", "#CC3433"),
    "Cincinnati Reds": ("#C6011F", "#000000"), "Cleveland Guardians": ("#E31937", "#00385D"),
    "Colorado Rockies": ("#33006F", "#C4CED4"), "Detroit Tigers": ("#0C2340", "#FA4616"),
    "Houston Astros": ("#EB6E1F", "#002D62"), "Kansas City Royals": ("#004687", "#BD9B60"),
    "Los Angeles Angels": ("#BA0021", "#003263"), "Los Angeles Dodgers": ("#005A9C", "#EF3E42"),
    "Miami Marlins": ("#00A3E0", "#EF3340"), "Milwaukee Brewers": ("#FFC52F", "#12284B"),
    "Minnesota Twins": ("#002B5C", "#D31145"), "New York Yankees": ("#003087", "#C4CED4"),
    "New York Mets": ("#002D72", "#FF5910"), "Athletics": ("#003831", "#EFB21E"),
    "Philadelphia Phillies": ("#E81828", "#002D72"), "Pittsburgh Pirates": ("#FDB827", "#27251F"),
    "San Diego Padres": ("#2F241D", "#FFC425"), "San Francisco Giants": ("#FD5A1E", "#27251F"),
    "Seattle Mariners": ("#0C2C56", "#005C5C"), "St. Louis Cardinals": ("#C41E3A", "#0C2340"),
    "Tampa Bay Rays": ("#092C5C", "#8FBCE6"), "Texas Rangers": ("#003278", "#C0111F"),
    "Toronto Blue Jays": ("#134A8E", "#E8291C"), "Washington Nationals": ("#AB0003", "#14225A"),
}
def _colors(team):
    t=str(team or "")
    for k,v in TEAM_COLORS.items():
        if k.lower() in t.lower() or t.lower() in k.lower():
            return v
    return "#B7FF4A","#F4A326"
def _elite(score):
    try: return float(score)>=78
    except Exception: return False

def inject_css():
    st.markdown("""
<style>
.stApp{background:#050505;color:#f5ead8}.block-container{max-width:1200px}
h1,h2,h3,.title{font-family:Impact,'Arial Black',sans-serif}
.stButton>button{min-height:66px;border-radius:20px;font-family:Impact,'Arial Black';font-size:24px;background:linear-gradient(90deg,#d9ff2f,#00ff73,#ff9900);color:#050505}
.cardx{border-radius:26px;padding:24px;margin:18px 0;background:#111;border:2px solid #333}
@keyframes pulseElite{from{filter:brightness(1)}to{filter:brightness(1.23);transform:translateY(-2px)}}
.metricgrid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.metricgrid div{background:#0b0b0b;border:1px solid #333;border-radius:12px;padding:10px}.metricgrid b{display:block;font-size:20px}.small{color:#bbb}
</style>
""", unsafe_allow_html=True)

def hero():
    st.markdown("<h1 class='title'>🔥 THE BLENDER</h1><div class='small'>19-gate 4/27 reset · no site bias · one owner per game</div>", unsafe_allow_html=True)

def blender_machine(names, state="READY"):
    txt=", ".join(names) if names else "Feed data → Run Blender"
    st.markdown(f"<div class='cardx'><h2>BLENDER MACHINE — {state}</h2><p>{txt}</p></div>", unsafe_allow_html=True)

def card(r):
    p,s=_colors(r.get("team",""))
    score=float(r.get("score",0) or 0)
    anim="animation:pulseElite 1.2s infinite alternate;" if _elite(score) else ""
    fire="🔥 " if _elite(score) else ""
    st.markdown(f"""
<div class='cardx' style='border-color:{s};box-shadow:{'0 0 25px '+s if _elite(score) else 'none'};{anim}background:linear-gradient(135deg,#101010,{p}44)'>
<h2 style='color:{s};font-size:54px;margin:0'>{fire}{r.get('player','')}</h2>
<div class='small'><b>{r.get('team','')}</b> vs {r.get('pitcher','')} · {r.get('official_core_role','')} · {r.get('archetype','')}</div>
<div style='font-size:74px;font-family:Impact;color:{s}'>{score:.1f}</div>
<div class='metricgrid'>
<div><b>{r.get('pull_pct','—')}</b><span>Pull</span></div><div><b>{r.get('sweet_spot_pct','—')}</b><span>Sweet</span></div>
<div><b>{r.get('barrel_pct','—')}</b><span>Barrel</span></div><div><b>{r.get('dmg','—')}</b><span>DMG</span></div>
<div><b>{r.get('hr_pa','—')}</b><span>HR/PA</span></div><div><b>{r.get('hpi','—')}</b><span>HPI</span></div>
</div>
<p class='small'><b>Path:</b> {r.get('gate_path','')}</p>
</div>
""", unsafe_allow_html=True)

def tickets_view(results, key_prefix="tickets"):
    st.markdown("## 🎟️ Tickets")
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"### {label}")
        df=results.get(key,pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
        if df is None or df.empty:
            st.info("No legs in this bucket yet.")
        else:
            for _,r in df.iterrows(): card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{label.lower().replace(' ','_')}.csv", key=f"{key_prefix}_{key}")

def game_board_view(results):
    st.markdown("## 🧠 Game Board / Gate Results")
    meta=results.get("meta",{}) if isinstance(results,dict) else {}
    if meta:
        c=st.columns(4); c[0].metric("Rows",meta.get("input_rows",0)); c[1].metric("Games",meta.get("games",0)); c[2].metric("Owners",meta.get("owners_locked",0)); c[3].metric("Survivors",meta.get("survivor_rows",0))
        st.info(meta.get("message",""))
    owners=results.get("owners",pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
    survivors=results.get("survivors",pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
    if owners is not None and not owners.empty:
        st.markdown("### Owners")
        for _,r in owners.iterrows(): card(r)
    if survivors is not None and not survivors.empty:
        st.markdown("### Full Survivor Board")
        cols=[c for c in ["game","player","team","pitcher","official_core_role","archetype","score","gate_grade","hard_fails","soft_fails","gate_path"] if c in survivors.columns]
        st.dataframe(survivors[cols], use_container_width=True, height=500)
        st.download_button("Download Survivor Board", csv_bytes(survivors), "survivor_board.csv", key="survivors_download")

def recap_view(results):
    st.markdown("## 2AM Recap")
    st.info("Recap hook ready.")
