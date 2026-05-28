
import html
import pandas as pd
import streamlit as st
from engine import csv_bytes


def _df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def _safe(v, default=""):
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    if v is None:
        return default
    s = str(v)
    return s if s.strip() else default


def _esc(v):
    return html.escape(_safe(v))


def inject_css():
    st.markdown('''
<style>
.stApp{background:#020202;color:#f5eadc;}
.block-container{max-width:1500px!important;padding-top:1.1rem!important;}
.big-title{font-size:78px;font-weight:1000;line-height:.92;letter-spacing:2px;margin:22px 0 34px 0;}
.big-title span{color:#b7ff32;}
button[kind="primary"], .stButton button{
  border-radius:42px!important;min-height:72px!important;
  background:linear-gradient(90deg,#b6ff3e,#00f59c,#ffa51e)!important;
  color:#050505!important;font-weight:900!important;border:0!important;font-size:19px!important;
}
.stDownloadButton button{border-radius:14px!important;background:#111827!important;color:#f5eadc!important;border:1px solid rgba(255,255,255,.13)!important;}
[data-testid="stFileUploader"]{background:rgba(255,255,255,.035);border-radius:18px;}
[data-testid="stMetric"]{background:rgba(12,18,28,.82);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:12px;}
[data-testid="stMetricValue"]{font-size:38px!important;color:#b7ff32!important;font-weight:950!important;}
.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px 0;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}

.board-scroll{width:100%;overflow-x:auto;padding:8px 0 18px;-webkit-overflow-scrolling:touch;}
.board-canvas{
  position:relative;width:1180px;height:770px;
  background:radial-gradient(circle at 50% 40%, rgba(255,255,255,.035), transparent 38%),linear-gradient(180deg,#05080d 0%,#020304 100%);
  border:1px solid rgba(255,255,255,.07);box-shadow:0 24px 70px rgba(0,0,0,.72);
  border-radius:8px;margin:0 auto;overflow:hidden;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;
}
.board-canvas:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent 0 49%,rgba(255,255,255,.025) 50%,transparent 51%),linear-gradient(0deg,transparent 0 49%,rgba(255,255,255,.018) 50%,transparent 51%);background-size:36px 36px;opacity:.28;pointer-events:none;}
.board-header{position:absolute;left:18px;right:18px;top:18px;height:62px;display:grid;grid-template-columns:280px 1fr 160px 160px 160px;gap:16px;align-items:center;z-index:5;}
.board-logo{display:flex;gap:12px;align-items:center;color:#fff6e7;font-weight:1000;letter-spacing:.7px;line-height:.95;font-size:22px;}
.board-logo-mark{width:44px;height:44px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.045);display:flex;align-items:center;justify-content:center;font-size:28px;box-shadow:0 0 24px rgba(64,150,255,.20);}
.board-menu{width:42px;height:42px;border-radius:8px;border:1px solid rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;color:#aeb7c5;margin-right:10px;}
.board-logo-wrap{display:flex;align-items:center;}
.top-stat{height:54px;background:rgba(8,12,18,.78);border:1px solid rgba(255,255,255,.11);border-radius:10px;color:#e7edf5;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:900;font-size:13px;line-height:1.15;}
.top-stat .green{color:#35ff63;font-size:23px;display:block;}
.road{position:absolute;left:58px;right:128px;height:122px;border:28px solid #020202;border-radius:80px;z-index:1;pointer-events:none;}
.road.r1{top:134px;border-left:0;border-top:0;}
.road.r2{top:322px;border-right:0;border-bottom:0;}
.road.r3{top:494px;border-left:0;border-top:0;right:220px;}
.arrow{position:absolute;color:white;font-size:44px;z-index:4;font-weight:1000;text-shadow:0 4px 10px rgba(0,0,0,.7);}
.arrow.a1{left:120px;top:180px;transform:rotate(225deg);}
.arrow.a2{left:585px;top:270px;}
.arrow.a3{right:185px;top:440px;transform:rotate(45deg);}
.tile{position:absolute;width:105px;height:92px;border-radius:5px;border:2px solid rgba(255,255,255,.92);color:white;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 7px 18px rgba(0,0,0,.46),inset 0 1px 0 rgba(255,255,255,.2);transform:skewX(-3deg);z-index:3;overflow:hidden;}
.tile:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.10),rgba(255,255,255,0));pointer-events:none;}
.tile-num{width:22px;height:22px;border-radius:50%;background:#fff8ef;color:#080d15;font-weight:1000;font-size:12px;display:flex;align-items:center;justify-content:center;margin-bottom:5px;z-index:2;}
.tile-label{font-size:11px;line-height:1.05;font-weight:1000;z-index:2;text-shadow:0 1px 3px rgba(0,0,0,.55);}
.t-blue{background:linear-gradient(160deg,#165be8,#083fa9);}
.t-red{background:linear-gradient(160deg,#ec2634,#9f111e);}
.t-orange{background:linear-gradient(160deg,#ff7a17,#c5460a);}
.t-green{background:linear-gradient(160deg,#25b955,#126c31);}
.t-purple{background:linear-gradient(160deg,#8b28d9,#551199);}
.start-tile{position:absolute;left:20px;top:114px;width:110px;height:92px;border-radius:7px;background:linear-gradient(160deg,#ffc527,#f59e0b);border:4px solid #fff8ef;color:white;font-size:31px;font-weight:1000;display:flex;align-items:center;justify-content:center;transform:rotate(-6deg);z-index:4;text-shadow:0 2px 7px rgba(0,0,0,.3);box-shadow:0 9px 20px rgba(0,0,0,.45);}
.finish-star{position:absolute;right:28px;top:456px;width:150px;height:138px;background:linear-gradient(160deg,#ffda30,#ff9900);clip-path:polygon(50% 0%,61% 25%,88% 13%,76% 39%,100% 50%,76% 61%,88% 87%,61% 75%,50% 100%,39% 75%,12% 87%,24% 61%,0% 50%,24% 39%,12% 13%,39% 25%);z-index:6;display:flex;align-items:center;justify-content:center;text-align:center;color:white;font-size:23px;font-weight:1000;line-height:1.05;filter:drop-shadow(0 8px 10px rgba(0,0,0,.55));text-shadow:0 2px 5px rgba(0,0,0,.28);}
.legend{position:absolute;left:410px;top:412px;width:360px;min-height:74px;background:rgba(4,8,14,.90);border:1px solid rgba(255,255,255,.15);border-radius:12px;z-index:5;color:#cfd7e5;font-size:10px;font-weight:800;padding:13px 16px;display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;}
.legend-title{grid-column:1/-1;color:white;font-size:10px;}
.dot{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:6px;vertical-align:-1px;}
.owner-row{position:absolute;left:16px;right:16px;top:618px;height:125px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;z-index:5;}
.owner-card{background:rgba(7,12,20,.86);border:1px solid rgba(255,255,255,.11);border-radius:10px;padding:14px 16px;color:#eaf0f8;box-shadow:0 12px 30px rgba(0,0,0,.4);overflow:hidden;}
.owner-card.core{border-top:3px solid #1769ff;}
.owner-card.alt{border-top:3px solid #e11d2f;}
.owner-card.who{border-top:3px solid #20b455;}
.owner-kicker{font-size:10px;font-weight:1000;letter-spacing:.5px;text-transform:uppercase;margin-bottom:8px;}
.owner-kicker.core{color:#347dff;}
.owner-kicker.alt{color:#ff3f4d;}
.owner-kicker.who{color:#4cff7d;}
.locked-pill{float:right;background:rgba(34,197,94,.18);border:1px solid rgba(92,255,120,.55);color:#d9ffdd;border-radius:999px;padding:4px 9px;font-size:9px;font-weight:1000;}
.owner-name{font-size:20px;font-weight:1000;color:white;margin-bottom:2px;}
.owner-role{font-size:11px;font-weight:850;color:#eef2f8;}
.owner-game{font-size:11px;color:#b9c2cf;line-height:1.22;}
.owner-vs{font-size:11px;font-weight:900;margin-top:7px;}
.owner-vs.core{color:#5aa2ff;}
.owner-vs.alt{color:#ff4c58;}
.owner-vs.who{color:#5cff82;}
.board-footer{position:absolute;left:16px;right:16px;bottom:12px;height:38px;border-top:1px solid rgba(255,255,255,.08);display:grid;grid-template-columns:1.1fr 1.1fr 1.2fr 1.2fr 1fr;gap:8px;color:#aab3c1;font-size:10px;align-items:center;z-index:5;}
.footer-item{border-left:1px solid rgba(255,255,255,.10);padding-left:14px;line-height:1.1;}
.footer-item b{display:block;color:#f4f8ff;font-size:11px;}
@media(max-width:800px){.big-title{font-size:58px;}.board-scroll{padding-bottom:12px;}}

.start-tile span{display:block;margin-top:4px;letter-spacing:.5px;}
.public-upload-box{
  background:rgba(8,12,18,.82);
  border:1px solid rgba(255,255,255,.10);
  border-radius:18px;
  padding:16px;
  margin:14px 0 18px;
  box-shadow:0 12px 30px rgba(0,0,0,.28);
}
.public-upload-title{
  font-weight:1000;
  font-size:22px;
  color:#f5eadc;
  margin-bottom:6px;
}
.public-upload-sub{
  color:#aab3c1;
  font-size:13px;
  margin-bottom:10px;
}


<style>
.board-shell{
    width:min(96vw,980px)!important;
    margin:auto!important;
    overflow:hidden!important;
}

.tile{
    width:82px!important;
    height:82px!important;
    border-radius:18px!important;
    font-size:10px!important;
    box-shadow:0 8px 18px rgba(0,0,0,.32)!important;
}

.tile-label{
    font-size:9px!important;
    line-height:1.1!important;
}

.owner-card{
    min-height:120px!important;
    padding:18px!important;
    margin-bottom:16px!important;
}

.footer-stats{
    position:relative!important;
    bottom:auto!important;
    margin-top:18px!important;
}

.legend{
    display:none!important;
}

.finish-star{
    transform:scale(.72)!important;
    right:8px!important;
    bottom:40px!important;
}

@media (max-width:768px){

.tile{
    width:64px!important;
    height:64px!important;
    border-radius:14px!important;
}

.tile-label{
    font-size:8px!important;
}

.finish-star{
    transform:scale(.58)!important;
    right:-12px!important;
}

}

/* REAL START-UPLOAD BUTTON */
.start-upload-zone{
  background:linear-gradient(160deg,#ffc527,#f59e0b);
  border:4px solid #fff8ef;
  color:#070707;
  border-radius:22px;
  padding:18px;
  margin:14px 0 18px;
  box-shadow:0 12px 28px rgba(0,0,0,.42);
}
.start-upload-title{
  font-size:30px;
  font-weight:1000;
  line-height:1;
  color:#070707;
}
.start-upload-sub{
  font-size:13px;
  font-weight:900;
  margin-top:6px;
  color:#111827;
}
.start-upload-zone [data-testid="stFileUploader"]{
  background:transparent!important;
  border:0!important;
  padding:0!important;
}
.start-upload-zone [data-testid="stFileUploader"] section{
  background:rgba(255,255,255,.18)!important;
  border:1px solid rgba(0,0,0,.18)!important;
  border-radius:16px!important;
}
.start-upload-zone [data-testid="stFileUploader"] button{
  background:#080808!important;
  color:#fff!important;
  border-radius:14px!important;
  font-weight:1000!important;
}

</style>

</style>
''', unsafe_allow_html=True)


