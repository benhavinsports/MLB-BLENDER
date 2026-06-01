
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from engine import csv_bytes


def _df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def inject_css():
    st.markdown("""
<style>
.stApp{background:#030407;color:#fff;}
.block-container{max-width:100vw!important;padding:0!important;margin:0!important;}
header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important;}
button[kind="primary"], .stButton button{
  border-radius:24px!important;
  min-height:56px!important;
  background:linear-gradient(90deg,#b6ff3e,#00f59c,#ffa51e)!important;
  color:#050505!important;
  font-weight:1000!important;
  border:0!important;
  box-shadow:0 0 20px rgba(183,255,60,.25)!important;
}
[data-testid="stFileUploader"]{
  background:rgba(5,10,18,.78)!important;
  border:1px solid rgba(255,255,255,.16)!important;
  border-radius:18px!important;
  padding:8px!important;
}
.machine-wrap{
  width:100%;
  min-height:660px;
  position:relative;
  background:radial-gradient(circle at 50% 34%,#17223b 0%,#070a10 39%,#020304 82%);
  overflow:hidden;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.machine-top{
  position:absolute;left:16px;right:16px;top:12px;height:58px;
  display:grid;grid-template-columns:230px 1fr 150px 150px 150px;gap:10px;z-index:8;
}
.machine-brand{display:flex;align-items:center;gap:10px;font-weight:1000;line-height:.9}
.machine-mark{width:46px;height:46px;border-radius:12px;background:#0b1220;border:1px solid rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:24px}
.machine-brand span{font-size:22px}.machine-brand small{letter-spacing:3px;font-size:10px;color:#b7c3d8}
.machine-pill{height:46px;border-radius:12px;background:#08101c;border:1px solid rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;text-align:center;font-size:12px;font-weight:900;color:#d9e6f7;padding:0 8px}
.machine-pill b{font-size:22px;color:#7dff9d;margin-left:6px}
.machine-start{position:absolute;left:18px;top:92px;width:136px;height:82px;background:linear-gradient(160deg,#ffe15b,#f59e0b);border:5px solid #fff;border-radius:12px;transform:rotate(-6deg);z-index:12;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:1000;text-shadow:0 3px 4px rgba(0,0,0,.35);color:white}
.machine-finish{position:absolute;right:45px;bottom:168px;width:124px;height:124px;background:#fbbf24;clip-path:polygon(50% 0%,61% 31%,94% 18%,74% 48%,100% 65%,67% 69%,79% 100%,50% 80%,21% 100%,33% 69%,0 65%,26% 48%,6% 18%,39% 31%);z-index:7;display:flex;align-items:center;justify-content:center;text-align:center;font-size:21px;font-weight:1000;text-shadow:0 2px 3px rgba(0,0,0,.25);color:white}
.machine-path{position:absolute;left:46px;right:46px;top:92px;bottom:170px;z-index:1}
.machine-path svg{width:100%;height:100%;overflow:visible}
.machine-tiles{position:absolute;inset:0;z-index:6}
.machine-node{position:absolute;width:126px;height:76px;border-radius:14px;background:#071224;border:3px solid rgba(255,255,255,.86);color:#fff;display:flex;flex-direction:column;justify-content:center;padding:9px;box-shadow:0 8px 14px rgba(0,0,0,.42)}
.machine-node.core{border-color:#60a5fa;box-shadow:0 0 24px rgba(59,130,246,.95),0 8px 14px rgba(0,0,0,.42)}
.machine-node.alt{border-color:#fb7185;box-shadow:0 0 24px rgba(239,68,68,.85),0 8px 14px rgba(0,0,0,.42)}
.machine-node.chaos{border-color:#4ade80;box-shadow:0 0 24px rgba(34,197,94,.88),0 0 18px rgba(168,85,247,.35),0 8px 14px rgba(0,0,0,.42)}
.machine-num{position:absolute;right:8px;top:7px;width:21px;height:21px;border-radius:999px;background:#fff;color:#08111f;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:1000}
.machine-bucket{font-size:9px;letter-spacing:.8px;font-weight:1000;text-transform:uppercase;color:#b7ff32;max-width:90px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.machine-owner{font-size:16px;font-weight:1000;line-height:1.02;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.machine-game{font-size:9px;color:#b8c4d8;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.machine-cards{position:absolute;left:14px;right:14px;bottom:36px;height:126px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;z-index:9}
.machine-card{background:#06101f;border:1px solid rgba(255,255,255,.15);border-radius:14px;padding:12px;position:relative;overflow:hidden}
.machine-card.core{box-shadow:0 0 22px rgba(59,130,246,.8);border-color:#2563eb}
.machine-card.alt{box-shadow:0 0 22px rgba(239,68,68,.72);border-color:#ef4444}
.machine-card.chaos{box-shadow:0 0 22px rgba(34,197,94,.72);border-color:#22c55e}
.machine-kicker{font-size:10px;letter-spacing:.8px;font-weight:1000;margin-bottom:5px}
.machine-cardname{font-size:22px;font-weight:1000;line-height:1;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:56px}
.machine-cardrole{font-size:11px;font-weight:900;color:#d7e2f0;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.machine-cardgame{font-size:10px;color:#aab3c1;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.machine-lock{position:absolute;right:10px;top:10px;border-radius:999px;background:rgba(34,197,94,.18);border:1px solid #67f08a;color:#d9ffdd;font-size:8px;font-weight:1000;padding:4px 7px}
.machine-footer{position:absolute;left:0;right:0;bottom:0;height:30px;background:#05080d;border-top:1px solid rgba(255,255,255,.10);display:grid;grid-template-columns:repeat(5,1fr);align-items:center;text-align:center;color:#aab3c1;font-size:9px;font-weight:900;z-index:12}
.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px 0;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}
@media(max-width:760px){
.machine-wrap{min-height:720px}.machine-top{left:7px;right:7px;top:6px;height:76px;grid-template-columns:1fr 1fr;gap:6px}
.machine-mark{width:34px;height:34px}.machine-brand span{font-size:16px}.machine-pill{height:32px;font-size:9px;border-radius:8px}.machine-pill b{font-size:15px}
.machine-start{left:9px;top:88px;width:92px;height:58px;border-width:3px;border-radius:9px;font-size:23px}.machine-path{left:4px;right:4px;top:126px;bottom:188px}
.machine-node{width:84px;height:58px;border-width:2px;border-radius:10px;padding:6px}.machine-num{width:15px;height:15px;font-size:8px;right:5px;top:5px}.machine-bucket{font-size:6px;max-width:62px}.machine-owner{font-size:11px}.machine-game{font-size:7px}
.machine-finish{right:18px;bottom:172px;width:78px;height:78px;font-size:13px}
.machine-cards{left:7px;right:7px;bottom:31px;height:134px;grid-template-columns:1fr;gap:6px}.machine-card{padding:8px;border-radius:10px}.machine-kicker{font-size:7px;margin-bottom:2px}.machine-cardname{font-size:14px}.machine-cardrole{font-size:8px;margin-top:2px}.machine-cardgame{font-size:7px}.machine-lock{font-size:6px;padding:2px 4px;right:6px;top:6px}
.machine-footer{height:26px;font-size:6px}
}
</style>
""", unsafe_allow_html=True)


