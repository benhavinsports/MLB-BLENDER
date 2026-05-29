
import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    .stApp{
        background:#000;
        color:white;
    }

    .main .block-container{
        padding-top:1rem;
        max-width:1000px;
    }

    .machine-title{
        font-size:68px;
        font-weight:900;
        line-height:0.88;
        margin-bottom:12px;
    }

    .board-shell{
        background:#020817;
        border:2px solid #1f2937;
        border-radius:28px;
        padding:18px;
        overflow:hidden;
        position:relative;
    }

    .track{
        position:relative;
        width:100%;
        height:430px;
        border-radius:30px;
        background:
        radial-gradient(circle at center,#0f172a 0%, #020617 70%);
    }

    .curve{
        position:absolute;
        left:40px;
        right:40px;
        top:72px;
        height:95px;
        border:18px solid black;
        border-radius:70px;
    }

    .curve2{
        position:absolute;
        left:90px;
        right:90px;
        bottom:92px;
        height:95px;
        border:18px solid black;
        border-radius:70px;
    }

    .gate{
        position:absolute;
        width:86px;
        height:86px;
        border-radius:22px;
        display:flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        color:white;
        font-weight:900;
        font-size:12px;
        border:3px solid white;
        box-shadow:0 0 12px rgba(255,255,255,.22);
    }

    .start{
        background:#facc15;
        color:black;
        font-size:34px;
        width:130px;
        height:92px;
        left:8px;
        top:110px;
        transform:rotate(-8deg);
    }

    .g1{left:155px;top:96px;background:#2563eb;}
    .g2{left:260px;top:96px;background:#ef4444;}
    .g3{left:365px;top:96px;background:#f97316;}
    .g4{left:470px;top:96px;background:#9333ea;}
    .g5{left:575px;top:96px;background:#ef4444;}
    .g6{left:680px;top:96px;background:#f97316;}

    .g17{left:310px;top:250px;background:#22c55e;}
    .g18{left:110px;top:250px;background:#9333ea;}
    .g19{left:110px;top:345px;background:#2563eb;}
    .g20{left:320px;top:345px;background:#f97316;}
    .g21{left:510px;top:345px;background:#ef4444;}
    .g22{left:700px;top:345px;background:#9333ea;}

    .footer-row{
        display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:12px;
        margin-top:18px;
    }

    .owner-card{
        border-radius:20px;
        padding:16px;
        background:#020817;
        min-height:160px;
        border:2px solid #1e293b;
    }

    .core{ box-shadow:0 0 18px #2563eb; border-color:#2563eb;}
    .alt{ box-shadow:0 0 18px #ef4444; border-color:#ef4444;}
    .chaos{ box-shadow:0 0 18px #22c55e; border-color:#22c55e;}

    .pill{
        display:inline-block;
        padding:6px 12px;
        border-radius:999px;
        border:2px solid #22c55e;
        color:#d9f99d;
        font-size:12px;
        font-weight:800;
    }

    button[kind="secondary"]{
        width:100%;
        border-radius:18px;
        min-height:72px;
        font-weight:800;
        font-size:18px;
        background:#071224;
        border:2px solid #1e293b;
        color:white;
    }
    </style>
    """, unsafe_allow_html=True)


def render_board(results):

    st.markdown('<div class="machine-title">THE<br>BLENDER<br>MACHINE</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "",
        type=["pdf","csv","xlsx"],
        label_visibility="collapsed"
    )

    st.markdown('<div class="board-shell"><div class="track">', unsafe_allow_html=True)

    st.markdown('<div class="curve"></div>', unsafe_allow_html=True)
    st.markdown('<div class="curve2"></div>', unsafe_allow_html=True)

    gates = [
        ("start","START"),
        ("g1","Core Matchup"),
        ("g2","Vegas"),
        ("g3","Starter"),
        ("g4","Ballpark"),
        ("g5","Weather"),
        ("g6","Discipline"),
        ("g17","Leverage"),
        ("g18","Lineup"),
        ("g19","Consistency"),
        ("g20","Recent"),
        ("g21","EV"),
        ("g22","Final")
    ]

    for cls,label in gates:
        st.markdown(f'<div class="gate {cls}">{label}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer-row">', unsafe_allow_html=True)

    cols = st.columns(3)

    cards = [
        ("CORE 1 · CLEAN LANE","Dillon Dingler","Primary / Clean Lane","Los Angeles Angels vs Detroit Tigers","core"),
        ("CORE 2 · ALT","Trevor Larnach","Adjacent / Transfer","Minnesota Twins vs Chicago White Sox","alt"),
        ("CORE 3 · WHO","Ezequiel Duran","Chaos / WHO","Houston Astros vs Texas Rangers","chaos")
    ]

    for i,(title,name,arch,matchup,cls) in enumerate(cards):
        with cols[i]:
            st.markdown(f'<div class="owner-card {cls}">', unsafe_allow_html=True)
            st.markdown(f'##### {title}')
            st.markdown('<span class="pill">LOCKED OWNER</span>', unsafe_allow_html=True)
            st.markdown(f'## {name}')
            st.write(arch)
            st.caption(matchup)

            if st.button(f"OPEN GAME", key=f"open_{i}"):
                st.session_state["selected"]=name

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    if "selected" in st.session_state:
        st.markdown(f"""
        ### {st.session_state['selected']}
        - Gates Passed: 18/23
        - Archetype: Pull-side power finisher
        - Weakness Attack: elevated fastballs
        - Lane: clean leverage lane
        """)
