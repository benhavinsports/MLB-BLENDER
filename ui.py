import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    .stApp{
        background:#000;
        color:white;
    }

    .main .block-container{
        max-width:1100px;
        padding-top:1rem;
    }

    .machine-title{
        font-size:72px;
        line-height:.88;
        font-weight:900;
        margin-bottom:18px;
    }

    .board-shell{
        background:#020817;
        border-radius:32px;
        padding:22px;
        border:2px solid #1e293b;
    }

    .top-track{
        position:relative;
        height:280px;
        border-radius:28px;
        background:#0f172a;
        overflow:hidden;
    }

    .path{
        position:absolute;
        top:90px;
        left:60px;
        right:60px;
        height:95px;
        border:16px solid black;
        border-radius:80px;
    }

    .gate{
        position:absolute;
        width:92px;
        height:92px;
        border-radius:22px;
        display:flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        font-size:11px;
        font-weight:900;
        color:white;
        border:3px solid white;
    }

    .start{
        background:#facc15;
        color:black;
        width:135px;
        height:95px;
        left:0px;
        top:92px;
        font-size:34px;
    }

    .g1{left:180px;top:92px;background:#2563eb;}
    .g2{left:300px;top:92px;background:#ef4444;}
    .g3{left:420px;top:92px;background:#f97316;}
    .g4{left:540px;top:92px;background:#9333ea;}
    .g5{left:660px;top:92px;background:#22c55e;}

    .footer{
        display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:14px;
        margin-top:18px;
    }

    .card{
        background:#071224;
        border-radius:24px;
        padding:18px;
        min-height:180px;
    }

    .core{
        border:2px solid #2563eb;
        box-shadow:0 0 20px #2563eb;
    }

    .alt{
        border:2px solid #ef4444;
        box-shadow:0 0 20px #ef4444;
    }

    .chaos{
        border:2px solid #22c55e;
        box-shadow:0 0 20px #22c55e;
    }

    .pill{
        display:inline-block;
        padding:5px 10px;
        border-radius:999px;
        border:1px solid #22c55e;
        color:#d9f99d;
        font-size:12px;
        margin-bottom:12px;
    }

    @media(max-width:768px){
        .machine-title{
            font-size:48px;
        }

        .footer{
            grid-template-columns:1fr;
        }

        .top-track{
            overflow-x:auto;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_gameboard(results):

    st.markdown('<div class="machine-title">THE<br>BLENDER<br>MACHINE</div>', unsafe_allow_html=True)

    st.markdown('<div class="board-shell">', unsafe_allow_html=True)

    st.markdown('<div class="top-track">', unsafe_allow_html=True)
    st.markdown('<div class="path"></div>', unsafe_allow_html=True)

    gates = [
        ("start","START"),
        ("g1","CORE"),
        ("g2","ALT"),
        ("g3","CHAOS"),
        ("g4","LANE"),
        ("g5","FINAL")
    ]

    for cls,label in gates:
        st.markdown(f'<div class="gate {cls}">{label}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer">', unsafe_allow_html=True)

    cols = st.columns(3)

    cards = [
        ("core","CORE 3",results["core3"][0]),
        ("alt","ALT 3",results["alt3"][0]),
        ("chaos","CHAOS 3",results["chaos3"][0])
    ]

    for i,(cls,title,data) in enumerate(cards):
        with cols[i]:
            st.markdown(f'<div class="card {cls}">', unsafe_allow_html=True)
            st.markdown(f'### {title}')
            st.markdown('<div class="pill">LOCKED OWNER</div>', unsafe_allow_html=True)
            st.markdown(f'## {data["player"]}')
            st.write(data["archetype"])
            st.caption(data["game"])
            st.write(f'Weakness: {data["weakness"]}')
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
