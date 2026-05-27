
import streamlit as st
def inject_css():
    st.markdown("""<style>.stApp{background:#050505;color:#f6eee6}.card{border:1px solid #2a2a2a;border-radius:22px;padding:22px;margin:16px 0;background:#101010}.badge{display:inline-block;border:2px solid #9cff57;border-radius:16px;padding:8px 13px;color:#ddffc8;background:#122900;font-weight:900}.name{font-size:34px;font-weight:950;color:#fff1e8}.role{font-size:20px;font-weight:800;color:#fff1e8;margin-top:8px}.sub{font-size:18px;color:#c8c0bb;margin-top:10px}.score{font-size:15px;color:#9cff57;margin-top:8px;font-weight:800}.kill{color:#ff7777}.pass{color:#9cff57}</style>""",unsafe_allow_html=True)
def render_card(c, show_path=False):
    st.markdown(f"""<div class="card"><div style="display:flex;justify-content:space-between;gap:10px;"><div><div class="name">{c.get('player','')}</div><div class="role">{c.get('role','Owner')}</div><div class="sub">{c.get('game','')} · vs {c.get('pitcher','')}</div><div class="score">Survivor score: {float(c.get('final_score',c.get('raw_score',0))):.1f} · target: {c.get('target_archetype','')}</div></div><div class="badge">LOCKED OWNER</div></div></div>""",unsafe_allow_html=True)
    if show_path:
        with st.expander("Gate path — "+str(c.get("player",""))):
            for g in c.get("gate_path",[]):
                st.markdown(f"<div class={'kill' if 'KILL' in g else 'pass'}>{g}</div>",unsafe_allow_html=True)
            if c.get("transfer_notes"): st.write(c.get("transfer_notes"))
def section(title,cards):
    st.subheader(title)
    for c in cards: render_card(c, True)
def render_results(r):
    st.caption(r.get("engine_version","")); st.success(r.get("message",""))
    section("CORE 3 — TRUE EVENT OWNERS", r.get("core",[]))
    section("ALT 3 — NEXT SURVIVORS", r.get("alt",[]))
    section("CHAOS 3 — ENTROPY OWNERS", r.get("chaos",[]))
    st.subheader("ALL GAME OWNERS")
    for o in r.get("owners",[]): render_card(o["owner"], False)