def hero():
    st.markdown('<div class="big-title">THE<br><span>BLENDER</span><br>MACHINE</div>', unsafe_allow_html=True)


GATES = [
    (1,"Core<br>Matchup<br>Filter","t-blue",150,120),(2,"Vegas Line<br>Screen","t-red",255,120),(3,"Opponent<br>Starter<br>Screen","t-orange",360,120),(4,"Ballpark<br>Factor<br>Gate","t-purple",465,120),(5,"Weather<br>Gate","t-red",570,120),(6,"Plate<br>Discipline<br>Gate","t-orange",675,120),(7,"Hard Hit<br>% Gate","t-blue",780,120),(8,"Barrel<br>% Gate","t-green",885,120),(9,"wOBA<br>Gate","t-purple",1000,150),(10,"xwOBA<br>Gate","t-green",1000,250),(11,"ISO<br>Power<br>Gate","t-red",888,330),(12,"Pitches Per<br>PA Gate","t-green",783,330),(13,"Swing<br>% Gate","t-purple",678,330),(14,"Chase<br>% Gate","t-blue",573,330),(15,"K %<br>Contact<br>Gate","t-orange",468,330),(16,"Batted Ball<br>Profile<br>Gate","t-red",363,330),(17,"Clutch / Leverage<br>Opportunity<br>Gate","t-green",258,330),(18,"Lineup<br>Position<br>Gate","t-purple",54,330),(19,"Consistency<br>Stability<br>Gate","t-blue",54,430),(20,"Recent Form<br>Gate","t-orange",160,528),(21,"Fade / Low<br>EV Filter<br>Gate","t-red",313,528),(22,"Final<br>Survivor<br>Cut","t-purple",466,528),(23,"LIVE<br>BLENDER","t-green",619,528)
]


