
import streamlit as st
import streamlit.components.v1 as components

def inject_css():
    st.markdown('<style>.stApp{background:#000;} .block-container{padding:0!important;max-width:100vw!important;}</style>', unsafe_allow_html=True)

def render_board(results):
    st.file_uploader('START', type=['pdf','csv','xlsx'], label_visibility='collapsed')
    html = '''
    <div style="width:100vw;min-height:100vh;background:#000;padding:12px;color:white;font-family:Arial;">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;">
        <div style="background:#071224;border:2px solid #3b82f6;border-radius:18px;padding:16px;box-shadow:0 0 30px #3b82f6;">
          <div style="color:#6aa2ff;font-weight:900;font-size:12px;">CORE 1</div>
          <div style="font-size:28px;font-weight:900;">Jakob Marsee</div>
          <div>Miami vs Toronto</div>
        </div>
        <div style="background:#071224;border:2px solid #fb923c;border-radius:18px;padding:16px;box-shadow:0 0 30px #fb923c;">
          <div style="color:#ff9c69;font-weight:900;font-size:12px;">ALT 1</div>
          <div style="font-size:28px;font-weight:900;">James Wood</div>
          <div>Nationals vs Guardians</div>
        </div>
        <div style="background:#071224;border:2px solid #22c55e;border-radius:18px;padding:16px;box-shadow:0 0 30px #22c55e;">
          <div style="color:#7dff9f;font-weight:900;font-size:12px;">CHAOS 1</div>
          <div style="font-size:28px;font-weight:900;">Julio Rodriguez</div>
          <div>Mariners vs Athletics</div>
        </div>
      </div>
    </div>
    '''
    components.html(html, height=900)
