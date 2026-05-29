
import json
import streamlit as st
import streamlit.components.v1 as components

def inject_css():
    st.markdown("""
<style>
.stApp{background:#000;color:#f5eadc;}
.block-container{max-width:1120px!important;padding-top:1rem!important;padding-left:.75rem!important;padding-right:.75rem!important;}
[data-testid="stFileUploader"]{
    background:linear-gradient(160deg,#ffcf33,#f59e0b)!important;
    border:4px solid #fff8ee!important;
    border-radius:22px!important;
    padding:16px!important;
    margin-bottom:16px!important;
    box-shadow:0 14px 34px rgba(0,0,0,.45)!important;
}
[data-testid="stFileUploader"]::before{
    content:"START";
    display:block;
    color:#050505;
    font-size:42px;
    font-weight:1000;
    line-height:1;
    margin-bottom:6px;
}
[data-testid="stFileUploader"]::after{
    content:"Upload slate file or run Live Public Blender";
    display:block;
    color:#050505;
    font-size:15px;
    font-weight:900;
    margin-top:4px;
}
[data-testid="stFileUploader"] section{
    background:rgba(255,255,255,.24)!important;
    border:1px solid rgba(0,0,0,.20)!important;
    border-radius:14px!important;
}
[data-testid="stFileUploader"] button{
    background:#050505!important;
    color:#fff!important;
    border-radius:12px!important;
    font-weight:900!important;
}
</style>
""", unsafe_allow_html=True)

def _default_games():
    # Demo board data. UI reads actual slate later when engine/feed is connected.
    return [
        {
            "label": "Miami Marlins vs Toronto Blue Jays",
            "owner": "Jakob Marsee",
            "bucket": "CORE 1 · CLEAN LANE",
            "role": "Event Owner",
            "pitcher": "Braydon Fisher",
            "time": "7:07 PM ET",
            "glow": "core",
            "archetype": "Clean lane finisher",
            "weakness": "Pitcher lane leak / elevated damage",
            "gates": "Passed board path"
        },
        {
            "label": "Washington Nationals vs Cleveland Guardians",
            "owner": "James Wood",
            "bucket": "CORE 2 · ADJACENT / DECOY TRANSFER",
            "role": "Adjacent / Decoy Transfer Owner",
            "pitcher": "Joey Cantillo",
            "time": "6:10 PM ET",
            "glow": "alt",
            "archetype": "Adjacent transfer bat",
            "weakness": "Pitch-around / matchup transfer lane",
            "gates": "Passed transfer path"
        },
        {
            "label": "Seattle Mariners vs Athletics",
            "owner": "Julio Rodríguez",
            "bucket": "CORE 3 · WHO / CHAOS",
            "role": "WHO / Chaos Owner",
            "pitcher": "Luis Severino",
            "time": "9:40 PM ET",
            "glow": "chaos",
            "archetype": "WHO / chaos finisher",
            "weakness": "Volatile game flow / bullpen lane",
            "gates": "Passed chaos path"
        }
    ]

def _games_from_session():
    # If future feed stores games, use it. Otherwise fall back to demo.
    try:
        import pandas as pd
        df = st.session_state.get("feed_df")
        if df is not None and not df.empty:
            games = []
            if "game_key" in df.columns:
                vals = []
                for v in df["game_key"].dropna().astype(str).tolist():
                    if v and v not in vals and v.lower() not in {"nan", "none"}:
                        vals.append(v)
                for i, v in enumerate(vals[:18]):
                    games.append({
                        "label": v,
                        "owner": "Pending Owner",
                        "bucket": f"GAME {i+1}",
                        "role": "Run Blender to lock owner",
                        "pitcher": "Pending",
                        "time": "",
                        "glow": ["core","alt","chaos"][i % 3],
                        "archetype": "Pending",
                        "weakness": "Pending",
                        "gates": "Pending"
                    })
            if games:
                return games
    except Exception:
        pass
    return _default_games()

def render_board(results=None):
    games = _games_from_session()
    if results and isinstance(results, dict):
        # Optional direct override
        if isinstance(results.get("games"), list) and results.get("games"):
            games = results["games"]

    total_hitters = 73
    survivors = 3
    selected_name = st.session_state.get("uploaded_file_name", "Today’s Slate")
    data_json = json.dumps(games).replace("</", "<\\/")

    html = f"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{{box-sizing:border-box}}
