
from __future__ import annotations
from typing import Any, Dict, List
import html
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from engine import csv_bytes
except Exception:
    def csv_bytes(df):
        return df.to_csv(index=False).encode("utf-8") if isinstance(df, pd.DataFrame) else b""

def _df(x): return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def _txt(x: Any) -> str:
    try:
        if x is None or pd.isna(x): return ""
    except Exception: pass
    return str(x).strip()

def _records(x: Any) -> List[Dict[str, Any]]:
    if isinstance(x, pd.DataFrame):
        if x.empty: return []
        return x.where(pd.notnull(x), None).to_dict(orient="records")
    if isinstance(x, list): return [r for r in x if isinstance(r, dict)]
    return []

def _first(row: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for k in keys:
        v=row.get(k)
        if _txt(v): return _txt(v)
    return default

def _player(row: Dict[str, Any]) -> str:
    return _first(row, ["owner","player","hitter","name"], "Waiting...")

def _game(row: Dict[str, Any], idx:int=0) -> str:
    return _first(row, ["game_key","original_game_key","game","matchup"], f"Game {idx+1}")

def inject_css():
    st.markdown("""
<style>
.stApp{background:#000;color:#fff;}
.block-container{max-width:100vw!important;padding:0!important;margin:0!important;}
header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important;}
/* START tile = upload trigger; hide separate upload box */
[data-testid="stFileUploader"]{
  position:fixed!important;left:10px!important;top:88px!important;width:108px!important;height:64px!important;
  opacity:.01!important;z-index:999999!important;margin:0!important;padding:0!important;overflow:hidden!important;
}
[data-testid="stFileUploader"] *{cursor:pointer!important;}
button[kind="primary"],.stButton button{border-radius:24px!important;min-height:54px!important;background:linear-gradient(90deg,#b6ff3e,#00f59c,#ffa51e)!important;color:#050505!important;font-weight:1000!important;border:0!important;}
.ticket-card{border:1px solid #2f2f2f;border-radius:22px;padding:18px;margin:14px;background:#0d0d0f;}
.score-pill{float:right;border:1px solid #a7ff3d;border-radius:16px;padding:12px 14px;color:#eaffcf;background:#182405;font-weight:900;}
.role-pill{display:inline-block;border:1px solid #444;border-radius:999px;padding:4px 9px;margin:4px 4px 4px 0;font-size:12px;}
.gate-pass{border-color:#b7ff3c!important;color:#dfffaa!important;background:rgba(183,255,60,.09)!important;}
.gate-cut{border-color:#ff5b61!important;color:#ffb3b6!important;background:rgba(255,91,97,.10)!important;}
</style>
""", unsafe_allow_html=True)

def hero():
    pass

def _rows(results):
    results = results if isinstance(results, dict) else {}
    owners=_records(results.get("owners")); core=_records(results.get("core")); alt=_records(results.get("alt")); chaos=_records(results.get("chaos"))
    board=_records(results.get("game_board")) or _records(results.get("games"))
    role={}
    for label, rows in [("CORE",core),("ALT",alt),("CHAOS",chaos)]:
        for i,r in enumerate(rows[:3]):
            role[_player(r).lower()] = f"{label} {i+1}"
    source=owners or core+alt+chaos or board
    tiles=[]; seen=set()
    for idx,r in enumerate(source):
        player=_player(r); game=_game(r,idx); key=(player.lower(),game.lower())
        if key in seen: continue
        seen.add(key)
        bucket=role.get(player.lower(), _first(r,["ticket_role","official_core_role","true_role_path","role","bucket"],f"GAME {idx+1}"))
        up=bucket.upper()
        glow="core" if "CORE" in up else "alt" if "ALT" in up else "chaos" if ("CHAOS" in up or "WHO" in up) else "game"
        tiles.append({"title":player,"game":game,"bucket":bucket,"glow":glow,"pitcher":_first(r,["pitcher","opposing_pitcher"],""),"role":_first(r,["ticket_role","official_core_role","true_role_path","role"],bucket),"weakness":_first(r,["final_reason","cut_reason","notes","parse_note"],"Blender details"),"gates":_first(r,["gate_path","gates","pass_depth"],"Hidden 23-gate formula")})
    if not tiles:
        for i in range(8):
            tiles.append({"title":f"Game {i+1}","game":"Upload slate","bucket":f"GAME {i+1}","glow":"game","pitcher":"","role":"Waiting","weakness":"Tap START to upload PDF.","gates":"Hidden 23-gate formula"})
    meta=results.get("meta",{}) if isinstance(results.get("meta"),dict) else {}
    return tiles,core,alt,chaos,meta.get("games",len(tiles)),meta.get("owners_locked",len([t for t in tiles if t["glow"] in ["core","alt","chaos"]])),meta.get("passed_rows",meta.get("hitters",len(tiles)))

def _card(rows,label,fallback):
    rows=_records(rows); r=rows[0] if rows else (fallback[0] if fallback else {})
    if isinstance(r,dict) and "title" in r:
        return {"label":label,"owner":r["title"],"role":r.get("role",label),"game":r.get("game",""),"pitcher":r.get("pitcher","")}
    return {"label":label,"owner":_player(r),"role":_first(r,["ticket_role","official_core_role","true_role_path","role","bucket"],label),"game":_game(r,0),"pitcher":_first(r,["pitcher","opposing_pitcher"],"")}

def blender_visual(results=None):
    if results is None: results=st.session_state.get("results",{}) or st.session_state.get("blender_results",{})
    tiles,core,alt,chaos,game_count,owners_count,hitters=_rows(results)
    n=max(1,min(len(tiles),23)); tiles=tiles[:n]
    coords=[(118,100),(196,100),(274,100),(352,101),(430,102),(508,104),(586,106),(664,110),(747,126),(805,176),(756,244),(678,252),(600,258),(522,262),(444,266),(366,270),(288,276),(210,286),(118,314),(86,394),(196,446),(344,452),(506,448)]
    colors=["#1d55e8","#d1332e","#e86f24","#702bb3","#c92d36","#e87420","#1d55e8","#2e9c42","#7326a2","#39a544","#b93331","#39a544","#7626a8","#1d55e8","#e87420","#b93030","#39a544","#7b2ab7","#1d55e8","#e87320","#c92d36","#7b2ab7","#39a143"]
    gates=[]; modal=[]
    for i,t in enumerate(tiles):
        x,y=coords[i]; color=colors[i%len(colors)]; glow=t.get("glow","game")
        cls=" core" if glow=="core" else " alt" if glow=="alt" else " chaos" if glow=="chaos" else ""
        title=html.escape(str(t.get("title",""))); game=html.escape(str(t.get("game",""))); bucket=html.escape(str(t.get("bucket","")))
        role=html.escape(str(t.get("role",""))); pitcher=html.escape(str(t.get("pitcher",""))); weakness=html.escape(str(t.get("weakness",""))); gate=html.escape(str(t.get("gates","")))
        modal.append({"title":title,"game":game,"bucket":bucket,"role":role,"pitcher":pitcher,"weakness":weakness,"gates":gate})
        gates.append(f'<button class="gate{cls}" style="left:{x}px;top:{y}px;background:{color};" onclick="openTile({i})"><span class="bubble">{i+1}</span><b>{bucket}</b><small>{title}</small></button>')
    c1=_card(core,"CORE 1 · CLEAN LANE",tiles); c2=_card(alt,"ALT 1 · NEXT MAN",tiles); c3=_card(chaos,"CHAOS 1 · WHO",tiles)
    def rc(d,css):
        return f'<button class="result-card {css}" onclick="openCard(\\\'{html.escape(d["owner"])}\\\',\\\'{html.escape(d["game"])}\\\',\\\'{html.escape(d["role"])}\\\',\\\'{html.escape(d["pitcher"])}\\\')"><div class="lock">LOCKED OWNER</div><div class="role">{html.escape(d["label"])}</div><div class="name">{html.escape(d["owner"])}</div><div class="sub">{html.escape(d["role"])}</div><div class="game-line">{html.escape(d["game"])}</div><div class="pitcher">{html.escape(d["pitcher"])}</div></button>'
    modal_json=str(modal).replace("</","<\\/")
    component=f"""
<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'/>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;background:#000;color:#fff;font-family:Arial,Helvetica,sans-serif;overflow:hidden}}.frame{{width:100%;height:100vh;background:#000;display:flex;justify-content:center;align-items:flex-start}}.board{{width:960px;height:515px;background:#020409;position:relative;overflow:hidden;transform-origin:top center}}
.top{{position:absolute;left:12px;right:12px;top:10px;height:58px;display:grid;grid-template-columns:245px 250px 145px 145px;gap:18px;align-items:center;z-index:5}}.brand{{display:flex;gap:10px;align-items:center;font-weight:900}}.logo{{width:42px;height:42px;border-radius:13px;border:1px solid rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-size:24px}}.brand-title{{font-size:21px;line-height:.9}}.brand-small{{font-size:10px;letter-spacing:2px;color:#d4d8e2}}.top-card{{height:42px;border:1px solid rgba(255,255,255,.17);background:#070d17;border-radius:9px;text-align:center;display:flex;align-items:center;justify-content:center;flex-direction:column;font-size:11px;font-weight:800;color:#dce7f7}}.top-card b{{font-size:21px;color:#76f184}}
.track-svg{{position:absolute;left:18px;top:76px;width:910px;height:350px;z-index:1}}.start{{position:absolute;left:16px;top:82px;width:96px;height:66px;z-index:6;background:linear-gradient(160deg,#ffe66d,#e5a91f);border:4px solid white;border-radius:9px;transform:rotate(-5deg);font-size:24px;color:white;font-weight:900;text-shadow:0 2px 4px #000;display:flex;align-items:center;justify-content:center}}.finish{{position:absolute;right:28px;top:310px;width:104px;height:104px;z-index:6;background:#f2bc2b;clip-path:polygon(50% 0%,61% 31%,94% 18%,74% 48%,100% 65%,67% 69%,79% 100%,50% 80%,21% 100%,33% 69%,0 65%,26% 48%,6% 18%,39% 31%);display:flex;align-items:center;justify-content:center;text-align:center;font-weight:900;font-size:21px;text-shadow:0 2px 3px #000}}
.gate{{position:absolute;width:74px;height:56px;z-index:5;border:2px solid rgba(255,255,255,.78);color:#fff;border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-weight:900;padding:3px;box-shadow:0 2px 8px rgba(0,0,0,.45);cursor:pointer}}.gate.core{{box-shadow:0 0 24px rgba(64,130,255,.95)}}.gate.alt{{box-shadow:0 0 24px rgba(255,60,60,.9)}}.gate.chaos{{box-shadow:0 0 24px rgba(55,255,105,.9),0 0 12px rgba(168,85,247,.55)}}.bubble{{position:absolute;top:3px;left:50%;transform:translateX(-50%);background:white;color:#111;width:18px;height:18px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:9px}}.gate b{{font-size:8px;margin-top:15px;line-height:1.05;max-height:18px;overflow:hidden}}.gate small{{font-size:6px;line-height:1;opacity:.95;max-height:18px;overflow:hidden}}
.legend{{position:absolute;left:360px;top:268px;width:220px;height:56px;border:1px solid rgba(255,255,255,.15);border-radius:10px;background:#03060d;z-index:7;padding:8px;font-size:7px;color:#cbd5e1}}.result-row{{position:absolute;left:12px;right:12px;bottom:40px;height:92px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;z-index:7}}.result-card{{text-align:left;background:#050a13;border:1px solid rgba(255,255,255,.14);border-radius:9px;padding:9px;position:relative;overflow:hidden;color:white;cursor:pointer}}.result-card.core{{box-shadow:0 0 18px rgba(59,130,246,.7);border-color:#1d4ed8}}.result-card.alt{{box-shadow:0 0 18px rgba(239,68,68,.7);border-color:#dc2626}}.result-card.chaos{{box-shadow:0 0 18px rgba(34,197,94,.7);border-color:#16a34a}}.lock{{position:absolute;right:8px;top:8px;border-radius:999px;background:#166534;color:white;padding:3px 7px;font-size:7px;font-weight:900}}.role{{font-size:9px;font-weight:900;margin-bottom:6px}}.name{{font-size:17px;font-weight:900;line-height:1;color:#fff}}.sub{{font-size:9px;font-weight:800;color:#d8e2f0;margin-top:5px}}.game-line{{font-size:8px;color:#c4ccd8;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.pitcher{{font-size:8px;color:#8be38e;margin-top:5px}}.foot{{position:absolute;left:0;right:0;bottom:0;height:32px;border-top:1px solid rgba(255,255,255,.09);display:grid;grid-template-columns:repeat(5,1fr);z-index:7;background:#03050a;color:#b8c1ce;font-size:8px;font-weight:800;text-align:center;align-items:center}}
.modal{{display:none;position:absolute;left:80px;right:80px;top:90px;z-index:30;background:#040812;border:1px solid rgba(255,255,255,.25);border-radius:18px;box-shadow:0 0 55px rgba(0,0,0,.9);padding:20px}}.modal.show{{display:block}}.modal h2{{margin:0;font-size:28px}}.modal p{{font-size:13px;color:#d9e2ef;line-height:1.35}}.close{{position:absolute;right:14px;top:10px;background:transparent;border:0;color:white;font-size:26px;cursor:pointer}}
@media(max-width:760px){{.board{{transform:scale(calc(100vw / 960));}}}}
</style></head><body><div class='frame'><div class='board'><div class='top'><div class='brand'><div class='logo'>☼</div><div><div class='brand-title'>BLENDER</div><div class='brand-small'>GAMEBOARD</div></div></div><div class='top-card'>Today’s Slate<br><span>Live Feed</span></div><div class='top-card'>Total Hitters <b>{hitters}</b></div><div class='top-card'>Survivors <b>{owners_count}</b></div></div><div class='start'>START</div><svg class='track-svg' viewBox='0 0 910 350'><path d='M82 58 C248 18 452 30 680 54 C850 72 876 154 742 176 C558 206 352 155 156 196 C32 222 25 322 188 337 C367 355 596 328 806 330' fill='none' stroke='#030608' stroke-width='64' stroke-linecap='round'/><path d='M82 58 C248 18 452 30 680 54 C850 72 876 154 742 176 C558 206 352 155 156 196 C32 222 25 322 188 337 C367 355 596 328 806 330' fill='none' stroke='white' stroke-width='5' stroke-linecap='round'/></svg>{''.join(gates)}<div class='legend'>LEGEND<br>🔵 Matchup & Environment &nbsp;&nbsp; 🔴 Offense Quality<br>🟠 Plate Discipline &nbsp;&nbsp; 🟢 Power / Contact Quality<br>🟣 Context & Consistency &nbsp;&nbsp; 🔒 Final Selection</div><div class='finish'>FINISH<br><span style='font-size:43%'>LOCKED<br>OWNERS</span></div><div class='result-row'>{rc(c1,'core')}{rc(c2,'alt')}{rc(c3,'chaos')}</div><div class='foot'><div>Blender Engine</div><div>23-Gate Progression</div><div>Immutable Mapping</div><div>{hitters} Players Processed</div><div>Owners Locked</div></div><div id='modal' class='modal'><button class='close' onclick='closeModal()'>×</button><div id='modalContent'></div></div></div></div><script>const modalItems={modal_json};function openTile(i){{const t=modalItems[i]||{{}};document.getElementById('modalContent').innerHTML=`<h2>${{t.title||'Game'}}</h2><p><b>${{t.bucket||''}}</b><br>${{t.game||''}}</p><p><b>Role:</b> ${{t.role||''}}<br><b>Pitcher:</b> ${{t.pitcher||''}}</p><p><b>Weakness:</b> ${{t.weakness||''}}</p><p><b>Gates:</b> ${{t.gates||''}}</p>`;document.getElementById('modal').classList.add('show');}}function openCard(owner,game,role,pitcher){{document.getElementById('modalContent').innerHTML=`<h2>${{owner}}</h2><p>${{game}}</p><p><b>Role:</b> ${{role}}<br><b>Pitcher:</b> ${{pitcher}}</p>`;document.getElementById('modal').classList.add('show');}}function closeModal(){{document.getElementById('modal').classList.remove('show');}}</script></body></html>"""
    components.html(component, height=535, scrolling=False)

def card(r, extra=""):
    name=r.get("player",r.get("owner","")); role=r.get("core_slot",r.get("official_core_role",r.get("ticket_role",""))); display_role=r.get("core_display_role",role); game=r.get("game_key",r.get("game","")); pitcher=r.get("pitcher",""); score=r.get("blender_score",r.get("score","")); arch=r.get("archetype",""); time=r.get("game_time_et","")
    time_part = ("· " + str(time)) if time else ""
    extra_html = ("<div style='opacity:.75;margin-top:8px'>" + str(extra) + "</div>") if extra else ""
    st.markdown(
        f"<div class='ticket-card'><div class='score-pill'>{score}</div><div style='font-size:24px;font-weight:900'>{name}</div>"
        f"<div style='opacity:.94;font-weight:800'>{display_role} · {arch}</div><div style='opacity:.82'>{game} {time_part}</div>"
        f"<div style='opacity:.72'>vs {pitcher}</div>{extra_html}</div>",
        unsafe_allow_html=True,
    )

def _ticket_window_filter(df, window):
    df=_df(df).copy()
    if df.empty: return df
    if window!="Full slate" and "slate_window" in df.columns:
        labels=set(df["slate_window"].dropna().astype(str).str.lower().unique())
        if labels & {"early","late"}: df=df[df["slate_window"].astype(str).str.lower()==window.lower()]
    return df

def tickets_view(results, key_prefix="tickets_locked"):
    st.markdown("## 🎟️ Tickets — LOCKED BLENDER")
    window=st.selectbox("Slate window",["Full slate","Early","Late"],key=f"{key_prefix}_window")
    for title,key in [("CORE 3 — TRUE EVENT OWNERS","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"### {title}")
        df=_ticket_window_filter(_df(results.get(key)),window) if isinstance(results,dict) else pd.DataFrame()
        if df.empty: st.info("No rows yet.")
        else:
            for _,r in df.head(3).iterrows(): card(r.to_dict())

def game_board_grid_view(results):
    st.markdown("## 🧩 Game Board")
    if not isinstance(results,dict): st.info("No results yet."); return
    board=_df(results.get("game_board"))
    if board.empty: board=_df(results.get("owners"))
    if board.empty: st.info("No game board rows yet."); return
    st.dataframe(board,use_container_width=True,height=420)
    st.download_button("Download Game Board CSV",csv_bytes(board),"game_board.csv","text/csv")

def render_board(results=None): blender_visual(results)
def game_board(results=None): return game_board_grid_view(results)
def board_view(results=None): return game_board_grid_view(results)
def feed_view(df=None):
    st.markdown("### Feed Data")
    st.dataframe(df,use_container_width=True) if isinstance(df,pd.DataFrame) and not df.empty else st.info("Upload feed to view data.")
def results_view(results=None): tickets_view(results or {})
def slate_view(*args, **kwargs): st.info("Slate view available after feed upload.")
def export_view(results=None):
    if isinstance(results,dict):
        for key in ["owners","core","alt","chaos"]:
            df=_df(results.get(key))
            if not df.empty: st.download_button(f"Download {key}.csv",csv_bytes(df),f"{key}.csv","text/csv")
def debug_view(results=None): st.write(results if results is not None else {})
