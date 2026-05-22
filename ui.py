
import streamlit as st
import pandas as pd
from engine import csv_bytes, run_recap_check

TEAM_COLORS = {
"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D","phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C","astros":"#EB6E1F","blue jays":"#134A8E","orioles":"#DF4601","rays":"#092C5C","royals":"#004687","cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E","diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831","white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0","nationals":"#AB0003","rangers":"#003278"
}

def team_color(team):
    t = str(team).lower()
    for k,v in TEAM_COLORS.items():
        if k in t:
            return v
    return "#d9ff2f"

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Rajdhani:wght@700&display=swap');
:root{--cream:#f5ead8;--acid:#d9ff2f;--green:#00ff73;--orange:#ff9900;--line:rgba(245,234,216,.16)}
.stApp{background:radial-gradient(circle at 14% 7%,rgba(217,255,47,.18),transparent 24%),linear-gradient(180deg,#030303,#090908,#030303);color:var(--cream)}
.block-container{max-width:1180px;padding:1rem 1rem 4rem}
.hero,.machine,.card,.ticket{border:1px solid var(--line);border-radius:30px;background:linear-gradient(155deg,rgba(23,22,21,.97),rgba(5,5,5,.98));padding:18px;margin:12px 0}
.title,.card-name,.score,.section-title{font-family:'Black Ops One'}
.title{font-size:clamp(46px,8vw,90px);line-height:.84}.hot{color:var(--acid)}
.stButton>button{min-height:72px;width:100%;border:0;border-radius:22px;font-family:'Black Ops One';font-size:24px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));color:#050505}
div[data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,15,.88);border:1px solid var(--line);border-radius:20px;padding:8px}
div[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--green))!important;color:#050505!important;border-radius:14px}
div[data-testid="stFileUploader"]{border:1px dashed rgba(217,255,47,.45)!important;border-radius:26px!important;background:linear-gradient(135deg,rgba(217,255,47,.10),rgba(0,255,115,.04))!important;padding:16px!important}
.blender-wrap{position:relative;height:500px;border-radius:34px;border:1px solid var(--line);background:radial-gradient(circle at center,rgba(217,255,47,.13),rgba(0,0,0,.97));overflow:hidden;margin-top:12px}
.jar{position:absolute;left:50%;top:48%;width:365px;height:365px;transform:translate(-50%,-50%);border-radius:58px 58px 125px 125px;border:3px solid rgba(245,234,216,.18);background:linear-gradient(180deg,rgba(245,234,216,.08),rgba(0,0,0,.38))}
.blade{position:absolute;left:50%;top:54%;width:285px;height:285px;margin:-142px;border-radius:50%;background:conic-gradient(transparent 0deg,var(--acid) 32deg,transparent 74deg,var(--green) 148deg,transparent 205deg,var(--orange) 268deg,transparent 320deg);animation:spin .52s linear infinite;z-index:2}
.blade:after{content:"";position:absolute;inset:58px;border-radius:50%;background:rgba(0,0,0,.72);border:1px solid rgba(245,234,216,.18)}
.center{position:absolute;left:50%;top:54%;width:122px;height:122px;margin:-61px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.32);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid);z-index:5}
.float{position:absolute;font-family:Rajdhani;background:rgba(245,234,216,.13);border:1px solid rgba(245,234,216,.22);border-radius:999px;padding:8px 12px;max-width:170px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;animation:dropmix 3.5s ease-in-out infinite;z-index:6}
.f1{top:82px;left:7%;animation-delay:.1s}.f2{top:88px;right:7%;animation-delay:.7s}.f3{bottom:140px;left:8%;animation-delay:1.1s}.f4{bottom:136px;right:8%;animation-delay:1.5s}.f5{top:34px;left:38%;animation-delay:2s}.f6{bottom:78px;left:36%;animation-delay:2.4s}
.feed-slot{position:absolute;left:50%;top:12px;transform:translateX(-50%);font-family:'Black Ops One';background:linear-gradient(90deg,var(--acid),var(--green));color:#050505;padding:13px 24px;border-radius:999px;z-index:8}
.output-slot{position:absolute;left:50%;bottom:0;transform:translateX(-50%);font-family:'Black Ops One';color:#ecffc1;background:rgba(5,5,5,.94);width:100%;text-align:center;padding:16px 10px;z-index:9}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes dropmix{0%{transform:translateY(-45px) scale(.92);opacity:.32}35%{transform:translateY(92px) scale(1);opacity:.96}70%{transform:translateY(188px) scale(.78);opacity:.32}100%{transform:translateY(-45px) scale(.92);opacity:.32}}
.card{position:relative;overflow:hidden}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}
.elite{animation:pulse 1.15s infinite;border-color:#d9ff2f!important;box-shadow:0 0 28px rgba(217,255,47,.35)}
@keyframes pulse{50%{filter:brightness(1.25);box-shadow:0 0 42px rgba(217,255,47,.55)}}
.card-name{font-size:34px;margin:12px 0}.meta,.reason,.leg{font-family:Rajdhani;color:#d8cfbf}.score{font-size:48px}.bar{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{border:1px solid rgba(245,234,216,.10);border-radius:14px;padding:9px}.stat span{display:block;color:#aaa}
.badge,.role{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:7px 10px;margin:4px;font-family:Rajdhani}
.leg{display:flex;justify-content:space-between;border-bottom:1px solid rgba(245,234,216,.1);padding:12px 0}.odds{background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);border-radius:10px;padding:6px 9px;color:#ecffc1}

div[data-testid="stFileUploader"]{
    border:2px dashed rgba(217,255,47,.65)!important;
    border-radius:28px!important;
    background:linear-gradient(135deg,rgba(217,255,47,.14),rgba(0,255,115,.06))!important;
    padding:18px!important;
    margin-top:-10px!important;
}
div[data-testid="stFileUploader"] section{
    border:0!important;
    background:transparent!important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]{
    border-radius:24px!important;
    min-height:92px!important;
}
.machine-stage{
    font-family:'Black Ops One';
    text-align:center;
    color:#050505;
    background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));
    border-radius:999px;
    padding:10px 18px;
    margin:10px auto;
    max-width:420px;
}

/* v63: the real Streamlit uploader is the only feed button */
div[data-testid="stFileUploader"]{
    border:2px solid rgba(217,255,47,.85)!important;
    border-radius:32px!important;
    background:linear-gradient(135deg,rgba(217,255,47,.22),rgba(0,255,115,.08),rgba(255,153,0,.08))!important;
    padding:20px!important;
    margin:14px 0 18px 0!important;
    box-shadow:0 0 30px rgba(217,255,47,.18)!important;
}
div[data-testid="stFileUploader"] label{
    font-family:'Black Ops One'!important;
    font-size:28px!important;
    color:#d9ff2f!important;
    text-align:center!important;
    display:block!important;
}
div[data-testid="stFileUploader"] section{
    min-height:120px!important;
    border:0!important;
    border-radius:26px!important;
    background:rgba(5,5,5,.72)!important;
}
div[data-testid="stFileUploader"] button{
    min-height:62px!important;
    border-radius:999px!important;
    background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))!important;
    color:#050505!important;
    font-family:'Black Ops One'!important;
    font-size:19px!important;
    border:0!important;
}
div[data-testid="stFileUploader"] small{
    color:#f5ead8!important;
    font-family:Rajdhani!important;
}

