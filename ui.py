
import pandas as pd
import streamlit as st
from engine import csv_bytes

TEAM_COLORS = {
    "Arizona Diamondbacks":("#A71930","#E3D4AD"),"Atlanta Braves":("#CE1141","#13274F"),"Baltimore Orioles":("#DF4601","#000000"),
    "Boston Red Sox":("#BD3039","#0C2340"),"Chicago Cubs":("#0E3386","#CC3433"),"Chicago White Sox":("#C4CED4","#27251F"),
    "Cincinnati Reds":("#C6011F","#000000"),"Cleveland Guardians":("#E31937","#00385D"),"Colorado Rockies":("#33006F","#C4CED4"),
    "Detroit Tigers":("#0C2340","#FA4616"),"Houston Astros":("#EB6E1F","#002D62"),"Kansas City Royals":("#004687","#BD9B60"),
    "Los Angeles Angels":("#BA0021","#003263"),"Los Angeles Dodgers":("#005A9C","#EF3E42"),"Miami Marlins":("#00A3E0","#EF3340"),
    "Milwaukee Brewers":("#FFC52F","#12284B"),"Minnesota Twins":("#002B5C","#D31145"),"New York Mets":("#002D72","#FF5910"),
    "New York Yankees":("#003087","#C4CED4"),"Athletics":("#003831","#EFB21E"),"Oakland Athletics":("#003831","#EFB21E"),
    "Philadelphia Phillies":("#E81828","#002D72"),"Pittsburgh Pirates":("#FDB827","#27251F"),"San Diego Padres":("#2F241D","#FFC425"),
    "San Francisco Giants":("#FD5A1E","#27251F"),"Seattle Mariners":("#0C2C56","#005C5C"),"St. Louis Cardinals":("#C41E3A","#0C2340"),
    "Tampa Bay Rays":("#092C5C","#8FBCE6"),"Texas Rangers":("#003278","#C0111F"),"Toronto Blue Jays":("#134A8E","#E8291C"),
    "Washington Nationals":("#AB0003","#14225A")
}
def _colors(team):
    low=str(team or "").lower()
    for k,v in TEAM_COLORS.items():
        if k.lower() in low or low in k.lower(): return v
    return "#B7FF4A","#F4A326"
def _elite(score):
    try: return float(score)>=78
    except Exception: return False
def _contrast(hex_color):
    try:
        h=hex_color.replace("#",""); r,g,b=int(h[:2],16),int(h[2:4],16),int(h[4:],16)
        return "#111" if (0.299*r+0.587*g+0.114*b)>155 else "#fff4e0"
    except Exception: return "#fff4e0"

def inject_css():
    st.markdown("""
<style>
.stApp{background:#050505;color:#f8eedf}
.block-container{max-width:1180px;padding-top:1rem}
h1,h2,h3,.title{font-family:Impact,'Arial Black',sans-serif;letter-spacing:.5px}
.stButton>button{min-height:64px;border-radius:22px;background:linear-gradient(90deg,#d8ff39,#00f47d,#f6a11a);color:#030303;border:0;font-size:22px;font-weight:900}
div[data-testid="stFileUploader"] section{background:#101010;border:2px solid #b7ff4a;border-radius:24px}
.machine{border:2px solid #333;border-radius:34px;padding:30px;background:linear-gradient(135deg,#111,#090909);margin:18px 0}
@keyframes elitePulse{from{filter:brightness(1)}to{filter:brightness(1.2);transform:translateY(-2px)}}
.player-card{border-radius:28px;padding:28px;margin:22px 0;color:#fff4e0}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.chip{border:1px solid;border-radius:999px;padding:8px 14px;font-weight:900}
.player-name{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(42px,8vw,78px);line-height:.96}
.score{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(58px,12vw,108px);line-height:1}
.bar{height:14px;background:#242424;border-radius:999px;overflow:hidden;margin:10px 0 20px}
.bar div{height:100%;border-radius:999px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.metrics div{background:#0b0b0bdd;border:1px solid #333;border-radius:16px;padding:14px}
.metrics b{display:block;font-size:24px}
.path{font-size:15px;line-height:1.5;font-weight:700;color:#efe7d5;margin-top:14px}
.hard{color:#ff9a9a}.soft{color:#ffe28a}

.v107-cockpit{
    border:2px solid #3a3a3a;border-radius:34px;padding:28px;margin:18px 0 26px;
    background:radial-gradient(circle at top left,#b7ff4a33,transparent 32%),linear-gradient(135deg,#101010,#050505 58%,#18240d);
    display:grid;grid-template-columns:1.25fr 1fr;gap:22px;align-items:center;
}
.v107-kicker{color:#b9b1a4;font-weight:800;letter-spacing:.08em;font-size:13px;margin-bottom:12px}
.v107-title{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(54px,11vw,118px);line-height:.86;color:#f8eedf;letter-spacing:1px}
.v107-title span{color:#caff3f;text-shadow:0 0 18px #caff3f55}
.v107-state{margin-top:18px;color:#0b0b0b;background:linear-gradient(90deg,#d8ff39,#00f47d,#f6a11a);display:inline-block;padding:10px 18px;border-radius:999px;font-weight:900}
.v107-cockpit-right{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.v107-dial{background:#0b0b0bdd;border:1px solid #303030;border-radius:22px;padding:20px;min-height:118px}
.v107-dial b{display:block;font-size:44px;color:#f8eedf;line-height:1}
.v107-dial span{display:block;margin-top:10px;color:#b9b1a4;font-weight:700}
@media(max-width:800px){.v107-cockpit{grid-template-columns:1fr}.v107-cockpit-right{grid-template-columns:repeat(2,1fr)}}

</style>
""", unsafe_allow_html=True)

