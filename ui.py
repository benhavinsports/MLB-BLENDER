
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


.v108-ticket-card{overflow:hidden}
.v108-metrics{grid-template-columns:repeat(3,minmax(0,1fr))!important}
.v108-metrics div{min-width:0;overflow:hidden}
.v108-metrics b{font-size:clamp(20px,5vw,32px)!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v108-board-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:16px;margin-top:18px}
.v108-board-card{border:2px solid var(--team2);border-radius:24px;background:radial-gradient(circle at top left,var(--team1),transparent 45%),linear-gradient(135deg,#111,#050505);padding:18px;min-height:270px;box-shadow:0 0 12px #000;overflow:hidden}
.v108-board-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.v108-role{border:1px solid var(--team2);border-radius:999px;padding:7px 12px;font-weight:900;font-size:13px;background:#111;color:#f8eedf}
.v108-role.primary{background:#163b17}.v108-role.adj{background:#3b2c08}.v108-role.who{background:#3b0f18}.v108-role.audit{background:#222}
.v108-score{font-family:Impact,'Arial Black',sans-serif;font-size:34px;color:var(--team2)}
.v108-board-name{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(28px,7vw,46px);line-height:.95;color:#f8eedf;margin-top:16px;white-space:normal}
.v108-board-game{font-size:14px;color:#d8d0c1;margin-top:8px;line-height:1.25}
.v108-board-archetype{font-weight:900;color:var(--team2);margin-top:8px;font-size:14px}
.v108-mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:14px}
.v108-mini-grid div{background:#080808cc;border:1px solid #333;border-radius:12px;padding:8px;min-width:0}
.v108-mini-grid b{display:block;font-size:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#f8eedf}
.v108-mini-grid span{font-size:11px;color:#aaa}
.v108-flags{margin-top:12px;font-size:12px;color:#ffe28a;line-height:1.25;max-height:48px;overflow:hidden}


.v109-cockpit{border:2px solid #303030;border-radius:34px;padding:28px;margin:18px 0 26px;background:radial-gradient(circle at top left,#b7ff4a33,transparent 32%),linear-gradient(135deg,#101010,#050505 58%,#18240d);display:grid;grid-template-columns:1.2fr 1fr;gap:20px;align-items:center}
.v109-kicker{color:#b9b1a4;font-weight:800;letter-spacing:.08em;font-size:13px;margin-bottom:12px}
.v109-title{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(54px,11vw,118px);line-height:.86;color:#f8eedf}
.v109-title span{color:#caff3f;text-shadow:0 0 18px #caff3f55}
.v109-state{margin-top:18px;color:#050505;background:linear-gradient(90deg,#d8ff39,#00f47d,#f6a11a);display:inline-block;padding:10px 18px;border-radius:999px;font-weight:900}
.v109-dials{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.v109-dials div{background:#0b0b0bdd;border:1px solid #303030;border-radius:22px;padding:20px;min-height:112px}
.v109-dials b{display:block;font-size:42px;color:#f8eedf;line-height:1}
.v109-dials span{display:block;margin-top:10px;color:#b9b1a4;font-weight:700}
.v109-board-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:16px;margin:18px 0}
.v109-board-card{border:2px solid var(--team2);border-radius:24px;background:radial-gradient(circle at top left,var(--team1),transparent 45%),linear-gradient(135deg,#111,#050505);padding:18px;min-height:270px;box-shadow:0 0 12px #000;overflow:hidden}
.v109-card-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.v109-card-top span{border:1px solid var(--team2);border-radius:999px;padding:7px 12px;font-weight:900;font-size:13px;background:#111;color:#f8eedf}
.v109-card-top b{font-family:Impact,'Arial Black',sans-serif;font-size:34px;color:var(--team2)}
.v109-name{font-family:Impact,'Arial Black',sans-serif;font-size:clamp(30px,7vw,48px);line-height:.95;color:#f8eedf;margin-top:16px}
.v109-game{font-size:14px;color:#d8d0c1;margin-top:8px;line-height:1.25}
.v109-arch{font-weight:900;color:var(--team2);margin-top:8px;font-size:14px}
.v109-mini{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:14px}
.v109-mini div{background:#080808cc;border:1px solid #333;border-radius:12px;padding:8px;min-width:0}
.v109-mini b{display:block;font-size:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#f8eedf}
.v109-mini span{font-size:11px;color:#aaa}
.v109-flags{margin-top:12px;font-size:12px;color:#ffe28a;line-height:1.25;max-height:48px;overflow:hidden}
@media(max-width:800px){.v109-cockpit{grid-template-columns:1fr}.v109-dials{grid-template-columns:repeat(2,1fr)}}


.v112-dials{grid-template-columns:repeat(2,1fr)!important}
.v112-dials div:last-child{grid-column:1 / -1}


.v113-board{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px;margin-top:18px}
.v113-tile{border:2px solid var(--team2);border-radius:22px;padding:16px;background:radial-gradient(circle at top left,var(--team1),transparent 42%),linear-gradient(135deg,#101010,#050505);min-height:250px;overflow:hidden}
.v113-pool{font-size:12px;color:#c9c1b4;text-transform:uppercase;font-weight:900;letter-spacing:.05em;margin-bottom:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v113-owner-row{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.v113-owner{font-family:Impact,'Arial Black',sans-serif;font-size:34px;line-height:.95;color:#f8eedf}
.v113-sub{font-size:13px;color:#bbb;margin-top:5px;line-height:1.2}
.v113-score{font-family:Impact,'Arial Black',sans-serif;font-size:38px;color:var(--team2)}
.v113-lanes{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:14px}
.v113-lanes div{border:1px solid #333;border-radius:12px;padding:8px;background:#080808cc;text-align:center}
.v113-lanes b{display:block;font-size:10px;color:#aaa}
.v113-lanes span{font-weight:900;font-size:13px}
.v113-lanes .pass{border-color:#91ff4a}.v113-lanes .pass span{color:#91ff4a}
.v113-lanes .cut{border-color:#733}.v113-lanes .cut span{color:#ff7171}
.v113-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}
.v113-metrics div{background:#080808cc;border:1px solid #333;border-radius:12px;padding:8px;min-width:0}
.v113-metrics b{display:block;color:#f8eedf;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v113-metrics span{font-size:10px;color:#aaa}
.v113-flags{font-size:12px;color:#ffe28a;margin-top:10px;line-height:1.25;max-height:46px;overflow:hidden}

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



# -------------------- v108 VISUAL + GAME BOARD CARDS --------------------
def fmt_metric_v108(x):
    try:
        if x is None or pd.isna(x):
            return "—"
        val = float(x)
        if abs(val) >= 100:
            return f"{val:.0f}"
        if abs(val) >= 10:
            return f"{val:.1f}"
        return f"{val:.2f}".rstrip("0").rstrip(".")
    except Exception:
        s = str(x)
        return "—" if s.lower() in {"nan","none",""} else s[:8]

def board_card_v108(r):
    p, s = _colors(r.get("team",""))
    score = 0
    try:
        score = float(r.get("score",0) or 0)
    except Exception:
        pass
    role = str(r.get("official_core_role",""))
    role_class = "who" if "who" in role.lower() else ("adj" if "adj" in role.lower() else ("primary" if "primary" in role.lower() else "audit"))
    hard = str(r.get("hard_fails","")).strip()
    soft = str(r.get("soft_fails","")).strip()
    flags = hard if hard else soft
    flags = flags if flags else "{board_lane_summary(row)}"
    st.markdown(f"""
    <div class="v108-board-card" style="--team1:{p};--team2:{s};">
      <div class="v108-board-top">
        <span class="v108-role {role_class}">{role or 'Owner'}</span>
        <span class="v108-score">{score:.1f}</span>
      </div>
      <div class="v108-board-name">{r.get('player','')}</div>
      <div class="v108-board-game">{r.get('team','')} vs {r.get('pitcher','')}</div>
      <div class="v108-board-archetype">{r.get('archetype','')}</div>
      <div class="v108-mini-grid">
        <div><b>{fmt_metric_v108(r.get('pull_pct'))}</b><span>Pull</span></div>
        <div><b>{fmt_metric_v108(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div>
        <div><b>{fmt_metric_v108(r.get('barrel_pct'))}</b><span>Barrel</span></div>
        <div><b>{fmt_metric_v108(r.get('dmg'))}</b><span>DMG</span></div>
        <div><b>{fmt_metric_v108(r.get('hr_pa'))}</b><span>HR/PA</span></div>
        <div><b>{fmt_metric_v108(r.get('hpi'))}</b><span>HPI</span></div>
      </div>
      <div class="v108-flags">{flags}</div>
    </div>
    """, unsafe_allow_html=True)

def game_board_grid_view(results, key_prefix="gb_grid_v108"):
    st.markdown("## 🧩 GAME BOARD — OWNERS BY GAME")
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    owners = results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    survivors = results.get("survivors", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    board = owners if owners is not None and not owners.empty else survivors

    if meta:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Rows", meta.get("input_rows",0))
        c2.metric("Games", meta.get("games",0))
        c3.metric("Owners", meta.get("owners_locked",0))
        c4.metric("Survivors", meta.get("survivor_rows",0))
        if meta.get("message"):
            st.info(meta.get("message"))

    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    if "score" in board.columns:
        board = board.sort_values("score", ascending=False).copy()

    # Filter/search controls to make board usable without endless scrolling.
    q = st.text_input("Search player/team/pitcher", "", key=f"{key_prefix}_search")
    role_options = ["All"]
    if "official_core_role" in board.columns:
        role_options += sorted([str(x) for x in board["official_core_role"].dropna().unique()])
    role_filter = st.selectbox("Role filter", role_options, key=f"{key_prefix}_role")

    filtered = board.copy()
    if q:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    if role_filter != "All" and "official_core_role" in filtered.columns:
        filtered = filtered[filtered["official_core_role"].astype(str) == role_filter]

    st.markdown('<div class="v108-board-grid">', unsafe_allow_html=True)
    for _, r in filtered.head(60).iterrows():
        board_card_v108(r)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Full audit table + gate paths", expanded=False):
        detail_cols = [c for c in [
            "game","player","team","pitcher","official_core_role","archetype","score",
            "pull_pct","sweet_spot_pct","barrel_pct","dmg","hr_pa","hpi",
            "hard_fails","soft_fails","gate_path"
        ] if c in filtered.columns]
        st.dataframe(filtered[detail_cols], use_container_width=True, height=500, hide_index=True)

    st.download_button("Download Game Board CSV", csv_bytes(filtered), "game_board.csv", "text/csv", key=f"{key_prefix}_download")



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
<div class="player-card v108-ticket-card" style="border:2px solid {s};box-shadow:{glow};{anim};background:radial-gradient(circle at top left,{p}55,transparent 36%),linear-gradient(135deg,#101010,#141414 48%,{p}33)">
<div class="chips"><span class="chip" style="background:{p};color:{txt};border-color:{s}">{r.get('official_core_role','')}</span><span class="chip" style="background:#111;color:{s};border-color:{p}">{r.get('archetype','')}</span></div>
<div class="player-name" style="color:{txt};text-shadow:0 0 10px {p}">{fire}{r.get('player','')}</div>
<p><b style="color:{s}">{r.get('team','')}</b> · {r.get('game','')} · vs {r.get('pitcher','')}</p>
<div class="score" style="color:{s}">{score:.1f}</div>
<b>TRUE BLEND SCORE</b>
<div class="bar"><div style="width:{min(100,max(0,score))}%;background:linear-gradient(90deg,{p},{s})"></div></div>
<div class="metrics v108-metrics">
<div><b>{fmt_metric_v108(r.get('pull_pct'))}</b><span>Pull</span></div><div><b>{fmt_metric_v108(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div><div><b>{fmt_metric_v108(r.get('barrel_pct'))}</b><span>Barrel</span></div>
<div><b>{fmt_metric_v108(r.get('dmg'))}</b><span>DMG</span></div><div><b>{fmt_metric_v108(r.get('hr_pa'))}</b><span>HR/PA</span></div><div><b>{fmt_metric_v108(r.get('hpi'))}</b><span>HPI</span></div>
</div>
<div class="path"><b>Blend path:</b> {r.get('gate_path','')}</div>
<div class="path hard">{('<b>Hard:</b> '+str(r.get('hard_fails',''))) if str(r.get('hard_fails','')).strip() else ''}</div>
<div class="path soft">{('<b>Soft:</b> '+str(r.get('soft_fails',''))) if str(r.get('soft_fails','')).strip() else ''}</div>
</div>
""", unsafe_allow_html=True)



# -------------------- v109 FINAL VISUAL LAYOUT --------------------
def fmt_v109(x):
    try:
        if x is None or pd.isna(x):
            return "—"
        v = float(x)
        if abs(v) >= 100: return f"{v:.0f}"
        if abs(v) >= 10: return f"{v:.1f}"
        return f"{v:.2f}".rstrip("0").rstrip(".")
    except Exception:
        s = str(x)
        return "—" if s.lower() in {"nan","none",""} else s[:8]

def blender_visual(results=None, feed_df=None, state="READY"):
    results = results or {}
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    core = results.get("core", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    feed_rows = 0 if feed_df is None or getattr(feed_df, "empty", True) else len(feed_df)
    st.markdown(f"""
<div class="v109-cockpit">
  <div>
    <div class="v109-kicker">19-GATE 4/27 RESET · NO SITE BIAS · ONE OWNER PER GAME</div>
    <div class="v109-title">THE<br><span>BLENDER</span><br>MACHINE</div>
    <div class="v109-state">STATE: {state}</div>
  </div>
  <div class="v109-dials">
    <div><b>{feed_rows}</b><span>Players Read</span></div>
    <div><b>{meta.get('games',0)}</b><span>Games</span></div>
    <div><b>{meta.get('owners_locked',0)}</b><span>Owners</span></div>
    <div><b>{0 if core is None or core.empty else len(core)}</b><span>Core Legs</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

def _card_shell_v109(r, compact=False):
    p,s = _colors(r.get("team",""))
    try: score = float(r.get("score",0) or 0)
    except Exception: score = 0
    role = str(r.get("official_core_role","Owner"))
    flags = str(r.get("hard_fails","")).strip() or str(r.get("soft_fails","")).strip() or "{board_lane_summary(row)}"
    cls = "who" if "who" in role.lower() else ("adj" if "adj" in role.lower() else ("primary" if "primary" in role.lower() else "alt"))
    return f"""
<div class="v109-board-card {cls}" style="--team1:{p};--team2:{s};">
  <div class="v109-card-top"><span>{role}</span><b>{score:.1f}</b></div>
  <div class="v109-name">{r.get('player','')}</div>
  <div class="v109-game"><b>{r.get('team','')}</b> vs {r.get('pitcher','')}</div>
  <div class="v109-arch">{r.get('archetype','')}</div>
  <div class="v109-mini">
    <div><b>{fmt_v109(r.get('pull_pct'))}</b><span>Pull</span></div>
    <div><b>{fmt_v109(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div>
    <div><b>{fmt_v109(r.get('barrel_pct'))}</b><span>Barrel</span></div>
    <div><b>{fmt_v109(r.get('dmg'))}</b><span>DMG</span></div>
    <div><b>{fmt_v109(r.get('hr_pa'))}</b><span>HR/PA</span></div>
    <div><b>{fmt_v109(r.get('hpi'))}</b><span>HPI</span></div>
  </div>
  <div class="v109-flags">{flags}</div>
</div>
"""

def card(r):
    st.markdown(_card_shell_v109(r), unsafe_allow_html=True)
    with st.expander("Blend path", expanded=False):
        st.write(str(r.get("gate_path","")))

def tickets_view(results, key_prefix="tickets"):
    st.markdown("## 🎟️ Tickets")
    if not isinstance(results, dict):
        results = {}
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"### {label}")
        df = results.get(key, pd.DataFrame())
        if df is None or df.empty:
            st.info("No valid pass-gate legs in this bucket yet.")
            continue
        st.markdown('<div class="v109-board-grid">', unsafe_allow_html=True)
        for _,r in df.iterrows():
            st.markdown(_card_shell_v109(r), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button(f"Download {label}", csv_bytes(df), f"{label.lower().replace(' ','_')}.csv", "text/csv", key=f"{key_prefix}_{key}_download")

def game_board_grid_view(results, key_prefix="gb_v109"):
    st.markdown("## 🧩 GAME BOARD — OWNERS BY GAME")
    if not isinstance(results, dict):
        st.warning("Run the Blender first.")
        return
    meta = results.get("meta", {})
    owners = results.get("owners", pd.DataFrame())
    survivors = results.get("survivors", pd.DataFrame())
    board = owners if owners is not None and not owners.empty else survivors

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Rows", meta.get("input_rows",0))
    c2.metric("Games", meta.get("games",0))
    c3.metric("Owners", meta.get("owners_locked",0))
    c4.metric("Survivors", meta.get("survivor_rows",0))
    if meta.get("message"):
        st.info(meta.get("message"))

    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    if "score" in board.columns:
        board = board.sort_values("score", ascending=False).copy()

    q = st.text_input("Search player/team/pitcher", "", key=f"{key_prefix}_search")
    if q:
        mask = board.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        board = board[mask]

    st.markdown('<div class="v109-board-grid">', unsafe_allow_html=True)
    for _,r in board.head(72).iterrows():
        st.markdown(_card_shell_v109(r), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Full audit table + gate paths", expanded=False):
        cols = [c for c in ["game","player","team","pitcher","official_core_role","archetype","score","pull_pct","sweet_spot_pct","barrel_pct","dmg","hr_pa","hpi","hard_fails","soft_fails","gate_path"] if c in board.columns]
        st.dataframe(board[cols], use_container_width=True, height=520, hide_index=True)

    st.download_button("Download Game Board CSV", csv_bytes(board), "game_board.csv", "text/csv", key=f"{key_prefix}_download")



# -------------------- v112 ATTACK POOL COCKPIT FIX --------------------
def blender_visual(results=None, feed_df=None, state="READY"):
    results = results or {}
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    core = results.get("core", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    owners = results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    feed_rows = 0 if feed_df is None or getattr(feed_df, "empty", True) else len(feed_df)

    slate_games = meta.get("slate_games", 0) or meta.get("true_slate_games", 0) or 0
    attack_pools = meta.get("attack_pools", 0) or meta.get("games", 0) or 0
    owners_locked = 0 if owners is None or owners.empty else len(owners)
    core_count = 0 if core is None or core.empty else len(core)

    st.markdown(f"""
<div class="v109-cockpit">
  <div>
    <div class="v109-kicker">19-GATE 4/27 RESET · NO SITE BIAS · ONE OWNER PER ATTACK POOL</div>
    <div class="v109-title">THE<br><span>BLENDER</span><br>MACHINE</div>
    <div class="v109-state">STATE: {state}</div>
  </div>
  <div class="v109-dials v112-dials">
    <div><b>{feed_rows}</b><span>Players Read</span></div>
    <div><b>{slate_games}</b><span>Slate Games</span></div>
    <div><b>{attack_pools}</b><span>Attack Pools</span></div>
    <div><b>{owners_locked}</b><span>Owners</span></div>
    <div><b>{core_count}</b><span>Core Legs</span></div>
  </div>
</div>
""", unsafe_allow_html=True)



# -------------------- v113 TRUE GAME BOARD GRID --------------------
def _v113_has_pass(row, gate):
    return f"{gate.lower()}: pass" in str(row.get("gate_path","")).lower()

def _v113_status(row, role):
    path = str(row.get("gate_path","")).lower()
    soft = str(row.get("soft_fails","")).lower()
    if role == "Primary":
        ok = ("5 pull-air: pass" in path and "16 finisher: pass" in path and "5 pull-air" not in soft and "16 finisher" not in soft)
    elif role == "Adjacent":
        ok = ("10.5 adjacent: pass" in path and "10.5 adjacent" not in soft)
    elif role == "WHO":
        ok = ("11 who/chaos: pass" in path and "11 who/chaos" not in soft)
    else:
        ok = False
    return "PASS" if ok else "CUT"

def _v113_board_tile(group):
    g = group.sort_values("score", ascending=False).copy() if "score" in group.columns else group.copy()
    top = g.iloc[0]
    p, s = _colors(top.get("team",""))
    score = float(top.get("score",0) or 0)
    owner = top.get("player","")
    role = top.get("official_core_role","Owner")
    pool = f"{top.get('team','')} vs {top.get('pitcher','')}" if str(top.get("pitcher","")).strip() else top.get("game","")
    pitcher = top.get("pitcher","")
    team = top.get("team","")
    flags = str(top.get("hard_fails","")).strip() or str(top.get("soft_fails","")).strip() or "Clean lane"

    primary = _v113_status(top, "Primary")
    adjacent = _v113_status(top, "Adjacent")
    who = _v113_status(top, "WHO")

    primary_cls = "pass" if primary == "PASS" else "cut"
    adjacent_cls = "pass" if adjacent == "PASS" else "cut"
    who_cls = "pass" if who == "PASS" else "cut"

    st.markdown(f"""
<div class="v113-tile" style="--team1:{p};--team2:{s};">
  <div class="v113-pool">{pool}</div>
  <div class="v113-owner-row">
    <div>
      <div class="v113-owner">{owner}</div>
      <div class="v113-sub">{team} vs {pitcher}</div>
    </div>
    <div class="v113-score">{score:.1f}</div>
  </div>

  <div class="v113-lanes">
    <div class="{primary_cls}"><b>PRIMARY</b><span>{primary}</span></div>
    <div class="{adjacent_cls}"><b>ADJACENT</b><span>{adjacent}</span></div>
    <div class="{who_cls}"><b>WHO</b><span>{who}</span></div>
  </div>

  <div class="v113-metrics">
    <div><b>{fmt_v109(top.get('pull_pct'))}</b><span>Pull</span></div>
    <div><b>{fmt_v109(top.get('dmg'))}</b><span>DMG</span></div>
    <div><b>{fmt_v109(top.get('hr_pa'))}</b><span>HR/PA</span></div>
  </div>

  <div class="v113-flags">{flags}</div>
</div>
""", unsafe_allow_html=True)

def game_board_grid_view(results, key_prefix="gb_v113"):
    st.markdown("## 🧩 GAME BOARD — ATTACK POOL BOARD")
    if not isinstance(results, dict):
        st.warning("Run the Blender first.")
        return

    meta = results.get("meta", {})
    owners = results.get("owners", pd.DataFrame())
    survivors = results.get("survivors", pd.DataFrame())
    board = owners if owners is not None and not owners.empty else survivors

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Slate Games", meta.get("slate_games", 0))
    c2.metric("Attack Pools", meta.get("attack_pools", meta.get("games", 0)))
    c3.metric("Owners", meta.get("owners_locked", 0))
    c4.metric("Survivors", meta.get("survivor_rows", 0))

    if meta.get("message"):
        st.info(meta.get("message"))

    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    if "score" in board.columns:
        board = board.sort_values("score", ascending=False).copy()

    q = st.text_input("Search board", "", key=f"{key_prefix}_search")
    if q:
        mask = board.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        board = board[mask]

    key_col = "game_key" if "game_key" in board.columns else ("attack_pool_key" if "attack_pool_key" in board.columns else "game")
    st.markdown('<div class="v113-board">', unsafe_allow_html=True)
    for _, group in board.groupby(key_col, dropna=False):
        _v113_board_tile(group)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Full audit table + gate paths", expanded=False):
        cols = [c for c in [
            "game","game_key","attack_pool_key","player","team","pitcher","official_core_role",
            "archetype","score","hard_fails","soft_fails","gate_path"
        ] if c in board.columns]
        st.dataframe(board[cols], use_container_width=True, height=540, hide_index=True)

    st.download_button("Download Game Board CSV", csv_bytes(board), "game_board.csv", "text/csv", key=f"{key_prefix}_download")



# -------------------- v125 STALE RESULT WARNING HELPER --------------------
def stale_guard_status(results=None):
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    return meta.get("engine_version", "v125_NO_STALE_RESULTS_DAILY_ONLY")

# -------------------- v127 GAME BOARD STATUS OVERRIDE --------------------
def _v113_status(row, role):
    col = {"Primary":"primary_status","Adjacent":"adjacent_status","WHO":"who_status"}.get(role)
    if col and col in row:
        return str(row.get(col) or "CUT")
    return "OWNER" if str(row.get("event_role","")) == role else "CUT"

# -------------------- v130 GAME BOARD STATUS OVERRIDE --------------------
def _v113_status(row, role):
    col = {"Primary":"primary_status","Adjacent":"adjacent_status","WHO":"who_status"}.get(role)
    if col and col in row:
        return str(row.get(col) or "CUT")
    return "OWNER" if str(row.get("event_role","")) == role else "CUT"



# -------------------- v137 BOARD UI HELPERS --------------------
def board_lane_summary(row):
    return str(row.get("board_lane_label") or row.get("lane_note") or "")

def gate_trace_html(row):
    raw = str(row.get("gate_trace_full", ""))
    if not raw:
        return ""
    html = ["<div style='display:flex;flex-wrap:wrap;gap:6px;margin-top:10px'>"]
    for part in raw.split("|"):
        part = part.strip()
        if ":" not in part:
            continue
        label, status = part.rsplit(":", 1)
        status = status.strip().upper()
        color = "#7CFF6B" if status == "PASS" else "#FFD166" if status == "SOFT" else "#FF6B6B"
        html.append(f"<span style='border:1px solid {color};color:{color};border-radius:10px;padding:4px 8px;font-size:12px;font-weight:800'>{label.strip()}: {status}</span>")
    html.append("</div>")
    return "".join(html)



# -------------------- v140 BOARD-GAME RENDERER --------------------
def _v140_chip(label, status):
    status = str(status).strip().upper()
    color = "#7CFF6B" if status == "PASS" else "#FFD166" if status == "SOFT" else "#FF6B6B"
    return f"<span class='v140-chip' style='border-color:{color};color:{color}'>{label}<b>{status}</b></span>"

def _v140_trace_html(row):
    raw = str(row.get("gate_trace_full", ""))
    if not raw:
        return ""
    chips = []
    for part in raw.split("|"):
        part = part.strip()
        if ":" not in part:
            continue
        label, status = part.rsplit(":", 1)
        chips.append(_v140_chip(label.strip(), status.strip()))
    return "<div class='v140-path'>" + "".join(chips) + "</div>"

def _v140_card(row):
    p, s = _colors(row.get("team", ""))
    role = str(row.get("event_role") or row.get("official_core_role") or "Audit")
    role_class = "who" if role == "WHO" else "adj" if role == "Adjacent" else "primary" if role == "Primary" else "audit"
    try:
        score = float(row.get("score", 0) or 0)
    except Exception:
        score = 0.0
    lane = str(row.get("board_lane_label") or row.get("lane_note") or "")
    soft = str(row.get("soft_gates", ""))
    cut = str(row.get("cut_gates", ""))
    html = f"""
    <div class='v140-tile' style='--team1:{p};--team2:{s};'>
      <div class='v140-top'><span class='v140-role {role_class}'>{role}</span><span class='v140-score'>{score:.1f}</span></div>
      <div class='v140-name'>{row.get('player','')}</div>
      <div class='v140-game'>{row.get('team','')} vs {row.get('pitcher','')}</div>
      <div class='v140-lane'>{lane}</div>
      {_v140_trace_html(row)}
      <div class='v140-summary'><b>SOFT:</b> {soft or '—'}<br><b>CUT:</b> {cut or '—'}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def game_board_grid_view(results, key_prefix="gb_v140"):
    st.markdown("## 🧩 GAME BOARD — BLENDER PATH")
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    owners = results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    survivors = results.get("survivors", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    board = survivors if survivors is not None and not survivors.empty else owners

    if meta:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows", meta.get("input_rows", meta.get("players", 0)))
        c2.metric("Games", meta.get("games", 0))
        c3.metric("Owners", meta.get("owners_locked", 0))
        c4.metric("Survivors", meta.get("survivor_rows", len(board) if board is not None else 0))

    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    role_options = ["All"]
    role_col = "event_role" if "event_role" in board.columns else "official_core_role"
    if role_col in board.columns:
        role_options += sorted([str(x) for x in board[role_col].dropna().unique()])
    col1, col2 = st.columns([2, 1])
    q = col1.text_input("Search player/team/pitcher", "", key=f"{key_prefix}_search")
    role_filter = col2.selectbox("Role", role_options, key=f"{key_prefix}_role")

    filtered = board.copy()
    if q:
        filtered = filtered[filtered.astype(str).apply(lambda c: c.str.contains(q, case=False, na=False)).any(axis=1)]
    if role_filter != "All" and role_col in filtered.columns:
        filtered = filtered[filtered[role_col].astype(str) == role_filter]
    if "score" in filtered.columns:
        filtered = filtered.sort_values("score", ascending=False)

    st.markdown("""
    <style>
    .v140-board-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:14px}
    .v140-tile{background:linear-gradient(135deg,#0b0b0d,#151515 55%,var(--team1));border:2px solid var(--team2);border-radius:18px;padding:14px;box-shadow:0 0 16px #000;color:white}
    .v140-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
    .v140-role{font-weight:900;border:1px solid #fff;border-radius:999px;padding:4px 10px;font-size:12px}
    .v140-role.primary{color:#7CFF6B}.v140-role.adj{color:#FFD166}.v140-role.who{color:#FF6B6B}.v140-role.audit{color:#ccc}
    .v140-score{font-size:24px;font-weight:900;color:var(--team2)}
    .v140-name{font-size:22px;font-weight:950;letter-spacing:.3px}
    .v140-game{opacity:.9;font-size:13px;margin:4px 0 8px}
    .v140-lane{font-size:13px;font-weight:800;color:var(--team2);margin-bottom:8px}
    .v140-path{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
    .v140-chip{display:inline-flex;gap:6px;border:1px solid;border-radius:999px;padding:4px 7px;font-size:11px;font-weight:800}
    .v140-chip b{font-weight:950}
    .v140-summary{font-size:12px;line-height:1.4;margin-top:8px;background:#0008;border-radius:10px;padding:8px}
    </style>
    <div class='v140-board-grid'>
    """, unsafe_allow_html=True)
    for _, row in filtered.head(80).iterrows():
        _v140_card(row)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Full PASS / SOFT / CUT audit table", expanded=False):
        cols = [c for c in [
            "game","player","team","pitcher","event_role","official_core_role","archetype","score",
            "board_lane_label","pass_gates","soft_gates","cut_gates","gate_trace_full",
            "hard_fails","soft_fails","gate_path"
        ] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, height=520, hide_index=True)

    st.download_button("Download Game Board CSV", csv_bytes(filtered), "game_board.csv", "text/csv", key=f"{key_prefix}_download")


# -------------------- v142 CLEAN PRODUCTION BOARD RENDERER --------------------
def board_lane_summary(row):
    return str(row.get("board_lane_label") or row.get("lane_note") or "")

def gate_trace_html(row):
    raw = str(row.get("gate_trace_full", ""))
    if not raw:
        return ""
    chips = []
    for part in raw.split("|"):
        part = part.strip()
        if ":" not in part:
            continue
        label, status = part.rsplit(":", 1)
        status = status.strip().upper()
        color = "#7CFF6B" if status == "PASS" else "#FFD166" if status == "SOFT" else "#FF6B6B"
        chips.append(f"<span class='bh-chip' style='border-color:{color};color:{color}'>{label.strip()} <b>{status}</b></span>")
    return "<div class='bh-path'>" + "".join(chips) + "</div>"

def game_board_grid_view(results, key_prefix="game_board"):
    st.markdown("## 🧩 Game Board — Blender Path")
    if not isinstance(results, dict):
        st.warning("Run the Blender first.")
        return
    board = results.get("survivors", pd.DataFrame())
    if board is None or board.empty:
        board = results.get("owners", pd.DataFrame())
    if board is None or board.empty:
        st.warning("Run the Blender first.")
        return

    st.markdown("""
    <style>
    .bh-board{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:14px}
    .bh-tile{background:linear-gradient(135deg,#08080a,#171717);border:2px solid #444;border-radius:18px;padding:14px;color:white;box-shadow:0 0 16px #000}
    .bh-top{display:flex;justify-content:space-between;align-items:center}
    .bh-role{border:1px solid #fff;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900}
    .bh-score{font-size:24px;font-weight:950;color:#FFD166}
    .bh-name{font-size:22px;font-weight:950;margin-top:6px}
    .bh-game{font-size:13px;opacity:.85;margin-bottom:8px}
    .bh-lane{font-size:13px;font-weight:900;color:#FFD166;margin-bottom:6px}
    .bh-path{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
    .bh-chip{display:inline-flex;gap:5px;border:1px solid;border-radius:999px;padding:4px 7px;font-size:11px;font-weight:800}
    .bh-summary{font-size:12px;line-height:1.35;margin-top:8px;background:#0008;border-radius:10px;padding:8px}
    </style>
    """, unsafe_allow_html=True)

    q = st.text_input("Search Game Board", "", key=f"{key_prefix}_search")
    filtered = board.copy()
    if q:
        filtered = filtered[filtered.astype(str).apply(lambda c: c.str.contains(q, case=False, na=False)).any(axis=1)]
    if "score" in filtered.columns:
        filtered = filtered.sort_values("score", ascending=False)

    st.markdown("<div class='bh-board'>", unsafe_allow_html=True)
    for _, row in filtered.head(80).iterrows():
        html = f"""
        <div class='bh-tile'>
          <div class='bh-top'><span class='bh-role'>{row.get('event_role', row.get('official_core_role','Audit'))}</span><span class='bh-score'>{float(row.get('score',0) or 0):.1f}</span></div>
          <div class='bh-name'>{row.get('player','')}</div>
          <div class='bh-game'>{row.get('team','')} vs {row.get('pitcher','')}</div>
          <div class='bh-lane'>{board_lane_summary(row)}</div>
          {gate_trace_html(row)}
          <div class='bh-summary'><b>SOFT:</b> {row.get('soft_gates','—') or '—'}<br><b>CUT:</b> {row.get('cut_gates','—') or '—'}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Full Game Board audit table", expanded=False):
        cols = [c for c in ["game","player","team","pitcher","event_role","official_core_role","archetype","score","board_lane_label","pass_gates","soft_gates","cut_gates","gate_trace_full","hard_fails","soft_fails","gate_path"] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, height=520, hide_index=True)
    st.download_button("Download Game Board CSV", csv_bytes(filtered), "game_board.csv", "text/csv", key=f"{key_prefix}_download")
