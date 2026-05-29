
import json
import streamlit as st
import streamlit.components.v1 as components


def inject_css():
    st.markdown("""
<style>
.stApp{background:#000;color:#f5eadc;}
.block-container{max-width:1200px!important;padding:1rem .75rem 2rem!important;}
[data-testid="stFileUploader"]{
  background:linear-gradient(160deg,#ffcf33,#f59e0b)!important;
  border:5px solid #fff8ef!important;
  border-radius:22px!important;
  padding:14px!important;
  margin:8px 0 16px!important;
  box-shadow:0 14px 34px rgba(0,0,0,.45)!important;
}
[data-testid="stFileUploader"]::before{
  content:"START";
  display:block;color:#050505;font-size:42px;font-weight:1000;line-height:1;margin-bottom:4px;
}
[data-testid="stFileUploader"]::after{
  content:"Upload PDF / CSV / XLSX or run Live Public Blender";
  display:block;color:#050505;font-size:15px;font-weight:900;margin-top:4px;
}
[data-testid="stFileUploader"] section{
  background:rgba(255,255,255,.22)!important;border:1px solid rgba(0,0,0,.20)!important;border-radius:14px!important;
}
[data-testid="stFileUploader"] button{
  background:#050505!important;color:#fff!important;border-radius:12px!important;font-weight:950!important;
}
</style>
""", unsafe_allow_html=True)


def _default_games():
    return [
        {"label":"Miami Marlins vs Toronto Blue Jays","owner":"Jakob Marsee","bucket":"CORE 1 · CLEAN LANE","role":"Event Owner","pitcher":"Braydon Fisher","time":"7:07 PM ET","archetype":"Clean lane finisher","weakness":"Elevated fastball / pull-air lane","gates":"Passed CORE ownership path"},
        {"label":"Washington Nationals vs Cleveland Guardians","owner":"James Wood","bucket":"CORE 2 · ADJACENT / TRANSFER","role":"Adjacent / Decoy Transfer Owner","pitcher":"Joey Cantillo","time":"6:10 PM ET","archetype":"Adjacent transfer bat","weakness":"Pitch-around / decoy transfer lane","gates":"Passed ALT transfer path"},
        {"label":"Seattle Mariners vs Athletics","owner":"Julio Rodríguez","bucket":"CORE 3 · WHO / CHAOS","role":"WHO / Chaos Owner","pitcher":"Luis Severino","time":"9:40 PM ET","archetype":"WHO / chaos finisher","weakness":"Volatile game flow / bullpen continuation","gates":"Passed chaos path"}
    ]


def _extract_games(results=None):
    if isinstance(results, dict):
        if isinstance(results.get("games"), list) and results["games"]:
            return results["games"]
        out = []
        for key in ["core", "alt", "chaos", "owners"]:
            val = results.get(key)
            if isinstance(val, list):
                for row in val:
                    if isinstance(row, dict):
                        out.append({
                            "label": row.get("game_key") or row.get("game") or row.get("label") or f"Game {len(out)+1}",
                            "owner": row.get("player") or row.get("owner") or "Pending Owner",
                            "bucket": row.get("core_slot") or row.get("bucket") or key.upper(),
                            "role": row.get("core_display_role") or row.get("role") or row.get("archetype") or "Owner",
                            "pitcher": row.get("pitcher") or "Pending",
                            "time": row.get("game_time_et") or "",
                            "archetype": row.get("archetype") or "Pending",
                            "weakness": row.get("weakness") or row.get("final_reason") or "Pending",
                            "gates": row.get("gates") or "Hidden public view"
                        })
        if out:
            return out[:18]
    return _default_games()


def render_board(results=None):
    uploaded = st.file_uploader(
        "START",
        type=["pdf", "csv", "xlsx", "xls", "txt", "md"],
        label_visibility="collapsed",
        key="start_upload_actual"
    )
    if uploaded is not None:
        st.session_state["uploaded_file_name"] = uploaded.name

    games = _extract_games(results or {})
    slate = st.session_state.get("uploaded_file_name", "Today’s Slate")
    data = json.dumps(games).replace("</", "<\\/")
    survivors = min(3, len(games))
    total_hitters = 73

    html = f"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#000;color:#f5eadc;font-family:Inter,Arial,Helvetica,sans-serif;}}
