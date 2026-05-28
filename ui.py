
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
:root{--bg:#020202;--cream:#f5eadc;--lime:#b7ff32;--red:#ff5d67;--green:#69f08a;--blue:#347dff;}
.stApp{background:#020202;color:var(--cream);}
.block-container{max-width:1180px!important;padding-top:1rem!important;padding-left:1rem!important;padding-right:1rem!important;}
.big-title{font-size:70px;font-weight:1000;line-height:.90;letter-spacing:2px;margin:20px 0 26px;}
.big-title span{color:var(--lime);}
button[kind="primary"], .stButton button{border-radius:18px!important;min-height:54px!important;font-weight:950!important;border:1px solid rgba(255,255,255,.10)!important;white-space:normal!important;}
.stDownloadButton button{border-radius:14px!important;background:#111827!important;color:#f5eadc!important;border:1px solid rgba(255,255,255,.13)!important;}
[data-testid="stFileUploader"]{background:rgba(255,255,255,.045);border-radius:18px;padding:12px;}
[data-testid="stFileUploader"] section{background:rgba(255,255,255,.06)!important;border:1px solid rgba(255,255,255,.10)!important;border-radius:16px!important;}
[data-testid="stFileUploader"] button{background:#0b1020!important;color:#fff!important;border-radius:12px!important;font-weight:950!important;}
[data-testid="stTabs"] button{font-size:18px!important;font-weight:900!important;color:#f5eadc!important;}
[data-testid="stTabs"] [aria-selected="true"]{color:#ff6b6b!important;border-bottom-color:#ff6b6b!important;}
[data-testid="stMetric"]{background:#080c14;border:1px solid rgba(255,255,255,.09);border-radius:18px;padding:16px;}
[data-testid="stMetricValue"]{font-size:38px!important;color:var(--lime)!important;font-weight:1000!important;}

.start-upload-card{background:linear-gradient(160deg,#ffcd31,#ff9c0f);border:4px solid #fff8ef;border-radius:24px;padding:18px 20px;margin:12px 0 18px;color:#070707;box-shadow:0 16px 34px rgba(0,0,0,.45);}
.start-upload-title{font-size:40px;font-weight:1000;line-height:1;}
.start-upload-sub{font-size:15px;font-weight:950;margin-top:8px;}
.start-upload-card [data-testid="stFileUploader"]{margin-top:12px;background:rgba(0,0,0,.08)!important;padding:8px!important;}
.start-upload-card [data-testid="stFileUploader"] section{background:rgba(255,255,255,.22)!important;border:1px solid rgba(0,0,0,.18)!important;}
.start-upload-card [data-testid="stFileUploader"] button{background:#050505!important;color:#fff!important;}

.public-board{background:radial-gradient(circle at 20% 18%,rgba(52,125,255,.12),transparent 30%),linear-gradient(180deg,#080c14,#030406);border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:14px;box-shadow:0 24px 60px rgba(0,0,0,.56);overflow:hidden;margin:12px 0 18px;}
.board-head{display:flex;align-items:center;gap:10px;margin-bottom:12px;}
.board-mark{width:36px;height:36px;border-radius:12px;border:1px solid rgba(255,255,255,.13);display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.05);}
.board-title{font-size:24px;font-weight:1000;line-height:1.02;}
.board-title small{display:block;font-size:12px;letter-spacing:2px;color:#fff;}
.board-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 14px;}
.board-stat{background:rgba(7,11,18,.82);border:1px solid rgba(255,255,255,.09);border-radius:12px;padding:8px 10px;font-weight:900;text-align:center;}
.board-stat b{color:var(--lime);font-size:20px;}
.game-tile-note{color:#aab3c1;font-size:13px;margin:0 0 8px;}

div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button{
  width:100%!important;min-height:70px!important;border-radius:16px!important;
  background:linear-gradient(160deg,#185be8,#0b3caa)!important;color:#fff!important;
  font-size:11px!important;line-height:1.08!important;box-shadow:0 10px 22px rgba(0,0,0,.36)!important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) .stButton button{background:linear-gradient(160deg,#e92a38,#9f111e)!important;}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stButton button{background:linear-gradient(160deg,#ff7a17,#bd450a)!important;}

.selected-game-panel{background:rgba(7,11,18,.88);border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:14px;margin-top:12px;}
.owner-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px;}
.owner-card{background:rgba(8,13,22,.88);border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:14px;min-height:126px;}
.owner-card.core{border-top:4px solid var(--blue);}
.owner-card.alt{border-top:4px solid var(--red);}
.owner-card.who{border-top:4px solid var(--green);}
.owner-kicker{font-size:10px;font-weight:1000;letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px;}
.owner-kicker.core{color:#6aa2ff}.owner-kicker.alt{color:#ff6872}.owner-kicker.who{color:#78ff98}
.locked-pill{float:right;background:rgba(34,197,94,.15);border:1px solid rgba(92,255,120,.48);color:#d9ffdd;border-radius:999px;padding:4px 8px;font-size:9px;font-weight:1000;}
.owner-name{font-size:20px;font-weight:1000;color:white;margin-bottom:4px;}
.owner-role{font-size:12px;font-weight:900;color:#f5eadc;}
.owner-game{font-size:12px;color:#b9c2cf;line-height:1.3;margin-top:5px;}
.owner-vs{font-size:11px;font-weight:900;margin-top:7px;color:#88b5ff;}
.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px 0;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}
@media(max-width:700px){
  .block-container{padding-left:.75rem!important;padding-right:.75rem!important;}
  .big-title{font-size:52px;margin-bottom:20px;}
  .start-upload-title{font-size:32px;}
  .board-title{font-size:20px;}
  .board-stats{grid-template-columns:repeat(3,1fr);}
  div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button{min-height:60px!important;font-size:10px!important;border-radius:14px!important;}
  .owner-row{grid-template-columns:1fr;}
}
</style>
""", unsafe_allow_html=True)


def hero():
    st.markdown('<div class="big-title">THE<br><span>BLENDER</span><br>MACHINE</div>', unsafe_allow_html=True)


def start_upload_area():
    st.markdown("""
<div class="start-upload-card">
  <div class="start-upload-title">START</div>
  <div class="start-upload-sub">Upload PDF / CSV / XLSX or run Live Public Blender</div>
</div>
""", unsafe_allow_html=True)
    return st.file_uploader("Upload slate file", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed", key="start_upload_real_control")


def _game_label_from_row(row, idx):
    d = row if isinstance(row, dict) else {}
    game = _safe(d.get("game_key", d.get("game", "")), "")
    if game and game.lower() not in {"nan", "none", "—"}:
        return game
    team = _safe(d.get("team", ""), "")
    opp = _safe(d.get("opponent", ""), "")
    if team and opp:
        return f"{team} vs {opp}"
    return f"Game {idx}"


def _get_games(results=None):
    games, seen = [], set()
    feed = st.session_state.get("feed_df", pd.DataFrame()) if hasattr(st, "session_state") else pd.DataFrame()
    if isinstance(feed, pd.DataFrame) and not feed.empty:
        for _, r in feed.iterrows():
            d = r.to_dict()
            label = _game_label_from_row(d, len(games)+1)
            if label not in seen:
                seen.add(label); games.append({"label": label, "row": d})
    if not games and isinstance(results, dict):
        for key in ["owners","core","alt","chaos","environment_board","survivors"]:
            df = _df(results.get(key))
            if df.empty: continue
            for _, r in df.iterrows():
                d = r.to_dict()
                label = _game_label_from_row(d, len(games)+1)
                if label not in seen:
                    seen.add(label); games.append({"label": label, "row": d})
    if not games:
        games = [{"label": "Upload slate to build board", "row": {}}]
    return games


def _pick_row(results, key, fallback_index=0):
    df = _df(results.get(key)) if isinstance(results, dict) else pd.DataFrame()
    if not df.empty: return df.iloc[0].to_dict()
    core = _df(results.get("core")) if isinstance(results, dict) else pd.DataFrame()
    if not core.empty and len(core) > fallback_index: return core.iloc[fallback_index].to_dict()
    owners = _df(results.get("owners")) if isinstance(results, dict) else pd.DataFrame()
    if not owners.empty and len(owners) > fallback_index: return owners.iloc[fallback_index].to_dict()
    return {}


def _owner_html(row, cls, title, fallback_name, fallback_role):
    name = _esc(row.get("player", fallback_name))
    role = _esc(row.get("core_display_role", row.get("official_core_role", row.get("core_slot", fallback_role))))
    game = _esc(row.get("game_key", row.get("game", "Run Blender to lock owner")))
    time = _esc(row.get("game_time_et", ""))
    pitcher = _esc(row.get("pitcher", "—"))
    if time: game = f"{game}<br>{time}"
    return f"""
<div class="owner-card {cls}">
  <div class="owner-kicker {cls}">{title}<span class="locked-pill">LOCKED</span></div>
  <div class="owner-name">{name}</div>
  <div class="owner-role">{role}</div>
  <div class="owner-game">{game}</div>
  <div class="owner-vs">vs {pitcher}</div>
</div>
"""


def render_gameboard(results=None):
    results = results if isinstance(results, dict) else {}
    games = _get_games(results)
    meta = results.get("meta", {}) if isinstance(results, dict) else {}
    survivors = _safe(meta.get("owners_locked", ""), "—")
    actual_count = len(games) if games[0]["label"] != "Upload slate to build board" else 0
    st.markdown(f"""
<div class="public-board">
  <div class="board-head">
    <div class="board-mark">☰</div><div class="board-mark">⚙</div>
    <div class="board-title">PUBLIC<br><small>BLENDER BOARD</small></div>
  </div>
  <div class="board-stats">
    <div class="board-stat">Slate Games<br><b>{actual_count}</b></div>
    <div class="board-stat">Survivors<br><b>{survivors}</b></div>
    <div class="board-stat">Engine<br><b>LIVE</b></div>
  </div>
  <div class="game-tile-note">Click a game tile to inspect that matchup path. Private Blender formula stays hidden.</div>
</div>
""", unsafe_allow_html=True)

    cols_per_row = 2 if len(games) <= 8 else 3
    for start in range(0, len(games), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            i = start + j
            if i >= len(games): continue
            g = games[i]
            with cols[j]:
                if st.button(f"{i+1} · {g['label']}", key=f"game_tile_{i}_{g['label']}", use_container_width=True):
                    st.session_state["selected_public_game"] = g["label"]
    selected = st.session_state.get("selected_public_game", games[0]["label"] if games else "")
    st.markdown(f"""
<div class="selected-game-panel">
  <b>Selected Game:</b> {_esc(selected)}
  <br><span style="color:#aab3c1;font-size:13px;">After the Blender runs, CORE / ALT / WHO owners populate below.</span>
</div>
""", unsafe_allow_html=True)
    core_row = _pick_row(results, "core", 0)
    alt_row = _pick_row(results, "alt", 1)
    who_row = _pick_row(results, "chaos", 2)
    owners = _owner_html(core_row, "core", "CORE · CLEAN", "Pending Core", "Event Owner") + _owner_html(alt_row, "alt", "ALT · TRANSFER", "Pending ALT", "Adjacent / Decoy Transfer Owner") + _owner_html(who_row, "who", "WHO · CHAOS", "Pending WHO", "WHO / Chaos Owner")
    st.markdown(f'<div class="owner-row">{owners}</div>', unsafe_allow_html=True)


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
    if df.empty: return df
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
        if df.empty: st.info("No surviving Blender path in this bucket.")
        else:
            for _, r in df.iterrows(): card(r)
            st.download_button(f"Download {label}", csv_bytes(df), f"{key}_locked_blender.csv", "text/csv", key=f"{key_prefix}_{key}_{window}_{len(df)}")


def _gate_badge(row):
    result = str(row.get("result", ""))
    cls = "gate-pass" if result == "PASS" else "gate-cut"
    gate = str(row.get("gate", "Gate")); reason = str(row.get("reason", "")); value = row.get("value", "")
    return f'<span class="role-pill {cls}"><b>{html.escape(gate)}</b><br>{html.escape(result)} · {html.escape(str(value))}<br><span style="opacity:.72">{html.escape(reason[:70])}</span></span>'


def _path_card(player, rows, owner_row=None):
    rows = rows.sort_values("step") if "step" in rows.columns else rows
    first = rows.iloc[0] if not rows.empty else {}
    r = owner_row.iloc[0] if owner_row is not None and not owner_row.empty else first
    name = _safe(player); role = _safe(r.get("official_core_role", r.get("role", "")))
    game = _safe(r.get("game_key", "")); pitcher = _safe(r.get("pitcher", "")); score = _safe(r.get("blender_score", r.get("owner_state", "")))
    status = "SURVIVED" if str(role) not in {"CUT", "NO PICK", "NO PLAY"} else "CUT"
    badges = "".join(_gate_badge(gr) for _, gr in rows.iterrows())
    st.markdown(f"""
<div class="ticket-card">
  <div class="score-pill">{_esc(status)}<br>{_esc(score)}</div>
  <div style="font-size:22px;font-weight:900">{_esc(name)}</div>
  <div style="opacity:.88">{_esc(role)} · {_esc(game)}</div>
  <div style="opacity:.7">vs {_esc(pitcher)}</div>
  <div style="margin-top:12px;overflow-x:auto;white-space:nowrap">{badges}</div>
</div>
""", unsafe_allow_html=True)


def game_board_grid_view(results, key_prefix="gb_locked"):
    st.markdown("## 🧩 GAME BOARD — LOCKED ENGINE STATE")
    render_gameboard(results)
    if not isinstance(results, dict):
        st.info("Run the Blender first."); return
    meta = results.get("meta", {}) or {}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Owners", meta.get("owners_locked", 0)); c2.metric("Pass Rows", meta.get("passed_rows", 0)); c3.metric("Cuts", meta.get("cut_rows", 0)); c4.metric("Core", meta.get("core_count", 0))
    owners = _df(results.get("owners")); board = _df(results.get("game_board")); cuts = _df(results.get("cuts")); roles = _df(results.get("role_board"))
    st.markdown("### Owners by Game")
    if owners.empty: st.warning("No owners locked.")
    else:
        for _, r in owners.head(30).iterrows(): card(r)
    st.markdown("### Private Gate Path Board")
    if board.empty or "player" not in board.columns: st.info("No private gate trace loaded.")
    else:
        view = st.radio("Board view", ["Owners first","Cuts first","All"], horizontal=True, key=f"{key_prefix}_view")
        if view == "Owners first" and not owners.empty: players = list(owners["player"].astype(str).head(25))
        elif view == "Cuts first" and not cuts.empty: players = list(cuts["player"].astype(str).head(25))
        else: players = list(board["player"].astype(str).drop_duplicates().head(40))
        for p in players:
            rows = board[board["player"].astype(str) == str(p)].copy()
            owner_row = owners[owners["player"].astype(str) == str(p)].copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
            _path_card(p, rows, owner_row)
    with st.expander("Raw role memory", expanded=False): st.dataframe(roles, use_container_width=True, hide_index=True)
    with st.expander("Raw gate trace table", expanded=False): st.dataframe(board, use_container_width=True, hide_index=True)