body{{
  margin:0;
  background:#000;
  color:#f5eadc;
  font-family:Inter,Arial,Helvetica,sans-serif;
}}
.machine{{
  width:100%;
  max-width:1040px;
  margin:0 auto;
}}
.title{{
  font-size:clamp(42px,8vw,82px);
  font-weight:1000;
  line-height:.88;
  letter-spacing:1px;
  margin:6px 0 16px;
}}
.title .lime{{color:#b7ff32}}
.board{{
  position:relative;
  width:100%;
  aspect-ratio: 1040 / 690;
  background:
    radial-gradient(circle at 40% 40%,rgba(35,75,145,.16),transparent 28%),
    linear-gradient(180deg,#070b12,#020304);
  border:1px solid rgba(255,255,255,.10);
  border-radius:16px;
  overflow:hidden;
  box-shadow:0 26px 80px rgba(0,0,0,.75);
}}
.header{{
  position:absolute;
  left:1.4%; right:1.4%; top:2%;
  height:8%;
  display:grid;
  grid-template-columns: 31% 27% 18% 18%;
  gap:1.7%;
  align-items:center;
}}
.logo{{
  display:flex;align-items:center;gap:10px;font-weight:1000;font-size:clamp(12px,2vw,23px);line-height:.95;
}}
.logoIcon{{
  width:42px;height:42px;border-radius:12px;border:1px solid rgba(255,255,255,.14);
  display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.04)
}}
.stat{{
  height:100%;
  border:1px solid rgba(255,255,255,.12);
  border-radius:9px;
  background:rgba(5,10,18,.75);
  display:flex;align-items:center;justify-content:center;gap:8px;
  font-size:clamp(9px,1.4vw,14px);
  font-weight:900;
  text-align:center;
}}
.stat b{{color:#78ff7a;font-size:clamp(13px,2.1vw,22px)}}

.road{{
  position:absolute;
  background:#000;
  border-radius:999px;
  box-shadow:inset 0 0 0 2px rgba(255,255,255,.03);
}}
.r1{{left:10%;right:7%;top:17%;height:10%;}}
.r2{{left:5%;right:20%;top:39%;height:10%;}}
.r3{{left:21%;right:14%;top:58%;height:10%;}}
.turn1{{right:2.6%;top:17%;width:15%;height:32%;border-radius:50%;background:transparent;border:44px solid #000;border-left-color:transparent;border-bottom-color:transparent;}}
.turn2{{left:1.5%;top:39%;width:15%;height:28%;border-radius:50%;background:transparent;border:42px solid #000;border-right-color:transparent;border-top-color:transparent;}}

.tile{{
  position:absolute;
  width:12.7%;
  height:11.2%;
  border-radius:12px;
  border:3px solid rgba(255,255,255,.92);
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;
  font-weight:1000;
  font-size:clamp(7px,1.25vw,13px);
  line-height:1.05;
  color:#fff;
  text-shadow:0 2px 4px rgba(0,0,0,.55);
  cursor:pointer;
  transition:.15s ease;
  box-shadow:0 5px 12px rgba(0,0,0,.32);
}}
.tile:hover{{transform:translateY(-2px) scale(1.02);filter:brightness(1.12)}}
.tile .num{{
  position:absolute;
  top:5px;
  left:50%;
  transform:translateX(-50%);
  width:24px;height:24px;
  border-radius:50%;
  background:#fff;color:#111;
  display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:1000;text-shadow:none;
}}
.tile .txt{{padding-top:15px}}
.start{{
  left:1.2%;top:14.8%;
  width:12.8%;height:13.5%;
  background:linear-gradient(160deg,#ffcf30,#f59e0b);
  color:#fff;
  font-size:clamp(18px,3.2vw,39px);
  transform:rotate(-5deg);
}}
.blue{{background:linear-gradient(160deg,#2563eb,#1d4ed8)}}
.red{{background:linear-gradient(160deg,#e33a45,#9f151e)}}
.orange{{background:linear-gradient(160deg,#f97316,#bd450a)}}
.purple{{background:linear-gradient(160deg,#9333ea,#5b21b6)}}
.green{{background:linear-gradient(160deg,#22c55e,#15803d)}}

.g1{{left:14.4%;top:15%}} .g2{{left:26.7%;top:15%}} .g3{{left:39.1%;top:15%}}
.g4{{left:51.5%;top:15%}} .g5{{left:63.9%;top:15%}} .g6{{left:76.3%;top:15%}}
.g7{{left:78.5%;top:30%}} .g8{{left:86.4%;top:35%}}
.g9{{left:85.6%;top:46.8%}} .g10{{left:78.4%;top:57.2%}}
.g11{{left:66.3%;top:47.5%}} .g12{{left:54%;top:47.5%}} .g13{{left:41.8%;top:47.5%}}
.g14{{left:29.5%;top:47.5%}} .g15{{left:17.3%;top:47.5%}} .g16{{left:7.4%;top:50.5%}}
.g17{{left:8.5%;top:63.5%}} .g18{{left:20.8%;top:64.5%}} .g19{{left:33.1%;top:64.5%}}
.g20{{left:45.5%;top:64.5%}} .g21{{left:57.8%;top:64.5%}} .g22{{left:70.2%;top:64.5%}}
.finish{{
  position:absolute;right:1.4%;top:55.8%;
  width:15%;height:18%;
  clip-path:polygon(50% 0%,61% 30%,95% 16%,78% 48%,100% 62%,66% 67%,70% 100%,50% 78%,30% 100%,34% 67%,0 62%,22% 48%,5% 16%,39% 30%);
  background:linear-gradient(160deg,#fff176,#fbbf24);
  color:white;
  display:flex;align-items:center;justify-content:center;text-align:center;
  font-size:clamp(10px,2vw,24px);
  font-weight:1000;
  text-shadow:0 2px 4px rgba(0,0,0,.35);
}}

.legend{{
  position:absolute;left:34%;top:43.2%;
  width:31%;height:10%;
  border:1px solid rgba(255,255,255,.18);
  background:rgba(4,8,16,.86);
  border-radius:9px;
  display:grid;grid-template-columns:1fr 1fr;
  padding:8px 12px;
  gap:4px 10px;
  font-size:clamp(7px,1vw,11px);
  font-weight:800;
}}
.dot{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-2px}}

.cards{{
  position:absolute;
  left:1.4%;right:1.4%;bottom:5.2%;
  height:19%;
  display:grid;
  grid-template-columns:1fr 1fr 1fr;
  gap:1.2%;
}}
.card{{
  border:1px solid rgba(255,255,255,.14);
  border-radius:9px;
  background:rgba(2,8,20,.92);
  padding:10px 12px;
  overflow:hidden;
}}
.card.core{{border-top:4px solid #2563eb;box-shadow:0 0 16px rgba(37,99,235,.32)}}
.card.alt{{border-top:4px solid #ef4444;box-shadow:0 0 16px rgba(239,68,68,.32)}}
.card.chaos{{border-top:4px solid #22c55e;box-shadow:0 0 16px rgba(34,197,94,.32)}}
.kicker{{font-size:clamp(8px,1.1vw,12px);font-weight:1000;letter-spacing:.6px;margin-bottom:6px}}
.name{{font-size:clamp(13px,2.1vw,24px);font-weight:1000;color:#fff;margin-bottom:2px}}
.role{{font-size:clamp(8px,1.1vw,12px);font-weight:900;color:#dbe4ef}}
.match{{font-size:clamp(7px,1vw,11px);color:#b7c1d1;line-height:1.25;margin-top:3px}}
.vs{{font-size:clamp(7px,1vw,11px);font-weight:900;margin-top:4px}}
.pill{{float:right;border-radius:999px;border:1px solid rgba(105,240,138,.62);padding:2px 7px;color:#d9ffdd;font-size:clamp(7px,.9vw,10px);font-weight:1000}}

.footer{{
  position:absolute;left:0;right:0;bottom:0;height:4%;
  background:rgba(2,6,12,.95);
  border-top:1px solid rgba(255,255,255,.10);
  display:grid;grid-template-columns:repeat(5,1fr);
  font-size:clamp(6px,.9vw,10px);
  color:#b7c1d1;
  align-items:center;text-align:center;font-weight:800;
}}

.detail{{
  margin-top:14px;
  background:#070b12;
  border:1px solid rgba(255,255,255,.13);
  border-radius:16px;
  padding:14px;
}}
.detail h2{{margin:0 0 6px;font-size:24px}}
.detailGrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}}
.info{{background:#0c1220;border:1px solid rgba(255,255,255,.10);border-radius:12px;padding:10px;font-size:13px}}
.info b{{display:block;color:#b7ff32;margin-bottom:3px}}

@media(max-width:720px){{
  .board{{aspect-ratio:1040/780}}
  .header{{grid-template-columns:1fr 1fr; height:14%;}}
  .logo{{font-size:16px}}
  .stat{{font-size:10px}}
  .r1{{top:21%}} .turn1{{top:21%}} .r2{{top:43%}} .turn2{{top:43%}} .r3{{top:62%}}
  .start{{top:18.8%}}
  .g1,.g2,.g3,.g4,.g5,.g6{{top:19%}}
  .g7{{top:34%}} .g8{{top:39%}} .g9{{top:50.8%}} .g10{{top:61.2%}}
  .g11,.g12,.g13,.g14,.g15{{top:51.5%}} .g16{{top:54.5%}}
  .g17{{top:67.5%}} .g18,.g19,.g20,.g21,.g22{{top:68.5%}}
  .finish{{top:59.8%}}
  .legend{{top:47%;left:32%;width:35%;font-size:7px;padding:5px}}
  .cards{{position:relative;left:auto;right:auto;bottom:auto;height:auto;display:grid;grid-template-columns:1fr;gap:10px;margin-top:12px}}
  .card{{min-height:115px;border-radius:12px}}
  .footer{{display:none}}
  .detailGrid{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="machine">
  <div class="title">THE<br><span class="lime">BLENDER</span><br>MACHINE</div>
  <div class="board">
    <div class="header">
      <div class="logo"><div class="logoIcon">☼</div><div>BLENDER<br><span style="font-size:60%;letter-spacing:2px">GAMEBOARD</span></div></div>
      <div class="stat">📅 {selected_name}</div>
      <div class="stat">Total Hitters <b>{total_hitters}</b></div>
      <div class="stat">Survivors <b>{survivors}</b></div>
    </div>

    <div class="road r1"></div><div class="road turn1"></div><div class="road r2"></div><div class="road turn2"></div><div class="road r3"></div>

    <div class="tile start" onclick="selectGame(0)">START</div>
    <div class="tile blue g1" onclick="selectGame(0)"><div class="num">1</div><div class="txt">Core<br>Matchup</div></div>
    <div class="tile red g2" onclick="selectGame(1)"><div class="num">2</div><div class="txt">Vegas<br>Screen</div></div>
    <div class="tile orange g3" onclick="selectGame(2)"><div class="num">3</div><div class="txt">Starter<br>Screen</div></div>
    <div class="tile purple g4" onclick="selectGame(0)"><div class="num">4</div><div class="txt">Ballpark<br>Gate</div></div>
    <div class="tile red g5" onclick="selectGame(1)"><div class="num">5</div><div class="txt">Weather<br>Gate</div></div>
    <div class="tile orange g6" onclick="selectGame(2)"><div class="num">6</div><div class="txt">Plate<br>Discipline</div></div>
    <div class="tile blue g7" onclick="selectGame(0)"><div class="num">7</div><div class="txt">Hard Hit<br>% Gate</div></div>
    <div class="tile green g8" onclick="selectGame(1)"><div class="num">8</div><div class="txt">Barrel<br>% Gate</div></div>
    <div class="tile purple g9" onclick="selectGame(2)"><div class="num">9</div><div class="txt">wOBA<br>Gate</div></div>
    <div class="tile green g10" onclick="selectGame(0)"><div class="num">10</div><div class="txt">xwOBA<br>Gate</div></div>
    <div class="tile red g11" onclick="selectGame(1)"><div class="num">11</div><div class="txt">ISO<br>Power</div></div>
    <div class="tile green g12" onclick="selectGame(2)"><div class="num">12</div><div class="txt">Pitches<br>Per PA</div></div>
    <div class="tile purple g13" onclick="selectGame(0)"><div class="num">13</div><div class="txt">Swing<br>% Gate</div></div>
    <div class="tile blue g14" onclick="selectGame(1)"><div class="num">14</div><div class="txt">Chase<br>% Gate</div></div>
    <div class="tile orange g15" onclick="selectGame(2)"><div class="num">15</div><div class="txt">K %<br>Contact</div></div>
    <div class="tile red g16" onclick="selectGame(0)"><div class="num">16</div><div class="txt">Batted Ball<br>Profile</div></div>
    <div class="tile green g17" onclick="selectGame(1)"><div class="num">17</div><div class="txt">Clutch /<br>Leverage</div></div>
    <div class="tile purple g18" onclick="selectGame(2)"><div class="num">18</div><div class="txt">Lineup<br>Position</div></div>
    <div class="tile blue g19" onclick="selectGame(0)"><div class="num">19</div><div class="txt">Consistency<br>Gate</div></div>
    <div class="tile orange g20" onclick="selectGame(1)"><div class="num">20</div><div class="txt">Recent<br>Form</div></div>
    <div class="tile red g21" onclick="selectGame(2)"><div class="num">21</div><div class="txt">Fade / Low<br>EV Filter</div></div>
    <div class="tile purple g22" onclick="selectGame(0)"><div class="num">22</div><div class="txt">Final<br>Survivor</div></div>
    <div class="finish" onclick="selectGame(0)">FINISH<br>🔒<br>OWNERS</div>

    <div class="legend">
      <div><span class="dot" style="background:#2563eb"></span>Matchup & Environment</div>
      <div><span class="dot" style="background:#ef4444"></span>Offense Quality</div>
      <div><span class="dot" style="background:#f97316"></span>Plate Discipline</div>
      <div><span class="dot" style="background:#22c55e"></span>Power & Contact</div>
      <div><span class="dot" style="background:#9333ea"></span>Context & Consistency</div>
      <div>🔒 Final Selection</div>
    </div>

    <div class="cards">
      <div class="card core" onclick="selectGame(0)">
        <div class="kicker" style="color:#6aa2ff">CORE 1 · CLEAN LANE <span class="pill">LOCKED OWNER</span></div>
        <div class="name" id="coreName">—</div>
        <div class="role" id="coreRole"></div>
        <div class="match" id="coreMatch"></div>
        <div class="vs" style="color:#88b5ff" id="coreVs"></div>
      </div>
      <div class="card alt" onclick="selectGame(1)">
        <div class="kicker" style="color:#ff6872">CORE 2 · ADJACENT / TRANSFER <span class="pill">LOCKED OWNER</span></div>
        <div class="name" id="altName">—</div>
        <div class="role" id="altRole"></div>
        <div class="match" id="altMatch"></div>
        <div class="vs" style="color:#ff6872" id="altVs"></div>
      </div>
      <div class="card chaos" onclick="selectGame(2)">
        <div class="kicker" style="color:#78ff98">CORE 3 · WHO / CHAOS <span class="pill">LOCKED OWNER</span></div>
        <div class="name" id="chaosName">—</div>
        <div class="role" id="chaosRole"></div>
        <div class="match" id="chaosMatch"></div>
        <div class="vs" style="color:#78ff98" id="chaosVs"></div>
      </div>
    </div>

    <div class="footer">
      <div>🧾 Blender Engine v0222</div><div>🛡 23-Gate Progression</div><div>🔒 Immutable Mapping</div><div>👥 73 Hitters Processed</div><div>✅ Owners Locked</div>
    </div>
  </div>
  <div class="detail" id="detail"></div>
</div>

<script>
const games = {data_json};

function fillCards(){{
  const core = games[0] || {{}};
  const alt = games[1] || games[0] || {{}};
  const chaos = games[2] || games[0] || {{}};

  document.getElementById("coreName").innerText = core.owner || "Pending Core";
  document.getElementById("coreRole").innerText = core.role || core.archetype || "";
  document.getElementById("coreMatch").innerText = (core.label || "") + (core.time ? " · " + core.time : "");
  document.getElementById("coreVs").innerText = core.pitcher ? "vs " + core.pitcher : "";

  document.getElementById("altName").innerText = alt.owner || "Pending ALT";
  document.getElementById("altRole").innerText = alt.role || alt.archetype || "";
  document.getElementById("altMatch").innerText = (alt.label || "") + (alt.time ? " · " + alt.time : "");
  document.getElementById("altVs").innerText = alt.pitcher ? "vs " + alt.pitcher : "";

  document.getElementById("chaosName").innerText = chaos.owner || "Pending WHO";
  document.getElementById("chaosRole").innerText = chaos.role || chaos.archetype || "";
  document.getElementById("chaosMatch").innerText = (chaos.label || "") + (chaos.time ? " · " + chaos.time : "");
  document.getElementById("chaosVs").innerText = chaos.pitcher ? "vs " + chaos.pitcher : "";
}}

function selectGame(i){{
  const g = games[i % games.length] || games[0] || {{}};
  document.getElementById("detail").innerHTML = `
    <h2>${{g.owner || "Pending Owner"}}</h2>
    <div style="color:#b7c1d1;font-weight:800">${{g.label || ""}} ${{g.time ? "· " + g.time : ""}}</div>
    <div class="detailGrid">
      <div class="info"><b>Archetype</b>${{g.archetype || "Pending"}}</div>
      <div class="info"><b>Pitcher Weakness</b>${{g.weakness || "Pending"}}</div>
      <div class="info"><b>Gates Passed</b>${{g.gates || "Hidden public view"}}</div>
      <div class="info"><b>Lane / Role</b>${{g.role || g.bucket || "Pending"}}</div>
    </div>
  `;
}}
fillCards();
selectGame(0);
</script>
</body>
</html>
    """
    components.html(html, height=850, scrolling=True)
