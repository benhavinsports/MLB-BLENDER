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
    st.markdown("""
<style>
:root{
  --cream:#f7ecdc;
  --lime:#b9ff37;
  --blue:#1f63ff;
  --red:#ef3340;
  --orange:#ff7a19;
  --green:#28c76f;
  --purple:#8f35e8;
  --dark:#020202;
  --panel:#070b12;
  --line:rgba(255,255,255,.13);
}
.stApp{background:#000;color:var(--cream);}
.block-container{max-width:1220px!important;padding:0.75rem 1rem 2rem!important;}
.big-title{font-size:68px;font-weight:1000;line-height:.89;letter-spacing:2px;margin:18px 0 22px;}
.big-title span{color:var(--lime);}
.stButton button{
  border-radius:18px!important;
  min-height:58px!important;
  font-weight:950!important;
  white-space:normal!important;
  border:1px solid rgba(255,255,255,.16)!important;
}
button[kind="primary"]{
  background:linear-gradient(90deg,#b7ff37,#00f0a0,#f5b533)!important;
  color:#050505!important;
  border:0!important;
}
.stDownloadButton button{border-radius:14px!important;background:#111827!important;color:var(--cream)!important;border:1px solid rgba(255,255,255,.13)!important;}
[data-testid="stMetric"]{background:#080c14;border:1px solid var(--line);border-radius:18px;padding:16px;}
[data-testid="stMetricValue"]{font-size:36px!important;color:var(--lime)!important;font-weight:1000!important;}

.start-zone{
  background:linear-gradient(160deg,#ffcf34,#f59e0b);
  border:4px solid #fff8ef;
  border-radius:24px;
  padding:18px 20px;
  margin:12px 0 18px;
  color:#070707;
  box-shadow:0 16px 34px rgba(0,0,0,.45);
}
.start-title{font-size:42px;font-weight:1000;line-height:1;}
.start-sub{font-size:15px;font-weight:950;margin-top:8px;}
.start-zone [data-testid="stFileUploader"]{margin-top:12px;background:rgba(0,0,0,.08)!important;padding:8px!important;border-radius:18px!important;}
.start-zone [data-testid="stFileUploader"] section{background:rgba(255,255,255,.22)!important;border:1px solid rgba(0,0,0,.18)!important;border-radius:16px!important;}
.start-zone [data-testid="stFileUploader"] button{background:#050505!important;color:#fff!important;border-radius:12px!important;font-weight:950!important;}

.board-shell{
  background:
    radial-gradient(circle at 55% 30%,rgba(255,255,255,.05),transparent 28%),
    linear-gradient(180deg,#060a10 0%,#010203 100%);
  border:1px solid rgba(255,255,255,.10);
  border-radius:18px;
  padding:14px;
  box-shadow:0 24px 70px rgba(0,0,0,.70);
  margin:14px 0 18px;
}
.board-head{
  display:grid;
  grid-template-columns:1.5fr .8fr .8fr .8fr;
  gap:10px;
  align-items:center;
  margin-bottom:12px;
}
.board-logo{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight:1000;
  font-size:22px;
  line-height:1;
}
.board-logo-mark{
  width:42px;height:42px;border-radius:13px;border:1px solid rgba(255,255,255,.14);
  display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.05);
}
.board-stat{
  background:rgba(7,11,18,.86);
  border:1px solid rgba(255,255,255,.12);
  border-radius:12px;
  padding:10px;
  text-align:center;
  font-weight:900;
  font-size:12px;
}
.board-stat b{display:block;color:var(--lime);font-size:22px;}
.board-note{color:#9ca7b8;font-size:13px;margin:6px 0 12px;}

.tile-blue button{background:linear-gradient(160deg,#2563eb,#1d4ed8)!important;color:white!important;}
.tile-red button{background:linear-gradient(160deg,#dc2626,#991b1b)!important;color:white!important;}
.tile-orange button{background:linear-gradient(160deg,#f97316,#c2410c)!important;color:white!important;}
.tile-purple button{background:linear-gradient(160deg,#9333ea,#6b21a8)!important;color:white!important;}
.tile-green button{background:linear-gradient(160deg,#22c55e,#15803d)!important;color:white!important;}
.tile-blue button,.tile-red button,.tile-orange button,.tile-purple button,.tile-green button{
  min-height:78px!important;
  font-size:12px!important;
  line-height:1.08!important;
  box-shadow:0 10px 22px rgba(0,0,0,.38)!important;
  border:2px solid rgba(255,255,255,.85)!important;
}
.core-glow button{box-shadow:0 0 0 2px #3b82f6,0 0 22px rgba(59,130,246,.65)!important;}
.alt-glow button{box-shadow:0 0 0 2px #ff5d67,0 0 22px rgba(255,93,103,.65)!important;}
.who-glow button{box-shadow:0 0 0 2px #69f08a,0 0 22px rgba(105,240,138,.65)!important;}

.selected-panel{
  background:rgba(7,11,18,.92);
  border:1px solid rgba(255,255,255,.12);
  border-radius:16px;
  padding:14px;
  margin-top:14px;
}
.owner-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;}
.owner-card{background:rgba(8,13,22,.92);border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:16px;min-height:140px;}
.owner-card.core{border-top:5px solid #347dff;box-shadow:0 0 22px rgba(52,125,255,.25);}
.owner-card.alt{border-top:5px solid #ff5d67;box-shadow:0 0 22px rgba(255,93,103,.25);}
.owner-card.who{border-top:5px solid #69f08a;box-shadow:0 0 22px rgba(105,240,138,.25);}
.owner-kicker{font-size:11px;font-weight:1000;letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px;}
.owner-kicker.core{color:#6aa2ff}.owner-kicker.alt{color:#ff6872}.owner-kicker.who{color:#78ff98}
.locked-pill{float:right;background:rgba(34,197,94,.15);border:1px solid rgba(92,255,120,.48);color:#d9ffdd;border-radius:999px;padding:4px 8px;font-size:9px;font-weight:1000;}
.owner-name{font-size:22px;font-weight:1000;color:white;margin-bottom:5px;}
.owner-role{font-size:13px;font-weight:900;color:var(--cream);}
.owner-game{font-size:12px;color:#b9c2cf;line-height:1.35;margin-top:6px;}
.owner-vs{font-size:12px;font-weight:900;margin-top:8px;color:#88b5ff;}

.detail-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;}
.detail-card{background:#090d16;border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:14px;}
.detail-card h4{margin:.1rem 0 .6rem;font-size:16px;}
.detail-pill{display:inline-block;border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:5px 9px;margin:3px;font-size:12px;background:rgba(255,255,255,.05);}
.pass{border-color:#69f08a;color:#bfffd0}.cut{border-color:#ff5d67;color:#ffc3c7}

.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px 0;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}

@media(max-width:760px){
  .block-container{padding-left:.75rem!important;padding-right:.75rem!important;}
  .big-title{font-size:48px;}
  .start-title{font-size:32px;}
  .board-head{grid-template-columns:1fr;gap:8px;}
  .tile-blue button,.tile-red button,.tile-orange button,.tile-purple button,.tile-green button{min-height:62px!important;font-size:10px!important;}
  .owner-row,.detail-grid{grid-template-columns:1fr;}
}
</style>
""", unsafe_allow_html=True)