def _pick_row(results, key, fallback_index=0):
    df = _df(results.get(key)) if isinstance(results, dict) else pd.DataFrame()
    if not df.empty:
        return df.iloc[0].to_dict()
    core = _df(results.get("core")) if isinstance(results, dict) else pd.DataFrame()
    if not core.empty and len(core) > fallback_index:
        return core.iloc[fallback_index].to_dict()
    owners = _df(results.get("owners")) if isinstance(results, dict) else pd.DataFrame()
    if not owners.empty and len(owners) > fallback_index:
        return owners.iloc[fallback_index].to_dict()
    return {}


def _owner_html(row, cls, title, fallback_name, fallback_role):
    name = _esc(row.get("player", fallback_name))
    role = _esc(row.get("core_display_role", row.get("official_core_role", row.get("core_slot", fallback_role))))
    game = _esc(row.get("game_key", row.get("game", "Run Blender to lock owner")))
    time = _esc(row.get("game_time_et", ""))
    pitcher = _esc(row.get("pitcher", "—"))
    if time:
        game = f"{game}<br>{time}"
    return f'''
<div class="owner-card {cls}">
  <div class="owner-kicker {cls}">{title}<span class="locked-pill">LOCKED OWNER</span></div>
  <div class="owner-name">{name}</div>
  <div class="owner-role">{role}</div>
  <div class="owner-game">{game}</div>
  <div class="owner-vs {cls}">vs {pitcher}</div>
</div>
'''