def _records(x: Any) -> List[Dict[str, Any]]:
    if isinstance(x, pd.DataFrame):
        if x.empty:
            return []
        return x.where(pd.notnull(x), None).to_dict(orient="records")
    if isinstance(x, list):
        return [r for r in x if isinstance(r, dict)]
    return []


def _first(row: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() and str(v).lower() != "nan":
            return str(v).strip()
    return default


def _player(row):
    return _first(row, ["owner", "player", "hitter", "name"], "Waiting...")


def _game(row, idx=0):
    return _first(row, ["game_key", "original_game_key", "game", "matchup"], f"Game {idx+1}")


def hero():
    st.markdown('<div style="padding:12px 16px 0;font-size:42px;font-weight:1000;line-height:.9">THE <span style="color:#b7ff32">BLENDER</span> MACHINE</div>', unsafe_allow_html=True)


def _machine_tiles_from_results(results):
    results = results if isinstance(results, dict) else {}
    owners = _records(results.get("owners"))
    core = _records(results.get("core"))
    alt = _records(results.get("alt"))
    chaos = _records(results.get("chaos"))
    board = _records(results.get("game_board")) or _records(results.get("games"))

    role_map = {}
    for label, rows in [("CORE", core), ("ALT", alt), ("CHAOS", chaos)]:
        for i, r in enumerate(rows[:3]):
            role_map[_player(r).lower()] = f"{label} {i+1}"

    source = owners or core + alt + chaos or board
    tiles, seen = [], set()
    for idx, r in enumerate(source):
        player = _player(r)
        game = _game(r, idx)
        key = (player.lower(), game.lower())
        if key in seen:
            continue
        seen.add(key)
        bucket = role_map.get(player.lower(), _first(r, ["ticket_role", "official_core_role", "true_role_path", "role", "bucket"], "OWNER"))
        up = bucket.upper()
        glow = "core" if "CORE" in up else "alt" if "ALT" in up else "chaos" if ("CHAOS" in up or "WHO" in up) else ""
        tiles.append({
            "owner": player,
            "game": game,
            "bucket": bucket,
            "glow": glow,
        })

    if not tiles:
        for i in range(8):
            tiles.append({"owner": "Waiting...", "game": f"Game {i+1}", "bucket": "UPLOAD", "glow": ""})
    return tiles, core, alt, chaos


def _machine_card(rows, label, css, fallback):
    rows = _records(rows)
    r = rows[0] if rows else (fallback[0] if fallback else {})
    name = _player(r)
    game = _game(r, 0)
    role = _first(r, ["ticket_role", "official_core_role", "true_role_path", "role", "bucket"], label)
    return f"""
    <div class="machine-card {css}">
      <div class="machine-lock">LOCKED</div>
      <div class="machine-kicker">{label}</div>
      <div class="machine-cardname">{name}</div>
      <div class="machine-cardrole">{role}</div>
      <div class="machine-cardgame">{game}</div>
    </div>
    """


def blender_visual():
    results = st.session_state.get("results", {}) if hasattr(st, "session_state") else {}
    tiles, core, alt, chaos = _machine_tiles_from_results(results)
    coords = [[9,17],[24,13],[38,15],[52,20],[66,22],[79,28],[84,41],[74,52],[59,49],[45,47],[31,50],[16,58],[10,72],[25,79],[42,77],[59,76],[75,74],[64,62],[49,62],[35,64],[22,68],[52,34],[68,37]]
    nodes = []
    for i, t in enumerate(tiles[:23]):
        x, y = coords[i % len(coords)]
        nodes.append(f"""
        <div class="machine-node {t.get('glow','')}" style="left:{x}%;top:{y}%">
          <div class="machine-num">{i+1}</div>
          <div class="machine-bucket">{t.get('bucket','')}</div>
          <div class="machine-owner">{t.get('owner','')}</div>
          <div class="machine-game">{t.get('game','')}</div>
        </div>
        """)
    meta = results.get("meta", {}) if isinstance(results, dict) and isinstance(results.get("meta"), dict) else {}
    owners_count = meta.get("owners_locked", len([t for t in tiles if t.get("owner") != "Waiting..."]))
    core_count = meta.get("core_count", len(core))
    game_count = meta.get("games", len({t.get("game") for t in tiles}))
    st.markdown(f"""
<div class="machine-wrap">
  <div class="machine-top">
    <div class="machine-brand"><div class="machine-mark">☼</div><div><span>BLENDER</span><br><small>GAMEBOARD</small></div></div>
    <div class="machine-pill">Feed Data Below</div>
    <div class="machine-pill">Games <b>{game_count}</b></div>
    <div class="machine-pill">Owners <b>{owners_count}</b></div>
    <div class="machine-pill">Core <b>{core_count}</b></div>
  </div>
  <div class="machine-start">START</div>
  <div class="machine-path"><svg viewBox="0 0 1000 560" preserveAspectRatio="none">
    <path d="M90,75 C215,28 340,32 470,78 C610,128 720,120 830,170 C955,230 930,342 770,368 C635,390 510,340 380,350 C230,362 90,422 150,494 C210,558 470,528 820,510" stroke="#071015" stroke-width="78" fill="none" stroke-linecap="round"/>
    <path d="M90,75 C215,28 340,32 470,78 C610,128 720,120 830,170 C955,230 930,342 770,368 C635,390 510,340 380,350 C230,362 90,422 150,494 C210,558 470,528 820,510" stroke="#2cff88" stroke-width="8" fill="none" stroke-linecap="round" opacity=".72"/>
  </svg></div>
  <div class="machine-tiles">{''.join(nodes)}</div>
  <div class="machine-finish">FINISH</div>
  <div class="machine-cards">
    {_machine_card(core, "CORE 1", "core", tiles)}
    {_machine_card(alt, "ALT 1", "alt", tiles)}
    {_machine_card(chaos, "CHAOS 1", "chaos", tiles)}
  </div>
  <div class="machine-footer"><div>Original App Flow</div><div>Backend Untouched</div><div>Dynamic Tiles</div><div>Core / Alt / Chaos</div><div>Visual Only</div></div>
</div>
""", unsafe_allow_html=True)
    st.markdown("### Feed Data")


def card(r, extra=""):
    name = r.get("player", r.get("owner", ""))
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
    buckets = [("CORE 3 — TRUE EVENT OWNERS", "core"), ("ALT 3", "alt"), ("CHAOS 3", "chaos")]
    for title, key in buckets:
        st.markdown(f"### {title}")
        df = _ticket_window_filter(_df(results.get(key)), window) if isinstance(results, dict) else pd.DataFrame()
        if df.empty:
            st.info("No rows yet.")
        else:
            for _, r in df.head(3).iterrows():
                card(r.to_dict())


def _gate_badge(gate):
    gate = str(gate)
    css = "gate-pass" if "PASS" in gate.upper() or "TRUE" in gate.upper() else "gate-cut"
    return f'<span class="role-pill {css}">{gate}</span>'


def _path_card(r):
    d = r.to_dict() if hasattr(r, "to_dict") else dict(r)
    gates = d.get("gate_path", d.get("gates", ""))
    return f"""
<div class="ticket-card">
  <div style="font-size:20px;font-weight:900">{d.get('player', d.get('owner',''))}</div>
  <div style="opacity:.8">{d.get('game_key', d.get('game',''))}</div>
  <div style="margin-top:8px">{_gate_badge(gates)}</div>
</div>
"""


def game_board_grid_view(results):
    st.markdown("## 🧩 Game Board")
    if not isinstance(results, dict):
        st.info("No results yet.")
        return
    board = _df(results.get("game_board"))
    if board.empty:
        board = _df(results.get("owners"))
    if board.empty:
        st.info("No game board rows yet.")
        return
    st.dataframe(board, use_container_width=True, height=420)
    st.download_button("Download Game Board CSV", csv_bytes(board), "game_board.csv", "text/csv")
