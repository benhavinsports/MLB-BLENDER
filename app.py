import streamlit as st
from ui import inject_css, render_board
from feeder import read_feed
from engine import run_true_blender

st.set_page_config(
    page_title="Blender Gameboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

uploaded = st.file_uploader(
    "START",
    type=["pdf", "csv", "xlsx", "xls"],
    label_visibility="collapsed",
    key="start_upload",
)

# Real visible run control. It does NOT rely on hidden overlay or stored dataframe.
# On click, it reparses the current uploaded file and runs the engine immediately.
st.markdown('<div class="run-box">', unsafe_allow_html=True)
run_clicked = st.button(
    "🔥 RUN BLENDER",
    key="run_blender_real_button",
    use_container_width=True,
)
st.markdown('</div>', unsafe_allow_html=True)

if uploaded is not None:
    st.session_state["uploaded_file_name"] = uploaded.name
    if not st.session_state.get("run_status"):
        st.session_state["run_status"] = "PDF loaded. Press RUN BLENDER."

if run_clicked:
    if uploaded is None:
        st.session_state["blender_error"] = "Upload a slate PDF with START first."
        st.session_state["run_status"] = "No PDF uploaded."
    else:
        try:
            st.session_state["run_status"] = "Running Blender..."
            st.session_state["blender_error"] = ""
            parsed_df = read_feed(uploaded.name, uploaded.getvalue())
            st.session_state["parsed_feed_rows"] = int(len(parsed_df)) if hasattr(parsed_df, "__len__") else 0
            results = run_true_blender(parsed_df)
            st.session_state["blender_results"] = results
            st.session_state["run_status"] = "Blender complete."
        except Exception as e:
            st.session_state["blender_error"] = f"Blender run error: {e}"
            st.session_state["run_status"] = "Blender failed."

render_board(st.session_state.get("blender_results", {}))