def hero():
    st.markdown('<div class="big-title">THE<br><span>BLENDER</span><br>MACHINE</div>', unsafe_allow_html=True)

def start_upload_area():
    st.markdown('<div class="start-zone"><div class="start-title">START</div><div class="start-sub">Upload PDF / CSV / XLSX or run Live Public Blender</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload slate file", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed", key="start_upload_real_control")
    st.markdown('</div>', unsafe_allow_html=True)
    return uploaded

def _game_label(row, idx):
    d = row if isinstance(row, dict) else {}
    for col in ["game_key", "original_game_key", "game"]:
        val = _safe(d.get(col, ""), "")
        if val and val.lower() not in {"nan","none","—"}:
            return val
    team = _safe(d.get("team",""), "")
    opp = _safe(d.get("opponent",""), "")
    if team and opp:
        return f"{team} vs {opp}"
    return f"Game {idx}"

def _get_games(results=None):
    feed = st.session_state.get("feed_df", pd.DataFrame()) if hasattr(st, "session_state") else pd.DataFrame()
    games = []
    if isinstance(feed, pd.DataFrame) and not feed.empty:
        for key_col in ["game_pk","official_game_pk","game_id"]:
            if key_col in feed.columns:
                vals = [v for v in feed[key_col].dropna().astype(str).replace("nan","").unique().tolist() if str(v).strip()]
                if vals and len(vals) <= 30:
                    for v in vals:
                        row = feed[feed[key_col].astype(str)==str(v)].iloc[0].to_dict()
                        games.append({"label": _game_label(row, len(games)+1), "row": row})
                    return games
        for key_col in ["original_game_key","game_key"]:
            if key_col in feed.columns:
                vals = []
                for v in feed[key_col].dropna().astype(str).tolist():
                    if v and v.lower() not in {"nan","none"} and v not in vals:
                        vals.append(v)
                if vals and len(vals) <= 30:
                    for v in vals:
                        row = feed[feed[key_col].astype(str)==v].iloc[0].to_dict()
                        games.append({"label": v, "row": row})
                    return games
        if "team" in feed.columns and "opponent" in feed.columns:
            seen = set()
            for _, r in feed.iterrows():
                d = r.to_dict()
                a, b = sorted([_safe(d.get("team","")), _safe(d.get("opponent",""))])
                key = f"{a} vs {b}"
                if a and b and key not in seen:
                    seen.add(key)
                    games.append({"label": key, "row": d})
            if games:
                return games
    if isinstance(results, dict):
        seen = set()
        for key in ["owners","core","alt","chaos","environment_board","survivors"]:
            df = _df(results.get(key))
            if df.empty:
                continue
            for _, r in df.iterrows():
                d = r.to_dict()
                label = _game_label(d, len(games)+1)
                if label not in seen:
                    seen.add(label)
                    games.append({"label": label, "row": d})
        if games:
            return games
    return [{"label":"Upload slate to build board", "row":{}}]

def _all_owner_rows(results):
    rows = []
    if not isinstance(results, dict):
        return rows
    for role, key in [("CORE","core"),("ALT","alt"),("WHO","chaos")]:
        df = _df(results.get(key))
        if not df.empty:
            for _, r in df.iterrows():
                d = r.to_dict()
                d["_bucket"] = role
                rows.append(d)
    return rows

def _rows_for_game(results, label):
    rows = []
    for d in _all_owner_rows(results):
        g = _safe(d.get("game_key", d.get("game","")), "")
        if label and (label.lower() in g.lower() or g.lower() in label.lower()):
            rows.append(d)
    return rows

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
    return f"""
<div class="owner-card {cls}">
  <div class="owner-kicker {cls}">{title}<span class="locked-pill">LOCKED</span></div>
  <div class="owner-name">{name}</div>
  <div class="owner-role">{role}</div>
  <div class="owner-game">{game}</div>
  <div class="owner-vs">vs {pitcher}</div>
</div>
"""

def render_public_gameboard(results=None):
    results = results if isinstance(results, dict) else {}
    games = _get_games(results)
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    survivors = _safe(meta.get("owners_locked", ""), "—")
    actual_count = 0 if games and games[0]["label"] == "Upload slate to build board" else len(games)

    st.markdown(f"""
<div class="board-shell">
  <div class="board-head">
    <div class="board-logo"><div class="board-logo-mark">⚙</div><div>BLENDER<br><span style="font-size:12px;letter-spacing:2px;">GAMEBOARD</span></div></div>
    <div class="board-stat">Slate Games<b>{actual_count}</b></div>
    <div class="board-stat">Survivors<b>{survivors}</b></div>
    <div class="board-stat">Engine<b>LIVE</b></div>
  </div>
  <div class="board-note">Click a game tile to open hitter info, passed gates, weaknesses, and archetype notes. Private formula stays hidden.</div>
</div>
""", unsafe_allow_html=True)

    core_rows = _df(results.get("core")) if isinstance(results, dict) else pd.DataFrame()
    alt_rows = _df(results.get("alt")) if isinstance(results, dict) else pd.DataFrame()
    who_rows = _df(results.get("chaos")) if isinstance(results, dict) else pd.DataFrame()

    def glow_for(label):
        label_l = label.lower()
        if not core_rows.empty and "game_key" in core_rows.columns and core_rows["game_key"].astype(str).str.lower().str.contains(label_l, regex=False, na=False).any():
            return "core-glow"
        if not alt_rows.empty and "game_key" in alt_rows.columns and alt_rows["game_key"].astype(str).str.lower().str.contains(label_l, regex=False, na=False).any():
            return "alt-glow"
        if not who_rows.empty and "game_key" in who_rows.columns and who_rows["game_key"].astype(str).str.lower().str.contains(label_l, regex=False, na=False).any():
            return "who-glow"
        return ""

    cols_per_row = 2 if len(games) <= 8 else 3
    colors = ["tile-blue","tile-red","tile-orange","tile-purple","tile-green"]
    for start in range(0, len(games), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            i = start + j
            if i >= len(games):
                continue
            g = games[i]
            tile_class = f"{colors[i % len(colors)]} {glow_for(g['label'])}"
            with cols[j]:
                st.markdown(f'<div class="{tile_class}">', unsafe_allow_html=True)
                if st.button(f"{i+1} · {g['label']}", key=f"main_game_tile_{i}_{abs(hash(g['label']))}", use_container_width=True):
                    st.session_state["selected_public_game"] = g["label"]
                st.markdown("</div>", unsafe_allow_html=True)

    selected = st.session_state.get("selected_public_game", games[0]["label"] if games else "")
    st.markdown(f"""
<div class="selected-panel">
  <b>Selected Game:</b> {_esc(selected)}
  <br><span style="color:#aab3c1;font-size:13px;">CORE / ALT / WHO cards below show the current Blender owners. Click a tile for that game’s detail section.</span>
</div>
""", unsafe_allow_html=True)

    owners = (
        _owner_html(_pick_row(results,"core",0), "core", "CORE 3 · CLEAN GLOW", "Pending Core", "Event Owner") +
        _owner_html(_pick_row(results,"alt",1), "alt", "ALT 3 · TRANSFER GLOW", "Pending ALT", "Adjacent / Decoy Transfer Owner") +
        _owner_html(_pick_row(results,"chaos",2), "who", "CHAOS 3 · WHO GLOW", "Pending WHO", "WHO / Chaos Owner")
    )
    st.markdown(f'<div class="owner-row">{owners}</div>', unsafe_allow_html=True)

def render_selected_game_details(results=None):
    results = results if isinstance(results, dict) else {}
    selected = st.session_state.get("selected_public_game", "")
    if not selected:
        return
    st.markdown("## Selected Game Intel")
    related = _rows_for_game(results, selected)
    board = _df(results.get("game_board")) if isinstance(results, dict) else pd.DataFrame()
    game_board = pd.DataFrame()
    if not board.empty and "game_key" in board.columns:
        game_board = board[board["game_key"].astype(str).str.contains(str(selected), case=False, regex=False, na=False)].copy()

    if not related and game_board.empty:
        st.info("Run the Blender to populate hitter intel for this game.")
        return

    if related:
        st.markdown('<div class="detail-grid">', unsafe_allow_html=True)
        for d in related[:6]:
            st.markdown(f"""
<div class="detail-card">
  <h4>{_esc(d.get('player',''))}</h4>
  <div class="detail-pill">{_esc(d.get('_bucket','OWNER'))}</div>
  <div class="detail-pill">{_esc(d.get('core_display_role', d.get('official_core_role', d.get('core_slot',''))))}</div>
  <div class="detail-pill">{_esc(d.get('archetype',''))}</div>
  <p style="color:#b9c2cf;font-size:13px;margin-top:8px;">vs {_esc(d.get('pitcher',''))}</p>
</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if not game_board.empty:
        st.markdown("### Gate Trace / Passed-Cut Intel")
        show_cols = [c for c in ["player","gate","result","value","reason","archetype","weakness","final_reason"] if c in game_board.columns]
        if show_cols:
            st.dataframe(game_board[show_cols].head(80), use_container_width=True, hide_index=True)
        else:
            st.dataframe(game_board.head(80), use_container_width=True, hide_index=True)

def blender_visual():
    render_public_gameboard(st.session_state.get("results", {}) if hasattr(st, "session_state") else {})

# Legacy compatibility names
def render_gameboard(results=None, board_key="visual"):
    render_public_gameboard(results)

def card(r, extra=""):
    name = _safe(r.get("player", ""))
    role = r.get("core_slot", r.get("official_core_role", r.get("ticket_role", "")))
    display_role = _safe(r.get("core_display_role", role))
    game = _safe(r.get("game_key", r.get("game", "")))
    pitcher = _safe(r.get("pitcher", ""))
    score = _safe(r.get("blender_score", r.get("score", "")))
    arch = _safe(r.get("archetype", ""))
    time = _safe(r.get("game_time_et", ""))
    st.markdown(f"""
<div class="ticket-card">
  <div class="score-pill">{_esc(score)}</div>
  <div style="font-size:24px;font-weight:900">{_esc(name)}</div>
  <div style="opacity:.94;font-weight:800">{_esc(display_role)} · {_esc(arch)}</div>
  <div style="opacity:.82">{_esc(game)} {('· ' + _esc(time)) if time else ''}</div>
  <div style="opacity:.72">vs {_esc(pitcher)}</div>
  {('<div style="opacity:.75;margin-top:8px">'+html.escape(str(extra))+'</div>') if extra else ''}
</div>
""", unsafe_allow_html=True)

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
    window = st.selectbox("Slate window", ["Full slate", "Early", "Late"], key=f"{key_prefix}_window")
    for label, key in [("CORE 3 — TRUE EVENT OWNERS","core"),("ALT 3","alt"),("CHAOS / WHO 3","chaos")]:
        st.markdown(f"### {label}")
        df = _ticket_window_filter(_df(results.get(key) if isinstance(results, dict) else None), window)
        if df.empty:
            st.info("No surviving Blender path in this bucket.")
        else:
            for _, r in df.iterrows():
                card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_locked_blender.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")

def game_board_grid_view(results, key_prefix="gb_locked"):
    render_public_gameboard(results)
    render_selected_game_details(results)
