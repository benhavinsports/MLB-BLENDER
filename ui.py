
from __future__ import annotations
import json
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

def inject_css():
    st.markdown("""
<style>
.stApp{background:#030407;color:#fff;}
.block-container{max-width:100vw!important;padding:0!important;margin:0!important;}
header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important;}
[data-testid="stFileUploader"]{
  position:fixed!important;
  left:9px!important;
  top:88px!important;
  width:105px!important;
  height:70px!important;
  opacity:.01!important;
  z-index:999999!important;
}
[data-testid="stFileUploader"] *{cursor:pointer!important;}
.run-box{
  position:fixed!important;
  right:14px!important;
  bottom:158px!important;
  width:190px!important;
  z-index:999999!important;
}
.run-box button{
  height:76px!important;
  border-radius:20px!important;
  border:4px solid #fff!important;
  background:linear-gradient(160deg,#fbbf24,#f97316)!important;
  color:#111!important;
  font-weight:1000!important;
  box-shadow:0 0 25px rgba(251,191,36,.9)!important;
}
</style>
""", unsafe_allow_html=True)

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

def _first(row, keys, default=""):
    for k in keys:
        if _txt(row.get(k)): return _txt(row.get(k))
    return default

def _normalize(results):
    if not isinstance(results, dict): results={}
    owners=_records(results.get("owners"))
    core=_records(results.get("core"))
    alt=_records(results.get("alt"))
    chaos=_records(results.get("chaos"))
    board=_records(results.get("game_board")) or _records(results.get("games"))
    role={}
    for label, rows in [("CORE",core),("ALT",alt),("CHAOS",chaos)]:
        for i,r in enumerate(rows[:3]):
            role[_first(r,["owner","player","hitter","name"],"Waiting...").lower()] = f"{label} {i+1}"
    src=owners or core+alt+chaos or board
    tiles=[]
    seen=set()
    for i,r in enumerate(src):
        player=_first(r,["owner","player","hitter","name"],"Waiting...")
        game=_first(r,["game_key","original_game_key","game","matchup"],f"Game {i+1}")
        k=(player.lower(),game.lower())
        if k in seen: continue
        seen.add(k)
        bucket=role.get(player.lower(), _first(r,["ticket_role","official_core_role","true_role_path","role","bucket"],"OWNER"))
        up=bucket.upper()
        glow="core" if "CORE" in up else "alt" if "ALT" in up else "chaos" if ("CHAOS" in up or "WHO" in up) else "none"
        tiles.append({
          "owner":player,"game":game,"bucket":bucket,"glow":glow,
          "role":_first(r,["ticket_role","official_core_role","true_role_path","role"],bucket),
          "pitcher":_first(r,["pitcher","opposing_pitcher"],""),
          "time":_first(r,["game_time_et","time"],""),
          "archetype":_first(r,["true_role_path","official_core_role","archetype"],bucket),
          "weakness":_first(r,["final_reason","cut_reason","notes","parse_note"],"Gate survivor"),
          "gates":_first(r,["gate_path","gates","pass_depth"],"Hidden 23-gate formula")
        })
    if not tiles:
        for i in range(8):
            tiles.append({"owner":"Waiting...","game":f"Game {i+1}","bucket":"UPLOAD","glow":"none","role":"Upload PDF then RUN","pitcher":"","time":"","archetype":"Pending","weakness":"Upload PDF on START, then press RUN BLENDER.","gates":"Hidden"})
    def cards(rows,label,glow):
        out=[]
        rows=_records(rows)
        for i,r in enumerate(rows[:3]):
            out.append({"slot":f"{label} {i+1}","owner":_first(r,["owner","player","hitter","name"],"Waiting..."),"game":_first(r,["game_key","game","matchup"],""),"role":_first(r,["ticket_role","official_core_role","role"],label)})
        fallback=[t for t in tiles if t["glow"]==glow] or tiles
        while len(out)<3:
            t=fallback[min(len(out),len(fallback)-1)]
            out.append({"slot":f"{label} {len(out)+1}","owner":t["owner"],"game":t["game"],"role":t["role"]})
        return out[:3]
    meta=results.get("meta",{}) if isinstance(results.get("meta"),dict) else {}
    return {"tiles":tiles,"core":cards(core,"CORE","core"),"alt":cards(alt,"ALT","alt"),"chaos":cards(chaos,"CHAOS","chaos"),
            "meta":{"games":_txt(meta.get("games")) or str(len({t["game"] for t in tiles})),
                    "owners":_txt(meta.get("owners_locked")) or str(len([t for t in tiles if t["owner"]!="Waiting..."])),
                    "core":_txt(meta.get("core_count")) or str(len(core))},
            "uploaded":_txt(st.session_state.get("uploaded_file_name")),
            "error":_txt(st.session_state.get("blender_error")),
            "status":_txt(st.session_state.get("run_status"))}

