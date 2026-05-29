
import streamlit as st

CORE_COLOR = "#3b82f6"
ALT_COLOR = "#ef4444"
CHAOS_COLOR = "#22c55e"

def inject_css():
    st.markdown("""
    <style>
    .stApp {
        background:#000;
        color:white;
    }

    .board-title{
        font-size:48px;
        font-weight:900;
        line-height:0.9;
        margin-bottom:20px;
    }

    .start-tile{
        background:#facc15;
        color:black;
        padding:28px;
        border-radius:24px;
        font-size:42px;
        font-weight:900;
        border:6px solid white;
        text-align:left;
        margin-bottom:20px;
    }

    .game-tile{
        background:#071224;
        border-radius:22px;
        padding:20px;
        margin-bottom:16px;
        border:2px solid #1e293b;
    }

    .core-glow{
        box-shadow:0 0 18px #3b82f6;
        border:2px solid #3b82f6;
    }

    .alt-glow{
        box-shadow:0 0 18px #ef4444;
        border:2px solid #ef4444;
    }

    .chaos-glow{
        box-shadow:0 0 18px #22c55e;
        border:2px solid #22c55e;
    }

    .owner-card{
        background:#020817;
        border-radius:24px;
        padding:22px;
        margin-top:12px;
    }
    </style>
    """, unsafe_allow_html=True)


def hero():
    st.markdown('<div class="board-title">THE<br>BLENDER<br>MACHINE</div>', unsafe_allow_html=True)


def start_tile():
    st.markdown(
        '<div class="start-tile">START<br><span style="font-size:20px;">Upload PDF / CSV / XLSX and run Live Public Blender</span></div>',
        unsafe_allow_html=True
    )

    return st.file_uploader(
        "",
        type=["pdf","csv","xlsx"],
        label_visibility="collapsed",
        key="main_upload"
    )


def render_gameboard(results):
    st.subheader("PUBLIC BLENDER BOARD")

    games = results.get("games", [])

    for i, game in enumerate(games):
        style = "core-glow"

        if game.get("type") == "alt":
            style = "alt-glow"

        if game.get("type") == "chaos":
            style = "chaos-glow"

        st.markdown(f'<div class="game-tile {style}">', unsafe_allow_html=True)

        if st.button(
            f"{i+1} · {game['label']}",
            key=f"game_tile_{i}"
        ):
            st.session_state["selected_game"] = game

        st.markdown("</div>", unsafe_allow_html=True)

    selected = st.session_state.get("selected_game")

    if selected:
        st.markdown('<div class="owner-card">', unsafe_allow_html=True)
        st.markdown(f"## {selected.get('owner','Pending')}")
        st.write(f"**Archetype:** {selected.get('archetype','Unknown')}")
        st.write(f"**Pitcher Weakness:** {selected.get('weakness','Unknown')}")
        st.write(f"**Gates Passed:** {selected.get('gates','Hidden')}")
        st.write(f"**Lane:** {selected.get('lane','Unknown')}")
        st.markdown("</div>", unsafe_allow_html=True)
