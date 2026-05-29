import json
import streamlit as st
import streamlit.components.v1 as components


def inject_css():
    st.markdown("""
<style>
.stApp{background:#000;color:#f5eadc;}
.block-container{max-width:100vw!important;padding:0!important;}
header,footer,[data-testid="stToolbar"]{display:none!important;}
[data-testid="stFileUploader"]{
  position:absolute!important;
  left:22px!important;
  top:74px!important;
  width:170px!important;
  height:96px!important;
  z-index:100!important;
  opacity:.015!important;
}
</style>
""", unsafe_allow_html=True)


def _demo_games():
    return [
        {"game":"Miami Marlins vs Toronto Blue Jays","owner":"Jakob Marsee","bucket":"CORE 1","glow":"core","role":"Event Owner","pitcher":"Braydon Fisher","time":"7:07 PM ET","archetype":"Clean lane finisher","weakness":"Elevated fastball / pull-air lane","gates":"Passed CORE ownership path"},
        {"game":"Los Angeles Angels vs Detroit Tigers","owner":"Dillon Dingler","bucket":"CORE 2","glow":"core","role":"Primary Clean Owner","pitcher":"Grayson Rodriguez","time":"1:10 PM ET","archetype":"Primary clean lane","weakness":"Inner-third fastball lane","gates":"Passed CORE ownership path"},
        {"game":"Boston Red Sox vs Baltimore Orioles","owner":"Wilyer Abreu","bucket":"CORE 3","glow":"core","role":"Event Owner","pitcher":"Dean Kremer","time":"7:05 PM ET","archetype":"Pull-air finisher","weakness":"RF pull-air lane","gates":"Passed CORE ownership path"},
        {"game":"Minnesota Twins vs Chicago White Sox","owner":"Trevor Larnach","bucket":"ALT 1","glow":"alt","role":"Adjacent Transfer Owner","pitcher":"Davis Martin","time":"2:10 PM ET","archetype":"Adjacent transfer bat","weakness":"Pull-side flyball lane","gates":"Passed ALT transfer path"},
        {"game":"Washington Nationals vs Cleveland Guardians","owner":"James Wood","bucket":"ALT 2","glow":"alt","role":"Decoy Transfer Owner","pitcher":"Joey Cantillo","time":"6:10 PM ET","archetype":"Transfer power bat","weakness":"Mistake pitch lane","gates":"Passed ALT transfer path"},
        {"game":"Chicago Cubs vs Pittsburgh Pirates","owner":"Marcell Ozuna","bucket":"ALT 3","glow":"alt","role":"Adjacent Transfer Owner","pitcher":"Colin Rea","time":"6:40 PM ET","archetype":"Power transfer bat","weakness":"Low-middle mistake lane","gates":"Passed ALT transfer path"},
        {"game":"Houston Astros vs Texas Rangers","owner":"Ezequiel Duran","bucket":"CHAOS 1","glow":"chaos","role":"WHO / Chaos Owner","pitcher":"Spencer Arrighetti","time":"8:05 PM ET","archetype":"WHO chaos bat","weakness":"Bullpen continuation lane","gates":"Passed CHAOS path"},
        {"game":"Seattle Mariners vs Athletics","owner":"Julio Rodriguez","bucket":"CHAOS 2","glow":"chaos","role":"WHO / Chaos Owner","pitcher":"Luis Severino","time":"9:40 PM ET","archetype":"Chaos finisher","weakness":"Volatile game-flow lane","gates":"Passed CHAOS path"},
        {"game":"Arizona Diamondbacks vs Colorado Rockies","owner":"Pending Owner","bucket":"GAME 9","glow":"none","role":"Run Blender to lock","pitcher":"Pending","time":"","archetype":"Pending","weakness":"Pending","gates":"Pending"},
        {"game":"New York Yankees vs Tampa Bay Rays","owner":"Pending Owner","bucket":"GAME 10","glow":"none","role":"Run Blender to lock","pitcher":"Pending","time":"","archetype":"Pending","weakness":"Pending","gates":"Pending"},
        {"game":"San Diego Padres vs San Francisco Giants","owner":"Pending Owner","bucket":"GAME 11","glow":"none","role":"Run Blender to lock","pitcher":"Pending","time":"","archetype":"Pending","weakness":"Pending","gates":"Pending"},
        {"game":"Philadelphia Phillies vs Atlanta Braves","owner":"Pending Owner","bucket":"GAME 12","glow":"none","role":"Run Blender to lock","pitcher":"Pending","time":"","archetype":"Pending","weakness":"Pending","gates":"Pending"}
    ]


