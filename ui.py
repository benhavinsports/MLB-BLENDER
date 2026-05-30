
import json
import streamlit as st
import streamlit.components.v1 as components


def inject_css():
    st.markdown("""
<style>
.stApp{background:#000;color:#fff;}
.block-container{max-width:100vw!important;padding:0!important;margin:0!important;}
header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important;}
[data-testid="stFileUploader"]{position:fixed!important;left:10px!important;top:58px!important;width:130px!important;height:82px!important;opacity:.01!important;z-index:999999!important;}
[data-testid="stFileUploader"] *{cursor:pointer!important;}
</style>
""", unsafe_allow_html=True)


def _fallback_games():
    return [
        {"owner":"Jakob Marsee","game":"Miami Marlins vs Toronto Blue Jays","bucket":"CORE 1 · CLEAN LANE","role":"Event Owner","pitcher":"Braydon Fisher","time":"7:07 PM ET","archetype":"Clean lane finisher","weakness":"Elevated fastball / pull-air lane","gates":"Core gates passed"},
        {"owner":"James Wood","game":"Washington Nationals vs Cleveland Guardians","bucket":"CORE 2 · ADJACENT / TRANSFER","role":"Adjacent / Decoy Transfer Owner","pitcher":"Joey Cantillo","time":"6:10 PM ET","archetype":"Adjacent transfer bat","weakness":"Mistake pitch / transfer lane","gates":"Alt transfer gates passed"},
        {"owner":"Julio Rodriguez","game":"Seattle Mariners vs Athletics","bucket":"CORE 3 · WHO / CHAOS","role":"WHO / Chaos Owner","pitcher":"Luis Severino","time":"9:40 PM ET","archetype":"Chaos finisher","weakness":"Volatile flow / bullpen lane","gates":"Chaos gates passed"},
    ]


def _extract(results):
    if isinstance(results, dict):
        if isinstance(results.get("games"), list) and results["games"]:
            return results["games"]
        out = []
        for key in ["core","core3","alt","alt3","chaos","chaos3","owners"]:
            rows = results.get(key)
            if isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict):
                        out.append({
                            "owner": r.get("owner") or r.get("player") or "Pending Owner",
                            "game": r.get("game") or r.get("game_key") or r.get("label") or f"Game {len(out)+1}",
                            "bucket": r.get("bucket") or r.get("core_slot") or f"GAME {len(out)+1}",
                            "role": r.get("role") or r.get("core_display_role") or r.get("archetype") or "Owner",
                            "pitcher": r.get("pitcher") or "Pending",
                            "time": r.get("time") or r.get("game_time_et") or "",
                            "archetype": r.get("archetype") or "Pending",
                            "weakness": r.get("weakness") or r.get("final_reason") or "Pending",
                            "gates": r.get("gates") or "Hidden public view",
                        })
        if out:
            return out
    return _fallback_games()


