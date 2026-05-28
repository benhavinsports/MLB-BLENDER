
import pandas as pd
import streamlit as st
from engine import csv_bytes


def inject_css():
    st.markdown("""
<style>
.stApp{background:#050505;color:#f5eadc;}
.big-title{font-size:52px;font-weight:900;line-height:.95;letter-spacing:1px;margin:18px 0 26px 0;}
.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px 0;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}
button[kind="primary"], .stButton button{border-radius:28px!important;min-height:58px;background:linear-gradient(90deg,#b6ff3e,#00f59c,#ffa51e)!important;color:#050505!important;font-weight:800!important;border:0!important;}
[data-testid="stMetricValue"]{font-size:48px;}
</style>
""", unsafe_allow_html=True)


def hero():
    st.markdown('<div class="big-title">THE<br><span style="color:#b7ff32">BLENDER</span><br>MACHINE</div>', unsafe_allow_html=True)


def blender_visual():
    st.markdown("### Feed Data")


def _df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def card(r, extra=""):
    name = r.get("player", "")
    role = r.get("core_slot", r.get("official_core_role", r.get("ticket_role", "")))
    display_role = r.get("core_display_role", role)
    game = r.get("game_key", r.get("game", ""))
    pitcher = r.get("pitcher", "")
    score = r.get("blender_score", r.get("score", ""))
    arch = r.get("archetype", "")
    time = r.get("game_time_et", "")
    st.markdown(f"""
<div class="ticket-card">
  <div class="score-pill">{score}</div>
  <div style="font-size:24px;font-weight:900">{name}</div>
  <div style="opacity:.94;font-weight:800">{display_role} · {arch}</div>
  <div style="opacity:.82">{game} {('· ' + time) if time else ''}</div>
  <div style="opacity:.72">vs {pitcher}</div>
  {('<div style="opacity:.75;margin-top:8px">'+str(extra)+'</div>') if extra else ''}
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

    buckets = [
        ("CORE 3 — TRUE EVENT OWNERS", "core"),
        ("ALT 3", "alt"),
        ("CHAOS / WHO 3", "chaos"),
    ]

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
    return f'<span class="role-pill {cls}"><b>{gate}</b><br>{result} · {value}<br><span style="opacity:.72">{reason[:70]}</span></span>'


def _path_card(player, rows, owner_row=None):
    rows = rows.sort_values("step") if "step" in rows.columns else rows
    first = rows.iloc[0] if not rows.empty else {}
    r = owner_row.iloc[0] if owner_row is not None and not owner_row.empty else first
    name = player
    role = r.get("official_core_role", r.get("role", ""))
    game = r.get("game_key", "")
    pitcher = r.get("pitcher", "")
    score = r.get("blender_score", r.get("owner_state", ""))
    status = "SURVIVED" if str(role) not in {"CUT", "NO PICK", "NO PLAY"} else "CUT"
    badges = "".join(_gate_badge(gr) for _, gr in rows.iterrows())
    st.markdown(f"""
<div class="ticket-card">
  <div class="score-pill">{status}<br>{score}</div>
  <div style="font-size:22px;font-weight:900">{name}</div>
  <div style="opacity:.88">{role} · {game}</div>
  <div style="opacity:.7">vs {pitcher}</div>
  <div style="margin-top:12px;overflow-x:auto;white-space:nowrap">{badges}</div>
</div>
""", unsafe_allow_html=True)


def game_board_grid_view(results, key_prefix="gb_locked"):
    st.markdown("## 🧩 GAME BOARD — LOCKED ENGINE STATE")
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
    if env.empty:
        st.warning("No environment locks found.")
    else:
        st.dataframe(env, use_container_width=True, hide_index=True)

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


# =========================
# FINAL BLENDER UI UPGRADE
# =========================

BLENDER_UI_CONFIG = {
    "glassmorphism_tiles": True,
    "core_alt_who_hierarchy": True,
    "archetype_pills": True,
    "chaos_meter": True,
    "clickable_gameboard_tiles": True,
    "elimination_timeline_hooks": True,
    "live_flow_hooks": True,
    "ownership_tracking_hooks": True,
}

CUSTOM_CSS = '''
<style>
:root{
 --bg:#05070b;
 --panel:rgba(12,18,28,.74);
 --line:rgba(255,255,255,.08);
 --text:#f3f5f7;
 --muted:#9aa4b2;
 --core:#2dd4bf;
 --alt:#f59e0b;
 --who:#ef4444;
}

.stApp{
 background:
 radial-gradient(circle at top left, rgba(56,189,248,.10), transparent 28%),
 radial-gradient(circle at bottom right, rgba(249,115,22,.10), transparent 26%),
 #05070b;
 color:var(--text);
}

.blender-board{
 background:rgba(10,14,22,.72);
 border:1px solid rgba(255,255,255,.06);
 backdrop-filter: blur(18px);
 border-radius:22px;
 padding:20px;
 box-shadow:0 24px 60px rgba(0,0,0,.45);
}

.board-tile{
 background:rgba(20,26,38,.70);
 border:1px solid rgba(255,255,255,.08);
 backdrop-filter: blur(16px);
 border-radius:16px;
 padding:14px;
 transition:all .25s ease;
}

.board-tile:hover{
 transform:translateY(-2px);
 border-color:rgba(255,255,255,.16);
 box-shadow:0 14px 34px rgba(0,0,0,.32);
}

.core-card{
 border-left:4px solid var(--core);
}

.alt-card{
 border-left:4px solid var(--alt);
}

.who-card{
 border-left:4px solid var(--who);
}

.archetype-pill{
 display:inline-flex;
 align-items:center;
 padding:6px 12px;
 border-radius:999px;
 font-size:11px;
 font-weight:800;
 letter-spacing:.3px;
 background:rgba(255,255,255,.06);
 border:1px solid rgba(255,255,255,.08);
 margin-right:6px;
 margin-bottom:6px;
}

.chaos-meter{
 width:100%;
 height:10px;
 border-radius:999px;
 background:linear-gradient(90deg,#22c55e,#facc15,#ef4444);
 overflow:hidden;
}

.owner-lock{
 background:rgba(34,197,94,.12);
 border:1px solid rgba(34,197,94,.45);
 color:#d1fae5;
 border-radius:999px;
 padding:4px 10px;
 font-size:10px;
 font-weight:900;
}

.intelligence-panel{
 background:rgba(12,18,28,.60);
 border:1px solid rgba(255,255,255,.05);
 border-radius:18px;
 padding:16px;
 margin-top:12px;
}

.timeline-node{
 border-left:2px solid rgba(255,255,255,.10);
 padding-left:12px;
 margin:10px 0;
}

.live-pulse{
 animation:pulseGlow 2.2s infinite;
}

@keyframes pulseGlow{
 0%{box-shadow:0 0 0 rgba(59,130,246,0);}
 50%{box-shadow:0 0 24px rgba(59,130,246,.25);}
 100%{box-shadow:0 0 0 rgba(59,130,246,0);}
}
</style>
'''
