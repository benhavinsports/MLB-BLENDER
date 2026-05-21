import html, pandas as pd, streamlit as st
from team_data import team_color

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)

def pct(x):
    try: return max(2,min(100,int(float(x or 0))))
    except Exception: return 0

def top_shell():
    st.markdown("""<div class="top"><div class="brand"><div class="mark">BH</div><div><div class="brand-title">THE BLENDER</div><div class="brand-sub">LOCK ROOM</div></div></div><div class="status">SYSTEM ARMED</div></div><div class="hero"><h1>THE <span class="hot">BLENDER</span><br/>LOCK ROOM</h1><span class="chip">OFFICIAL 0 → 18</span><span class="chip">10.5 SEQUENCED</span><span class="chip">ONE OWNER PER GAME</span><span class="chip">NO REVIVALS</span></div>""", unsafe_allow_html=True)

def live_blender(names=None, owner="READY", status="UPLOAD SLATE → FEEDER LOCK → RUN"):
    names=names or ["Upload Slate","Feed PDF","Lock Data","Run Machine"]
    n=(names+names+names)[:6]
    html_names="".join([f"<div class='float-name n{i+1}'>{html.escape(str(nm))}</div>" for i,nm in enumerate(n)])
    st.markdown(f"""<div class="live-wrap"><div class="live-head"><h3>BLENDER MACHINE</h3><span class="tag">PRIVATE FEED</span></div><div class="blender-stage"><div class="blade"></div><div class="center">{html.escape(str(owner))[:18]}</div>{html_names}<div class="machine-feed"><span>{html.escape(status)}</span></div></div></div>""", unsafe_allow_html=True)

def player_card(r):
    p=pct(r.get("score")); color=team_color(r.get("team",""))
    st.markdown(f"""<div class="card" style="border-color:{color}88"><span class="role">{r.get('role','Primary')}</span><div class="player">{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small>TRUE BLEND SCORE</small></div><div class="ring"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">CONF {p}%</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)
