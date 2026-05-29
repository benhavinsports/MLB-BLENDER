
import streamlit as st
import streamlit.components.v1 as components

def inject_css():
    st.markdown('<style>.stApp{background:#000;}.block-container{padding:0!important;max-width:100vw!important;}header,footer,[data-testid="stToolbar"]{display:none!important;}</style>', unsafe_allow_html=True)

def render_board(results):
    st.file_uploader("START", type=["pdf","csv","xlsx"], label_visibility="collapsed")
    html = '''
    <div style="width:100vw;height:100vh;background:#000;padding:6px;font-family:Arial;">
      <div style="position:relative;width:100%;height:100%;border-radius:18px;background:linear-gradient(180deg,#070b12,#020304);border:1px solid rgba(255,255,255,.12);overflow:hidden;">
        <div style="position:absolute;left:12px;top:12px;width:110px;height:70px;background:linear-gradient(160deg,#ffe05b,#f59e0b);border:4px solid white;border-radius:12px;transform:rotate(-6deg);display:flex;align-items:center;justify-content:center;color:white;font-size:28px;font-weight:900;">START</div>
        <div style="position:absolute;left:40px;right:40px;top:120px;height:260px;border:40px solid #000;border-radius:120px;"></div>

        <div style="position:absolute;left:80px;top:130px;width:120px;height:70px;background:#071224;border:3px solid #3b82f6;border-radius:12px;box-shadow:0 0 20px #3b82f6;padding:8px;color:white;">
          <div style="font-size:10px;color:#6aa2ff;font-weight:900;">CORE 1</div>
          <div style="font-size:18px;font-weight:900;">Jakob Marsee</div>
          <div style="font-size:9px;">MIA vs TOR</div>
        </div>

        <div style="position:absolute;left:250px;top:130px;width:120px;height:70px;background:#071224;border:3px solid #3b82f6;border-radius:12px;box-shadow:0 0 20px #3b82f6;padding:8px;color:white;">
          <div style="font-size:10px;color:#6aa2ff;font-weight:900;">CORE 2</div>
          <div style="font-size:18px;font-weight:900;">Dingler</div>
          <div style="font-size:9px;">LAA vs DET</div>
        </div>

        <div style="position:absolute;left:420px;top:130px;width:120px;height:70px;background:#071224;border:3px solid #fb923c;border-radius:12px;box-shadow:0 0 20px #fb923c;padding:8px;color:white;">
          <div style="font-size:10px;color:#ff9c69;font-weight:900;">ALT 1</div>
          <div style="font-size:18px;font-weight:900;">James Wood</div>
          <div style="font-size:9px;">WSH vs CLE</div>
        </div>

        <div style="position:absolute;left:590px;top:130px;width:120px;height:70px;background:#071224;border:3px solid #22c55e;border-radius:12px;box-shadow:0 0 20px #22c55e;padding:8px;color:white;">
          <div style="font-size:10px;color:#7dff9f;font-weight:900;">CHAOS 1</div>
          <div style="font-size:18px;font-weight:900;">Julio</div>
          <div style="font-size:9px;">SEA vs ATH</div>
        </div>
      </div>
    </div>
    '''
    components.html(html, height=760, scrolling=False)