def render_board(results=None):
    data=_normalize(results)
    payload=json.dumps(data).replace("</","<\\/")
    html=r"""
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{box-sizing:border-box}html,body{margin:0;background:#030407;color:#fff;font-family:Arial,Helvetica,sans-serif;overflow:hidden}
.board{width:100vw;height:100vh;position:relative;background:radial-gradient(circle at 50% 33%,#17223b 0%,#070a10 38%,#020304 82%);overflow:hidden}
.top{position:absolute;left:16px;right:16px;top:10px;height:60px;display:grid;grid-template-columns:215px 1fr 140px 140px 140px;gap:10px;z-index:8}.brand{display:flex;align-items:center;gap:10px;font-weight:1000;line-height:.9}.mark{width:46px;height:46px;border-radius:12px;background:#0b1220;border:1px solid rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:24px}.brand span{font-size:22px}.brand small{letter-spacing:3px;font-size:10px;color:#b7c3d8}.pill{height:46px;border-radius:12px;background:#08101c;border:1px solid rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;text-align:center;font-size:12px;font-weight:900;color:#d9e6f7;padding:0 8px}.pill b{font-size:22px;color:#7dff9d;margin-left:6px}
.start{position:absolute;left:18px;top:90px;width:136px;height:82px;background:linear-gradient(160deg,#ffe15b,#f59e0b);border:5px solid #fff;border-radius:12px;transform:rotate(-6deg);z-index:12;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:1000;text-shadow:0 3px 4px rgba(0,0,0,.35)}
.path{position:absolute;left:46px;right:46px;top:92px;bottom:170px;z-index:1}.path svg{width:100%;height:100%;overflow:visible}.tiles{position:absolute;inset:0;z-index:6}.node{position:absolute;width:126px;height:76px;border-radius:14px;background:#071224;border:3px solid rgba(255,255,255,.86);color:#fff;display:flex;flex-direction:column;justify-content:center;padding:9px;cursor:pointer;box-shadow:0 8px 14px rgba(0,0,0,.42)}.node.core{border-color:#60a5fa;box-shadow:0 0 24px rgba(59,130,246,.95),0 8px 14px rgba(0,0,0,.42)}.node.alt{border-color:#fb7185;box-shadow:0 0 24px rgba(239,68,68,.85),0 8px 14px rgba(0,0,0,.42)}.node.chaos{border-color:#4ade80;box-shadow:0 0 24px rgba(34,197,94,.88),0 0 18px rgba(168,85,247,.35),0 8px 14px rgba(0,0,0,.42)}
.num{position:absolute;right:8px;top:7px;width:21px;height:21px;border-radius:999px;background:#fff;color:#08111f;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:1000}.bucket{font-size:9px;letter-spacing:.8px;font-weight:1000;text-transform:uppercase;color:#b7ff32;max-width:90px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.owner{font-size:16px;font-weight:1000;line-height:1.02;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.game{font-size:9px;color:#b8c4d8;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.finish{position:absolute;right:45px;bottom:168px;width:124px;height:124px;background:#fbbf24;clip-path:polygon(50% 0%,61% 31%,94% 18%,74% 48%,100% 65%,67% 69%,79% 100%,50% 80%,21% 100%,33% 69%,0 65%,26% 48%,6% 18%,39% 31%);z-index:7;display:flex;align-items:center;justify-content:center;text-align:center;font-size:21px;font-weight:1000;text-shadow:0 2px 3px rgba(0,0,0,.25)}
.cards{position:absolute;left:14px;right:14px;bottom:36px;height:126px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;z-index:9}.card{background:#06101f;border:1px solid rgba(255,255,255,.15);border-radius:14px;padding:12px;position:relative;overflow:hidden;cursor:pointer}.card.core{box-shadow:0 0 22px rgba(59,130,246,.8);border-color:#2563eb}.card.alt{box-shadow:0 0 22px rgba(239,68,68,.72);border-color:#ef4444}.card.chaos{box-shadow:0 0 22px rgba(34,197,94,.72);border-color:#22c55e}.kicker{font-size:10px;letter-spacing:.8px;font-weight:1000;margin-bottom:5px}.cardName{font-size:22px;font-weight:1000;line-height:1;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:56px}.cardRole{font-size:11px;font-weight:900;color:#d7e2f0;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.cardGame{font-size:10px;color:#aab3c1;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lock{position:absolute;right:10px;top:10px;border-radius:999px;background:rgba(34,197,94,.18);border:1px solid #67f08a;color:#d9ffdd;font-size:8px;font-weight:1000;padding:4px 7px}
.footer{position:absolute;left:0;right:0;bottom:0;height:30px;background:#05080d;border-top:1px solid rgba(255,255,255,.10);display:grid;grid-template-columns:repeat(5,1fr);align-items:center;text-align:center;color:#aab3c1;font-size:9px;font-weight:900;z-index:12}
.detail{display:none;position:absolute;left:18px;right:18px;top:82px;min-height:220px;background:rgba(5,10,20,.98);border:1px solid rgba(255,255,255,.22);border-radius:16px;padding:18px;z-index:50;box-shadow:0 0 60px rgba(0,0,0,.9)}.detail.show{display:block}.close{position:absolute;right:14px;top:9px;font-size:26px;cursor:pointer}.detail h2{margin:0 0 7px;font-size:36px;line-height:1}.detailGame{font-size:16px;font-weight:900;color:#cbd5e1;margin-bottom:12px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.info{background:#0b1220;border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:11px;font-size:12px;line-height:1.3}.info b{display:block;color:#b7ff32;font-size:14px;margin-bottom:4px}
.err{position:absolute;left:170px;top:82px;right:18px;z-index:20;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.45);padding:8px 10px;border-radius:10px;color:#fecaca;font-size:12px;font-weight:900;display:none}
@media(max-width:760px){.top{left:7px;right:7px;top:6px;height:76px;grid-template-columns:1fr 1fr;gap:6px}.mark{width:34px;height:34px}.brand span{font-size:16px}.pill{height:32px;font-size:9px;border-radius:8px}.pill b{font-size:15px}.start{left:9px;top:88px;width:92px;height:58px;border-width:3px;border-radius:9px;font-size:23px}.path{left:4px;right:4px;top:126px;bottom:188px}.node{width:84px;height:58px;border-width:2px;border-radius:10px;padding:6px}.num{width:15px;height:15px;font-size:8px;right:5px;top:5px}.bucket{font-size:6px;max-width:62px}.owner{font-size:11px}.game{font-size:7px}.finish{right:18px;bottom:172px;width:78px;height:78px;font-size:13px}.cards{left:7px;right:7px;bottom:31px;height:134px;grid-template-columns:1fr;gap:6px}.card{padding:8px;border-radius:10px}.kicker{font-size:7px;margin-bottom:2px}.cardName{font-size:14px}.cardRole{font-size:8px;margin-top:2px}.cardGame{font-size:7px}.lock{font-size:6px;padding:2px 4px;right:6px;top:6px}.footer{height:26px;font-size:6px}.detail{left:8px;right:8px;top:88px;padding:12px}.detail h2{font-size:25px}.detailGame{font-size:12px}.grid{grid-template-columns:1fr 1fr;gap:6px}.info{font-size:9px;padding:8px}.info b{font-size:10px}.err{left:108px;top:88px;font-size:9px}}
</style></head><body><div class="board">
<div class="top"><div class="brand"><div class="mark">☼</div><div><span>BLENDER</span><br><small>GAMEBOARD</small></div></div><div class="pill" id="uploadName">START Upload</div><div class="pill">Games <b id="gameCount">0</b></div><div class="pill">Owners <b id="ownerCount">0</b></div><div class="pill">Core <b id="coreCount">0</b></div></div><div class="err" id="errBox"></div>
<div class="start">START</div><div class="path"><svg viewBox="0 0 1000 560" preserveAspectRatio="none"><path d="M90,75 C215,28 340,32 470,78 C610,128 720,120 830,170 C955,230 930,342 770,368 C635,390 510,340 380,350 C230,362 90,422 150,494 C210,558 470,528 820,510" stroke="#071015" stroke-width="78" fill="none" stroke-linecap="round"/><path d="M90,75 C215,28 340,32 470,78 C610,128 720,120 830,170 C955,230 930,342 770,368 C635,390 510,340 380,350 C230,362 90,422 150,494 C210,558 470,528 820,510" stroke="#2cff88" stroke-width="8" fill="none" stroke-linecap="round" opacity=".72"/></svg></div><div id="tiles" class="tiles"></div><div class="finish">FINISH</div>
<div class="cards"><div id="coreCard" class="card core"></div><div id="altCard" class="card alt"></div><div id="chaosCard" class="card chaos"></div></div><div class="footer"><div>START Upload</div><div>Visible Run Button</div><div>Dynamic Tiles</div><div>Core / Alt / Chaos</div><div>Clickable Board</div></div><div id="detail" class="detail"><div class="close" onclick="hideDetail()">×</div><div id="detailInner"></div></div></div>
<script>
const data=__DATA__;const coords=[[9,17],[24,13],[38,15],[52,20],[66,22],[79,28],[84,41],[74,52],[59,49],[45,47],[31,50],[16,58],[10,72],[25,79],[42,77],[59,76],[75,74],[64,62],[49,62],[35,64],[22,68],[52,34],[68,37]];
function esc(s){return String(s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[m]));}function short(s,n){s=String(s||"");return s.length>n?s.slice(0,n-1)+"…":s;}function cls(g){return g==="core"?"core":g==="alt"?"alt":g==="chaos"?"chaos":"";}
function renderTop(){document.getElementById("uploadName").textContent=data.uploaded?(data.status||("Loaded: "+data.uploaded)):"START Upload";document.getElementById("gameCount").textContent=data.meta.games;document.getElementById("ownerCount").textContent=data.meta.owners;document.getElementById("coreCount").textContent=data.meta.core;if(data.error){const e=document.getElementById("errBox");e.textContent=data.error;e.style.display="block";}}
function renderTiles(){const root=document.getElementById("tiles");root.innerHTML="";data.tiles.forEach((t,i)=>{const p=coords[i%coords.length];const d=document.createElement("div");d.className="node "+cls(t.glow);d.style.left=p[0]+"%";d.style.top=p[1]+"%";d.onclick=()=>selectTile(i);d.innerHTML=`<div class="num">${i+1}</div><div class="bucket">${esc(short(t.bucket,16))}</div><div class="owner">${esc(short(t.owner,19))}</div><div class="game">${esc(short(t.game,24))}</div>`;root.appendChild(d);});}
function cardHtml(arr,label,idx){const t=(arr&&arr[idx])||{};return `<div class="lock">LOCKED</div><div class="kicker">${label} ${idx+1}</div><div class="cardName">${esc(t.owner||"Waiting...")}</div><div class="cardRole">${esc(t.role||label)}</div><div class="cardGame">${esc(t.game||"Upload slate PDF")}</div>`}
function renderCards(){document.getElementById("coreCard").innerHTML=cardHtml(data.core,"CORE",0);document.getElementById("altCard").innerHTML=cardHtml(data.alt,"ALT",0);document.getElementById("chaosCard").innerHTML=cardHtml(data.chaos,"CHAOS",0);document.getElementById("coreCard").onclick=()=>selectTile(0);document.getElementById("altCard").onclick=()=>selectTile(Math.min(1,data.tiles.length-1));document.getElementById("chaosCard").onclick=()=>selectTile(Math.min(2,data.tiles.length-1));}
function selectTile(i){const t=data.tiles[i]||data.tiles[0]||{};document.getElementById("detailInner").innerHTML=`<h2>${esc(t.owner||"Pending Owner")}</h2><div class="detailGame">${esc(t.game||"")} ${t.time?"· "+esc(t.time):""}</div><div class="grid"><div class="info"><b>Bucket</b>${esc(t.bucket||"Pending")}</div><div class="info"><b>Archetype</b>${esc(t.archetype||"Pending")}</div><div class="info"><b>Pitcher / Weakness</b>${esc(t.pitcher||"")}<br>${esc(t.weakness||"Pending")}</div><div class="info"><b>Gates</b>${esc(t.gates||"Hidden")}</div></div>`;document.getElementById("detail").classList.add("show");}
function hideDetail(){document.getElementById("detail").classList.remove("show")}renderTop();renderTiles();renderCards();
</script></body></html>
"""
    components.html(html.replace("__DATA__", payload), height=900, scrolling=False)