</style>
""", unsafe_allow_html=True)

def hero():
    st.markdown("""<div class="hero"><div class="title">THE <span class="hot">BLENDER</span><br/>MACHINE</div></div>""", unsafe_allow_html=True)

def blender_machine(names, state="READY"):
    names = names or ["Drop File","Players In","Gates Spin","Owners Out"]
    names = (names + names + names)[:6]
    floats = "".join([f"<div class='float f{i+1}'>{str(n)[:22]}</div>" for i,n in enumerate(names)])
    st.markdown(f"""<div class="machine"><div class="blender-wrap"><div class="jar"><div class="blade"></div><div class="center">{state}</div>{floats}</div><div class="output-slot">FEED DATA HERE BELOW → BLADES SPIN → OWNERS LOCK → TICKETS POP OUT</div></div></div>""", unsafe_allow_html=True)
    st.markdown(f"<div class='machine-stage'>{state}</div>", unsafe_allow_html=True)

def fmt(x):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)

def pct(x):
    try:
        return max(2,min(100,int(float(x or 0))))
    except Exception:
        return 0

def card(r):
    p = pct(r.get("score"))
    color = team_color(r.get("team",""))
    elite = p >= 75
    cls = " card elite" if elite else " card"
    fire = "🔥 " if elite else ""
    path = str(r.get("gate_path",""))
    short = " | ".join(path.split(" | ")[:6])
    st.markdown(f"""<div class="{cls}" style="border-color:{color}99"><span class="role">{r.get('official_core_role','')}</span><span class="badge">{r.get('archetype','')}</span><div class="card-name">{fire}{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small style="display:block;font-family:Rajdhani;color:#aaa;font-size:13px">TRUE BLEND SCORE</small></div><div class="bar"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><div class="reason"><b>Blend path:</b> {short}</div></div>""", unsafe_allow_html=True)

def tickets_view(results, key_prefix='tickets'):
    st.markdown("<div class='section-title' style='font-size:34px'>TICKETS</div>", unsafe_allow_html=True)
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"<div class='ticket'><h2>{label}</h2>", unsafe_allow_html=True)
        df = results.get(key, pd.DataFrame()) if results else pd.DataFrame()
        if df is None or df.empty:
            st.info("Run the Blender first.")
        else:
            for _,r in df.iterrows():
                fire = "🔥 " if int(r.get("score",0)) >= 75 else ""
                st.markdown(f"<div class='leg'><span><b>{fire}{r.get('player','')}</b><br><small>{r.get('official_core_role','')} · {r.get('archetype','')} · {r.get('team','')} vs {r.get('pitcher','')}</small></span><span class='odds'>{int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
            st.download_button(f"Download {label}", csv_bytes(df), f"{label.lower().replace(' ','_')}.csv", "text/csv", key=f"{key_prefix}_{key}_download")
        st.markdown("</div>", unsafe_allow_html=True)

def game_board_view(results):
    st.markdown("<div class='section-title' style='font-size:34px'>GAME BOARD — OWNERS BY GAME</div>", unsafe_allow_html=True)
    owners = results.get("owners", pd.DataFrame()) if results else pd.DataFrame()
    survivors = results.get("survivors", pd.DataFrame()) if results else pd.DataFrame()
    if owners is None or owners.empty:
        st.info("Run the Blender first.")
        return
    for _,r in owners.iterrows():
        card(r)
    with st.expander("All Survivors + Gates"):
        cols = [c for c in ["page","game","player","team","pitcher","official_core_role","archetype","score","gate_path","notes"] if c in survivors.columns]
        st.dataframe(survivors[cols], use_container_width=True, height=450)
    st.download_button("Download Game Board CSV", csv_bytes(owners), "game_board.csv", "text/csv", key="game_board_download_csv_btn")

def recap_view(results):
    st.markdown("<div class='ticket'><h3>2AM EASTERN AUTO RECAP</h3><p>Recap checks only saved locked Game Board owners. Manual button below runs the same locked-owner check now.</p></div>", unsafe_allow_html=True)
    if st.button("RUN RECAP NOW", key="manual_recap_now_btn"):
        recap, meta = run_recap_check(results)
        st.write(meta)
        if recap is not None and not recap.empty:
            keep=[c for c in ["player","team","pitcher","score","official_core_role","archetype","hit_hr"] if c in recap.columns]
            st.dataframe(recap[keep], use_container_width=True)
            st.download_button("Download Recap CSV", csv_bytes(recap), "recap.csv", "text/csv", key="recap_download_csv_btn")
        else:
            st.info("No locked Game Board owners found yet.")