def hero():
    st.markdown("<h1 class='title'>🔥 THE BLENDER MACHINE</h1><p>v97 PDF feed fixed · 19-gate run · no site bias · owner commit</p>", unsafe_allow_html=True)

def blender_machine(names, state="READY"):
    txt=", ".join(names) if names else "Feed data → Run Blender"
    st.markdown(f"<div class='machine'><h2>BLENDER MACHINE — {state}</h2><p>{txt}</p></div>", unsafe_allow_html=True)

def card(r):
    p,s=_colors(r.get("team",""))
    try: score=float(r.get("score",0) or 0)
    except Exception: score=0
    elite=_elite(score)
    anim="animation:elitePulse 1.25s infinite alternate;" if elite else ""
    glow=f"0 0 26px {s}" if elite else "none"
    fire="🔥 " if elite else ""
    txt=_contrast(p)
    st.markdown(f"""
<div class="player-card" style="border:2px solid {s};box-shadow:{glow};{anim};background:radial-gradient(circle at top left,{p}55,transparent 36%),linear-gradient(135deg,#101010,#141414 48%,{p}33)">
<div class="chips"><span class="chip" style="background:{p};color:{txt};border-color:{s}">{r.get('official_core_role','')}</span><span class="chip" style="background:#111;color:{s};border-color:{p}">{r.get('archetype','')}</span></div>
<div class="player-name" style="color:{txt};text-shadow:0 0 10px {p}">{fire}{r.get('player','')}</div>
<p><b style="color:{s}">{r.get('team','')}</b> · {r.get('game','')} · vs {r.get('pitcher','')}</p>
<div class="score" style="color:{s}">{score:.1f}</div>
<b>TRUE BLEND SCORE</b>
<div class="bar"><div style="width:{min(100,max(0,score))}%;background:linear-gradient(90deg,{p},{s})"></div></div>
<div class="metrics">
<div><b>{r.get('pull_pct','—')}</b><span>Pull</span></div><div><b>{r.get('sweet_spot_pct','—')}</b><span>Sweet</span></div><div><b>{r.get('barrel_pct','—')}</b><span>Barrel</span></div>
<div><b>{r.get('dmg','—')}</b><span>DMG</span></div><div><b>{r.get('hr_pa','—')}</b><span>HR/PA</span></div><div><b>{r.get('hpi','—')}</b><span>HPI</span></div>
</div>
<div class="path"><b>Blend path:</b> {r.get('gate_path','')}</div>
<div class="path hard">{('<b>Hard:</b> '+str(r.get('hard_fails',''))) if str(r.get('hard_fails','')).strip() else ''}</div>
<div class="path soft">{('<b>Soft:</b> '+str(r.get('soft_fails',''))) if str(r.get('soft_fails','')).strip() else ''}</div>
</div>
""", unsafe_allow_html=True)

