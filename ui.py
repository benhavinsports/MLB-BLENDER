import html
import pandas as pd
import streamlit as st
from schema import team_color

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x, float) else str(x)

def pct(x):
    try: return max(2, min(100, int(float(x or 0))))
    except Exception: return 0

def safe_table(df, height=360):
    if df is None or df.empty:
        st.info("No data.")
        return
    show = df.copy()
    for c in show.columns:
        show[c] = show[c].apply(lambda x: str(x) if isinstance(x, (list, tuple, dict, set)) else x)
        if show[c].dtype == "object":
            show[c] = show[c].astype(str)
    st.dataframe(show, use_container_width=True, height=height)

def css():
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Rajdhani:wght@700&display=swap');:root{--cream:#f5ead8;--acid:#d9ff2f;--green:#00ff73;--orange:#ff9900;--red:#ff355c;--line:rgba(245,234,216,.15)}.stApp{background:radial-gradient(circle at 15% 5%,rgba(217,255,47,.16),transparent 24%),linear-gradient(180deg,#050505,#090908);color:var(--cream)}.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(245,234,216,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(245,234,216,.04) 1px,transparent 1px);background-size:34px 34px}.block-container{max-width:1180px;padding:1rem 1rem 4rem}.hero,.panel,.card,.ticket{border:1px solid var(--line);border-radius:28px;background:linear-gradient(160deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:18px;margin:12px 0}.title,.card-name,.score{font-family:'Black Ops One'}.title{font-size:clamp(42px,7vw,82px);line-height:.86}.hot{color:var(--acid)}.chip,.role,.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:8px 11px;margin:5px;font-family:Rajdhani}.stButton>button{min-height:60px;width:100%;border:0;border-radius:18px;font-family:'Black Ops One';font-size:20px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));color:#050505}.blade-stage{position:relative;height:300px;border-radius:24px;border:1px solid var(--line);overflow:hidden;background:#050505}.blade{position:absolute;left:50%;top:50%;width:230px;height:230px;margin:-115px;border-radius:50%;background:conic-gradient(transparent 0deg,var(--acid) 38deg,transparent 78deg,var(--green) 155deg,transparent 200deg,var(--orange) 265deg,transparent 320deg);animation:spin .95s linear infinite}.center{position:absolute;left:50%;top:50%;width:112px;height:112px;margin:-56px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.25);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid)}@keyframes spin{to{transform:rotate(360deg)}}.card{position:relative;overflow:hidden}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.card-name{font-size:32px;margin:12px 0}.meta{font-family:Rajdhani;color:#aaa}.score{font-size:44px}.bar{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{border:1px solid rgba(245,234,216,.10);border-radius:14px;padding:9px}.stat b{font-size:20px}.stat span{display:block;font-family:Rajdhani;color:#aaa}.bad{border:1px solid rgba(255,53,92,.35);background:rgba(255,53,92,.10);border-radius:16px;padding:12px}.good{border:1px solid rgba(0,255,115,.28);background:rgba(0,255,115,.08);border-radius:16px;padding:12px}</style>""", unsafe_allow_html=True)

def hero():
    st.markdown("""<div class="hero"><div class="title">THE <span class="hot">BLENDER</span><br/>LOCK ROOM</div><span class="chip">FEEDER FIRST</span><span class="chip">0 → 18</span><span class="chip">10.5 IN SEQUENCE</span><span class="chip">ONE OWNER PER GAME</span></div>""", unsafe_allow_html=True)

def wheel(status="READY"):
    st.markdown(f"""<div class="panel"><h3 style="font-family:Black Ops One">BLENDER MACHINE</h3><div class="blade-stage"><div class="blade"></div><div class="center">{html.escape(str(status))[:16]}</div></div></div>""", unsafe_allow_html=True)

def card(r):
    p = pct(r.get("score"))
    color = team_color(r.get("team",""))
    st.markdown(f"""<div class="card" style="border-color:{color}99"><span class="role">{r.get('role','Primary')}</span><div class="card-name">{html.escape(str(r.get('player','')))}</div><div class="meta"><span style="color:{color};font-weight:900">{html.escape(str(r.get('team','')))}</span> vs {html.escape(str(r.get('pitcher','')))} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small style="display:block;font-family:Rajdhani;color:#aaa;font-size:13px">TRUE BLEND SCORE</small></div><div class="bar"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">CONF {p}%</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)