def render_gameboard(results=None):
    results = results if isinstance(results, dict) else {}
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    total = _safe(meta.get("total_hitters", ""), "73")
    survivors = _safe(meta.get("owners_locked", ""), "3")
    version = _safe(meta.get("version", ""), "v270")
    slate = _safe(meta.get("slate_date", ""), "Today’s Slate")

    gate_html = "".join(
        f'<div class="tile {cls}" style="left:{x}px;top:{y}px;"><div class="tile-num">{n}</div><div class="tile-label">{label}</div></div>'
        for n, label, cls, x, y in GATES
    )

    core_row = _pick_row(results, "core", 0)
    alt_row = _pick_row(results, "alt", 1)
    who_row = _pick_row(results, "chaos", 2)

    owner_html = (
        _owner_html(core_row, "core", "CORE 1 · CLEAN LANE", "Pending Core", "Event Owner") +
        _owner_html(alt_row, "alt", "CORE 2 · ADJACENT / DECOY TRANSFER", "Pending ALT", "Adjacent / Decoy Transfer Owner") +
        _owner_html(who_row, "who", "CORE 3 · WHO / CHAOS", "Pending WHO", "WHO / Chaos Owner")
    )

    html_block = f'''
<div class="board-scroll">
  <div class="board-canvas">
    <div class="board-header">
      <div class="board-logo-wrap">
        <div class="board-menu">☰</div>
        <div class="board-logo"><div class="board-logo-mark">⚙</div><div>PUBLIC<br><span style="font-size:14px;">BLENDER BOARD</span></div></div>
      </div>
      <div class="top-stat">📅 &nbsp; {slate}</div>
      <div class="top-stat">Slate Games<span class="green">{total}</span></div>
      <div class="top-stat">Survivors<span class="green">{survivors}</span></div>
      <div class="top-stat">Engine<span class="green">LIVE</span></div>
    </div>
    <div class="road r1"></div><div class="road r2"></div><div class="road r3"></div>
    <div class="arrow a1">↳</div><div class="arrow a2">↑</div><div class="arrow a3">↰</div>
    <div class="start-tile">START</div>
    {gate_html}
    <div class="legend">
      <div class="legend-title">PUBLIC BOARD</div>
      <div><span class="dot" style="background:#1769ff"></span>Slate Matchups</div>
      <div><span class="dot" style="background:#e11d2f"></span>High Pressure Game</div>
      <div><span class="dot" style="background:#f97316"></span>Live Blender Path</div>
      <div><span class="dot" style="background:#20b455"></span>Owner Candidate</div>
      <div><span class="dot" style="background:#7c2bd0"></span>Chaos Watch</div>
      <div>🔒 Final Public Owners</div>
    </div>
    <div class="finish-star">FINISH<br>🔒<br>OWNERS</div>
    <div class="owner-row">{owner_html}</div>
    <div class="board-footer">
      <div class="footer-item">📅 <b>Blender Engine</b>{version}</div>
      <div class="footer-item">🛡️ <b>Live Engine</b>Protected</div>
      <div class="footer-item">🔒 <b>Immutable Mapping</b>Player ↔ Game Locked</div>
      <div class="footer-item">👥 <b>{total} Hitters Processed</b>{survivors} Survivors Remaining</div>
      <div class="footer-item">✅ <b>Owners Locked</b>Public Board</div>
    </div>
  </div>
</div>
'''
    st.markdown(html_block, unsafe_allow_html=True)