def tickets_view(results, key_prefix="tickets"):
    st.markdown("## 🎟️ Tickets")
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"### {label}")
        df=results.get(key,pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
        if df is None or df.empty:
            st.info("No valid pass-gate legs in this bucket yet.")
        else:
            for _,r in df.iterrows(): card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{label.lower().replace(' ','_')}.csv", "text/csv", key=f"{key_prefix}_{key}_download")

def game_board_view(results, key_prefix="gb"):
    st.markdown("## GAME BOARD — GATE RESULTS")
    meta=results.get("meta",{}) if isinstance(results,dict) else {}
    owners=results.get("owners",pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
    survivors=results.get("survivors",pd.DataFrame()) if isinstance(results,dict) else pd.DataFrame()
    unique=f"{key_prefix}_{meta.get('engine_version','v97')}_{meta.get('input_rows',0)}_{meta.get('survivor_rows',0)}"
    if meta:
        c=st.columns(4)
        c[0].metric("Input Rows",meta.get("input_rows",0)); c[1].metric("Games",meta.get("games",0))
        c[2].metric("Owners Locked",meta.get("owners_locked",0)); c[3].metric("Survivor Rows",meta.get("survivor_rows",0))
        st.info(meta.get("message",""))
    if owners is not None and not owners.empty:
        st.markdown("### Locked Owners")
        for _,r in owners.iterrows(): card(r)
        st.download_button("Download Game Board CSV", csv_bytes(owners), "game_board.csv", "text/csv", key=f"{unique}_owners")
    if survivors is not None and not survivors.empty:
        st.markdown("### Survivors / Audit Board")
        cols=[c for c in ["page","raw_line_no","parse_note","game","game_key","player","team","pitcher","official_core_role","archetype","score","gate_grade","hard_fails","soft_fails","gate_path"] if c in survivors.columns]
        st.dataframe(survivors[cols],use_container_width=True,height=500)
        st.download_button("Download Survivors CSV", csv_bytes(survivors), "survivors.csv", "text/csv", key=f"{unique}_survivors")

def recap_view(results):
    st.markdown("## 2AM Recap")
    st.info("Recap hook ready. It checks locked owners only.")



# -------------------- v107 BLENDER VISUAL + COMPACT GAME BOARD --------------------
def blender_visual(results=None, feed_df=None, state="READY"):
    results = results or {}
    owners = results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    core = results.get("core", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    meta = results.get("meta", {}) if isinstance(results, dict) else {}

    feed_rows = 0 if feed_df is None or getattr(feed_df, "empty", True) else len(feed_df)
    games = meta.get("games", 0)
    locked = meta.get("owners_locked", 0)
    core_count = 0 if core is None or core.empty else len(core)

    st.markdown(f"""
    <div class="v107-cockpit">
        <div class="v107-cockpit-left">
            <div class="v107-kicker">19-GATE 4/27 RESET · NO SITE BIAS · ONE OWNER PER GAME</div>
            <div class="v107-title">THE<br><span>BLENDER</span><br>MACHINE</div>
            <div class="v107-state">STATE: {state}</div>
        </div>
        <div class="v107-cockpit-right">
            <div class="v107-dial"><b>{feed_rows}</b><span>Players Read</span></div>
            <div class="v107-dial"><b>{games}</b><span>Games</span></div>
            <div class="v107-dial"><b>{locked}</b><span>Owners Locked</span></div>
            <div class="v107-dial"><b>{core_count}</b><span>Core Legs</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def compact_game_board_view(results, key_prefix="gb_compact"):
    st.markdown("## 🧩 Game Board — Compact Owner Grid")
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    owners = results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    survivors = results.get("survivors", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    unique = f"{key_prefix}_{meta.get('engine_version','v107')}_{meta.get('input_rows',0)}_{meta.get('survivor_rows',0)}"

    if meta:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Input Rows", meta.get("input_rows", 0))
        c2.metric("Games", meta.get("games", 0))
        c3.metric("Owners Locked", meta.get("owners_locked", 0))
        c4.metric("Survivor Rows", meta.get("survivor_rows", 0))
        if meta.get("message"):
            st.info(meta.get("message"))

    board = owners if owners is not None and not owners.empty else survivors
    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    show_cols = [c for c in [
        "game","player","team","pitcher","official_core_role","archetype","score",
        "pull_pct","sweet_spot_pct","barrel_pct","dmg","hr_pa","hpi",
        "hard_fails","soft_fails"
    ] if c in board.columns]

    compact = board[show_cols].copy()
    if "score" in compact.columns:
        compact = compact.sort_values("score", ascending=False)

    st.dataframe(compact, use_container_width=True, height=720, hide_index=True)

    with st.expander("Full gate paths / audit details", expanded=False):
        detail_cols = [c for c in [
            "page","raw_line_no","parse_note","game","game_key","player","team","pitcher",
            "official_core_role","archetype","score","gate_grade","hard_fails","soft_fails","gate_path"
        ] if c in board.columns]
        st.dataframe(board[detail_cols], use_container_width=True, height=520, hide_index=True)

    st.download_button("Download Compact Game Board CSV", csv_bytes(compact), "compact_game_board.csv", "text/csv", key=f"{unique}_compact")
    st.download_button("Download Full Game Board CSV", csv_bytes(board), "full_game_board.csv", "text/csv", key=f"{unique}_full")