.wrap{{width:100%;max-width:1120px;margin:0 auto;}}
.title{{font-size:clamp(48px,8vw,88px);font-weight:1000;line-height:.88;letter-spacing:2px;margin:4px 0 14px;}}
.title span{{color:#b7ff32}}
.board{{width:100%;position:relative;background:radial-gradient(circle at 50% 32%,rgba(36,70,130,.18),transparent 35%),linear-gradient(180deg,#070b12,#020304);border:1px solid rgba(255,255,255,.11);border-radius:18px;overflow:hidden;box-shadow:0 28px 80px rgba(0,0,0,.75);}}
svg{{width:100%;height:auto;display:block}}
.node,.ownerCard,.finish{{cursor:pointer;transition:.12s ease}}
.node:hover,.ownerCard:hover,.finish:hover{{filter:brightness(1.18);transform:translateY(-2px)}}
#detail{{margin-top:14px;background:#070b12;border:1px solid rgba(255,255,255,.13);border-radius:18px;padding:16px;}}
#detail h2{{margin:0 0 8px;color:#fff;font-size:clamp(28px,5vw,46px);line-height:1;}}
.detailGame{{color:#cbd5e1;font-weight:900;font-size:clamp(14px,2vw,22px);margin-bottom:12px;line-height:1.25}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
.info{{background:#0b1220;border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:12px;font-size:13px;line-height:1.35}}
.info b{{display:block;color:#b7ff32;font-size:16px;margin-bottom:4px}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}#detail{{padding:12px}}}}
</style>
</head>
<body>
<div class="wrap">
<div class="title">THE<br><span>BLENDER</span><br>MACHINE</div>
<div class="board">
<svg viewBox="0 0 1120 720" xmlns="http://www.w3.org/2000/svg">
<defs>
<filter id="blueGlow" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#3b82f6"/></filter>
<filter id="redGlow" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#ef4444"/></filter>
<filter id="greenGlow" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#22c55e"/></filter>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070b12"/><stop offset="1" stop-color="#020304"/></linearGradient>
<linearGradient id="yellow" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe05b"/><stop offset="1" stop-color="#f59e0b"/></linearGradient>
<linearGradient id="blue" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#1d4ed8"/></linearGradient>
<linearGradient id="red" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ef4444"/><stop offset="1" stop-color="#991b1b"/></linearGradient>
<linearGradient id="orange" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fb923c"/><stop offset="1" stop-color="#c2410c"/></linearGradient>
<linearGradient id="purple" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a855f7"/><stop offset="1" stop-color="#6b21a8"/></linearGradient>
<linearGradient id="green" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4ade80"/><stop offset="1" stop-color="#15803d"/></linearGradient>
</defs>
<rect x="4" y="4" width="1112" height="712" rx="20" fill="url(#bg)" stroke="rgba(255,255,255,.12)"/>

<!-- header -->
<rect x="24" y="24" width="52" height="52" rx="12" fill="#0b1220" stroke="rgba(255,255,255,.16)"/>
<text x="50" y="57" fill="#e5e7eb" text-anchor="middle" font-size="26">☼</text>
<text x="92" y="50" fill="#fff" font-size="23" font-weight="1000">BLENDER</text>
<text x="92" y="74" fill="#fff" font-size="14" font-weight="900" letter-spacing="5">GAMEBOARD</text>
<rect x="405" y="24" width="300" height="52" rx="9" fill="#080d16" stroke="rgba(255,255,255,.15)"/>
<text x="555" y="57" fill="#f5eadc" font-size="17" text-anchor="middle" font-weight="900">📅 {slate}</text>
<rect x="724" y="24" width="185" height="52" rx="9" fill="#080d16" stroke="rgba(255,255,255,.15)"/>
<text x="786" y="57" fill="#f5eadc" font-size="15" text-anchor="middle" font-weight="900">Total Hitters</text>
<text x="862" y="59" fill="#78ff7a" font-size="24" text-anchor="middle" font-weight="1000">{total_hitters}</text>
<rect x="928" y="24" width="165" height="52" rx="9" fill="#080d16" stroke="rgba(255,255,255,.15)"/>
<text x="988" y="57" fill="#f5eadc" font-size="15" text-anchor="middle" font-weight="900">Survivors</text>
<text x="1055" y="59" fill="#78ff7a" font-size="24" text-anchor="middle" font-weight="1000">{survivors}</text>

<!-- board road -->
<path d="M128 159 H955 Q1020 159 1020 236 Q1020 313 955 313 H160 Q48 313 48 410 Q48 507 160 507 H892" fill="none" stroke="#000" stroke-width="58" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M128 159 H955 Q1020 159 1020 236 Q1020 313 955 313 H160 Q48 313 48 410 Q48 507 160 507 H892" fill="none" stroke="rgba(255,255,255,.03)" stroke-width="52" stroke-linecap="round" stroke-linejoin="round"/>

<!-- start -->
<g class="node" onclick="selectGame(0)">
<rect x="18" y="122" width="126" height="88" rx="10" fill="url(#yellow)" stroke="#fff" stroke-width="5" transform="rotate(-6 81 166)"/>
<text x="81" y="177" text-anchor="middle" fill="#fff" font-size="35" font-weight="1000" transform="rotate(-6 81 166)">START</text>
</g>

<!-- 22 board tiles -->
{_tile_svg()}

<!-- finish -->
<g class="finish" onclick="selectGame(0)">
<polygon points="950,407 969,447 1012,429 991,471 1034,493 987,499 997,545 950,514 903,545 913,499 866,493 909,471 888,429 931,447" fill="#fbbf24" stroke="#fff" stroke-width="4"/>
<text x="950" y="477" text-anchor="middle" fill="#fff" font-size="26" font-weight="1000">FINISH</text>
<text x="950" y="505" text-anchor="middle" fill="#fff" font-size="16" font-weight="1000">🔒 OWNERS</text>
</g>

<!-- legend -->
<rect x="372" y="286" width="330" height="74" rx="9" fill="rgba(4,8,16,.88)" stroke="rgba(255,255,255,.18)"/>
<circle cx="394" cy="309" r="7" fill="#2563eb"/><text x="410" y="313" fill="#dbe4ef" font-size="11" font-weight="800">Matchup & Environment</text>
<circle cx="558" cy="309" r="7" fill="#ef4444"/><text x="574" y="313" fill="#dbe4ef" font-size="11" font-weight="800">Offense Quality</text>
<circle cx="394" cy="333" r="7" fill="#f97316"/><text x="410" y="337" fill="#dbe4ef" font-size="11" font-weight="800">Plate Discipline</text>
<circle cx="558" cy="333" r="7" fill="#22c55e"/><text x="574" y="337" fill="#dbe4ef" font-size="11" font-weight="800">Power & Contact</text>

<!-- owner cards -->
{_owner_svg()}
</svg>
</div>
<div id="detail"></div>
</div>
<script>
const games = {data};
function short(s,n){{s=s||""; return s.length>n ? s.slice(0,n-1)+"…" : s;}}
function fill(){{
  const c=games[0]||{{}}, a=games[1]||c, w=games[2]||c;
  document.getElementById("coreName").textContent=short(c.owner||"Pending Core",22);
  document.getElementById("coreRole").textContent=short(c.role||c.archetype||"",44);
  document.getElementById("coreMatch").textContent=short((c.label||"")+(c.time?" · "+c.time:""),60);
  document.getElementById("altName").textContent=short(a.owner||"Pending ALT",22);
  document.getElementById("altRole").textContent=short(a.role||a.archetype||"",44);
  document.getElementById("altMatch").textContent=short((a.label||"")+(a.time?" · "+a.time:""),60);
  document.getElementById("chaosName").textContent=short(w.owner||"Pending WHO",22);
  document.getElementById("chaosRole").textContent=short(w.role||w.archetype||"",44);
  document.getElementById("chaosMatch").textContent=short((w.label||"")+(w.time?" · "+w.time:""),60);
}}
function selectGame(i){{
  const g=games[i%games.length]||games[0]||{{}};
  document.getElementById("detail").innerHTML=`
    <h2>${{g.owner||"Pending Owner"}}</h2>
    <div class="detailGame">${{g.label||""}} ${{g.time ? "· "+g.time : ""}}</div>
    <div class="grid">
      <div class="info"><b>Archetype</b>${{g.archetype||"Pending"}}</div>
      <div class="info"><b>Pitcher Weakness</b>${{g.weakness||"Pending"}}</div>
      <div class="info"><b>Gates Passed</b>${{g.gates||"Hidden public view"}}</div>
      <div class="info"><b>Lane / Role</b>${{g.role||g.bucket||"Pending"}}</div>
    </div>`;
}}
fill(); selectGame(0);
</script>
</body>
</html>
"""
    components.html(html, height=880, scrolling=True)


def _tile_svg():
    specs = [
        (0,1,152,125,"blue","Core","Matchup"), (1,2,268,125,"red","Vegas","Screen"), (2,3,384,125,"orange","Starter","Screen"),
        (0,4,500,125,"purple","Ballpark","Gate"), (1,5,616,125,"red","Weather","Gate"), (2,6,732,125,"orange","Plate","Discipline"),
        (0,7,850,206,"blue","Hard Hit","% Gate"), (1,8,928,276,"green","Barrel","% Gate"), (2,9,868,358,"purple","wOBA","Gate"),
        (0,10,762,386,"green","xwOBA","Gate"), (1,11,650,315,"red","ISO","Power"), (2,12,536,315,"green","Pitches","Per PA"),
        (0,13,422,315,"purple","Swing","% Gate"), (1,14,308,315,"blue","Chase","% Gate"), (2,15,194,315,"orange","K %","Contact"),
        (0,16,80,315,"red","Batted Ball","Profile"), (1,17,66,410,"green","Clutch /","Leverage"), (2,18,178,450,"purple","Lineup","Position"),
        (0,19,292,450,"blue","Consistency","Gate"), (1,20,406,450,"orange","Recent","Form"), (2,21,520,450,"red","Fade / Low","EV Filter"),
        (0,22,634,450,"purple","Final","Survivor"),
    ]
    out = []
    for game_i, num, x, y, color, a, b in specs:
        out.append(f"""
<g class="node" onclick="selectGame({game_i})">
<rect x="{x}" y="{y}" width="104" height="74" rx="8" fill="url(#{color})" stroke="#fff" stroke-width="4"/>
<circle cx="{x+52}" cy="{y+21}" r="15" fill="#fff"/>
<text x="{x+52}" y="{y+26}" text-anchor="middle" fill="#111" font-size="13" font-weight="1000">{num}</text>
<text x="{x+52}" y="{y+50}" text-anchor="middle" fill="#fff" font-size="11" font-weight="1000">{a}</text>
<text x="{x+52}" y="{y+66}" text-anchor="middle" fill="#fff" font-size="11" font-weight="1000">{b}</text>
</g>""")
    return "\n".join(out)


def _owner_svg():
    return """
<g class="ownerCard" onclick="selectGame(0)" filter="url(#blueGlow)">
<rect x="15" y="558" width="348" height="105" rx="10" fill="#071224" stroke="#2563eb" stroke-width="2"/>
<text x="36" y="585" fill="#6aa2ff" font-size="12" font-weight="1000" letter-spacing="1">CORE 1 · CLEAN LANE</text>
<rect x="258" y="574" width="82" height="21" rx="10" fill="rgba(34,197,94,.18)" stroke="#69f08a"/>
<text x="299" y="588" fill="#d9ffdd" font-size="9" font-weight="1000" text-anchor="middle">LOCKED OWNER</text>
<text id="coreName" x="36" y="616" fill="#fff" font-size="25" font-weight="1000"></text>
<text id="coreRole" x="36" y="638" fill="#dbe4ef" font-size="12" font-weight="800"></text>
<text id="coreMatch" x="36" y="655" fill="#b7c1d1" font-size="10"></text>
</g>
<g class="ownerCard" onclick="selectGame(1)" filter="url(#redGlow)">
<rect x="386" y="558" width="348" height="105" rx="10" fill="#071224" stroke="#ef4444" stroke-width="2"/>
<text x="407" y="585" fill="#ff6872" font-size="12" font-weight="1000" letter-spacing="1">CORE 2 · ADJACENT / TRANSFER</text>
<rect x="629" y="574" width="82" height="21" rx="10" fill="rgba(34,197,94,.18)" stroke="#69f08a"/>
<text x="670" y="588" fill="#d9ffdd" font-size="9" font-weight="1000" text-anchor="middle">LOCKED OWNER</text>
<text id="altName" x="407" y="616" fill="#fff" font-size="25" font-weight="1000"></text>
<text id="altRole" x="407" y="638" fill="#dbe4ef" font-size="12" font-weight="800"></text>
<text id="altMatch" x="407" y="655" fill="#b7c1d1" font-size="10"></text>
</g>
<g class="ownerCard" onclick="selectGame(2)" filter="url(#greenGlow)">
<rect x="757" y="558" width="348" height="105" rx="10" fill="#071224" stroke="#22c55e" stroke-width="2"/>
<text x="778" y="585" fill="#78ff98" font-size="12" font-weight="1000" letter-spacing="1">CORE 3 · WHO / CHAOS</text>
<rect x="1000" y="574" width="82" height="21" rx="10" fill="rgba(34,197,94,.18)" stroke="#69f08a"/>
<text x="1041" y="588" fill="#d9ffdd" font-size="9" font-weight="1000" text-anchor="middle">LOCKED OWNER</text>
<text id="chaosName" x="778" y="616" fill="#fff" font-size="25" font-weight="1000"></text>
<text id="chaosRole" x="778" y="638" fill="#dbe4ef" font-size="12" font-weight="800"></text>
<text id="chaosMatch" x="778" y="655" fill="#b7c1d1" font-size="10"></text>
</g>
"""