def blender_visual():
    results = st.session_state.get("results", {}) if hasattr(st, "session_state") else {}
    render_gameboard(results)


def card(r, extra=""):
    name = _safe(r.get("player", ""))
    role = r.get("core_slot", r.get("official_core_role", r.get("ticket_role", "")))
    display_role = _safe(r.get("core_display_role", role))
    game = _safe(r.get("game_key", r.get("game", "")))
    pitcher = _safe(r.get("pitcher", ""))
    score = _safe(r.get("blender_score", r.get("score", "")))
    arch = _safe(r.get("archetype", ""))
    time = _safe(r.get("game_time_et", ""))
    st.markdown(f'''
<div class="ticket-card">
  <div class="score-pill">{_esc(score)}</div>
  <div style="font-size:24px;font-weight:900">{_esc(name)}</div>
  <div style="opacity:.94;font-weight:800">{_esc(display_role)} · {_esc(arch)}</div>
  <div style="opacity:.82">{_esc(game)} {('· ' + _esc(time)) if time else ''}</div>
  <div style="opacity:.72">vs {_esc(pitcher)}</div>
  {('<div style="opacity:.75;margin-top:8px">'+html.escape(str(extra))+'</div>') if extra else ''}
</div>
''', unsafe_allow_html=True)


def _ticket_window_filter(df, window):
    df = _df(df).copy()
    if df.empty:
        return df
    if window != "Full slate" and "slate_window" in df.columns:
        labels = set(df["slate_window"].dropna().astype(str).str.lower().unique())
        if labels & {"early", "late"}:
            df = df[df["slate_window"].astype(str).str.lower() == window.lower()]
    return df


def tickets_view(results, key_prefix="tickets_locked"):
    st.markdown("## 🎟️ Tickets — LOCKED BLENDER")
    render_gameboard(results)
    window = st.selectbox("Slate window", ["Full slate", "Early", "Late"], key=f"{key_prefix}_window")
    buckets = [("CORE 3 — TRUE EVENT OWNERS", "core"),("ALT 3", "alt"),("CHAOS / WHO 3", "chaos")]
    for label, key in buckets:
        st.markdown(f"### {label}")
        df = _ticket_window_filter(_df(results.get(key) if isinstance(results, dict) else None), window)
        if df.empty:
            st.info("No surviving Blender path in this bucket.")
        else:
            for _, r in df.iterrows():
                card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_locked_blender.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")


def _gate_badge(row):
    result = str(row.get("result", ""))
    cls = "gate-pass" if result == "PASS" else "gate-cut"
    gate = str(row.get("gate", "Gate"))
    reason = str(row.get("reason", ""))
    value = row.get("value", "")
    return f'<span class="role-pill {cls}"><b>{html.escape(gate)}</b><br>{html.escape(result)} · {html.escape(str(value))}<br><span style="opacity:.72">{html.escape(reason[:70])}</span></span>'


def _path_card(player, rows, owner_row=None):
    rows = rows.sort_values("step") if "step" in rows.columns else rows
    first = rows.iloc[0] if not rows.empty else {}
    r = owner_row.iloc[0] if owner_row is not None and not owner_row.empty else first
    name = _safe(player)
    role = _safe(r.get("official_core_role", r.get("role", "")))
    game = _safe(r.get("game_key", ""))
    pitcher = _safe(r.get("pitcher", ""))
    score = _safe(r.get("blender_score", r.get("owner_state", "")))
    status = "SURVIVED" if str(role) not in {"CUT", "NO PICK", "NO PLAY"} else "CUT"
    badges = "".join(_gate_badge(gr) for _, gr in rows.iterrows())
    st.markdown(f'''
<div class="ticket-card">
  <div class="score-pill">{_esc(status)}<br>{_esc(score)}</div>
  <div style="font-size:22px;font-weight:900">{_esc(name)}</div>
  <div style="opacity:.88">{_esc(role)} · {_esc(game)}</div>
  <div style="opacity:.7">vs {_esc(pitcher)}</div>
  <div style="margin-top:12px;overflow-x:auto;white-space:nowrap">{badges}</div>
</div>
''', unsafe_allow_html=True)