def _games_from_results(results):
    if isinstance(results, dict):
        if isinstance(results.get("games"), list) and results["games"]:
            return results["games"]
        out = []
        groups = [("core3","core"),("core","core"),("alt3","alt"),("alt","alt"),("chaos3","chaos"),("chaos","chaos"),("owners","none")]
        for key, glow in groups:
            rows = results.get(key)
            if isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict):
                        out.append({
                            "game": r.get("game") or r.get("game_key") or r.get("label") or "Game",
                            "owner": r.get("owner") or r.get("player") or "Pending Owner",
                            "bucket": r.get("bucket") or r.get("core_slot") or f"GAME {len(out)+1}",
                            "glow": r.get("glow") or glow,
                            "role": r.get("role") or r.get("archetype") or "Owner",
                            "pitcher": r.get("pitcher") or "Pending",
                            "time": r.get("time") or r.get("game_time_et") or "",
                            "archetype": r.get("archetype") or "Pending",
                            "weakness": r.get("weakness") or r.get("final_reason") or "Pending",
                            "gates": r.get("gates") or "Hidden public view",
                        })
        if out:
            return out
    return _demo_games()


def render_board(results=None):
    uploaded = st.file_uploader("START", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed", key="hidden_start_upload")
    if uploaded is not None:
        st.session_state["uploaded_file_name"] = uploaded.name

    games = _games_from_results(results or {})
    slate = st.session_state.get("uploaded_file_name", "Today’s Slate")
    payload = json.dumps(games).replace("</", "<\\/")
    total = len(games)
    core = sum(1 for g in games if str(g.get("glow","")).lower()=="core")
    alt = sum(1 for g in games if str(g.get("glow","")).lower()=="alt")
    chaos = sum(1 for g in games if str(g.get("glow","")).lower()=="chaos")

    template = r"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
*{box-sizing:border-box}
body{margin:0;background:#000;color:#f5eadc;font-family:Inter,Arial,Helvetica,sans-serif;overflow-x:hidden}
.board{min-height:100vh;width:100vw;background:radial-gradient(circle at 58% 40%,rgba(42,80,160,.18),transparent 35%),linear-gradient(180deg,#080b12,#020304);padding:16px;position:relative;overflow:hidden}
.header{display:grid;grid-template-columns:1.4fr 1fr .6fr .6fr .6fr;gap:12px;align-items:center;margin-bottom:14px}
.logo{display:flex;align-items:center;gap:10px;font-weight:1000;font-size:26px;line-height:.9}
.logoIcon{width:54px;height:54px;border-radius:14px;background:#0b1220;border:1px solid rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center}
.stat{height:54px;border:1px solid rgba(255,255,255,.15);border-radius:12px;background:#080d16;display:flex;align-items:center;justify-content:center;gap:8px;font-weight:900;text-align:center}
.stat b{color:#78ff7a;font-size:25px}
.stage{position:relative;min-height:calc(100vh - 110px);border-radius:20px;border:1px solid rgba(255,255,255,.10);overflow:hidden;background:rgba(0,0,0,.35)}
.road{position:absolute;left:40px;right:40px;top:88px;height:390px;border:54px solid #000;border-radius:120px;opacity:.94;pointer-events:none}
.start{position:absolute;left:22px;top:54px;width:150px;height:98px;border-radius:18px;border:5px solid #fff;background:linear-gradient(160deg,#ffe05b,#f59e0b);display:flex;align-items:center;justify-content:center;color:white;font-size:38px;font-weight:1000;transform:rotate(-6deg);text-shadow:0 3px 4px rgba(0,0,0,.35);z-index:3;cursor:pointer}
.startSub{position:absolute;left:190px;top:60px;right:20px;color:#98a4b8;font-size:15px;font-weight:800;z-index:3}
.tiles{position:relative;z-index:2;padding:180px 24px 24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.tile{min-height:122px;border-radius:16px;background:#071224;border:2px solid rgba(255,255,255,.14);padding:13px;cursor:pointer;position:relative;transition:.15s ease}
.tile:hover{transform:translateY(-2px);filter:brightness(1.12)}
.tile.core{border-color:#3b82f6;box-shadow:0 0 0 2px rgba(59,130,246,.38),0 0 28px rgba(59,130,246,.95)}
.tile.alt{border-color:#fb923c;box-shadow:0 0 0 2px rgba(251,146,60,.38),0 0 28px rgba(239,68,68,.78),0 0 18px rgba(251,146,60,.65)}
.tile.chaos{border-color:#22c55e;box-shadow:0 0 0 2px rgba(34,197,94,.35),0 0 26px rgba(34,197,94,.85),0 0 24px rgba(168,85,247,.50)}
.bucket{font-size:12px;font-weight:1000;letter-spacing:1px;margin-bottom:6px;text-transform:uppercase}
.core .bucket{color:#6aa2ff}.alt .bucket{color:#ff9c69}.chaos .bucket{color:#7dff9f}
.owner{font-size:25px;font-weight:1000;line-height:1.04;color:white;margin-bottom:6px}
.role{font-size:12px;font-weight:900;color:#dbe4ef;line-height:1.2}
.game{font-size:11px;color:#aab3c1;line-height:1.25;margin-top:8px}
.lock{position:absolute;right:10px;top:10px;border:1px solid rgba(105,240,138,.62);background:rgba(34,197,94,.16);color:#d9ffdd;border-radius:999px;padding:3px 7px;font-size:9px;font-weight:1000}
.detail{position:relative;z-index:3;margin:14px 24px 24px;background:#070b12;border:1px solid rgba(255,255,255,.13);border-radius:16px;padding:16px}
.detail h2{font-size:36px;margin:0 0 6px;line-height:1}
.detailGame{color:#cbd5e1;font-weight:900;font-size:18px;margin-bottom:12px}
.infoGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.info{background:#0b1220;border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:11px;font-size:13px;line-height:1.3}
.info b{display:block;color:#b7ff32;font-size:15px;margin-bottom:4px}
@media(max-width:760px){
  .board{padding:8px}
  .header{grid-template-columns:1fr 1fr;gap:7px}
  .logo{font-size:19px}.logoIcon{width:42px;height:42px}
  .stat{height:42px;font-size:11px}.stat b{font-size:20px}
  .stage{min-height:calc(100vh - 92px)}
  .road{display:none}
  .start{position:relative;left:auto;top:auto;width:115px;height:74px;font-size:30px;margin:8px 0 8px 8px}
  .startSub{position:relative;left:auto;right:auto;top:auto;margin:0 8px 8px;font-size:12px}
  .tiles{padding:8px;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .tile{min-height:118px;padding:11px}
  .owner{font-size:20px}.role{font-size:11px}.game{font-size:10px}.lock{font-size:8px}
  .detail{margin:10px 8px 8px;padding:12px}
  .detail h2{font-size:29px}.detailGame{font-size:14px}
  .infoGrid{grid-template-columns:1fr;gap:8px}
}
</style>
</head>
<body>
<div class="board">
  <div class="header">
    <div class="logo"><div class="logoIcon">☼</div><div>BLENDER<br><span style="font-size:55%;letter-spacing:4px">GAMEBOARD</span></div></div>
    <div class="stat">📅 __SLATE__</div>
    <div class="stat">Games <b>__TOTAL__</b></div>
    <div class="stat">Core <b>__CORE__</b></div>
    <div class="stat">Alt/Chaos <b>__ALTCHAOS__</b></div>
  </div>
  <div class="stage">
    <div class="road"></div>
    <div class="start" onclick="alert('Tap the yellow START area to upload slate data.')">START</div>
    <div class="startSub">Every full-slate game gets an owner tile. Only locked Core / Alt / Chaos owners glow. Private gate formula stays hidden.</div>
    <div id="tiles" class="tiles"></div>
    <div id="detail" class="detail"></div>
  </div>
</div>
<script>
const games = __DATA__;
function tileClass(g){const glow=(g.glow||"").toLowerCase();return glow==="core"?"core":glow==="alt"?"alt":glow==="chaos"?"chaos":"";}
function renderTiles(){
  const root=document.getElementById("tiles"); root.innerHTML="";
  games.forEach((g,i)=>{
    const c=tileClass(g);
    const el=document.createElement("div");
    el.className="tile "+c;
    el.onclick=()=>selectGame(i);
    el.innerHTML=`
      <div class="lock">${c ? "LOCKED OWNER" : "OWNER TILE"}</div>
      <div class="bucket">${g.bucket || ("GAME "+(i+1))}</div>
      <div class="owner">${g.owner || "Pending Owner"}</div>
      <div class="role">${g.role || g.archetype || ""}</div>
      <div class="game">${i+1} · ${g.game || ""} ${g.time ? " · "+g.time : ""}</div>`;
    root.appendChild(el);
  });
}
function selectGame(i){
  const g=games[i]||games[0]||{};
  document.getElementById("detail").innerHTML=`
    <h2>${g.owner || "Pending Owner"}</h2>
    <div class="detailGame">${g.game || ""} ${g.time ? "· "+g.time : ""}</div>
    <div class="infoGrid">
      <div class="info"><b>Archetype</b>${g.archetype || "Pending"}</div>
      <div class="info"><b>Gates Passed</b>${g.gates || "Hidden public view"}</div>
      <div class="info"><b>Pitcher Weakness</b>${g.weakness || "Pending"}</div>
      <div class="info"><b>Lane Type</b>${g.role || g.bucket || "Pending"}</div>
    </div>`;
}
renderTiles(); selectGame(0);
</script>
</body>
</html>
"""
    html = (template
            .replace("__DATA__", payload)
            .replace("__SLATE__", slate)
            .replace("__TOTAL__", str(total))
            .replace("__CORE__", str(core))
            .replace("__ALTCHAOS__", str(alt + chaos)))
    components.html(html, height=960, scrolling=True)