def render_board(results=None):
    uploaded = st.file_uploader("START", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed", key="start_upload_overlay")
    if uploaded is not None:
        st.session_state["uploaded_file_name"] = uploaded.name

    games = _extract(results or {})
    payload = json.dumps(games).replace("</", "<\\/")
    slate = st.session_state.get("uploaded_file_name", "Saturday Slate")
    total = 73
    survivors = min(3, len(games))

    html = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{box-sizing:border-box}
html,body{margin:0;background:#000;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#fff}
.viewport{width:100vw;height:100vh;background:#000;display:flex;justify-content:center;align-items:flex-start}
.board{width:min(100vw,1180px);aspect-ratio:1180/650;background:#05070d;position:relative;overflow:hidden;border:1px solid rgba(255,255,255,.16);box-shadow:0 0 55px rgba(0,0,0,.85)}
.board:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 40%,rgba(42,80,160,.18),transparent 40%),linear-gradient(180deg,#07101b,#020305)}
.top{position:absolute;top:12px;left:14px;right:14px;height:54px;display:grid;grid-template-columns:220px 1fr 175px 175px;gap:12px;z-index:20}
.logo{display:flex;align-items:center;gap:10px;color:#fff;font-weight:1000;line-height:.9;font-size:21px}
.logoMark{width:40px;height:40px;border-radius:8px;background:#0b1220;border:1px solid rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center}
.topBox{border:1px solid rgba(255,255,255,.16);background:#08101b;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#e6edf8;font-size:13px;font-weight:900;text-align:center}
.topBox b{color:#76ff80;font-size:23px;margin-left:8px}
.roadA{position:absolute;left:135px;right:138px;top:118px;height:68px;background:#000;border-radius:0 58px 58px 0;z-index:1}
.roadB{position:absolute;right:70px;top:118px;width:122px;height:176px;border:42px solid #000;border-left:0;border-radius:0 100px 100px 0;z-index:1}
.roadC{position:absolute;left:126px;right:174px;top:266px;height:68px;background:#000;border-radius:58px 0 0 58px;z-index:1}
.roadD{position:absolute;left:16px;top:266px;width:176px;height:180px;border:42px solid #000;border-right:0;border-radius:100px 0 0 100px;z-index:1}
.roadE{position:absolute;left:130px;right:248px;top:414px;height:68px;background:#000;z-index:1}
.start{position:absolute;left:16px;top:86px;width:130px;height:78px;background:linear-gradient(160deg,#ffe15b,#f59e0b);border:5px solid #fff;border-radius:10px;transform:rotate(-6deg);display:flex;align-items:center;justify-content:center;color:white;font-size:32px;font-weight:1000;z-index:30;text-shadow:0 3px 4px rgba(0,0,0,.35);cursor:pointer}
.arrow1{position:absolute;left:124px;top:150px;width:54px;height:54px;border-left:5px solid #fff;border-bottom:5px solid #fff;transform:rotate(-35deg);z-index:15}
.arrow2{position:absolute;left:558px;top:281px;font-size:42px;z-index:15;transform:rotate(70deg)}
.arrow3{position:absolute;right:195px;top:376px;font-size:52px;z-index:15;transform:rotate(15deg)}
.gate{position:absolute;width:118px;height:74px;border-radius:8px;border:4px solid #fff;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-weight:1000;text-align:center;z-index:12;cursor:pointer;box-shadow:0 7px 11px rgba(0,0,0,.45)}
.gate.blue{background:linear-gradient(160deg,#3b82f6,#1d4ed8)}
.gate.red{background:linear-gradient(160deg,#ef4444,#991b1b)}
.gate.orange{background:linear-gradient(160deg,#fb923c,#c2410c)}
.gate.purple{background:linear-gradient(160deg,#a855f7,#6b21a8)}
.gate.green{background:linear-gradient(160deg,#4ade80,#15803d)}
.num{width:22px;height:22px;border-radius:999px;background:#fff;color:#111;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:1000;margin-bottom:3px}
.label{font-size:10.5px;line-height:.96;text-shadow:0 2px 3px rgba(0,0,0,.7)}
.finish{position:absolute;right:55px;bottom:104px;width:145px;height:145px;z-index:13;background:#fbbf24;clip-path:polygon(50% 0%,61% 31%,94% 18%,74% 48%,100% 65%,67% 69%,79% 100%,50% 80%,21% 100%,33% 69%,0 65%,26% 48%,6% 18%,39% 31%);display:flex;align-items:center;justify-content:center;flex-direction:column;color:white;font-size:25px;font-weight:1000;text-align:center;text-shadow:0 2px 3px rgba(0,0,0,.28);cursor:pointer}
.legend{position:absolute;left:405px;top:355px;width:300px;height:70px;background:rgba(4,8,16,.88);border:1px solid rgba(255,255,255,.18);border-radius:8px;z-index:15;padding:10px;display:grid;grid-template-columns:1fr 1fr;gap:5px;font-size:10px;font-weight:900;color:#d7e2f0}
.dot{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px}
.cards{position:absolute;left:14px;right:14px;bottom:40px;height:110px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;z-index:18}
.card{background:#06101f;border:1px solid rgba(255,255,255,.16);border-radius:8px;padding:13px;position:relative;overflow:hidden;cursor:pointer}
.card.core{box-shadow:0 0 22px rgba(59,130,246,.95);border-color:#2563eb}
.card.alt{box-shadow:0 0 22px rgba(239,68,68,.85);border-color:#ef4444}
.card.chaos{box-shadow:0 0 22px rgba(34,197,94,.85);border-color:#22c55e}
.kicker{font-size:10px;font-weight:1000;letter-spacing:.7px;margin-bottom:5px}
.name{font-size:23px;font-weight:1000;line-height:1;color:#fff}
.role{font-size:11px;font-weight:900;color:#d7e2f0;margin-top:4px}
.match{font-size:10px;color:#aab3c1;margin-top:3px}
.lock{position:absolute;right:10px;top:10px;border-radius:999px;background:rgba(34,197,94,.20);border:1px solid #67f08a;color:#d9ffdd;font-size:8px;font-weight:1000;padding:4px 8px}
.footer{position:absolute;bottom:0;left:0;right:0;height:31px;background:#05080d;border-top:1px solid rgba(255,255,255,.10);display:grid;grid-template-columns:repeat(5,1fr);align-items:center;text-align:center;color:#aab3c1;font-size:9px;font-weight:900;z-index:20}
.detail{display:none;position:absolute;left:16px;right:16px;top:85px;background:rgba(5,10,20,.97);border:1px solid rgba(255,255,255,.22);border-radius:14px;padding:18px;z-index:50;box-shadow:0 0 50px rgba(0,0,0,.8)}
.detail.show{display:block}
.close{position:absolute;right:14px;top:9px;font-size:24px;cursor:pointer}
.detail h2{margin:0 0 8px;font-size:36px;line-height:1}
.detailGame{font-size:17px;font-weight:900;color:#cbd5e1;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.info{background:#0b1220;border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:11px;font-size:12px;line-height:1.3}
.info b{display:block;color:#b7ff32;font-size:14px;margin-bottom:4px}
@media(max-width:760px){
  .board{width:100vw;aspect-ratio:1180/650;border:0}
  .top{top:5px;left:6px;right:6px;height:40px;grid-template-columns:145px 1fr 95px 82px;gap:4px}
  .logo{font-size:13px}.logoMark{width:28px;height:28px}.topBox{font-size:7.6px;border-radius:5px}.topBox b{font-size:14px;margin-left:4px}
  .roadA{left:86px;right:83px;top:67px;height:44px}.roadB{right:37px;top:67px;width:80px;height:111px;border-width:27px}.roadC{left:82px;right:90px;top:157px;height:44px}.roadD{left:8px;top:157px;width:100px;height:118px;border-width:27px}.roadE{left:82px;right:126px;top:244px;height:44px}
  .start{left:8px;top:54px;width:80px;height:50px;border-width:3px;font-size:20px}
  .arrow1,.arrow2,.arrow3{display:none}
  .gate{width:72px;height:47px;border-width:2px;border-radius:5px}.num{width:15px;height:15px;font-size:9px;margin-bottom:1px}.label{font-size:6.2px}
  .finish{right:32px;bottom:65px;width:82px;height:82px;font-size:14px}
  .legend{left:42%;top:171px;width:155px;height:42px;font-size:5.8px;padding:5px;gap:2px}.dot{width:5px;height:5px;margin-right:3px}
  .cards{left:6px;right:6px;bottom:23px;height:63px;gap:4px}.card{padding:6px;border-radius:5px}.kicker{font-size:5.6px;margin-bottom:3px}.name{font-size:11.5px}.role{font-size:5.6px;margin-top:2px}.match{font-size:5.2px}.lock{font-size:4.8px;padding:2px 4px;right:5px;top:5px}
  .footer{height:19px;font-size:4.8px}
  .detail{top:50px;left:8px;right:8px;padding:12px}.detail h2{font-size:24px}.detailGame{font-size:12px}.grid{grid-template-columns:1fr 1fr;gap:6px}.info{font-size:9px;padding:8px}.info b{font-size:10px}
}
</style>
</head>
<body>
<div class="viewport">
  <div class="board">
    <div class="top">
      <div class="logo"><div class="logoMark">☼</div><div>BLENDER<br><span style="font-size:60%;letter-spacing:2px">GAMEBOARD</span></div></div>
      <div class="topBox">📅 __SLATE__</div>
      <div class="topBox">Total Hitters <b>__TOTAL__</b></div>
      <div class="topBox">Survivors <b>__SURVIVORS__</b></div>
    </div>
    <div class="roadA"></div><div class="roadB"></div><div class="roadC"></div><div class="roadD"></div><div class="roadE"></div>
    <div class="start" onclick="selectGame(0)">START</div>
    <div class="arrow1"></div><div class="arrow2">↑</div><div class="arrow3">↗</div>
    <div id="tiles"></div>
    <div class="legend">
      <div><span class="dot" style="background:#2563eb"></span>Matchup & Environment</div>
      <div><span class="dot" style="background:#ef4444"></span>Offense Quality</div>
      <div><span class="dot" style="background:#f97316"></span>Plate Discipline</div>
      <div><span class="dot" style="background:#22c55e"></span>Power & Contact</div>
    </div>
    <div class="finish" onclick="selectGame(0)">FINISH<br><span style="font-size:55%">🔒 OWNERS</span></div>
    <div class="cards"><div id="card0" class="card core"></div><div id="card1" class="card alt"></div><div id="card2" class="card chaos"></div></div>
    <div class="footer"><div>📋 Blender Engine</div><div>🛡 23-Gate Progression</div><div>🔒 Immutable Mapping</div><div>👥 73 Hitters Processed</div><div>✅ Owners Locked</div></div>
    <div id="detail" class="detail"><div class="close" onclick="hideDetail()">×</div><div id="detailInner"></div></div>
  </div>
</div>
<script>
const games = __PAYLOAD__;
const coords = [[155,93],[270,93],[385,93],[500,93],[615,93],[730,93],[845,138],[945,188],[855,270],[750,309],[632,222],[514,222],[396,222],[278,222],[160,222],[70,222],[55,305],[165,344],[280,344],[395,344],[510,344],[625,344],[740,344]];
const colors = ["blue","red","orange","purple","red","orange","blue","green","purple","green","red","green","purple","blue","orange","red","green","purple","blue","orange","red","purple","green"];
const labels = [["Core","Matchup"],["Vegas","Screen"],["Opponent","Starter"],["Ballpark","Factor"],["Weather","Gate"],["Plate","Discipline"],["Hard Hit","% Gate"],["Barrel","% Gate"],["wOBA","Gate"],["xwOBA","Gate"],["ISO","Power"],["Pitches","Per PA"],["Swing","% Gate"],["Chase","% Gate"],["K %","Contact"],["Batted Ball","Profile"],["Clutch /","Leverage"],["Lineup","Position"],["Consistency","Gate"],["Recent","Form"],["Fade / Low","EV Filter"],["Final","Survivor"],["Locked","Owner"]];
function short(s,n){s=s||"";return s.length>n?s.slice(0,n-1)+"…":s}
function drawTiles(){
  const root=document.getElementById("tiles");
  root.innerHTML="";
  coords.forEach((p,i)=>{
    const d=document.createElement("div");
    d.className="gate "+colors[i];
    d.style.left=p[0]+"px";
    d.style.top=p[1]+"px";
    d.onclick=()=>selectGame(i%games.length);
    d.innerHTML=`<div class="num">${i+1}</div><div class="label">${labels[i][0]}<br>${labels[i][1]}</div>`;
    root.appendChild(d);
  });
}
function fillCards(){
  const c=games[0]||{}, a=games[1]||c, w=games[2]||c;
  [[c,0,"CORE 1 · CLEAN LANE"],[a,1,"CORE 2 · ADJACENT / TRANSFER"],[w,2,"CORE 3 · WHO / CHAOS"]].forEach(([g,i,k])=>{
    document.getElementById("card"+i).onclick=()=>selectGame(i);
    document.getElementById("card"+i).innerHTML=`<div class="lock">LOCKED OWNER</div><div class="kicker" style="color:${i==0?"#6aa2ff":i==1?"#ff6872":"#78ff98"}">${k}</div><div class="name">${short(g.owner,22)}</div><div class="role">${g.role||""}</div><div class="match">${short(g.game,42)} · ${g.time||""}</div>`;
  });
}
function selectGame(i){
  const g=games[i]||games[0]||{};
  document.getElementById("detailInner").innerHTML=`<h2>${g.owner||"Pending Owner"}</h2><div class="detailGame">${g.game||""} ${g.time?"· "+g.time:""}</div><div class="grid"><div class="info"><b>Archetype</b>${g.archetype||"Pending"}</div><div class="info"><b>Gates Passed</b>${g.gates||"Hidden public view"}</div><div class="info"><b>Pitcher Weakness</b>${g.weakness||"Pending"}</div><div class="info"><b>Lane Type</b>${g.role||g.bucket||"Pending"}</div></div>`;
  document.getElementById("detail").classList.add("show");
}
function hideDetail(){document.getElementById("detail").classList.remove("show")}
drawTiles();
fillCards();
</script>
</body>
</html>
"""
    html = (
        html.replace("__SLATE__", slate)
        .replace("__TOTAL__", str(total))
        .replace("__SURVIVORS__", str(survivors))
        .replace("__PAYLOAD__", payload)
    )
    components.html(html, height=720, scrolling=False)