def game_board_grid_view(results, key_prefix="gb_locked"):
    st.markdown("## 🧩 GAME BOARD — LOCKED ENGINE STATE")
    render_gameboard(results)
    if not isinstance(results, dict):
        st.info("Run the Blender first.")
        return
    meta = results.get("meta", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Owners", meta.get("owners_locked", 0))
    c2.metric("Pass Rows", meta.get("passed_rows", 0))
    c3.metric("Cuts", meta.get("cut_rows", 0))
    c4.metric("Core", meta.get("core_count", 0))
    if meta.get("message"):
        st.info(meta["message"])
    if meta.get("missing_core_roles"):
        st.warning("Core integrity: missing required role(s): " + str(meta.get("missing_core_roles")) + ". No duplicate refill was used.")
    env = _df(results.get("environment_board"))
    core = _df(results.get("core"))
    owners = _df(results.get("owners"))
    board = _df(results.get("game_board"))
    survivors = _df(results.get("survivors"))
    cuts = _df(results.get("cuts"))
    roles = _df(results.get("role_board"))

    st.markdown("### 1️⃣ Locked Attack Sides")
    st.dataframe(env, use_container_width=True, hide_index=True) if not env.empty else st.warning("No environment locks found.")

    st.markdown("### 2️⃣ Structured Core")
    if core.empty:
        st.warning("No complete Core paths survived. No generic refill was forced.")
    else:
        for _, r in core.iterrows():
            card(r)

    st.markdown("### 3️⃣ Owners by Game")
    if owners.empty:
        st.warning("No owners locked.")
    else:
        for _, r in owners.head(30).iterrows():
            card(r)

    st.markdown("### 4️⃣ Gate Path Board")
    if board.empty or "player" not in board.columns:
        st.info("No gate trace loaded.")
    else:
        view = st.radio("Board view", ["Owners first", "Cuts first", "All"], horizontal=True, key=f"{key_prefix}_view")
        if view == "Owners first" and not owners.empty:
            players = list(owners["player"].astype(str).head(25))
        elif view == "Cuts first" and not cuts.empty:
            players = list(cuts["player"].astype(str).head(25))
        else:
            players = list(board["player"].astype(str).drop_duplicates().head(40))
        for p in players:
            rows = board[board["player"].astype(str) == str(p)].copy()
            owner_row = owners[owners["player"].astype(str) == str(p)].copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
            _path_card(p, rows, owner_row)

    st.markdown("### 5️⃣ Pass Rows")
    passed = survivors[survivors["blender_eligible"] == True] if "blender_eligible" in survivors.columns else pd.DataFrame()
    if passed.empty:
        st.info("No pass rows.")
    else:
        for _, r in passed.head(30).iterrows():
            card(r, r.get("final_reason", ""))

    st.markdown("### 6️⃣ Cut Rows")
    if cuts.empty:
        st.info("No cut rows.")
    else:
        for _, r in cuts.head(30).iterrows():
            card(r, f"{r.get('stop_gate','')} · {r.get('final_reason','')}")

    with st.expander("Raw role memory", expanded=False):
        st.dataframe(roles, use_container_width=True, hide_index=True)
    with st.expander("Raw gate trace table", expanded=False):
        st.dataframe(board, use_container_width=True, hide_index=True)



def public_start_upload_panel():
    st.markdown("""
<div class="public-upload-box">
  <div class="public-upload-title">START · Upload PDF / Live Public Blender</div>
  <div class="public-upload-sub">The public board hides the private Blender formula. Upload a slate and run the live board.</div>
</div>
""", unsafe_allow_html=True)



def start_upload_header():
    st.markdown("""
<div class="start-upload-zone">
  <div class="start-upload-title">START</div>
  <div class="start-upload-sub">Upload PDF / CSV / XLSX and run Live Public Blender</div>
</div>
""", unsafe_allow_html=True)
